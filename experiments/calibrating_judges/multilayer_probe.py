#!/usr/bin/env python
"""Multi-layer probes: does combining layers beat the paper's single fixed layer as an escalation signal?

For one cheap judge, with the same pooled training, 5 folds grouped by question, training settings, stronger judge and 20% escalation as
cascade_eval.py, compare three trust scores:
  single     the paper's fixed middle layer (the README's probe)
  avg_all    one probe per saved layer, scores averaged
  avg_top3   one probe per saved layer, average of the 3 layers with the lowest Brier on a validation split of the TRAINING questions only
Unfinished answers are escalated first for every score, as in the README. Run niced with few threads: CPU-bound."""
import argparse, json, os, sys
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
from evaluate import train_probe, predict
from metrics import brier
from cascade_eval import gen, load_run, curve, BENCH, RATES


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--low", required=True); ap.add_argument("--high-jb", required=True); ap.add_argument("--layer", type=int, required=True); ap.add_argument("--results", default="local_results")
    ap.add_argument("--judgments-bff", default="../tinker_pool_8models_judgments_bff.jsonl"); ap.add_argument("--judgments-rb2", default="../tinker_pool_8models_judgments.jsonl")
    ap.add_argument("--seeds", type=int, default=2); ap.add_argument("--threads", type=int, default=2); ap.add_argument("--out", default="results_multilayer")
    a = ap.parse_args(); torch.set_num_threads(a.threads); os.makedirs(a.out, exist_ok=True)
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "role_conditioned_panels")); from data import load_judgments; from audit import match_matrix
    A, Y, G, bench_of, parsed_all, ctx = [], [], [], [], [], {}
    for b in BENCH:
        _, p = load_run(a.results, a.low, b, "uncertainty__n1_t0.0"); itm = pd.read_csv(f"{p}_items.csv", dtype={"item_id": str}); L = gen(f"{p}_gen.jsonl").set_index("item_id").loc[itm["item_id"]]
        A.append(np.load(f"{p}_acts.npy").astype(np.float32)); layers = json.load(open(f"{p}_layers.json"))
        ok_l = L["correct"].values.astype(int); Y.append(ok_l); G += [f"{b}|{x}" for x in itm["group"].astype(str)]; bench_of += [b] * len(itm); parsed_all.append(L["verdict"].notna().values)
        if b == "judgebench":
            _, ph = load_run(a.results, a.high_jb, b, "uncertainty__n1_t0.0"); ok_h = gen(f"{ph}_gen.jsonl").set_index("item_id").loc[itm["item_id"], "correct"].values.astype(int)
        else:                                                                    # top-3 vote of the 8-judge pool, the cheap judge's own model excluded
            d = load_judgments(a.judgments_bff if b == "bff" else a.judgments_rb2, b, condition="none"); C = match_matrix(d.Z, d.Y).astype(int); idx = {i: k for k, i in enumerate(d.item_ids)}
            sel = np.array([idx[i] for i in itm["item_id"]]); accx = C[sel].mean(0); accx[[k for k, n_ in enumerate(list(d.judge_names)) if n_.lower() == a.low.lower()]] = -1.0
            top3 = list(np.argsort(-accx)[:3]); ok_h = ((d.Z[sel][:, top3].sum(1) * 2 > 3).astype(int) == d.Y[sel]).astype(int)
        ctx[b] = dict(ok_l=ok_l, ok_h=ok_h, rnd=ok_l.mean() + 0.2 * (ok_h.mean() - ok_l.mean()))
    A = np.concatenate(A); Y = np.concatenate(Y); G = np.array(G); bench_of = np.array(bench_of); parsed_all = np.concatenate(parsed_all)
    li_fix = layers.index(a.layer); k20 = 10; assert abs(RATES[k20] - 0.2) < 1e-9
    res = {m: {b: dict(acc20=[], auroc=[]) for b in BENCH} for m in ["single", "avg_all", "avg_top3"]}; picks = []
    for seed in range(a.seeds):
        rng = np.random.default_rng(seed); ug = rng.permutation(np.unique(G)); fold_of = {g: i % 5 for i, g in enumerate(ug)}; f = np.array([fold_of[g] for g in G])
        S = np.zeros((len(Y), len(layers))); top = np.zeros((len(Y), 3), int)
        for k in range(5):
            te = np.where(f == k)[0]; tr_all = np.where(f != k)[0]; tg = rng.permutation(np.unique(G[tr_all])); va_g = set(tg[:max(1, int(round(0.15 * len(tg))))])
            va = tr_all[np.array([g in va_g for g in G[tr_all]])]; tr = tr_all[np.array([g not in va_g for g in G[tr_all]])]; vb = []
            for li in range(len(layers)):
                vb.append(brier(predict(train_probe(A[tr][:, li], Y[tr], seed=seed + k), A[va][:, li]), Y[va]))
                S[te, li] = predict(train_probe(A[tr_all][:, li], Y[tr_all], seed=seed + k), A[te][:, li])
            t3 = np.argsort(vb)[:3]; top[te] = t3; picks.append([layers[i] for i in t3]); print(f"  seed {seed} fold {k}: best validation layers {[layers[i] for i in t3]}", flush=True)
        scores = dict(single=S[:, li_fix], avg_all=S.mean(1), avg_top3=np.take_along_axis(S, top, 1).mean(1))
        for m, s in scores.items():
            for b in BENCH:
                msk = bench_of == b; c = ctx[b]
                res[m][b]["acc20"].append(curve(np.where(parsed_all[msk], s[msk], -1.0), c["ok_l"], c["ok_h"])[k20]); res[m][b]["auroc"].append(roc_auc_score(c["ok_l"], s[msk]))
    rows = [dict(judge=a.low, bench=b, method=m, acc20=float(np.mean(res[m][b]["acc20"])) * 100, auroc=float(np.mean(res[m][b]["auroc"])), random20=ctx[b]["rnd"] * 100) for m in res for b in BENCH]
    df = pd.DataFrame(rows); df.to_csv(os.path.join(a.out, f"multilayer_{a.low}.csv"), index=False)
    print(df.pivot(index="bench", columns="method", values="acc20").round(1).to_string()); print("picked layers:", picks)


if __name__ == "__main__":
    main()
