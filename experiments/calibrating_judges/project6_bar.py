#!/usr/bin/env python
"""Project 6: be stricter on questions that look hard. Team data only (anchoring_early_answer belief rows, clean labels); tiny, CPU.
Per (judge, candidate answer): m_C = the judge's verdict log-odds of accepting the answer (readout at its verdict); target_ok = the answer is right;
belief = share of the judge's 7 own solves that reach this answer. Label-free hardness = 1 - 2|belief - 0.5| (the judge's own solves are split),
averaged over the question's candidates (question-level) so it is known before grading any one answer.
  spoken       the judge's written verdict (acc_C)
  fixed bar    accept if m_C > t,                 t fitted on the training questions (maximise accuracy)
  adjusted bar accept if m_C > t0 + t1 * hardness, (t0, t1) fitted on the training questions (PRIMARY, fixed before running)
50 random 50/50 splits by question; accuracy on the test half. Pre-registered pass bar: adjusted beats fixed by >= 1 point with the 95% interval
over splits above 0 in at least 4 of the 9 judge x benchmark settings."""
import json, itertools, numpy as np, pandas as pd
R = pd.DataFrame(json.load(open("targets/belief_rows_clean.json")))
for c in ["m_C", "belief", "target_ok", "acc_C"]: R[c] = pd.to_numeric(R[c], errors="coerce")
R = R.dropna(subset=["m_C", "belief", "target_ok"]); R["qid"] = R["item"].astype(str).str.replace(r"-(chosen|rejected)\d+$", "", regex=True).str.replace(r"-t\d$", "", regex=True)
R["hard_item"] = 1 - 2 * (R["belief"] - 0.5).abs(); R["hard"] = R.groupby(["judge", "bench", "qid"])["hard_item"].transform("mean")
T = np.linspace(-8, 8, 161); S1 = np.linspace(-8, 8, 81); rows = []
for (j, b), d in R.groupby(["judge", "bench"]):
    q = d["qid"].unique(); y = d["target_ok"].values.astype(int); m = d["m_C"].values; h = d["hard"].values; sp = d["acc_C"].values; res = []
    for s in range(50):
        rq = np.random.default_rng(s).permutation(q); trq = set(rq[: len(q) // 2]); tr = d["qid"].isin(trq).values; te = ~tr
        acc = lambda acc_, idx: ((acc_ == y)[idx]).mean()
        t = T[np.argmax([acc((m > t_).astype(int), tr) for t_ in T])]
        best = max(((t0, t1) for t0 in T[::2] for t1 in S1[::2]), key=lambda p: acc((m > p[0] + p[1] * h).astype(int), tr))
        res.append([acc((m > t).astype(int), te), acc((m > best[0] + best[1] * h).astype(int), te), np.nanmean((sp == y)[te]) if np.isfinite(sp).any() else np.nan])
    res = np.array(res) * 100; diff = res[:, 1] - res[:, 0]
    rows.append(dict(judge=j, bench=b, n=len(d), spoken=np.nanmean(res[:, 2]), fixed_bar=res[:, 0].mean(), adjusted_bar=res[:, 1].mean(), gain=diff.mean(), lo=np.percentile(diff, 2.5), hi=np.percentile(diff, 97.5)))
O = pd.DataFrame(rows); pd.set_option("display.width", 200); print(O.round(1).to_string(index=False))
k = int(((O.gain >= 1) & (O.lo > 0)).sum()); print(f"\nPRE-REGISTERED (adjusted beats fixed by >= 1 pt, interval above 0, in >= 4 of 9): {k} -> {'PASS' if k >= 4 else 'FAIL'}")
