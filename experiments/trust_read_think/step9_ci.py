#!/usr/bin/env python3
"""
Confidence intervals for the cascade comparison (Step 7 setup, thinking on 20% of items, 1,024 tokens).

For each benchmark, 10 draws of 100 labelled items; each test item's correctness under each policy is averaged over the
draws in which it was a test item. 95% CIs of accuracy differences come from 2,000 bootstrap resamples of questions
(paired: the same resample for every policy). "All five" averages the five benchmark accuracies in each resample.

  .venv/bin/python experiments/trust_read_think/step9_ci.py
"""
import json
import warnings
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")
import step7
from step6 import load, draw_labels

HERE = Path(__file__).resolve().parent
from paths import RAW, RES, ITEMS  # noqa: E402
BENCHES = step7.BENCHES
Q, B_BOOT = 0.2, 2000
POLS = ("cascade", "cascade_cal", "gut_think", "probe_think", "router_think", "gut", "probe", "think")


def per_item(d):
    """Mean correctness per item per policy over the draws (NaN where never a test item)."""
    n = len(d["y"])
    tot = {p: np.zeros(n) for p in POLS}
    cnt = np.zeros(n)
    for seed in range(step7.DRAWS):
        lab = draw_labels(d["g"], np.random.default_rng(seed), step7.N_LAB)
        te = np.setdiff1d(np.arange(n), lab)
        sc = step7_scores(d, lab, te)
        for p in POLS:
            tot[p][te] += ((sc[p] > 0.5) == d["y"][te])
        cnt[te] += 1
    return {p: tot[p] / np.where(cnt == 0, np.nan, cnt) for p in POLS}


def step7_scores(d, lab, te):
    """Re-implements step7.one_draw's policies at Q and returns the final scores per policy."""
    import step7 as s7
    from sklearn.decomposition import PCA
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.model_selection import GroupKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    y, g, hs, gut, think = d["y"], d["g"], d["hs"], d["gut"], d["think"]
    L = s7.pick_layer(hs[lab], y[lab], g[lab], 20)
    oof = np.zeros(len(lab))
    for a, c in GroupKFold(5).split(lab, y[lab], g[lab]):
        oof[c] = s7.probe().fit(hs[lab[a], L], y[lab[a]]).decision_function(hs[lab[c], L])
    platt = LogisticRegression(C=1e4).fit(oof[:, None], y[lab])
    pr = platt.predict_proba(s7.probe().fit(hs[lab, L], y[lab]).decision_function(hs[te, L])[:, None])[:, 1]
    conf = s7.conf
    pca = make_pipeline(StandardScaler(), PCA(16, random_state=0)).fit(hs[lab, L])
    f = lambda idx: np.c_[conf(gut[idx]), gut[idx], pca.transform(hs[idx, L])]
    gain = ((think[lab] > 0.5) == y[lab]).astype(float) - ((gut[lab] > 0.5) == y[lab]).astype(float)
    rgain = Ridge(alpha=10.0).fit(f(lab), gain).predict(f(te))
    gt, tt = gut[te], think[te]
    k = int(round(Q * len(te)))
    mc = np.maximum(conf(gt), conf(pr))
    # cascade v3 (added after the gpt-oss / Nemotron runs): Platt-calibrate the gut on the labelled items as well, so
    # "more confident" compares two calibrated probabilities instead of an overconfident gut against a calibrated probe
    lg = lambda p: np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
    gc = LogisticRegression(C=1e4).fit(lg(gut[lab])[:, None], y[lab]).predict_proba(lg(gt)[:, None])[:, 1]
    mcc = np.maximum(conf(gc), conf(pr))
    cascade_cal = s7.route(np.where(conf(gc) >= conf(pr), gc, pr), tt, np.argsort(mcc, kind="stable"), k)
    return dict(cascade_cal=cascade_cal, cascade=s7.route(np.where(conf(gt) >= conf(pr), gt, pr), tt, np.argsort(mc, kind="stable"), k),
                gut_think=s7.route(gt, tt, np.argsort(conf(gt), kind="stable"), k),
                probe_think=s7.route(pr, tt, np.argsort(conf(pr), kind="stable"), k),
                router_think=s7.route(gt, tt, np.argsort(-rgain, kind="stable"), k),
                gut=gt, probe=pr, think=tt)


def main():
    D = load()
    C, G = {}, {}
    for b in BENCHES:
        C[b] = per_item(D[b])
        G[b] = D[b]["g"]
    rng = np.random.default_rng(0)
    boots = {b: [] for b in BENCHES}
    for b in BENCHES:
        ug = np.unique(G[b])
        idx = {q: np.where(G[b] == q)[0] for q in ug}
        for _ in range(B_BOOT):
            ii = np.concatenate([idx[q] for q in rng.choice(ug, len(ug))])
            boots[b].append({p: np.nanmean(C[b][p][ii]) for p in POLS})
    ci = lambda a: [round(float(np.percentile(a, 2.5)), 3), round(float(np.percentile(a, 97.5)), 3)]
    res = {}
    for b in list(BENCHES) + ["all"]:
        get = (lambda p: np.array([x[p] for x in boots[b]])) if b != "all" else \
            (lambda p: np.mean([[x[p] for x in boots[bb]] for bb in BENCHES], 0))
        point = {p: round(float(np.nanmean(C[b][p])), 3) for p in POLS} if b != "all" else \
            {p: round(float(np.mean([np.nanmean(C[bb][p]) for bb in BENCHES])), 3) for p in POLS}
        res[b] = dict(acc=point, acc_ci={p: ci(get(p)) for p in POLS},
                      cascade_minus={p: dict(d=round(point["cascade"] - point[p], 3), ci=ci(get("cascade") - get(p)))
                                     for p in POLS if p != "cascade"},
                      cascade_cal_minus={p: dict(d=round(point["cascade_cal"] - point[p], 3),
                                                 ci=ci(get("cascade_cal") - get(p))) for p in POLS if p != "cascade_cal"})
        print(b, json.dumps(res[b]["cascade_minus"]), flush=True)
    (RES / "step9_ci.json").write_text(json.dumps(dict(think_share=Q, results=res), indent=1))


if __name__ == "__main__":
    main()
