#!/usr/bin/env python
"""Kill test, step 1, for 'flip the verdict when the probe is confident it is wrong' (binary / pairwise verdicts: the opposite verdict is then right).

For each cheap judge and benchmark, with the README's error probe (fixed layer, pooled training, 5 folds grouped by question, the paper's
settings; several seeds), rank the FINISHED verdicts by P(cheap judge right), lowest first, and report for the lowest 5% / 10% / 20%:
  precision    share of those verdicts that are actually wrong (flipping them helps only above 50%)
  acc_flip     accuracy of the whole benchmark when exactly those verdicts are flipped (no extra judge call; unfinished answers stay wrong)
Kill rule fixed before running: precision under 55% at every cut in every setting -> stop.
Runs on Modal CPU (modal_generate.py::script)."""
import argparse, json, os
import numpy as np, pandas as pd, torch
from evaluate import train_probe, predict
from cascade_eval import gen, load_run, BENCH


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judges", default="Qwen3.5-4B:16,Qwen3.5-9B:16,gpt-oss-20b:8"); ap.add_argument("--results", default="local_results"); ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--threads", type=int, default=8); ap.add_argument("--out", default="results_flip")
    a = ap.parse_args(); torch.set_num_threads(a.threads); os.makedirs(a.out, exist_ok=True); rows = []
    for jl in a.judges.split(","):
        j, layer = jl.split(":"); layer = int(layer); A, Y, G, B, P = [], [], [], [], []
        for b in BENCH:
            _, p = load_run(a.results, j, b, "uncertainty__n1_t0.0"); itm = pd.read_csv(f"{p}_items.csv", dtype={"item_id": str}); L = gen(f"{p}_gen.jsonl").set_index("item_id").loc[itm["item_id"]]
            layers = json.load(open(f"{p}_layers.json")); A.append(np.load(f"{p}_acts.npy", mmap_mode="r")[:, layers.index(layer)].astype(np.float32))
            Y.append(L["correct"].values.astype(int)); P.append(L["verdict"].notna().values); G += [f"{b}|{x}" for x in itm["group"].astype(str)]; B += [b] * len(itm)
        A = np.concatenate(A); Y = np.concatenate(Y); P = np.concatenate(P); G = np.array(G); B = np.array(B); S = np.zeros((a.seeds, len(Y)))
        for seed in range(a.seeds):
            rng = np.random.default_rng(seed); ug = rng.permutation(np.unique(G)); fold_of = {g: i % 5 for i, g in enumerate(ug)}; f = np.array([fold_of[g] for g in G])
            for k in range(5):
                te = np.where(f == k)[0]; tr = np.where(f != k)[0]; S[seed, te] = predict(train_probe(A[tr], Y[tr], seed=seed + k), A[te])
        for b in BENCH:
            m = B == b; y, pa, n = Y[m], P[m], m.sum()
            for cut in [0.05, 0.10, 0.20]:
                prec, accf = [], []
                for seed in range(a.seeds):
                    s = S[seed, m]; fin = np.where(pa)[0]; order = fin[np.argsort(s[fin], kind="stable")]; k_ = int(round(cut * n)); flip = order[:k_]
                    prec.append(1 - y[flip].mean()); y2 = y.copy(); y2[flip] = 1 - y2[flip]; accf.append(y2.mean())
                rows.append(dict(judge=j, bench=b, cut=int(cut * 100), n=int(n), cheap_alone=y.mean() * 100, unfinished=(~pa).mean() * 100,
                                 precision=np.mean(prec) * 100, acc_flip=np.mean(accf) * 100, gain_flip=(np.mean(accf) - y.mean()) * 100))
        print(f"{j} done", flush=True)
    R = pd.DataFrame(rows); R.to_csv(os.path.join(a.out, "flip_step1.csv"), index=False); pd.set_option("display.width", 200); print(R.round(1).to_string(index=False))
    alive = (R.precision >= 55).any(); print("\nKILL RULE (precision < 55% everywhere):", "PASSED - not killed" if alive else "KILLED")


if __name__ == "__main__":
    main()
