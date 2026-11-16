#!/usr/bin/env python
"""Probe each judge on its OWN correctness, small and large judges side by side (one benchmark at a time).

Same recipe for every judge, so judges of different depth are compared fairly: the paper's linear probe and training settings, 5 folds grouped
by question, and the layer(s) chosen INSIDE each training fold (average of the 3 layers with the lowest Brier on a 15% validation split of the
training questions; never the test questions). Per judge:
  acc_alone       the judge's own verdict accuracy
  auroc           how well the probe separates its right from its wrong verdicts (out of fold)
  errors_caught   share of the judge's errors that fall in the 20% it trusts least (unfinished answers first)
  acc_kept80      accuracy on the 80% it trusts most (selective accuracy)
Memory: one layer at a time (memory-mapped). Runs on Modal CPU (modal_generate.py::strongprobe), not on the laptop."""
import argparse, json, os
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
from evaluate import train_probe, predict
from metrics import brier
from cascade_eval import gen, load_run


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judges", default="Qwen3.5-4B,Qwen3.5-9B,Qwen3.8-27B,gpt-oss-20b,gpt-oss-120b"); ap.add_argument("--bench", default="rb2safety"); ap.add_argument("--results", default="local_results")
    ap.add_argument("--seeds", type=int, default=2); ap.add_argument("--threads", type=int, default=2); ap.add_argument("--out", default="results_strong_probe")
    a = ap.parse_args(); torch.set_num_threads(a.threads); os.makedirs(a.out, exist_ok=True); rows = []
    for j in a.judges.split(","):
        _, p = load_run(a.results, j, a.bench, "uncertainty__n1_t0.0")
        if not os.path.exists(f"{p}_acts.npy"):
            print(f"skip {j}: no activations for {a.bench}"); continue
        itm = pd.read_csv(f"{p}_items.csv", dtype={"item_id": str}); L = gen(f"{p}_gen.jsonl").set_index("item_id").loc[itm["item_id"]]; layers = json.load(open(f"{p}_layers.json"))
        A = np.load(f"{p}_acts.npy", mmap_mode="r")                            # memory-mapped: only ONE layer is read into memory at a time
        Y = L["correct"].values.astype(int); parsed = L["verdict"].notna().values; G = itm["group"].astype(str).values; n = len(Y); nl = len(layers)
        res = dict(auroc=[], caught=[], kept=[]); picks = []
        for seed in range(a.seeds):
            rng = np.random.default_rng(seed); ug = rng.permutation(np.unique(G)); fold_of = {g: i % 5 for i, g in enumerate(ug)}; f = np.array([fold_of[g] for g in G]); splits = []
            for k in range(5):                                                   # the folds and validation splits are fixed first (same random stream as before)
                te = np.where(f == k)[0]; tr_all = np.where(f != k)[0]; tg = rng.permutation(np.unique(G[tr_all])); va_g = set(tg[:max(1, int(round(0.15 * len(tg))))])
                splits.append((te, tr_all, tr_all[np.isin(G[tr_all], list(va_g))], tr_all[~np.isin(G[tr_all], list(va_g))]))
            VB = np.zeros((5, nl)); P = np.zeros((nl, n))
            for li in range(nl):                                                 # one layer in memory: train the validation probe and the test probe for every fold
                X = np.ascontiguousarray(A[:, li]).astype(np.float32)
                for k, (te, tr_all, va, tr) in enumerate(splits):
                    VB[k, li] = brier(predict(train_probe(X[tr], Y[tr], seed=seed + k), X[va]), Y[va]); P[li, te] = predict(train_probe(X[tr_all], Y[tr_all], seed=seed + k), X[te])
                del X
            s = np.zeros(n)
            for k, (te, *_rest) in enumerate(splits):
                top = np.argsort(VB[k])[:3]; picks.append([layers[i] for i in top]); s[te] = P[top][:, te].mean(0)
            t = np.where(parsed, s, -1e6); order = np.lexsort((np.random.default_rng(1).random(n), t)); flag = np.zeros(n, bool); flag[order[:int(round(0.2 * n))]] = True
            res["auroc"].append(roc_auc_score(Y, s)); res["caught"].append(((Y == 0) & flag).sum() / max(1, (Y == 0).sum())); res["kept"].append(Y[~flag].mean())
            print(f"  {j} seed {seed}: AUROC {res['auroc'][-1]:.3f}", flush=True)
        rows.append(dict(judge=j, bench=a.bench, n=n, n_layers=max(layers), acc_alone=Y.mean() * 100, errors=int((Y == 0).sum()), cut_off=float((~parsed).mean()) * 100,
                         auroc=np.mean(res["auroc"]), errors_caught=np.mean(res["caught"]) * 100, acc_kept80=np.mean(res["kept"]) * 100,
                         errors_caught_random=20.0, picked_layers=str(sorted(set(sum(picks, []))))))
        pd.DataFrame(rows).to_csv(os.path.join(a.out, f"strong_probe_{a.bench}.csv"), index=False)
    print(pd.DataFrame(rows).drop(columns=["picked_layers"]).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
