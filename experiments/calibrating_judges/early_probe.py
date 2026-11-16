#!/usr/bin/env python
"""Probe during reasoning: can the cheap judge's activations PART-WAY through its reasoning already tell which verdicts to escalate?

For each fraction f of the judge's generated tokens (and the last token, f = 1), train the same probe as cascade_eval.py (one layer, pooled
benchmarks, 5 folds grouped by question, the paper's training settings) on the activations at that point, to predict whether the FINAL verdict
is right. Report per benchmark:
  auroc      how well the probe at f separates final-right from final-wrong verdicts
  acc20      accuracy of the final verdicts when the 20% least-trusted at f go to the stronger judge (same stronger judge as the README)
  tokens     share of the cheap judge's generated tokens still spent if the escalated items are stopped at f (kept items run to the end)
At f < 1 the judge has not finished, so 'unfinished answers first' cannot be used; the probe alone ranks. At f = 1 we report both.
Needs <results>/<model>__<bench>__uncertainty__n1_t0.0__pos/ from modal_generate.py::posacts. Run niced, few threads: CPU-bound."""
import argparse, json, os, sys
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
from evaluate import train_probe, predict
from cascade_eval import gen, load_run, curve, BENCH, RATES


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--low", required=True); ap.add_argument("--layer", type=int, default=16); ap.add_argument("--results", default="local_results")
    ap.add_argument("--judgments-bff", default="../tinker_pool_8models_judgments_bff.jsonl"); ap.add_argument("--judgments-rb2", default="../tinker_pool_8models_judgments.jsonl")
    ap.add_argument("--high-jb", required=True, help="model whose JudgeBench run is the stronger judge (as in cascade_eval.py)")
    ap.add_argument("--seeds", type=int, default=3); ap.add_argument("--threads", type=int, default=2); ap.add_argument("--out", default="results_early_probe")
    a = ap.parse_args(); torch.set_num_threads(a.threads); os.makedirs(a.out, exist_ok=True)
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "role_conditioned_panels")); from data import load_judgments; from audit import match_matrix
    P, Y, G, bench_of, ntok, parsed_all, ctx = [], [], [], [], [], [], {}
    for b in BENCH:
        _, p = load_run(a.results, a.low, b, "uncertainty__n1_t0.0"); tag = os.path.basename(p)
        q = os.path.join(f"{os.path.dirname(p)}__pos", tag)
        itm = pd.read_csv(f"{q}_items.csv", dtype={"item_id": str}); L = gen(f"{p}_gen.jsonl").set_index("item_id").loc[itm["item_id"]]
        layers = json.load(open(f"{q}_layers.json")); fracs = json.load(open(f"{q}_positions.json"))["fracs"]
        P.append(np.load(f"{q}_posacts.npy", mmap_mode="r")[:, :, layers.index(a.layer), :].astype(np.float32))
        ok_l = L["correct"].values.astype(int); parsed = L["verdict"].notna().values
        Y.append(ok_l); G += [f"{b}|{x}" for x in itm["group"].astype(str)]; bench_of += [b] * len(itm); ntok.append(L["n_tokens"].values); parsed_all.append(parsed)
        if b == "judgebench":
            _, ph = load_run(a.results, a.high_jb, b, "uncertainty__n1_t0.0"); ok_h = gen(f"{ph}_gen.jsonl").set_index("item_id").loc[itm["item_id"], "correct"].values.astype(int)
        else:                                                                    # top-3 vote of the 8-judge pool, the cheap judge's own model excluded
            d = load_judgments(a.judgments_bff if b == "bff" else a.judgments_rb2, b, condition="none"); C = match_matrix(d.Z, d.Y).astype(int); idx = {i: k for k, i in enumerate(d.item_ids)}
            sel = np.array([idx[i] for i in itm["item_id"]]); accx = C[sel].mean(0); accx[[k for k, n_ in enumerate(list(d.judge_names)) if n_.lower() == a.low.lower()]] = -1.0
            top3 = list(np.argsort(-accx)[:3]); ok_h = ((d.Z[sel][:, top3].sum(1) * 2 > 3).astype(int) == d.Y[sel]).astype(int)
        ctx[b] = dict(ok_l=ok_l, ok_h=ok_h, rnd=ok_l.mean() + 0.2 * (ok_h.mean() - ok_l.mean()), alone=ok_l.mean(), strong=ok_h.mean())
    P = np.concatenate(P); Y = np.concatenate(Y); G = np.array(G); bench_of = np.array(bench_of); ntok = np.concatenate(ntok); parsed_all = np.concatenate(parsed_all)
    k20 = list(np.round(RATES, 4)).index(0.2); rows = []
    for fi, fr in enumerate(fracs):
        res = {b: dict(auroc=[], acc20=[], acc20_cut=[], tokens=[]) for b in BENCH}
        for seed in range(a.seeds):
            rng = np.random.default_rng(seed); ug = rng.permutation(np.unique(G)); fold_of = {g: i % 5 for i, g in enumerate(ug)}; f = np.array([fold_of[g] for g in G]); oof = np.zeros(len(Y))
            for k in range(5):
                te = np.where(f == k)[0]; tr = np.where(f != k)[0]
                oof[te] = predict(train_probe(P[tr, fi], Y[tr], seed=seed + k), P[te, fi])
            for b in BENCH:
                m = bench_of == b; c = ctx[b]; s = oof[m]; n = m.sum(); esc = np.zeros(n, bool); esc[np.argsort(s + 1e-9 * np.random.default_rng(0).random(n), kind="stable")[:int(round(0.2 * n))]] = True
                t = ntok[m]; spent = np.where(esc, np.maximum(1, np.round(fr * t)), t).sum() / t.sum()
                res[b]["auroc"].append(roc_auc_score(c["ok_l"], s)); res[b]["acc20"].append(curve(s, c["ok_l"], c["ok_h"])[k20]); res[b]["tokens"].append(spent)
                res[b]["acc20_cut"].append(curve(np.where(parsed_all[m], s, -1.0), c["ok_l"], c["ok_h"])[k20])
        for b in BENCH:
            c = ctx[b]; r = {k: float(np.mean(v)) for k, v in res[b].items()}
            rows.append(dict(judge=a.low, bench=b, frac=fr, auroc=r["auroc"], acc20=r["acc20"] * 100, acc20_cut_first=(r["acc20_cut"] * 100 if fr == 1.0 else np.nan),
                             tokens_spent=r["tokens"] * 100, random20=c["rnd"] * 100, cheap_alone=c["alone"] * 100, strong_alone=c["strong"] * 100))
        print(f"fraction {fr:.2f}: " + "  ".join(f"{r['bench']} AUROC {r['auroc']:.3f} acc20 {r['acc20']:.1f} tokens {r['tokens_spent']:.0f}%" for r in rows[-3:]), flush=True)
    pd.DataFrame(rows).to_csv(os.path.join(a.out, f"early_probe_{a.low}.csv"), index=False); print("saved")


if __name__ == "__main__":
    main()
