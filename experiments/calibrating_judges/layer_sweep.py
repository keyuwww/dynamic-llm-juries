#!/usr/bin/env python
"""How does the probe change across layers, and how does the validation split choose a layer?

For one cheap judge L, at every saved layer: train the probe exactly as in cascade_eval.py (pooled BFF + RewardBench-2 Safety + JudgeBench, 5 folds by question) and record
  val_brier_fold{k}   the Brier score on the validation split inside training fold k (the quantity the validation rule minimises to pick a layer)
  per benchmark: pts = accuracy points above random escalation when the 20% least-trusted verdicts go to the stronger judge (the cascade measure of the README),
                 test_brier and auroc of the out-of-fold probe output for 'this verdict is right'.
The data is loaded once; the folds and validation splits are the same for every layer (same random stream as cascade_eval.oof_probe). Run it niced with few threads: it is CPU-bound."""
import argparse, json, os, sys
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
from evaluate import train_probe, predict
from metrics import brier
from cascade_eval import gen, load_run, curve, BENCH


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--low", required=True); ap.add_argument("--high", required=True); ap.add_argument("--results", default="local_results")
    ap.add_argument("--judgments-bff", default="../tinker_pool_8models_judgments_bff.jsonl"); ap.add_argument("--judgments-rb2", default="../tinker_pool_8models_judgments.jsonl")
    ap.add_argument("--threads", type=int, default=2); ap.add_argument("--seed", type=int, default=0); ap.add_argument("--out", default="results_layer_sweep")
    a = ap.parse_args(); torch.set_num_threads(a.threads); os.makedirs(a.out, exist_ok=True)
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "role_conditioned_panels")); from data import load_judgments; from audit import match_matrix
    A, Y, G, ids, bench_of, ctx = [], [], [], [], [], {}
    for b in BENCH:
        _, p = load_run(a.results, a.low, b, "uncertainty__n1_t0.0"); itm = pd.read_csv(f"{p}_items.csv", dtype={"item_id": str}); L = gen(f"{p}_gen.jsonl").set_index("item_id").loc[itm["item_id"]]
        A.append(np.load(f"{p}_acts.npy")); Y.append(L["correct"].values.astype(int)); G += [f"{b}|{x}" for x in itm["group"].astype(str)]; ids += list(itm["item_id"]); bench_of += [b] * len(itm); layers = json.load(open(f"{p}_layers.json"))
        ok_l = L["correct"].values.astype(int); parsed = L["verdict"].notna().values
        if b == "judgebench":                                                    # stronger judge: the other hosted reasoning judge
            _, ph = load_run(a.results, a.high, b, "uncertainty__n1_t0.0"); ok_h = gen(f"{ph}_gen.jsonl").set_index("item_id").loc[itm["item_id"], "correct"].values.astype(int)
        else:                                                                    # stronger judge: the saved top-3 vote of the 8-judge pool
            d = load_judgments(a.judgments_bff if b == "bff" else a.judgments_rb2, b, condition="none"); C = match_matrix(d.Z, d.Y).astype(int); idx = {i: k for k, i in enumerate(d.item_ids)}
            sel = np.array([idx[i] for i in itm["item_id"]]); top3 = list(np.argsort(-C[sel].mean(0))[:3]); ok_h = ((d.Z[sel][:, top3].sum(1) * 2 > 3).astype(int) == d.Y[sel]).astype(int)
        ctx[b] = dict(ok_l=ok_l, ok_h=ok_h, parsed=parsed, a_low=ok_l.mean(), rnd=ok_l.mean() + 0.2 * (ok_h.mean() - ok_l.mean()))
    A = np.concatenate(A); Y = np.concatenate(Y); G = np.array(G); bench_of = np.array(bench_of)
    rng = np.random.default_rng(a.seed); ug = rng.permutation(np.unique(G)); fold_of = {g: i % 5 for i, g in enumerate(ug)}; f = np.array([fold_of[g] for g in G]); splits = []
    for k in range(5):                                                           # the same folds and validation splits as cascade_eval.oof_probe
        te = np.where(f == k)[0]; tr_all = np.where(f != k)[0]; tg = rng.permutation(np.unique(G[tr_all])); n_va = max(1, int(round(0.15 * len(tg)))); va_g = set(tg[:n_va])
        va = tr_all[np.array([g in va_g for g in G[tr_all]])]; tr = tr_all[np.array([g not in va_g for g in G[tr_all]])]; splits.append((tr, va, te, tr_all))
    rows = []
    for li, Lyr in enumerate(layers):
        X = np.ascontiguousarray(A[:, li, :]).astype(np.float32); oof = np.zeros(len(Y)); row = dict(layer=Lyr)
        for k, (tr, va, te, tr_all) in enumerate(splits):
            row[f"val_brier_fold{k}"] = brier(predict(train_probe(X[tr], Y[tr], seed=a.seed + k), X[va]), Y[va]); oof[te] = predict(train_probe(X[tr_all], Y[tr_all], seed=a.seed + k), X[te])
        row["val_brier_mean"] = np.mean([row[f"val_brier_fold{k}"] for k in range(5)])
        for b in BENCH:
            m = bench_of == b; c = ctx[b]; p = oof[m]; acc20 = float(curve(np.where(c["parsed"], p, -1.0), c["ok_l"], c["ok_h"])[10])
            row[f"{b}_pts"] = (acc20 - c["rnd"]) * 100; row[f"{b}_test_brier"] = float(np.mean((p - c["ok_l"]) ** 2)); row[f"{b}_auroc"] = float(roc_auc_score(c["ok_l"], p)) if 0 < c["ok_l"].mean() < 1 else np.nan
        rows.append(row); pd.DataFrame(rows).to_csv(os.path.join(a.out, f"layer_sweep_{a.low}.csv"), index=False)
        print(f"layer {Lyr:>2}: validation Brier {row['val_brier_mean']:.4f} | points above random: " + "  ".join(f"{b} {row[f'{b}_pts']:+.1f}" for b in BENCH), flush=True)
    print("done")


if __name__ == "__main__":
    main()
