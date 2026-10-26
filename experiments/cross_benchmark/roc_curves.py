"""ROC curves for the best judge's confident errors, per pairwise benchmark and signal (no new calls).

Signals (higher = more likely an error), on pairs where the best judge is consistent in the stored run:
  own        the best judge's low stated confidence (results/confidence run, mean of both orders)
  flips      number of the other 7 judges that flip (stored run)
  pooled     other judges' disagreement + half-weighted flips (stored run)
  others_conf  other judges' low stated confidence (mean rank, confidence run)
  combined   rank average of own and pooled
Usage: python roc_curves.py -> results/flips/roc_curves.json
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from conf_analysis import per_pair, read  # noqa: E402
from flip_analysis import load  # noqa: E402
from order_consistency import auroc  # noqa: E402

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


def main():
    out = {}
    for b in BENCHES:
        df, target, J = load(b)
        P = per_pair(read("confidence", b))
        T = P[P.judge == target].set_index("pair_id")
        d = df[df.t_flip == 0].join(T[["stated"]], how="inner")
        d["stated"] = d.stated.fillna(d.stated.median())
        O = P[P.judge != target].pivot_table(index="pair_id", columns="judge", values="stated").reindex(d.index)
        y = d.t_conf_err.values.astype(int)
        own = (-d.stated).rank(pct=True).values
        pooled = d.eu.rank(pct=True).values
        sig = {"own": own, "flips": d.n_flip.values.astype(float), "pooled": pooled,
               "others_conf": (-O).rank(pct=True).mean(1).fillna(0.5).values, "combined": (own + pooled) / 2}
        out[b] = dict(target=target, n=int(len(y)), errors=int(y.sum()),
                      curves={k: dict(auc=round(float(auroc(y, v)), 3), pts=roc(y, v)) for k, v in sig.items()})
        print(b, target, len(y), int(y.sum()), {k: v["auc"] for k, v in out[b]["curves"].items()})
    (HERE / "results" / "flips" / "roc_curves.json").write_text(json.dumps(out))


if __name__ == "__main__":
    main()
