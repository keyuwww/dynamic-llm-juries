#!/usr/bin/env python3
"""
Calibration check: for each of the 11 judges, is its reported p (confidence that the response
is correct/chosen) actually calibrated against the human label, or just a binary verdict with
noise on top? Computes a 10-bin reliability table (predicted vs. observed fraction positive),
Brier score, and expected calibration error (ECE) per judge per benchmark.

Usage (repo root): uv run python experiments/certifier/run_calibration.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from loaders import bff_long, safety_long, wide_pool, ALL_JUDGES


def ece_and_brier(p, gold, n_bins=10):
    p, gold = np.asarray(p), np.asarray(gold, dtype=float)
    brier = float(np.mean((p - gold) ** 2))
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    rows = []
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (p >= lo) & (p < hi) if i < n_bins - 1 else (p >= lo) & (p <= hi)
        if mask.sum() == 0:
            continue
        conf = p[mask].mean()
        acc = gold[mask].mean()
        w = mask.sum() / len(p)
        ece += w * abs(conf - acc)
        rows.append(dict(bin=f"[{lo:.1f},{hi:.1f})", n=int(mask.sum()), mean_p=float(conf), frac_positive=float(acc)))
    return brier, ece, rows


def main():
    benches = [
        ("BFF noref", bff_long("noref")),
        ("BFF ref", bff_long("ref")),
        ("Safety", safety_long()),
    ]
    L = ["# Calibration check: is each judge's confidence score meaningful, or just a verdict?", "",
         "Brier score (lower better) and expected calibration error (ECE, lower better) of each "
         "judge's raw p against the human/gold label.", ""]
    summary_rows = []
    for label, df in benches:
        items, gold, pmat, _ = wide_pool(df, ALL_JUDGES)
        L.append(f"## {label} (n={len(items)})\n")
        L.append("| Judge | Brier score | ECE |")
        L.append("|---|---|---|")
        for j in ALL_JUDGES:
            brier, ece, _ = ece_and_brier(pmat[j], gold)
            L.append(f"| {j} | {brier:.3f} | {ece:.3f} |")
            summary_rows.append(dict(bench=label, judge=j, brier=brier, ece=ece))
        L.append("")
    pd.DataFrame(summary_rows).to_csv(HERE / "calibration_results.csv", index=False)
    (HERE / "calibration_summary.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
