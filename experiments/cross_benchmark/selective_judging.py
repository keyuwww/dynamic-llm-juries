"""Selective judging: hold back the items a judge doubts most for human review, keep the expert's verdict on the rest.

Expert = most accurate judge on each benchmark. Per item, expert score = share of the two orders it gets right.
Ranking signals for which items to hold back (higher = hold back first):
  expert_own   the expert's own low stated confidence
  <judge>      one weaker judge's low stated confidence (each of the 7)
  weak_pool    mean within-judge doubt rank over the 7 weaker judges
  random       expected value of a random hold-back (the base accuracy, and errors caught in proportion)
For hold-back shares 0-50%: expert accuracy on the kept items, and the share of the expert's errors that land in the
held-back set (what a human reviewer would catch). Ties in confidence are broken by averaging over random orders.

Escalate-up check: on the 20% of items the weak pool doubts most, the accuracy of every judge and of the best possible
pick. If the stronger judges are no better there than elsewhere, the right fallback is a human, not a bigger model.
Usage: python selective_judging.py -> results/flips/selective_judging.{json,md}
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from order_consistency import SHORT  # noqa: E402
from sensor_router import BENCHES, load  # noqa: E402

OUT = HERE / "results" / "flips"
QS = [round(q, 2) for q in np.arange(0, 0.51, 0.05)]


def curve(score, s, reps=50):
    """Kept accuracy and share of errors caught at each hold-back share, random tie-breaking."""
    err = 1 - score
    n = len(score)
    acc, caught = np.zeros(len(QS)), np.zeros(len(QS))
    rng = np.random.default_rng(0)
    for _ in range(reps):
        order = np.lexsort((rng.random(n), -s))            # most doubted first
        for i, q in enumerate(QS):
            k = int(round(q * n))
            held, kept = order[:k], order[k:]
            acc[i] += score[kept].mean() / reps
            caught[i] += (err[held].sum() / err.sum() if err.sum() else 0) / reps
    return acc, caught


def main():
    R, L = [], ["# Selective judging: hold back doubted items for human review", "",
                "Expert accuracy on kept items, and share of the expert's errors caught in the held-back set. "
                "Random hold-back keeps accuracy flat and catches errors in proportion to the share held back.", ""]
    for b in BENCHES:
        S, _, _, C, _, cost = load(b)
        best = S.mean().idxmax()
        y = S[best].values
        D = 1 - C.rank(pct=True)                      # doubt rank per judge
        weak = [j for j in S.columns if j != best]
        sig = {"expert_own": D[best].values, "weak_pool": D[weak].mean(1).values}
        sig.update({SHORT[j]: D[j].values for j in weak})
        res = {k: curve(y, v) for k, v in sig.items()}
        base = float(y.mean())
        rec = dict(bench=b, expert=best, n=len(y), base_acc=base, q=QS,
                   curves={k: dict(acc=a.round(4).tolist(), caught=c.round(4).tolist()) for k, (a, c) in res.items()},
                   cost_per_pair={SHORT[j]: float(cost.get(j, np.nan)) for j in S.columns})
        # escalate-up check on the 20% the weak pool doubts most
        top = sig["weak_pool"] >= np.quantile(sig["weak_pool"], 0.8)
        rec["top20"] = dict(n=int(top.sum()),
                            acc_flagged={SHORT[j]: float(S[j][top].mean()) for j in S.columns},
                            acc_rest={SHORT[j]: float(S[j][~top].mean()) for j in S.columns},
                            oracle_flagged=float(S[top].max(1).mean()), oracle_rest=float(S[~top].max(1).mean()))
        R.append(rec)
        i10, i20 = QS.index(0.1), QS.index(0.2)
        rows = [dict(signal=k, acc_hold10=a[i10], acc_hold20=a[i20], caught_hold10=c[i10], caught_hold20=c[i20])
                for k, (a, c) in res.items()]
        t = rec["top20"]
        L += [f"## {b} (expert {SHORT[best]}, n={len(y)}, base accuracy {base:.3f})", "",
              pd.DataFrame(rows).sort_values("caught_hold20", ascending=False).round(3).to_markdown(index=False), "",
              f"Top-20% flagged by weak pool (n={t['n']}): accuracy flagged vs rest", "",
              pd.DataFrame({"flagged": t["acc_flagged"], "rest": t["acc_rest"]}).round(3).to_markdown(), "",
              f"Best possible pick: flagged {t['oracle_flagged']:.3f}, rest {t['oracle_rest']:.3f}", ""]
    (OUT / "selective_judging.json").write_text(json.dumps(R, indent=1))
    (OUT / "selective_judging.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
