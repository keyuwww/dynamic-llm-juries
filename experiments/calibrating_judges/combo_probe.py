#!/usr/bin/env python
"""Can the better probe get better? (1) combine it with cheap signals, (2) train it per benchmark instead of pooled.

Probe = confirm_probe.py's: standardised logistic regression (C = 0.01) at every saved layer, probabilities averaged; activations at the last token.
Outer splits: 5 folds by question over the three benchmarks (same random stream as confirm_probe.py), 3 seeds. Scored on BFF and Safety.
  V1 pooled probe            trained on the training folds of all three benchmarks (= confirm_probe.py)
  V2 per-benchmark probe     trained on the training folds of this benchmark only
  V3 pooled probe + signals  logistic-regression combiner (per benchmark) on: probe logit, verdict, error-question verdict and disagreement (Qwen only;
                             no error-question run for gpt-oss), token statistics (mean log-prob, mean entropy, verdict-token probability, log length)
  V4 per-benchmark + signals PRIMARY, fixed before running
The combiner is trained on training questions only, with probe scores cross-fitted on them (inner 3 folds), so no item scores itself.
Baselines: verdict-only rule, 10 reruns (README), random. Accuracy with 20% escalated (unfinished answers first) to the README's stronger judge.
Pre-registered pass bar: V4 - V1 at 20% has a 95% paired bootstrap CI above 0 in at least 3 of the 6 judge x benchmark settings.
Runs on Modal CPU (modal_generate.py::script)."""
import argparse, json, os, warnings
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from cascade_eval import gen, load_run, BENCH
warnings.filterwarnings("ignore")
EVAL = ["bff", "rb2safety"]


def fit_pred(Xtr, ytr, Xte):
    sc = StandardScaler().fit(Xtr); return LogisticRegression(C=0.01, max_iter=2000).fit(sc.transform(Xtr), ytr).predict_proba(sc.transform(Xte))[:, 1]


def probe(A, y, tr, te, nj):
    """average over layers of per-layer logistic regression; layers in parallel"""
    return np.mean(Parallel(n_jobs=nj)(delayed(fit_pred)(A[tr, l], y[tr], A[te, l]) for l in range(A.shape[1])), 0)


def crossfit(A, y, idx, groups, nj, seed):
    """probe scores for the items in idx, each scored by a probe trained on the other inner folds (3 folds by question)"""
    out = np.zeros(len(idx)); ug = np.random.default_rng(seed).permutation(np.unique(groups[idx])); fo = {g: k % 3 for k, g in enumerate(ug)}; f = np.array([fo[g] for g in groups[idx]])
    for k in range(3):
        out[f == k] = probe(A, y, idx[f != k], idx[f == k], nj)
    return out


def esc_acc(trust, ol, oh, fin, tie):
    n = len(ol); m = int(round(0.2 * n)); k = np.lexsort((tie, np.where(~fin, -1e9, trust))); e = np.zeros(n, bool); e[k[:m]] = True
    return np.where(e, oh, ol).mean()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", required=True); ap.add_argument("--results", default="local_results"); ap.add_argument("--targets", default="targets/strong_judge_correct.json")
    ap.add_argument("--seeds", type=int, default=3); ap.add_argument("--n-boot", type=int, default=1000); ap.add_argument("--threads", type=int, default=8); ap.add_argument("--out", default="results_combo")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True); TG = json.load(open(a.targets)); j = a.judge; nj = a.threads
    A, Y, G, B, FIN, IDS, F, CONS = [], [], [], [], [], [], [], []
    for b in BENCH:
        _, p = load_run(a.results, j, b, "uncertainty__n1_t0.0"); itm = pd.read_csv(f"{p}_items.csv", dtype={"item_id": str}); ids = list(itm["item_id"]); L = gen(f"{p}_gen.jsonl").set_index("item_id").loc[ids]
        A.append(np.load(f"{p}_acts.npy").astype(np.float32)); Y.append(L["correct"].values.astype(int)); FIN.append(L["verdict"].notna().values)
        G += [f"{b}|{x}" for x in itm["group"].astype(str)]; B += [b] * len(ids); IDS += ids
        T = pd.read_csv(f"{p}_tokstats.csv", dtype={"item_id": str}).set_index("item_id").reindex(ids)
        feats = {"verdict_good": (L["verdict"].values == 1.0).astype(float) if b != "judgebench" else (L["verdict"].astype(str).values == "A").astype(float),
                 "mean_logprob": T["mean_logprob"].values, "mean_entropy": T["mean_entropy"].values, "verdict_prob": T["verdict_prob"].values, "log_len": np.log1p(T["n_gen"].values)}
        _, pe = load_run(a.results, j, b, "error__n1_t0.0")
        if b in EVAL and os.path.exists(f"{pe}_gen.jsonl"):
            E = gen(f"{pe}_gen.jsonl").set_index("item_id").reindex(ids); fe = E["verdict"].notna().values
            feats["err_says_good"] = (E["verdict"].values == 1.0).astype(float); feats["disagree"] = (~(L["verdict"].notna().values & fe) | (L["verdict"].values != E["verdict"].values)).astype(float)
        F.append(pd.DataFrame(feats))
        _, ps = load_run(a.results, j, b, "uncertainty__n10_t0.7"); S = gen(f"{ps}_gen.jsonl"); gv = L["verdict"]; cons = np.zeros(len(ids)); pos = {i: k for k, i in enumerate(ids)}
        for iid, d in S.groupby("item_id"):
            if iid in pos and pd.notna(gv.iloc[pos[iid]]): cons[pos[iid]] = float((d["verdict"] == gv.iloc[pos[iid]]).sum()) / len(d)
        CONS.append(cons)
    A = np.concatenate(A); Y = np.concatenate(Y); FIN = np.concatenate(FIN); G = np.array(G); B = np.array(B); IDS = np.array(IDS); CONS = np.concatenate(CONS)
    FT = pd.concat(F, ignore_index=True).fillna(0.0); n = len(Y); SC = {v: np.zeros((a.seeds, n)) for v in ["V1", "V2", "V3", "V4"]}
    logit = lambda p: np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))
    for seed in range(a.seeds):
        rng = np.random.default_rng(seed); ug = rng.permutation(np.unique(G)); fold_of = {g: i % 5 for i, g in enumerate(ug)}; f = np.array([fold_of[g] for g in G])
        for k in range(5):
            te, tr = np.where(f == k)[0], np.where(f != k)[0]
            p1_te = probe(A, Y, tr, te, nj); SC["V1"][seed, te] = p1_te; m1 = crossfit(A, Y, tr, G, nj, seed + k)   # pooled probe, cross-fitted on training items
            for b in EVAL:
                trb, teb = tr[B[tr] == b], te[B[te] == b]
                p2_te = probe(A, Y, trb, teb, nj); SC["V2"][seed, teb] = p2_te
                p1_tr = m1[B[tr] == b]
                p2_tr = crossfit(A, Y, trb, G, nj, seed + k)                                                                # per-benchmark probe, cross-fitted
                cols = [c for c in FT.columns if FT[c].iloc[np.r_[trb, teb]].std() > 0]
                for v, ptr, pte in [("V3", p1_tr, p1_te[B[te] == b]), ("V4", p2_tr, p2_te)]:
                    Xtr = np.c_[logit(ptr), FT.iloc[trb][cols].values]; Xte = np.c_[logit(pte), FT.iloc[teb][cols].values]
                    sc = StandardScaler().fit(Xtr); SC[v][seed, teb] = LogisticRegression(C=1.0, max_iter=2000).fit(sc.transform(Xtr), Y[trb]).predict_proba(sc.transform(Xte))[:, 1]
            print(f"{j} seed {seed} fold {k} done", flush=True)
    rows = []; tie = np.random.default_rng(12345).random(n)
    for b in EVAL:
        m = B == b; ol, fin, t, g = Y[m], FIN[m], tie[m], G[m]; oh = np.array([TG[j][b][i] for i in IDS[m]]); good = FT["verdict_good"].values[m].astype(bool); nb = m.sum()
        def scores(idx):
            o, h, fi, tt = ol[idx], oh[idx], fin[idx], t[idx]
            r = {v: np.mean([esc_acc(SC[v][s, m][idx], o, h, fi, tt) for s in range(a.seeds)]) for v in SC}
            r["reruns10"] = esc_acc(CONS[m][idx], o, h, fi, tt); r["verdict_only"] = np.mean([esc_acc((np.where(good, 0, 1) + 0.5 * np.random.default_rng(s).random(nb))[idx], o, h, fi, tt) for s in range(20)])
            return r
        full = scores(np.arange(nb)); ug = np.unique(g); gi = {x: np.where(g == x)[0] for x in ug}; rb = np.random.default_rng(7); D = {"V4-V1": [], "V4-reruns": [], "V3-V1": [], "V2-V1": []}
        for _ in range(a.n_boot):
            s_ = scores(np.concatenate([gi[x] for x in rb.choice(ug, len(ug))]))
            D["V4-V1"].append(s_["V4"] - s_["V1"]); D["V4-reruns"].append(s_["V4"] - s_["reruns10"]); D["V3-V1"].append(s_["V3"] - s_["V1"]); D["V2-V1"].append(s_["V2"] - s_["V1"])
        row = dict(judge=j, bench=b, random=(ol.mean() + 0.2 * (oh.mean() - ol.mean())) * 100, **{k_: v_ * 100 for k_, v_ in full.items()})
        for k_, v_ in D.items():
            v_ = np.array(v_) * 100; obs = {"V4-V1": full["V4"] - full["V1"], "V4-reruns": full["V4"] - full["reruns10"], "V3-V1": full["V3"] - full["V1"], "V2-V1": full["V2"] - full["V1"]}[k_] * 100
            row[k_] = f"{obs:+.1f} [{np.percentile(v_, 2.5):+.1f},{np.percentile(v_, 97.5):+.1f}]"; row[k_ + "_lo"] = np.percentile(v_, 2.5)
        rows.append(row)
    R = pd.DataFrame(rows); R.to_csv(os.path.join(a.out, f"combo_{j}.csv"), index=False); pd.set_option("display.width", 260)
    print(R[[c for c in R.columns if not c.endswith("_lo")]].round(1).to_string(index=False))


if __name__ == "__main__":
    main()
