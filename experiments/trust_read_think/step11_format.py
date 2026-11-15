#!/usr/bin/env python3
"""
Step 11 of Trust / Read / Think: predict the task format (recognize vs solve) and route on it.

Probe -> think wins on recognize tasks; the cascade (calibrated gut + probe) -> think wins on solve tasks. So:
  format probe   logistic regression on the judge's hidden state at the verdict position (mid depth), label
                 recognize = {safety, focus, factuality}, solve = {math, bff}. Leave-one-benchmark-out: the probe that
                 routes a benchmark never saw that benchmark (or its format label). (cf. "Linear probes detect task
                 format", arXiv 2606.02907)
  format-aware   per item: predicted recognize -> probe verdict; predicted solve -> cascade verdict (more confident
                 of calibrated gut / probe). Then think on the 20% least confident items overall.
Compared with: probe->think, cascade (v3)->think, gut->think, think on all, and an oracle that knows each benchmark's
true format. Same 100-label draws as Steps 7 and 9; 95% CIs from paired bootstrap over questions.

  JUDGE=<judge> .venv/bin/python experiments/trust_read_think/step11_format.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
from paths import RES, JUDGE  # noqa: E402
from step2 import probe
from step5 import pick_layer
from step6 import load, draw_labels

BENCHES = ("safety", "focus", "math", "bff", "factuality")
SOLVE = {"math", "bff"}
N_LAB, DRAWS, Q, B_BOOT = 100, 10, 0.2, 2000
POLS = ("format_aware", "oracle_format", "probe_think", "cascade_think", "gut_think", "think")
conf = lambda p: np.abs(2 * p - 1)
lg = lambda p: np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))


def format_scores(D):
    """P(solve) per item, leave-one-benchmark-out, from the hidden state at mid depth."""
    nL = D[BENCHES[0]]["hs"].shape[1] - 1
    L = max(1, round(nL / 2))
    out = {}
    for b in BENCHES:
        tr = [o for o in BENCHES if o != b]
        X = np.concatenate([D[o]["hs"][:, L] for o in tr])
        y = np.concatenate([np.full(len(D[o]["y"]), int(o in SOLVE)) for o in tr])
        w = np.concatenate([np.full(len(D[o]["y"]), 1 / len(D[o]["y"])) for o in tr])   # each benchmark weighs the same
        m = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=3000))
        m.fit(X, y, logisticregression__sample_weight=w * len(y) / w.sum())
        out[b] = m.predict_proba(D[b]["hs"][:, L])[:, 1]
    return out


def route(base, conf_base, think, k):
    s = base.copy()
    o = np.argsort(conf_base, kind="stable")[:k]
    s[o] = think[o]
    return s


def one_draw(d, psolve, is_solve, seed):
    y, g, hs, gut, think = d["y"], d["g"], d["hs"], d["gut"], d["think"]
    lab = draw_labels(g, np.random.default_rng(seed), N_LAB)
    te = np.setdiff1d(np.arange(len(y)), lab)
    L = pick_layer(hs[lab], y[lab], g[lab], 20)
    oof = np.zeros(len(lab))
    for a, c in GroupKFold(5).split(lab, y[lab], g[lab]):
        oof[c] = probe().fit(hs[lab[a], L], y[lab[a]]).decision_function(hs[lab[c], L])
    platt = LogisticRegression(C=1e4).fit(oof[:, None], y[lab])
    pr = platt.predict_proba(probe().fit(hs[lab, L], y[lab]).decision_function(hs[te, L])[:, None])[:, 1]
    gc = LogisticRegression(C=1e4).fit(lg(gut[lab])[:, None], y[lab]).predict_proba(lg(gut[te])[:, None])[:, 1]
    tt, k = think[te], int(round(Q * len(te)))
    casc = np.where(conf(gc) >= conf(pr), gc, pr)
    casc_c = np.maximum(conf(gc), conf(pr))
    solve = psolve[te] > 0.5
    fa = np.where(solve, casc, pr)
    fa_c = np.where(solve, casc_c, conf(pr))
    orc = casc if is_solve else pr
    orc_c = casc_c if is_solve else conf(pr)
    pol = dict(format_aware=route(fa, fa_c, tt, k), oracle_format=route(orc, orc_c, tt, k),
               probe_think=route(pr, conf(pr), tt, k), cascade_think=route(casc, casc_c, tt, k),
               gut_think=route(gc, conf(gc), tt, k), think=tt)
    return te, {p: ((s > 0.5) == y[te]).astype(float) for p, s in pol.items()}


def main():
    D = load()
    ps = format_scores(D)
    fmt = {b: dict(true="solve" if b in SOLVE else "recognize", share_predicted_solve=round(float((ps[b] > 0.5).mean()), 3))
           for b in BENCHES}
    print("format probe (leave-one-benchmark-out):", json.dumps(fmt), flush=True)
    C = {}
    for b in BENCHES:
        n = len(D[b]["y"])
        tot, cnt = {p: np.zeros(n) for p in POLS}, np.zeros(n)
        for seed in range(DRAWS):
            te, corr = one_draw(D[b], ps[b], b in SOLVE, seed)
            for p in POLS:
                tot[p][te] += corr[p]
            cnt[te] += 1
        C[b] = {p: tot[p] / np.where(cnt == 0, np.nan, cnt) for p in POLS}
    rng = np.random.default_rng(0)
    boots = {}
    for b in BENCHES:
        g = D[b]["g"]
        ug = np.unique(g)
        idx = {q: np.where(g == q)[0] for q in ug}
        boots[b] = [{p: np.nanmean(C[b][p][ii]) for p in POLS}
                    for ii in (np.concatenate([idx[q] for q in rng.choice(ug, len(ug))]) for _ in range(B_BOOT))]
    ci = lambda x: [round(float(np.percentile(x, 2.5)), 3), round(float(np.percentile(x, 97.5)), 3)]
    res = dict(judge=JUDGE, format=fmt, benches={})
    for b in list(BENCHES) + ["all"]:
        if b == "all":
            get = lambda p: np.mean([[x[p] for x in boots[bb]] for bb in BENCHES], 0)
            acc = {p: round(float(np.mean([np.nanmean(C[bb][p]) for bb in BENCHES])), 3) for p in POLS}
        else:
            get = lambda p, b=b: np.array([x[p] for x in boots[b]])
            acc = {p: round(float(np.nanmean(C[b][p])), 3) for p in POLS}
        res["benches"][b] = dict(acc=acc, format_aware_minus={p: dict(d=round(acc["format_aware"] - acc[p], 3),
                                                                       ci=ci(get("format_aware") - get(p)))
                                                              for p in POLS if p != "format_aware"})
        print(f"{b:10s} " + "  ".join(f"{p} {v}" for p, v in acc.items()), flush=True)
    print("format_aware minus (all):", json.dumps(res["benches"]["all"]["format_aware_minus"]))
    (RES / "step11_format.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
