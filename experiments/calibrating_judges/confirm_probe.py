#!/usr/bin/env python
"""Confirmation run for the better-trained probe, fixed in advance: logistic regression (standardised, C = 0.01) at every saved layer, probabilities
averaged ('logreg_avg_layers' in probe_zoo.py). Same activations, stronger judges and escalation rule as the README; 5 seeds = 5 different
5-fold splits by question. Compared at 20% escalated (unfinished answers first) with: the paper's probe (linear, its training settings, fixed
middle layer), the verdict-only rule (random among items the judge marked 'correct'), 10 reruns (share of samples agreeing with the greedy verdict)
and random. 95% paired bootstrap CIs over questions for new - paper, new - verdict-only, new - reruns (seed-averaged).
Runs on Modal CPU (modal_generate.py::script)."""
import argparse, json, os, warnings
import numpy as np, pandas as pd, torch
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from evaluate import train_probe, predict
from cascade_eval import gen, load_run, BENCH
warnings.filterwarnings("ignore")


def esc_acc(trust, ol, oh, fin, tie):
    n = len(ol); m = int(round(0.2 * n)); k = np.lexsort((tie, np.where(~fin, -1e9, trust))); e = np.zeros(n, bool); e[k[:m]] = True
    return np.where(e, oh, ol).mean()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", required=True); ap.add_argument("--layer", type=int, required=True); ap.add_argument("--results", default="local_results")
    ap.add_argument("--targets", default="targets/strong_judge_correct.json"); ap.add_argument("--seeds", type=int, default=5); ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--threads", type=int, default=8); ap.add_argument("--out", default="results_confirm")
    a = ap.parse_args(); torch.set_num_threads(a.threads); os.makedirs(a.out, exist_ok=True); TG = json.load(open(a.targets)); j = a.judge
    A, Y, G, B, FIN, V, IDS, CONS = [], [], [], [], [], [], [], []
    for b in BENCH:
        _, p = load_run(a.results, j, b, "uncertainty__n1_t0.0"); itm = pd.read_csv(f"{p}_items.csv", dtype={"item_id": str}); ids = list(itm["item_id"]); L = gen(f"{p}_gen.jsonl").set_index("item_id").loc[ids]
        A.append(np.load(f"{p}_acts.npy").astype(np.float32)); layers = json.load(open(f"{p}_layers.json"))
        Y.append(L["correct"].values.astype(int)); FIN.append(L["verdict"].notna().values); V += list(L["verdict"].astype(str)); G += [f"{b}|{x}" for x in itm["group"].astype(str)]; B += [b] * len(ids); IDS += ids
        _, ps = load_run(a.results, j, b, "uncertainty__n10_t0.7"); S = gen(f"{ps}_gen.jsonl"); gv = L["verdict"]; cons = np.zeros(len(ids)); pos = {i: k for k, i in enumerate(ids)}
        for iid, d in S.groupby("item_id"):
            if iid in pos and pd.notna(gv.iloc[pos[iid]]): cons[pos[iid]] = float((d["verdict"] == gv.iloc[pos[iid]]).sum()) / len(d)
        CONS.append(cons)
    A = np.concatenate(A); Y = np.concatenate(Y); FIN = np.concatenate(FIN); G = np.array(G); B = np.array(B); V = np.array(V); IDS = np.array(IDS); CONS = np.concatenate(CONS)
    li = layers.index(a.layer); nl = len(layers); NEW = np.zeros((a.seeds, len(Y))); OLD = np.zeros((a.seeds, len(Y)))
    for seed in range(a.seeds):
        rng = np.random.default_rng(seed); ug = rng.permutation(np.unique(G)); fold_of = {g: i % 5 for i, g in enumerate(ug)}; f = np.array([fold_of[g] for g in G])
        for k in range(5):
            te, tr = np.where(f == k)[0], np.where(f != k)[0]; probs = []
            for l in range(nl):
                sc = StandardScaler().fit(A[tr, l]); probs.append(LogisticRegression(C=0.01, max_iter=2000).fit(sc.transform(A[tr, l]), Y[tr]).predict_proba(sc.transform(A[te, l]))[:, 1])
            NEW[seed, te] = np.mean(probs, 0); OLD[seed, te] = predict(train_probe(A[tr, li], Y[tr], seed=seed + k), A[te, li])
        print(f"{j} seed {seed} done", flush=True)
    rows = []; tie = np.random.default_rng(12345).random(len(Y))
    for b in BENCH:
        m = B == b; ol, fin, t = Y[m], FIN[m], tie[m]; oh = np.array([TG[j][b][i] for i in IDS[m]]); good = (V[m] == "1.0"); g = G[m]; n = m.sum()
        vo_trust = lambda r: np.where(good, 0, 1) + 0.5 * r.random(n) if b != "judgebench" else r.random(n)
        def scores(idx):
            o, h, fi, tt = ol[idx], oh[idx], fin[idx], t[idx]
            new = np.mean([esc_acc(NEW[s, m][idx], o, h, fi, tt) for s in range(a.seeds)]); old = np.mean([esc_acc(OLD[s, m][idx], o, h, fi, tt) for s in range(a.seeds)])
            rr = esc_acc(CONS[m][idx], o, h, fi, tt); vo = np.mean([esc_acc(vo_trust(np.random.default_rng(s))[idx], o, h, fi, tt) for s in range(20)])
            return new, old, vo, rr
        new, old, vo, rr = scores(np.arange(n)); ug = np.unique(g); gi = {x: np.where(g == x)[0] for x in ug}; rb = np.random.default_rng(7); D = []
        for _ in range(a.n_boot):
            bi = np.concatenate([gi[x] for x in rb.choice(ug, len(ug))]); s_ = scores(bi); D.append([s_[0] - s_[1], s_[0] - s_[2], s_[0] - s_[3]])
        D = np.array(D) * 100; lo, hi = np.percentile(D, 2.5, 0), np.percentile(D, 97.5, 0)
        rows.append(dict(judge=j, bench=b, random=(ol.mean() + 0.2 * (oh.mean() - ol.mean())) * 100, verdict_only=vo * 100, paper_probe=old * 100, reruns10=rr * 100, new_probe=new * 100,
                         new_minus_paper=f"{(new-old)*100:+.1f} [{lo[0]:+.1f},{hi[0]:+.1f}]", new_minus_verdict=f"{(new-vo)*100:+.1f} [{lo[1]:+.1f},{hi[1]:+.1f}]", new_minus_reruns=f"{(new-rr)*100:+.1f} [{lo[2]:+.1f},{hi[2]:+.1f}]"))
    R = pd.DataFrame(rows); R.to_csv(os.path.join(a.out, f"confirm_{j}.csv"), index=False); pd.set_option("display.width", 250); print(R.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
