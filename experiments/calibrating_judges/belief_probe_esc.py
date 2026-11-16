#!/usr/bin/env python
"""Belief probe for escalation: read the judge's belief (normally 7 own solves) from its activations, then escalate with it. BFF, Qwen3.5-4B / 9B.

Activations: the judge's own run (last token, every saved layer), the same as the correctness probe. Belief target: share of the judge's 7 own
solves that reach the candidate's answer (anchoring_early_answer, clean labels); needed only for TRAINING items.
Outer splits: 5 folds by question over the three benchmarks (as confirm_probe.py), 3 seeds; BFF is scored.
  belief probe     per layer: standardised ridge regression activations -> belief (alpha by inner CV), predictions averaged over layers;
                   trained on the outer-training BFF items that have a belief value; predicts every test item (no solves needed at test time)
  P                correctness probe (the better probe: logistic regression per layer, averaged; pooled over the three benchmarks)
  PB               combiner on predicted-belief features only: predicted belief, |predicted belief - 0.5|, verdict follows predicted belief, verdict
  P+PB             combiner on logit(P) + the predicted-belief features                                                       (PRIMARY)
  TB               combiner on the TRUE 7-solve belief features (reference; needs 7 solves at test time)
Combiners are logistic regressions trained on outer-training BFF items, on cross-fitted P and predicted belief (inner 3 folds), so no item is
scored by a model that saw it. Baselines: 10 reruns, verdict-only rule, random. Accuracy with 10/20/30% escalated, unfinished answers first.
Also: out-of-fold Spearman between predicted and true belief. Pre-registered pass bar: P+PB beats P at 20% with the 95% paired bootstrap CI
above 0 for at least 1 of the 2 judges. Runs on Modal CPU (modal_generate.py::script)."""
import argparse, json, os, warnings
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression, RidgeCV
from sklearn.preprocessing import StandardScaler
from cascade_eval import gen, load_run, BENCH
from combo_probe import probe, crossfit
warnings.filterwarnings("ignore")


def ridge_layer(Xtr, ytr, Xte):
    sc = StandardScaler().fit(Xtr); return RidgeCV(alphas=[1e1, 1e2, 1e3, 1e4, 1e5]).fit(sc.transform(Xtr), ytr).predict(sc.transform(Xte))


def belief_probe(A, bel, tr, te, nj):
    """train on tr (items with a belief value), predict te; average of per-layer ridge predictions"""
    return np.mean(Parallel(n_jobs=nj)(delayed(ridge_layer)(A[tr, l], bel[tr], A[te, l]) for l in range(A.shape[1])), 0)


def crossfit_belief(A, bel, has, idx, groups, nj, seed):
    out = np.zeros(len(idx)); ug = np.random.default_rng(seed).permutation(np.unique(groups[idx])); fo = {g: k % 3 for k, g in enumerate(ug)}; f = np.array([fo[g] for g in groups[idx]])
    for k in range(3):
        trk = idx[(f != k) & has[idx]]; out[f == k] = belief_probe(A, bel, trk, idx[f == k], nj)
    return out


def esc_acc(trust, ol, oh, fin, tie, rate=0.2):
    n = len(ol); m = int(round(rate * n)); k = np.lexsort((tie, np.where(~fin, -1e9, trust))); e = np.zeros(n, bool); e[k[:m]] = True
    return np.where(e, oh, ol).mean()


def lr(Xtr, ytr, Xte):
    sc = StandardScaler().fit(Xtr); return LogisticRegression(C=1.0, max_iter=2000).fit(sc.transform(Xtr), ytr).predict_proba(sc.transform(Xte))[:, 1]


def bfeat(b, vg):
    return np.c_[b, np.abs(b - 0.5), ((vg == 1) == (b >= 0.5)).astype(float), vg]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", required=True); ap.add_argument("--results", default="local_results"); ap.add_argument("--targets", default="targets/strong_judge_correct.json")
    ap.add_argument("--belief", default="targets/belief_rows_clean.json"); ap.add_argument("--seeds", type=int, default=3); ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--threads", type=int, default=8); ap.add_argument("--out", default="results_belief_probe")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True); TG = json.load(open(a.targets)); j = a.judge; nj = a.threads
    BR = pd.DataFrame(json.load(open(a.belief))); BR = BR[(BR.bench == "bff") & (BR.judge == j.lower())].drop_duplicates("item").set_index("item")
    A, Y, G, B, FIN, IDS, VG, CONS = [], [], [], [], [], [], [], []
    for b in BENCH:
        _, p = load_run(a.results, j, b, "uncertainty__n1_t0.0"); itm = pd.read_csv(f"{p}_items.csv", dtype={"item_id": str}); ids = list(itm["item_id"]); L = gen(f"{p}_gen.jsonl").set_index("item_id").loc[ids]
        A.append(np.load(f"{p}_acts.npy").astype(np.float32)); Y.append(L["correct"].values.astype(int)); FIN.append(L["verdict"].notna().values); VG.append((L["verdict"].values == 1.0).astype(float))
        G += [f"{b}|{x}" for x in itm["group"].astype(str)]; B += [b] * len(ids); IDS += ids
        _, ps = load_run(a.results, j, b, "uncertainty__n10_t0.7"); S = gen(f"{ps}_gen.jsonl"); gv = L["verdict"]; cons = np.zeros(len(ids)); pos = {i: k for k, i in enumerate(ids)}
        for iid, d in S.groupby("item_id"):
            if iid in pos and pd.notna(gv.iloc[pos[iid]]): cons[pos[iid]] = float((d["verdict"] == gv.iloc[pos[iid]]).sum()) / len(d)
        CONS.append(cons)
    A = np.concatenate(A); Y = np.concatenate(Y); FIN = np.concatenate(FIN); VG = np.concatenate(VG); G = np.array(G); B = np.array(B); IDS = np.array(IDS); CONS = np.concatenate(CONS); n = len(Y)
    BEL = np.array([float(BR.loc[i, "belief"]) if (b_ == "bff" and i in BR.index) else np.nan for i, b_ in zip(IDS, B)]); HAS = ~np.isnan(BEL); BELf = np.nan_to_num(BEL, nan=0.5)
    print(f"{j}: BFF items with belief {int(HAS.sum())} of {int((B == 'bff').sum())}", flush=True)
    logit = lambda p: np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))
    SC = {v: np.zeros((a.seeds, n)) for v in ["P", "PB", "P+PB", "TB"]}; PBEL = np.full((a.seeds, n), np.nan)
    for seed in range(a.seeds):
        rng = np.random.default_rng(seed); ug = rng.permutation(np.unique(G)); fold_of = {g: i % 5 for i, g in enumerate(ug)}; f = np.array([fold_of[g] for g in G])
        for k in range(5):
            te, tr = np.where(f == k)[0], np.where(f != k)[0]; trb, teb = tr[B[tr] == "bff"], te[B[te] == "bff"]
            p_te = probe(A, Y, tr, te, nj); SC["P"][seed, te] = p_te; p_tr = crossfit(A, Y, tr, G, nj, seed + k)[B[tr] == "bff"]
            pb_te = belief_probe(A, BELf, trb[HAS[trb]], teb, nj); PBEL[seed, teb] = pb_te
            pb_tr = crossfit_belief(A, BELf, HAS, trb, G, nj, seed + k)
            Ftr, Fte = bfeat(pb_tr, VG[trb]), bfeat(pb_te, VG[teb]); pteb = p_te[B[te] == "bff"]
            SC["PB"][seed, teb] = lr(Ftr, Y[trb], Fte)
            SC["P+PB"][seed, teb] = lr(np.c_[logit(p_tr), Ftr], Y[trb], np.c_[logit(pteb), Fte])
            tb_tr, tb_te = bfeat(BELf[trb], VG[trb]), bfeat(BELf[teb], VG[teb])
            SC["TB"][seed, teb] = lr(np.c_[tb_tr, (~HAS[trb]).astype(float)], Y[trb], np.c_[tb_te, (~HAS[teb]).astype(float)])
            print(f"{j} seed {seed} fold {k} done", flush=True)
    m = B == "bff"; mh = m & HAS
    rho = np.mean([spearmanr(PBEL[s, mh], BEL[mh]).statistic for s in range(a.seeds)]); print(f"{j}: out-of-fold Spearman(predicted belief, true belief) on BFF = {rho:.2f}", flush=True)
    ol, fin, g = Y[m], FIN[m], G[m]; oh = np.array([TG[j]["bff"][i] for i in IDS[m]]); good = VG[m].astype(bool); nb = m.sum(); tie = np.random.default_rng(12345).random(nb)
    def scores(idx, rate=0.2):
        o, h, fi, t = ol[idx], oh[idx], fin[idx], tie[idx]
        r = {v: np.mean([esc_acc(SC[v][s, m][idx], o, h, fi, t, rate) for s in range(a.seeds)]) for v in SC}
        r["reruns10"] = esc_acc(CONS[m][idx], o, h, fi, t, rate); r["verdict_only"] = np.mean([esc_acc((np.where(good, 0, 1) + 0.5 * np.random.default_rng(s).random(nb))[idx], o, h, fi, t, rate) for s in range(20)])
        return r
    rows = []
    for rate in [0.1, 0.2, 0.3]:
        full = scores(np.arange(nb), rate); row = dict(judge=j, escalated=int(rate * 100), random=(ol.mean() + rate * (oh.mean() - ol.mean())) * 100, **{k_: v_ * 100 for k_, v_ in full.items()})
        if rate == 0.2:
            gi = {x: np.where(g == x)[0] for x in np.unique(g)}; ugs = np.array(list(gi)); rb = np.random.default_rng(7); D = []
            for _ in range(a.n_boot):
                s_ = scores(np.concatenate([gi[x] for x in rb.choice(ugs, len(ugs))])); D.append([s_["P+PB"] - s_["P"], s_["PB"] - s_["P"], s_["P+PB"] - s_["reruns10"], s_["P+PB"] - s_["TB"]])
            D = np.array(D) * 100; lo, hi = np.percentile(D, 2.5, 0), np.percentile(D, 97.5, 0)
            obs = [full["P+PB"] - full["P"], full["PB"] - full["P"], full["P+PB"] - full["reruns10"], full["P+PB"] - full["TB"]]
            for nm, o_, l_, u_ in zip(["P+PB_minus_P", "PB_minus_P", "P+PB_minus_reruns", "P+PB_minus_TB"], obs, lo, hi): row[nm] = f"{o_*100:+.1f} [{l_:+.1f},{u_:+.1f}]"
        rows.append(row)
    R = pd.DataFrame(rows); R.to_csv(os.path.join(a.out, f"belief_probe_{j}.csv"), index=False); pd.set_option("display.width", 280); print(R.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
