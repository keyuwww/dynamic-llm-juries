#!/usr/bin/env python3
"""
Frozen-threshold cascade, following arXiv:2609.26550 ("JEV-as-a-Judge: Accept When Confident,
Escalate When Unsure"). Differs from run_toe.py in two ways that matter:

  1. The confidence threshold is picked on a held-out TUNE split, then frozen and applied to a
     disjoint TEST split -- not swept and reported at its best point on the same data it's
     evaluated on (which is what run_toe.py does; that's test-set leakage).
  2. Escalation target is a genuinely different, stronger REASONING judge (gpt-oss-120b from the
     Tinker pool, which generates a textual rationale before its verdict), not the same fast
     model shown a reference answer.

For each of Jev / Laya / jeff (the fast, decision-only judges), on each of BFF-noref / BFF-ref /
Safety: tune a frozen confidence threshold tau on 50% of items (maximize cascade kappa on that
half only), then apply it on the other 50%, escalating low-confidence verdicts to gpt-oss-120b.
Report the cascade's accuracy as a fraction of the comparator's own accuracy on the same held-out
test items -- the paper's "retains X% of the comparator's accuracy" framing -- plus coverage
(fraction NOT escalated).

Uses only already-collected judge data -- no new API calls.

Usage (repo root): uv run python experiments/trust_or_escalate/run_frozen_cascade.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "certifier"))
from loaders import bff_long, safety_long, wide_pool  # noqa: E402

FAST_JUDGES = ["jev", "laya", "jeff"]
COMPARATOR = "gpt-oss-120b"  # fixed in advance, not cherry-picked per benchmark


def kappa(y, yhat):
    y, yhat = np.asarray(y), np.asarray(yhat)
    n = len(y)
    if n == 0:
        return float("nan")
    po = (y == yhat).mean()
    p1, q1 = y.mean(), yhat.mean()
    pe = p1 * q1 + (1 - p1) * (1 - q1)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def cascade_predict(p_fast, p_comp, tau):
    conf = np.abs(p_fast - 0.5) * 2
    escalate = conf < tau
    yhat = np.where(escalate, (p_comp >= 0.5).astype(int), (p_fast >= 0.5).astype(int))
    return yhat, escalate


def run_one(fast_judge, df, label, out_rows):
    items, gold, pmat, _ = wide_pool(df, [fast_judge, COMPARATOR])
    n = len(items)
    rng = np.random.RandomState(0)
    order = rng.permutation(n)
    half = n // 2
    tune_idx, test_idx = order[:half], order[half:]

    p_fast, p_comp = pmat[fast_judge], pmat[COMPARATOR]

    taus = np.arange(0.0, 1.01, 0.05)
    best_tau, best_kappa = 0.0, -2.0
    for tau in taus:
        yhat, _ = cascade_predict(p_fast[tune_idx], p_comp[tune_idx], tau)
        k = kappa(gold[tune_idx], yhat)
        if k > best_kappa:
            best_kappa, best_tau = k, tau

    yhat_test, escalate_test = cascade_predict(p_fast[test_idx], p_comp[test_idx], best_tau)
    cascade_kappa = kappa(gold[test_idx], yhat_test)
    cascade_acc = float((yhat_test == gold[test_idx]).mean())

    comp_yhat_test = (p_comp[test_idx] >= 0.5).astype(int)
    comp_acc = float((comp_yhat_test == gold[test_idx]).mean())
    comp_kappa = kappa(gold[test_idx], comp_yhat_test)

    fast_yhat_test = (p_fast[test_idx] >= 0.5).astype(int)
    fast_acc = float((fast_yhat_test == gold[test_idx]).mean())
    fast_kappa = kappa(gold[test_idx], fast_yhat_test)

    coverage = float((~escalate_test).mean())
    pct_of_comparator = 100.0 * cascade_acc / comp_acc if comp_acc > 0 else float("nan")

    out_rows.append(dict(
        benchmark=label, fast_judge=fast_judge, comparator=COMPARATOR,
        frozen_tau=float(best_tau), n_tune=len(tune_idx), n_test=len(test_idx),
        coverage_test=coverage, escalation_rate_test=1 - coverage,
        cascade_accuracy=cascade_acc, cascade_kappa=cascade_kappa,
        comparator_accuracy=comp_acc, comparator_kappa=comp_kappa,
        fast_alone_accuracy=fast_acc, fast_alone_kappa=fast_kappa,
        pct_of_comparator_accuracy_retained=pct_of_comparator,
    ))


def main():
    benches = [
        ("BFF noref", bff_long("noref")),
        ("BFF ref", bff_long("ref")),
        ("Safety", safety_long()),
    ]
    rows = []
    for label, df in benches:
        for fj in FAST_JUDGES:
            run_one(fj, df, label, rows)

    res = pd.DataFrame(rows)
    res.to_csv(HERE / "frozen_cascade_results.csv", index=False)

    L = ["# Frozen-threshold cascade (arXiv:2609.26550 methodology)", "",
         "Confidence threshold tuned on a held-out 50% TUNE split, frozen, then applied to the "
         "other 50% TEST split (no test-set leakage, unlike run_toe.py's sweep-and-report-best). "
         f"Escalation target fixed in advance: {COMPARATOR} (a Tinker-pool reasoning judge), not "
         "re-picked per benchmark. Uses only already-collected judge data.", "",
         "| Benchmark | Fast judge | Frozen tau | Coverage (test) | Cascade kappa | Comparator kappa | Fast-alone kappa | % of comparator accuracy retained |",
         "|---|---|---|---|---|---|---|---|"]
    for _, r in res.iterrows():
        L.append(f"| {r.benchmark} | {r.fast_judge} | {r.frozen_tau:.2f} | {r.coverage_test:.3f} | "
                  f"{r.cascade_kappa:.3f} | {r.comparator_kappa:.3f} | {r.fast_alone_kappa:.3f} | "
                  f"{r.pct_of_comparator_accuracy_retained:.1f}% |")
    (HERE / "frozen_cascade_summary.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
