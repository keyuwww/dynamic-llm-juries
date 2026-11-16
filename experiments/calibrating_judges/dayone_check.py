#!/usr/bin/env python
"""Day-one check for 'escalate where the stronger judge would change the verdict':
for each cheap judge and benchmark, split items by (cheap right?, strong right?) and look at the 20% the current probe escalates.
Verdicts are binary / pairwise, so cheap and strong give the same verdict exactly when they are both right or both wrong.
  gain   cheap wrong, strong right   (escalating fixes it)
  loss   cheap right, strong wrong   (escalating breaks it)
  same_r both right                  (escalating changes nothing)
  same_w both wrong                  (escalating changes nothing; only a human could fix it)
Probe = the README's probe (fixed layer, pooled training, 5 folds by question, one seed); unfinished answers first."""
import argparse, json, os, sys
import numpy as np, pandas as pd, torch
from evaluate import train_probe, predict
from cascade_eval import gen, load_run, BENCH


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--low", required=True); ap.add_argument("--high-jb", required=True); ap.add_argument("--layer", type=int, required=True); ap.add_argument("--results", default="local_results")
    ap.add_argument("--judgments-bff", default="../tinker_pool_8models_judgments_bff.jsonl"); ap.add_argument("--judgments-rb2", default="../tinker_pool_8models_judgments.jsonl"); ap.add_argument("--threads", type=int, default=2)
    a = ap.parse_args(); torch.set_num_threads(a.threads)
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "role_conditioned_panels")); from data import load_judgments; from audit import match_matrix
    A, Y, G, bench_of, parsed_all, OH = [], [], [], [], [], []
    for b in BENCH:
        _, p = load_run(a.results, a.low, b, "uncertainty__n1_t0.0"); itm = pd.read_csv(f"{p}_items.csv", dtype={"item_id": str}); L = gen(f"{p}_gen.jsonl").set_index("item_id").loc[itm["item_id"]]
        layers = json.load(open(f"{p}_layers.json")); A.append(np.load(f"{p}_acts.npy", mmap_mode="r")[:, layers.index(a.layer)].astype(np.float32))
        Y.append(L["correct"].values.astype(int)); G += [f"{b}|{x}" for x in itm["group"].astype(str)]; bench_of += [b] * len(itm); parsed_all.append(L["verdict"].notna().values)
        if b == "judgebench":
            _, ph = load_run(a.results, a.high_jb, b, "uncertainty__n1_t0.0"); OH.append(gen(f"{ph}_gen.jsonl").set_index("item_id").loc[itm["item_id"], "correct"].values.astype(int))
        else:
            d = load_judgments(a.judgments_bff if b == "bff" else a.judgments_rb2, b, condition="none"); C = match_matrix(d.Z, d.Y).astype(int); idx = {i: k for k, i in enumerate(d.item_ids)}
            sel = np.array([idx[i] for i in itm["item_id"]]); accx = C[sel].mean(0); accx[[k for k, n_ in enumerate(list(d.judge_names)) if n_.lower() == a.low.lower()]] = -1.0
            top3 = list(np.argsort(-accx)[:3]); OH.append(((d.Z[sel][:, top3].sum(1) * 2 > 3).astype(int) == d.Y[sel]).astype(int))
    A = np.concatenate(A); Y = np.concatenate(Y); G = np.array(G); bench_of = np.array(bench_of); parsed_all = np.concatenate(parsed_all); OH = np.concatenate(OH)
    rng = np.random.default_rng(0); ug = rng.permutation(np.unique(G)); fold_of = {g: i % 5 for i, g in enumerate(ug)}; f = np.array([fold_of[g] for g in G]); s = np.zeros(len(Y))
    for k in range(5):
        te = np.where(f == k)[0]; tr = np.where(f != k)[0]; s[te] = predict(train_probe(A[tr], Y[tr], seed=k), A[te])
    rows = []
    for b in BENCH:
        m = bench_of == b; l, h = Y[m], OH[m]; n = m.sum(); sc = np.where(parsed_all[m], s[m], -1.0)
        esc = np.zeros(n, bool); esc[np.argsort(sc + 1e-9 * np.random.default_rng(0).random(n), kind="stable")[:int(round(0.2 * n))]] = True
        cat = lambda x: dict(gain=((l == 0) & (h == 1))[x].mean(), loss=((l == 1) & (h == 0))[x].mean(), same_r=((l == 1) & (h == 1))[x].mean(), same_w=((l == 0) & (h == 0))[x].mean())
        al, es = cat(np.ones(n, bool)), cat(esc)
        rows.append(dict(judge=a.low, bench=b, n=n, all_gain=al["gain"], all_loss=al["loss"], all_same_w=al["same_w"], esc_gain=es["gain"], esc_loss=es["loss"], esc_same_r=es["same_r"], esc_same_w=es["same_w"],
                         esc_wasted=es["same_r"] + es["same_w"], n_gain_items=int(((l == 0) & (h == 1)).sum())))
    df = pd.DataFrame(rows); os.makedirs("results_dayone", exist_ok=True); df.to_csv(f"results_dayone/dayone_{a.low}.csv", index=False)
    print((df.set_index(["judge", "bench"]).drop(columns=["n_gain_items", "n"]) * 100).round(1).to_string()); print(df[["bench", "n", "n_gain_items"]].to_string(index=False))


if __name__ == "__main__":
    main()
