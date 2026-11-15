#!/usr/bin/env python3
"""
Step 7 of Trust / Read / Think: the three-step cascade, end to end, per item.

  item -> Gut (thinking off)      confident?  -> keep the gut verdict         (Trust)
       -> Probe (same forward pass) confident? -> use the probe's verdict     (Read)
       -> Think (1,024 tokens)                                               (Think)

Per benchmark, 10 random draws: 100 labelled items (whole questions) train the probe; everything else is the test set.
  probe        standardize + L2 logistic (C = 0.3) at the layer picked by inner CV (Step 5); Platt-calibrated on
               cross-fitted scores of the labelled items (as in LLMs Encode Their Failures), so its confidence is honest
  gut gate     keep the gut where its confidence |2P - 1| >= t_g; t_g is the lowest threshold at which, on the
               labelled items, the gut is at least as accurate as the cross-fitted probe on those same items
  think budget q of the test items (10 / 20 / 30 / 50%): the least confident probe items among those the gut did
               not keep go to Think; the rest are Read. If fewer items are left than the budget, all of them think.
Baselines at the same thinking share:
  gut->think       gut verdict, think on the least confident gut items (Isaac / Minh style escalation)
  probe->think     probe verdict, think on the least confident probe items
  router->think    Think When Needed-style router (arXiv 2601.18146): ridge regression of the gain from thinking
                   (think right - gut right) on [gut confidence, gut P, 16 PCA components of the hidden state], fit on the
                   labelled items (thinking run on them); think on the items with the largest predicted gain
  gut, probe, think   no routing
Reported: accuracy and same-source AUROC on the test items, actual thinking share, share of items ending at each step.

  .venv/bin/python experiments/trust_read_think/step7.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
from step2 import strata_auc, probe
from step5 import pick_layer
from step6 import load, draw_labels

HERE = Path(__file__).resolve().parent
from paths import RAW, RES, ITEMS  # noqa: E402
BENCHES = ("safety", "focus", "math", "bff", "factuality")
N_LAB, DRAWS, QS = 100, 10, (0.1, 0.2, 0.3, 0.5)


def conf(p):
    return np.abs(2 * p - 1)


def route(base_p, think_p, order, k):
    """Final scores: base everywhere, think on the first k items of order."""
    out = base_p.copy()
    out[order[:k]] = think_p[order[:k]]
    return out


def one_draw(d, seed):
    y, g, st, hs, gut, think = d["y"], d["g"], d["st"], d["hs"], d["gut"], d["think"]
    rng = np.random.default_rng(seed)
    lab = draw_labels(g, rng, N_LAB)
    te = np.setdiff1d(np.arange(len(y)), lab)
    L = pick_layer(hs[lab], y[lab], g[lab], 20)
    # cross-fitted probe logits on the labelled items -> Platt scaling
    oof = np.zeros(len(lab))
    for a, c in GroupKFold(5).split(lab, y[lab], g[lab]):
        oof[c] = probe().fit(hs[lab[a], L], y[lab[a]]).decision_function(hs[lab[c], L])
    platt = LogisticRegression(C=1e4).fit(oof[:, None], y[lab])
    pr_lab = platt.predict_proba(oof[:, None])[:, 1]
    full = probe().fit(hs[lab, L], y[lab])
    pr = platt.predict_proba(full.decision_function(hs[te, L])[:, None])[:, 1]
    # gut gate threshold from the labelled items
    cg_lab, gut_ok, pr_ok = conf(gut[lab]), (gut[lab] > 0.5) == y[lab], (pr_lab > 0.5) == y[lab]
    t_g = 1.01
    for t in np.sort(np.unique(cg_lab)):
        m = cg_lab >= t
        if m.sum() >= 5 and gut_ok[m].mean() >= pr_ok[m].mean():
            t_g = t
            break
    # Think When Needed-style router, fit on the labelled items
    feats = lambda idx, pca: np.c_[conf(gut[idx]), gut[idx], pca.transform(hs[idx, L])]
    pca = make_pipeline(StandardScaler(), PCA(16, random_state=0)).fit(hs[lab, L])
    gain = ((think[lab] > 0.5) == y[lab]).astype(float) - gut_ok.astype(float)
    rgain = Ridge(alpha=10.0).fit(feats(lab, pca), gain).predict(feats(te, pca))

    yt, stt, gt, tt = y[te], st[te], gut[te], think[te]
    n = len(te)
    keep_gut = conf(gt) >= t_g
    out = {}
    for q in QS:
        k = int(round(q * n))
        # cascade
        rest = np.where(~keep_gut)[0]
        rest_sorted = rest[np.argsort(conf(pr[rest]), kind="stable")]
        thinkers = rest_sorted[:k]
        casc = np.where(keep_gut, gt, pr)
        casc[thinkers] = tt[thinkers]
        # variant (added after the first run): per item, the more confident of gut and probe gives the verdict; think on
        # the items where even the more confident one is least sure
        mc = np.maximum(conf(gt), conf(pr))
        casc2 = route(np.where(conf(gt) >= conf(pr), gt, pr), tt, np.argsort(mc, kind="stable"), k)
        pol = dict(cascade=casc, cascade_maxconf=casc2,
                   gut_think=route(gt, tt, np.argsort(conf(gt), kind="stable"), k),
                   probe_think=route(pr, tt, np.argsort(conf(pr), kind="stable"), k),
                   router_think=route(gt, tt, np.argsort(-rgain, kind="stable"), k))
        out[str(q)] = {name: dict(acc=float(((s > 0.5) == yt).mean()), auc=strata_auc(s, yt, stt))
                       for name, s in pol.items()}
        out[str(q)]["cascade"]["think_share"] = len(thinkers) / n
        th2 = np.argsort(mc, kind="stable")[:k]
        nt = np.setdiff1d(np.arange(n), th2)
        out[str(q)]["cascade_maxconf"]["steps"] = dict(gut=float((conf(gt[nt]) >= conf(pr[nt])).sum() / n),
                                                       read=float((conf(gt[nt]) < conf(pr[nt])).sum() / n), think=k / n)
        out[str(q)]["cascade"]["steps"] = dict(gut=float(keep_gut.mean()), read=float((n - keep_gut.sum() - len(thinkers)) / n),
                                               think=len(thinkers) / n)
    out["fixed"] = {name: dict(acc=float(((s > 0.5) == yt).mean()), auc=strata_auc(s, yt, stt))
                    for name, s in dict(gut=gt, probe=pr, think=tt).items()}
    return out


def mean(rows, path):
    vals = []
    for r in rows:
        x = r
        for p in path:
            x = x[p]
        vals.append(x)
    if isinstance(vals[0], dict):
        return {k: mean(vals, [k]) for k in vals[0]}
    return round(float(np.mean(vals)), 3)


def main():
    D = load()
    res = {}
    for b in BENCHES:
        rows = [one_draw(D[b], s) for s in range(DRAWS)]
        res[b] = {key: mean(rows, [key]) for key in rows[0]}
        f = res[b]["fixed"]
        print(f"== {b}: gut {f['gut']['acc']} probe {f['probe']['acc']} think {f['think']['acc']}", flush=True)
        for q in QS:
            r = res[b][str(q)]
            print(f"  think {int(q * 100)}%: cascade {r['cascade']['acc']} maxconf {r['cascade_maxconf']['acc']} "
                  f"(steps {r['cascade_maxconf']['steps']}) | "
                  f"gut->think {r['gut_think']['acc']} probe->think {r['probe_think']['acc']} "
                  f"router->think {r['router_think']['acc']}", flush=True)
    (RES / "step7.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
