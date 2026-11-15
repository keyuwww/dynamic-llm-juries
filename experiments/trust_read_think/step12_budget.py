#!/usr/bin/env python3
"""
Step 12 of Trust / Read / Think: move the thinking budget to solve-type tasks.

Thinking hurts on recognize tasks and helps on solve tasks, yet Steps 7-11 spent the same 20% on every benchmark.
Here the overall budget stays at 20% of all test items (all 5 benchmarks pooled) but is allocated differently:
  uniform 20%          probe -> think, 20% on every benchmark (the current policy)
  pooled confidence    probe -> think, the 20% least confident items across all benchmarks (no format knowledge)
  format (predicted)   leave-one-benchmark-out format probe (Step 11): items predicted solve use the cascade verdict
                       (calibrated gut / probe) and receive all of the thinking budget; predicted recognize items use
                       the probe and never think
  format (known)       the same with each benchmark's true format (upper bound for format routing)
Same 100-label draws, probe and gut calibration as Steps 9 and 11. Accuracy is the mean of the 5 benchmark accuracies;
95% CIs from paired bootstrap over questions.

  JUDGE=<judge> .venv/bin/python experiments/trust_read_think/step12_budget.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

warnings.filterwarnings("ignore")
from paths import RES, JUDGE  # noqa: E402
from step2 import probe
from step5 import pick_layer
from step6 import load, draw_labels
from step11_format import format_scores, BENCHES, SOLVE

N_LAB, DRAWS, Q, B_BOOT = 100, 10, 0.2, 2000
POLS = ("uniform", "pooled_conf", "format_predicted", "format_known")
conf = lambda p: np.abs(2 * p - 1)
lg = lambda p: np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))


def reads(d, seed):
    y, g, hs, gut = d["y"], d["g"], d["hs"], d["gut"]
    lab = draw_labels(g, np.random.default_rng(seed), N_LAB)
    te = np.setdiff1d(np.arange(len(y)), lab)
    L = pick_layer(hs[lab], y[lab], g[lab], 20)
    oof = np.zeros(len(lab))
    for a, c in GroupKFold(5).split(lab, y[lab], g[lab]):
        oof[c] = probe().fit(hs[lab[a], L], y[lab[a]]).decision_function(hs[lab[c], L])
    platt = LogisticRegression(C=1e4).fit(oof[:, None], y[lab])
    pr = platt.predict_proba(probe().fit(hs[lab, L], y[lab]).decision_function(hs[te, L])[:, None])[:, 1]
    gc = LogisticRegression(C=1e4).fit(lg(gut[lab])[:, None], y[lab]).predict_proba(lg(gut[te])[:, None])[:, 1]
    return te, pr, gc


def main():
    D = load()
    ps = format_scores(D)
    C = {b: {p: np.zeros(len(D[b]["y"])) for p in POLS} for b in BENCHES}
    cnt = {b: np.zeros(len(D[b]["y"])) for b in BENCHES}
    share = {p: {b: [] for b in BENCHES} for p in POLS}
    for seed in range(DRAWS):
        R = {b: reads(D[b], seed) for b in BENCHES}
        # pool all test items of all benchmarks for this draw
        bench = np.concatenate([[b] * len(R[b][0]) for b in BENCHES])
        idx = np.concatenate([R[b][0] for b in BENCHES])
        y = np.concatenate([D[b]["y"][R[b][0]] for b in BENCHES])
        pr = np.concatenate([R[b][1] for b in BENCHES])
        gc = np.concatenate([R[b][2] for b in BENCHES])
        tt = np.concatenate([D[b]["think"][R[b][0]] for b in BENCHES])
        psolve = np.concatenate([ps[b][R[b][0]] > 0.5 for b in BENCHES])
        known = np.array([b in SOLVE for b in bench])
        casc, casc_c = np.where(conf(gc) >= conf(pr), gc, pr), np.maximum(conf(gc), conf(pr))
        K = int(round(Q * len(y)))
        out = {}
        # uniform: 20% within each benchmark
        s = pr.copy()
        for b in BENCHES:
            m = np.where(bench == b)[0]
            o = m[np.argsort(conf(pr[m]), kind="stable")[:int(round(Q * len(m)))]]
            s[o] = tt[o]
        out["uniform"] = (s, None)
        s = pr.copy()
        o = np.argsort(conf(pr), kind="stable")[:K]
        s[o] = tt[o]
        out["pooled_conf"] = (s, o)
        for name, solve in (("format_predicted", psolve), ("format_known", known)):
            base, bc = np.where(solve, casc, pr), np.where(solve, casc_c, conf(pr))
            sol = np.where(solve)[0]
            o = sol[np.argsort(bc[sol], kind="stable")[:K]]          # the whole budget goes to solve items
            s = base.copy()
            s[o] = tt[o]
            out[name] = (s, o)
        for p, (s, o) in out.items():
            corr = ((s > 0.5) == y).astype(float)
            thought = np.zeros(len(y), bool)
            if o is not None:
                thought[o] = True
            for b in BENCHES:
                m = bench == b
                C[b][p][idx[m]] += corr[m]
                share[p][b].append(float(thought[m].mean()) if o is not None else Q)
        for b in BENCHES:
            cnt[b][R[b][0]] += 1
    acc_item = {b: {p: C[b][p] / np.where(cnt[b] == 0, np.nan, cnt[b]) for p in POLS} for b in BENCHES}
    rng = np.random.default_rng(0)
    boots = {}
    for b in BENCHES:
        g = D[b]["g"]
        ug = np.unique(g)
        ix = {q: np.where(g == q)[0] for q in ug}
        boots[b] = [{p: np.nanmean(acc_item[b][p][ii]) for p in POLS}
                    for ii in (np.concatenate([ix[q] for q in rng.choice(ug, len(ug))]) for _ in range(B_BOOT))]
    ci = lambda x: [round(float(np.percentile(x, 2.5)), 3), round(float(np.percentile(x, 97.5)), 3)]
    res = dict(judge=JUDGE, budget=Q, benches={})
    for b in list(BENCHES) + ["all"]:
        if b == "all":
            get = lambda p: np.mean([[x[p] for x in boots[bb]] for bb in BENCHES], 0)
            acc = {p: round(float(np.mean([np.nanmean(acc_item[bb][p]) for bb in BENCHES])), 3) for p in POLS}
            sh = None
        else:
            get = lambda p, b=b: np.array([x[p] for x in boots[b]])
            acc = {p: round(float(np.nanmean(acc_item[b][p])), 3) for p in POLS}
            sh = {p: round(float(np.mean(share[p][b])), 3) for p in POLS}
        res["benches"][b] = dict(acc=acc, think_share=sh,
                                 minus_uniform={p: dict(d=round(acc[p] - acc["uniform"], 3),
                                                        ci=ci(get(p) - get("uniform"))) for p in POLS if p != "uniform"})
        print(f"{b:10s} acc {acc}  think share {sh}", flush=True)
    print("vs uniform (all):", json.dumps(res["benches"]["all"]["minus_uniform"]))
    (RES / "step12_budget.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
