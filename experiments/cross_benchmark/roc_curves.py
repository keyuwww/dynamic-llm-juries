"""ROC curves for the best judge's errors, per pairwise benchmark and signal (no new calls).

Two conditions (higher score = more likely an error):
  all         every pair; error = the best judge is wrong in at least one order (stored run). A pair it flips is
              always an error, so its own flip is a signal here.
  consistent  pairs where the best judge gives the same answer in both orders; error = wrong in both orders.
Signals (individual only; no combinations):
  own_flip     the best judge picks the same position in both orders (all-pairs condition only)
  own          the best judge's low stated confidence (confidence run, mean of both orders)
  flips        number of the other 7 judges that flip (stored run)
  pooled       other judges' disagreement with the best judge's verdict in each order, averaged over orders and
               judges (stored run); on consistent pairs this equals disagreement + half-weighted flips
  others_conf  other judges' low stated confidence (mean within-judge rank, confidence run)
Usage: python roc_curves.py -> results/flips/roc_curves.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from conf_analysis import per_pair, read  # noqa: E402
from flip_analysis import load  # noqa: E402
from order_consistency import POOL, auroc, pair_table  # noqa: E402

BENCHES = ["bffpair", "judgebench", "alpacafarm", "mtbhuman"]


def roc(y, s):
    """Exact ROC points (one per distinct threshold), as [fpr, tpr] in percent."""
    order = np.argsort(-s, kind="mergesort")
    s, y = s[order], y[order]
    P, N = y.sum(), len(y) - y.sum()
    pts, tp, fp = [[0.0, 0.0]], 0, 0
    for i in range(len(s)):
        tp += y[i]
        fp += 1 - y[i]
        if i == len(s) - 1 or s[i + 1] != s[i]:
            pts.append([round(100 * fp / N, 2), round(100 * tp / P, 2)])
    return pts


def curves(y, sig):
    return {k: dict(auc=round(float(auroc(y, v)), 3), pts=roc(y, v)) for k, v in sig.items()}


def signals_all(b, target, P):
    """All pairs: per-order verdicts of every judge from the stored run."""
    w = pair_table(b, "none")
    v0 = w.pivot_table(index="pair_id", columns="judge", values=0)
    v1 = w.pivot_table(index="pair_id", columns="judge", values=1)
    fl = w.pivot_table(index="pair_id", columns="judge", values="flip")
    err = w.pivot_table(index="pair_id", columns="judge", values="err")
    J = [j for j in POOL if j in fl.columns]
    ok = fl[J].dropna().index
    others = [j for j in J if j != target]
    y = (err.loc[ok, target] > 0).values.astype(int)
    dis = ((v0.loc[ok, others].ne(v0.loc[ok, target], axis=0)).astype(int) +
           (v1.loc[ok, others].ne(v1.loc[ok, target], axis=0)).astype(int)) / 2
    conf = P.pivot_table(index="pair_id", columns="judge", values="stated").reindex(ok)
    own_flip = fl.loc[ok, target].values
    own = (-conf[target].fillna(conf[target].median())).rank(pct=True).values
    pooled = pd.Series(dis.mean(1).values).rank(pct=True).values
    sig = {"own_flip": own_flip, "own": own, "flips": fl.loc[ok, others].sum(1).values.astype(float),
           "pooled": pooled, "others_conf": (-conf[others]).rank(pct=True).mean(1).fillna(0.5).values}
    return y, sig, dict(n=int(len(y)), errors=int(y.sum()), own_flip_rate=float(own_flip.mean()))


def signals_consistent(df, target, P):
    T = P[P.judge == target].set_index("pair_id")
    d = df[df.t_flip == 0].join(T[["stated"]], how="inner")
    d["stated"] = d.stated.fillna(d.stated.median())
    O = P[P.judge != target].pivot_table(index="pair_id", columns="judge", values="stated").reindex(d.index)
    y = d.t_conf_err.values.astype(int)
    own = (-d.stated).rank(pct=True).values
    pooled = d.eu.rank(pct=True).values
    sig = {"own": own, "flips": d.n_flip.values.astype(float), "pooled": pooled,
           "others_conf": (-O).rank(pct=True).mean(1).fillna(0.5).values}
    return y, sig, dict(n=int(len(y)), errors=int(y.sum()))


def main():
    out = {}
    for b in BENCHES:
        df, target, J = load(b)
        P = per_pair(read("confidence", b))
        out[b] = dict(target=target)
        for cond, fn in [("all", lambda: signals_all(b, target, P)), ("consistent", lambda: signals_consistent(df, target, P))]:
            y, sig, info = fn()
            out[b][cond] = dict(info, curves=curves(y, sig))
            print(b, cond, target, info, {k: v["auc"] for k, v in out[b][cond]["curves"].items()})
    (HERE / "results" / "flips" / "roc_curves.json").write_text(json.dumps(out))


if __name__ == "__main__":
    main()
