#!/usr/bin/env python3
"""
Steps 3 and 4 of Trust / Read / Think (all on saved Step 1 data; no GPU).

Step 4: can Read work on a benchmark WITHOUT its gold labels?
  Probes trained on pseudo-labels, cross-fitted by question (an item is never scored by a probe trained on it), layer
  picked by inner CV on the pseudo-labels (no gold labels anywhere):
    conf_gut   items where the gut is sure (P > 0.9 or < 0.1); label = the gut's verdict              (free)
    agree      items where the gut and Think@1,024 agree; label = the shared verdict          (needs thinking)
    agree_k    the same, but thinking on only k random items (k = 25, 50, 100), 5 draws each
  Compared with Trust (gut), the supervised Read (gold labels, Step 2) and Think. Checks: how often the pseudo-labels
  are right, and AUROC on the hard items (gut and Think@1,024 disagree).

Step 3: does a free signal predict where the gut is wrong or where thinking flips it?
  signals  gut uncertainty 1 - |2P - 1|; gut-probe conflict |P_gut - P_probe| (label-free agree probe, and the
           supervised probe as a ceiling)
  targets  gut wrong (vs gold); flip (Think@1,024 verdict differs from the gut's)
  routing  start from the gut verdict, send the top q% of items by signal to Think@1,024; accuracy vs q, compared
           with random routing (mean of 200 draws)

  .venv/bin/python experiments/trust_read_think/step34.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
from joblib import Parallel, delayed
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

warnings.filterwarnings("ignore")
import step2
from step2 import BENCHES, strata_auc, probe

HERE = Path(__file__).resolve().parent
from paths import RAW, RES, ITEMS  # noqa: E402
LAYERS = list(range(4, 33, 2))
TB = 1024                # thinking budget used for pseudo-labels, flips and routing
QS = (0.0, 0.1, 0.2, 0.3, 0.5, 1.0)


def fit_score(X, yp, train_mask, g, seed=0):
    """Cross-fitted probe scores from pseudo-labels yp, using only items in train_mask for training.
    Layer chosen by 3-fold inner CV AUROC on the pseudo-labels. Returns (scores, layers picked)."""
    out, picked = np.full(len(yp), 0.5), []
    for tr, te in GroupKFold(5).split(X[:, 0], yp, g):
        tr = tr[train_mask[tr]]
        if len(np.unique(yp[tr])) < 2 or min(np.bincount(yp[tr].astype(int))) < 3:
            continue
        if len(tr) < 60:          # too few to pick a layer: fixed default (layer 20, mid-depth), no labels used
            picked.append(20)
            out[te] = probe().fit(X[tr, 20], yp[tr]).predict_proba(X[te, 20])[:, 1]
            continue
        inner = list(GroupKFold(3).split(tr, yp[tr], g[tr]))

        def cv(l):
            s, ok = np.zeros(len(tr)), True
            for a, b in inner:
                if len(np.unique(yp[tr][a])) < 2:
                    ok = False
                    break
                s[b] = probe().fit(X[tr][a, l], yp[tr][a]).predict_proba(X[tr][b, l])[:, 1]
            return roc_auc_score(yp[tr], s) if ok and len(np.unique(yp[tr])) == 2 else 0.5
        sc = Parallel(n_jobs=-1)(delayed(cv)(l) for l in LAYERS)
        L = LAYERS[int(np.argmax(sc))]
        picked.append(L)
        out[te] = probe().fit(X[tr, L], yp[tr]).predict_proba(X[te, L])[:, 1]
    return out, picked


def boot_diff(a, b, y, g, st, n=1000, seed=0):
    rng = np.random.default_rng(seed)
    ug = np.unique(g)
    idx = {k: np.where(g == k)[0] for k in ug}
    d = []
    for _ in range(n):
        ii = np.concatenate([idx[k] for k in rng.choice(ug, len(ug))])
        d.append(strata_auc(a[ii], y[ii], st[ii]) - strata_auc(b[ii], y[ii], st[ii]))
    return [round(float(np.percentile(d, 2.5)), 3), round(float(np.percentile(d, 97.5)), 3)]


def auc_ci(sig, tgt, g, n=500, seed=0):
    rng = np.random.default_rng(seed)
    ug = np.unique(g)
    idx = {k: np.where(g == k)[0] for k in ug}
    v = []
    for _ in range(n):
        ii = np.concatenate([idx[k] for k in rng.choice(ug, len(ug))])
        if len(np.unique(tgt[ii])) == 2:
            v.append(roc_auc_score(tgt[ii], sig[ii]))
    return [round(float(roc_auc_score(tgt, sig)), 3),
            [round(float(np.percentile(v, 2.5)), 3), round(float(np.percentile(v, 97.5)), 3)]]


def route_acc(gut_v, think_v, y, signal, q, rng=None):
    n = len(y)
    k = int(round(q * n))
    order = rng.permutation(n) if rng is not None else np.argsort(-signal, kind="stable")
    v = gut_v.copy()
    v[order[:k]] = think_v[order[:k]]
    return float((v == y).mean())


def main():
    D = step2.load()
    res = {}
    for b in BENCHES:
        d = D[b]
        y, g, st, X, gut = d["y"], d["group"], d["strata"], d["hs"], d["gut"]
        think = d["think"][TB]
        sup = np.load(RAW / f"{b}_read_oof.npy")[0]          # supervised Read from Step 2
        gv, tv = (gut > 0.5).astype(int), (think > 0.5).astype(int)
        r = dict(n=len(y))

        # ---------------- Step 4: label-free Read
        conf = (gut > 0.9) | (gut < 0.1)
        agree = gv == tv
        s_conf, L_conf = fit_score(X, gv, conf, g)
        s_agree, L_agree = fit_score(X, gv, agree, g)
        r["pseudo"] = dict(conf_frac=round(float(conf.mean()), 3), conf_label_acc=round(float((gv == y)[conf].mean()), 3),
                           agree_frac=round(float(agree.mean()), 3),
                           agree_label_acc=round(float((gv == y)[agree].mean()), 3))
        scores = dict(trust=gut, read_sup=sup, read_conf=s_conf, read_agree=s_agree, think=think)
        auc = {k: strata_auc(s, y, st) for k, s in scores.items()}
        r["auc"] = {k: round(float(v), 3) for k, v in auc.items()}
        gap = auc["read_sup"] - auc["trust"]
        r["vs_trust"] = {k: dict(d=round(float(auc[k] - auc["trust"]), 3), ci=boot_diff(scores[k], gut, y, g, st),
                                 gap_recovered=round(float((auc[k] - auc["trust"]) / gap), 2) if gap > 0.02 else None)
                         for k in ("read_conf", "read_agree")}
        r["layers"] = dict(conf=L_conf, agree=L_agree)
        # hard items: gut and Think disagree (plain AUROC; too few per stratum for same-source)
        hard = ~agree
        r["hard"] = dict(n=int(hard.sum()), **{k: round(float(roc_auc_score(y[hard], s[hard])), 3)
                                               for k, s in scores.items() if len(np.unique(y[hard])) == 2})
        # thinking on only k items
        ug = np.unique(g)
        r["agree_k"] = {}
        for k in (25, 50, 100):
            vals = []
            for seed in range(5):
                rng = np.random.default_rng(seed)
                thought = np.zeros(len(y), bool)
                thought[rng.choice(len(y), min(k, len(y)), replace=False)] = True
                s, _ = fit_score(X, gv, agree & thought, g)
                vals.append(strata_auc(s, y, st))
            r["agree_k"][k] = [round(float(np.mean(vals)), 3), round(float(np.std(vals)), 3)]

        # ---------------- Step 3: free signals for routing
        flip = (gv != tv).astype(int)
        wrong = (gv != y).astype(int)
        sig = dict(uncertainty=1 - np.abs(2 * gut - 1), conflict_free=np.abs(gut - s_agree),
                   conflict_sup=np.abs(gut - sup), conflict_conf=np.abs(gut - s_conf))
        r["detect"] = {t: {k: auc_ci(s, tgt, g) for k, s in sig.items()}
                       for t, tgt in (("gut_wrong", wrong), ("flip", flip))}
        r["flip_rate"], r["gut_acc"], r["think_acc"] = (round(float(flip.mean()), 3), round(float((gv == y).mean()), 3),
                                                        round(float((tv == y).mean()), 3))
        rr = [np.random.default_rng(s) for s in range(200)]
        r["routing"] = {"random": [round(float(np.mean([route_acc(gv, tv, y, None, q, x) for x in rr])), 3) for q in QS]}
        for k in ("uncertainty", "conflict_free", "conflict_sup"):
            r["routing"][k] = [round(route_acc(gv, tv, y, sig[k], q), 3) for q in QS]
        res[b] = r
        print(b, json.dumps(r), flush=True)
    (RES / "step34.json").write_text(json.dumps(dict(qs=QS, budget=TB, benches=res), indent=1))


if __name__ == "__main__":
    main()
