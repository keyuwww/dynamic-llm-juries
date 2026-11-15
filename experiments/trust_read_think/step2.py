#!/usr/bin/env python3
"""
Step 2 of Trust / Read / Think: which read wins on which benchmark?

  Trust  gut P(CORRECT) (thinking off)
  Read   a linear probe on the hidden state at the gut verdict position (same forward pass, no extra cost)
           in-bench   cross-fitted: GroupKFold(5) by question; the layer is picked inside each training fold
                      (inner GroupKFold(3)), so the score is not tuned on the items it is tested on
           transfer   trained on the other three benchmarks only (no labels from the test benchmark); layer =
                      best average layer on those three
  Think  forced verdict after 512 / 1,024 / 2,048 / 4,096 thinking tokens

Metric: same-source (within-strata) AUROC, as in Step 1. 95% CIs: paired bootstrap over questions (1,000 draws).
Probe: standardize, logistic regression C = 0.3 (the weight-space study's setting).

  .venv/bin/python experiments/trust_read_think/step2.py
"""
import json
from pathlib import Path

import numpy as np
from joblib import Parallel, delayed
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
from paths import RAW, RES, ITEMS  # noqa: E402
BENCHES = ("safety", "focus", "math", "bff")
BUDGETS = (512, 1024, 2048, 4096)
C = 0.3


def probe():
    return make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=3000))


def strata_auc(score, gold, strata):
    num = den = 0.0
    for s in np.unique(strata):
        m = strata == s
        pos, neg = score[m & (gold == 1)], score[m & (gold == 0)]
        if len(pos) and len(neg):
            w = len(pos) * len(neg)
            num += w * ((pos[:, None] > neg[None]).mean() + 0.5 * (pos[:, None] == neg[None]).mean())
            den += w
    return num / den if den else float("nan")


def load():
    items = [json.loads(l) for l in open(ITEMS / "items.jsonl")]
    D = {}
    for b in BENCHES:
        sub = [it for it in items if it["bench"] == b]
        th = {json.loads(l)["id"]: json.loads(l) for l in open(RAW / f"{b}_think.jsonl")}
        f = np.load(RAW / f"{b}_fast.npz")
        D[b] = dict(y=np.array([it["gold"] for it in sub]), group=np.array([it["group"] for it in sub]),
                    strata=np.array([it["strata"] for it in sub]), hs=f["hs"].astype(np.float32), gut=f["p"],
                    think={B: np.array([th[it["id"]]["p_budget"][str(B)] for it in sub]) for B in BUDGETS})
    return D


def cv_curve(X, y, g, strata):
    """Plain cross-fitted AUROC at every layer (for the curve and for picking transfer layers)."""
    folds = list(GroupKFold(5).split(X[:, 0], y, g))

    def one(l):
        oof = np.zeros(len(y))
        for tr, te in folds:
            oof[te] = probe().fit(X[tr, l], y[tr]).predict_proba(X[te, l])[:, 1]
        return strata_auc(oof, y, strata)
    return Parallel(n_jobs=-1)(delayed(one)(l) for l in range(1, X.shape[1]))   # layers 1..32


def nested_read(X, y, g, strata, layers):
    """Out-of-fold probe scores; each outer fold picks its layer by inner CV on its own training items."""
    oof, picked = np.zeros(len(y)), []
    for tr, te in GroupKFold(5).split(X[:, 0], y, g):
        inner = list(GroupKFold(3).split(tr, y[tr], g[tr]))

        def score(l):
            s = np.zeros(len(tr))
            for a, b in inner:
                s[b] = probe().fit(X[tr][a, l], y[tr][a]).predict_proba(X[tr][b, l])[:, 1]
            return strata_auc(s, y[tr], strata[tr])
        sc = Parallel(n_jobs=-1)(delayed(score)(l) for l in layers)
        L = layers[int(np.argmax(sc))]
        picked.append(int(L))
        oof[te] = probe().fit(X[tr, L], y[tr]).predict_proba(X[te, L])[:, 1]
    return oof, picked


def boot(scores, y, g, strata, n=1000, seed=0):
    """Paired bootstrap over questions: AUROC of each read and of each difference vs Trust."""
    rng = np.random.default_rng(seed)
    ug = np.unique(g)
    idx = {k: np.where(g == k)[0] for k in ug}
    out = {k: [] for k in scores}
    for _ in range(n):
        pick = rng.choice(ug, len(ug))
        ii = np.concatenate([idx[k] for k in pick])
        st = strata[ii]   # a duplicated question adds identical pos/neg pairs, same as weighting it twice
        for k, s in scores.items():
            out[k].append(strata_auc(s[ii], y[ii], st))
    return {k: np.array(v) for k, v in out.items()}


def main():
    D = load()
    res = {}
    curves = {}
    for b in BENCHES:
        d = D[b]
        curves[b] = cv_curve(d["hs"], d["y"], d["group"], d["strata"])
        print(b, "curve", np.round(curves[b], 3).tolist(), flush=True)
    for b in BENCHES:
        d = D[b]
        y, g, st = d["y"], d["group"], d["strata"]
        read, picked = nested_read(d["hs"], y, g, st, list(range(4, d["hs"].shape[1], 2)))
        # transfer: train on the other three benchmarks, at their best average layer
        others = [o for o in BENCHES if o != b]
        Lt = int(np.argmax(np.mean([curves[o] for o in others], 0))) + 1
        Xtr = np.concatenate([D[o]["hs"][:, Lt] for o in others])
        ytr = np.concatenate([D[o]["y"] for o in others])
        transfer = probe().fit(Xtr, ytr).predict_proba(d["hs"][:, Lt])[:, 1]
        scores = {"trust": d["gut"], "read": read, "read_transfer": transfer,
                  **{f"think_{B}": d["think"][B] for B in BUDGETS}}
        point = {k: strata_auc(s, y, st) for k, s in scores.items()}
        bs = boot(scores, y, g, st)
        ci = lambda a: [round(float(np.percentile(a, 2.5)), 3), round(float(np.percentile(a, 97.5)), 3)]
        r = dict(n=len(y), read_layers=picked, transfer_layer=Lt,
                 curve=[round(float(x), 3) for x in curves[b]],
                 auc={k: round(float(v), 3) for k, v in point.items()},
                 ci={k: ci(v) for k, v in bs.items()},
                 diff_vs_trust={k: dict(d=round(float(point[k] - point["trust"]), 3), ci=ci(bs[k] - bs["trust"]))
                                for k in scores if k != "trust"},
                 read_vs_best_think=None)
        best = max(BUDGETS, key=lambda B: point[f"think_{B}"])
        r["read_vs_best_think"] = dict(budget=best, d=round(float(point["read"] - point[f"think_{best}"]), 3),
                                       ci=ci(bs["read"] - bs[f"think_{best}"]))
        res[b] = r
        print(b, json.dumps({k: r[k] for k in ("auc", "diff_vs_trust", "read_vs_best_think", "read_layers",
                                               "transfer_layer")}), flush=True)
        np.save(RAW / f"{b}_read_oof.npy", np.stack([read, transfer]))
    (RES / "step2.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
