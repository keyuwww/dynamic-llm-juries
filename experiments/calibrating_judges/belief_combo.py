#!/usr/bin/env python
"""Does the team's belief signal ('the judge approves what it already believes', from 7 solve attempts) improve escalation over the better probe?

BFF, cheap judges Qwen3.5-4B and Qwen3.5-9B (the judges with belief data). Belief rows: targets/belief_rows_clean.json (anchoring_early_answer).
Per item: belief = share of the judge's 7 own solves that reach the candidate's answer; match0 = first solve matches; follows = our verdict agrees with
belief (said CORRECT and belief >= 0.5, or INCORRECT and belief < 0.5); |belief - 0.5|; missing flag (26 items have no belief row, filled with 0.5).
Methods, all with combiners trained on training questions only (5 folds by question over the three benchmarks, as confirm_probe.py; 3 seeds):
  probe          the better probe (logistic regression at every layer, averaged; pooled training over the three benchmarks)
  belief         logistic regression on the belief features + verdict
  probe+belief   logistic regression on logit(probe, cross-fitted on training items) + belief features + verdict   (PRIMARY)
Baselines: 10 reruns, verdict-only rule, random. Accuracy with 20% escalated (also 10% and 30%), unfinished answers first.
Pre-registered pass bar: probe+belief beats probe at 20% with the 95% paired bootstrap CI above 0 for at least 1 of the 2 judges.
Runs on Modal CPU (modal_generate.py::script)."""
import argparse, json, os, warnings
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from cascade_eval import gen, load_run, BENCH
from combo_probe import probe, crossfit
warnings.filterwarnings("ignore")


def esc_acc(trust, ol, oh, fin, tie, rate=0.2):
    n = len(ol); m = int(round(rate * n)); k = np.lexsort((tie, np.where(~fin, -1e9, trust))); e = np.zeros(n, bool); e[k[:m]] = True
    return np.where(e, oh, ol).mean()


def lr(Xtr, ytr, Xte):
    sc = StandardScaler().fit(Xtr); return LogisticRegression(C=1.0, max_iter=2000).fit(sc.transform(Xtr), ytr).predict_proba(sc.transform(Xte))[:, 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", required=True); ap.add_argument("--results", default="local_results"); ap.add_argument("--targets", default="targets/strong_judge_correct.json")
    ap.add_argument("--belief", default="targets/belief_rows_clean.json"); ap.add_argument("--bench", default="bff"); ap.add_argument("--cheap", action="store_true", help="replace the 7-solve belief by the one-pass candidate log-probability (cand_logprob.py)"); ap.add_argument("--seeds", type=int, default=3); ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--threads", type=int, default=8); ap.add_argument("--out", default="results_belief")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True); TG = json.load(open(a.targets)); j = a.judge; nj = a.threads
    BR = pd.DataFrame(json.load(open(a.belief))); BR = BR[(BR.bench == a.bench) & (BR.judge == j.lower())].copy()
    BR["item"] = BR["item"].astype(str).str.replace(r"^judgebench-(claude|gpt)-", "", regex=True); BR = BR.drop_duplicates("item").set_index("item")   # JudgeBench ids: strip the split prefix
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
    bel = np.array([float(BR.loc[i, "belief"]) if i in BR.index else 0.5 for i in IDS]); miss = np.array([0.0 if i in BR.index else 1.0 for i in IDS])
    m0 = np.array([float(BR.loc[i, "match0"]) if i in BR.index else 0.5 for i in IDS]); follows = ((VG == 1) == (bel >= 0.5)).astype(float) * (1 - miss) * (a.bench != "judgebench")   # undefined for pairwise verdicts
    FB = np.c_[bel, m0, np.abs(bel - 0.5), follows, miss, VG]
    if a.cheap:                                                                    # one forward pass: how likely the judge model finds the candidate's response
        C = pd.read_csv(f"{a.results}/{j}__bff__candlp/{j}__bff__candlp.csv", dtype={"item_id": str}).set_index("item_id")
        cl = np.array([[C.loc[i, "mean_lp"], C.loc[i, "min_lp"], np.log(C.loc[i, "n_tok"])] if i in C.index else [0.0, 0.0, 0.0] for i in IDS])
        FB = np.c_[cl, VG, cl[:, 0] * VG]; print(f"{j}: cheap belief; corr(mean_lp, 7-solve belief) on BFF = {np.corrcoef(cl[B == 'bff', 0][miss[B == 'bff'] == 0], bel[B == 'bff'][miss[B == 'bff'] == 0])[0, 1]:.2f}", flush=True); m_bff = B == a.bench; print(f"{j}: belief rows for {int((1 - miss[m_bff]).sum())} of {int(m_bff.sum())} {a.bench} items", flush=True)
    logit = lambda p: np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))
    SC = {v: np.zeros((a.seeds, n)) for v in ["probe", "belief", "probe+belief"]}
    for seed in range(a.seeds):
        rng = np.random.default_rng(seed); ug = rng.permutation(np.unique(G)); fold_of = {g: i % 5 for i, g in enumerate(ug)}; f = np.array([fold_of[g] for g in G])
        for k in range(5):
            te, tr = np.where(f == k)[0], np.where(f != k)[0]; p_te = probe(A, Y, tr, te, nj); SC["probe"][seed, te] = p_te
            p_tr = crossfit(A, Y, tr, G, nj, seed + k); trb, mte = tr[B[tr] == a.bench], B[te] == a.bench; teb = te[mte]
            SC["belief"][seed, teb] = lr(FB[trb], Y[trb], FB[teb])
            SC["probe+belief"][seed, teb] = lr(np.c_[logit(p_tr[B[tr] == a.bench]), FB[trb]], Y[trb], np.c_[logit(p_te[mte]), FB[teb]])
            print(f"{j} seed {seed} fold {k} done", flush=True)
    m = m_bff; ol, fin, g = Y[m], FIN[m], G[m]; oh = np.array([TG[j][a.bench][i] for i in IDS[m]]); good = VG[m].astype(bool); nb = m.sum(); tie = np.random.default_rng(12345).random(nb)
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
                s_ = scores(np.concatenate([gi[x] for x in rb.choice(ugs, len(ugs))])); D.append([s_["probe+belief"] - s_["probe"], s_["belief"] - s_["probe"], s_["probe+belief"] - s_["reruns10"]])
            D = np.array(D) * 100; lo, hi = np.percentile(D, 2.5, 0), np.percentile(D, 97.5, 0)
            obs = [full["probe+belief"] - full["probe"], full["belief"] - full["probe"], full["probe+belief"] - full["reruns10"]]
            for nm, o_, l_, u_ in zip(["combo_minus_probe", "belief_minus_probe", "combo_minus_reruns"], obs, lo, hi): row[nm] = f"{o_*100:+.1f} [{l_:+.1f},{u_:+.1f}]"
        rows.append(row)
    R = pd.DataFrame(rows); R.to_csv(os.path.join(a.out, f"belief_{j}_{a.bench}{'_cheap' if a.cheap else ''}.csv"), index=False); pd.set_option("display.width", 260); print(R.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
