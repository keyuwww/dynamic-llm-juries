#!/usr/bin/env python3
"""
Diversity / error-overlap analysis: do Jev/Laya/jeff (HTTP System One backends) make different
mistakes than the 8 Tinker-hosted open-weight models, or the same ones? If different, mixed-
architecture juries should beat same-family ensembles at equal size -- this is the empirical
check for that claim.

For each benchmark/condition: pairwise phi-coefficient (binary correlation) of each judge's
correctness (right/wrong per item) against every other judge; average intra-Tinker-pool
correlation vs. average Tinker-vs-HTTP cross-family correlation. Also reports, per HTTP judge,
how many items it gets right while a majority of the Tinker-8 get wrong (and vice versa) --
i.e. items a mixed jury would catch that a Tinker-only jury would miss.

Usage (repo root): uv run python experiments/certifier/run_diversity.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from loaders import bff_long, safety_long, wide_pool, ALL_JUDGES, TINKER_POOL, HTTP_BFF


def phi(a, b):
    """Phi coefficient (Pearson correlation of two binary vectors)."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if a.std() == 0 or b.std() == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def analyze(df, label, out_prefix):
    items, gold, pmat, _ = wide_pool(df, ALL_JUDGES)
    correct = {j: (pmat[j] >= 0.5).astype(int) == gold for j in ALL_JUDGES}
    n = len(items)
    print(f"{label}: n={n}", flush=True)

    # pairwise phi matrix
    mat = pd.DataFrame(index=ALL_JUDGES, columns=ALL_JUDGES, dtype=float)
    for j1 in ALL_JUDGES:
        for j2 in ALL_JUDGES:
            mat.loc[j1, j2] = phi(correct[j1], correct[j2])
    mat.to_csv(HERE / f"{out_prefix}_phi_matrix.csv")

    http_judges = list(HTTP_BFF.keys())
    intra_tinker = [mat.loc[j1, j2] for i1, j1 in enumerate(TINKER_POOL)
                     for j2 in TINKER_POOL[i1 + 1:]]
    cross = [mat.loc[j1, j2] for j1 in http_judges for j2 in TINKER_POOL]
    intra_http = [mat.loc[j1, j2] for i1, j1 in enumerate(http_judges) for j2 in http_judges[i1 + 1:]]

    # unique catches: item where this judge right but Tinker-8 majority wrong
    tinker_majority_correct = (sum(correct[j].astype(int) for j in TINKER_POOL) >= (len(TINKER_POOL) / 2 + 0.5)).astype(bool)
    catches = {}
    for j in http_judges:
        catches[j] = int((correct[j] & ~tinker_majority_correct).sum())
    http_majority_correct = (sum(correct[j].astype(int) for j in http_judges) >= 2).astype(bool)
    tinker_catches_vs_http = int((tinker_majority_correct & ~http_majority_correct).sum())

    return dict(
        label=label, n=n,
        intra_tinker_mean=float(np.nanmean(intra_tinker)) if intra_tinker else float("nan"),
        intra_http_mean=float(np.nanmean(intra_http)) if intra_http else float("nan"),
        cross_mean=float(np.nanmean(cross)) if cross else float("nan"),
        unique_catches_by_http=catches,
        tinker_majority_catches_http_misses=tinker_catches_vs_http,
    )


def main():
    benches = [
        ("BFF noref", bff_long("noref"), "bff_noref"),
        ("BFF ref", bff_long("ref"), "bff_ref"),
        ("Safety", safety_long(), "safety"),
    ]
    L = ["# Diversity / error-overlap analysis: mixed-architecture vs. same-family agreement", "",
         "Phi coefficient (binary correlation) of per-item correctness between judge pairs. Lower "
         "correlation = more independent errors = more ensemble value from combining them.", ""]
    all_res = []
    for label, df, prefix in benches:
        res = analyze(df, label, prefix)
        all_res.append(res)
        L.append(f"## {label} (n={res['n']})\n")
        L.append(f"- Mean intra-Tinker-pool correctness correlation: {res['intra_tinker_mean']:.3f}")
        L.append(f"- Mean intra-HTTP-backend (Jev/Laya/jeff) correctness correlation: {res['intra_http_mean']:.3f}")
        L.append(f"- Mean cross-family (HTTP vs. Tinker) correctness correlation: {res['cross_mean']:.3f}")
        L.append("")
        L.append("Unique catches (judge right, Tinker-8 majority wrong):")
        for j, c in res["unique_catches_by_http"].items():
            L.append(f"  - {j}: {c} items")
        L.append(f"Tinker-8 majority right, HTTP-judge majority wrong: {res['tinker_majority_catches_http_misses']} items")
        L.append("")
    (HERE / "diversity_summary.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
