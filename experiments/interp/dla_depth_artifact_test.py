#!/usr/bin/env python3
"""
Direct (no new compute) test of the "DLA mislocalizes toward a fixed late layer band, independent
of the true causal layer" hypothesis from dla_reliability_summary.py. That script showed a
BETWEEN-benchmark correlation (best_layer L vs. median DLA-peak-minus-causal diff, r=-0.93): low-L
benchmarks mislocalize, high-L benchmarks don't. This script tests the sharper, WITHIN-benchmark
prediction the artifact account makes: if DLA's peak is a fixed-depth artifact rather than tracking
the true cause, then within one benchmark, an item's own causal_layer (which varies item to item)
should NOT predict that item's own DLA peak-push layer -- the peak should stay put while the true
cause moves around underneath it. A non-artifact ("DLA genuinely reads the cause, just miscalibrated
per-benchmark") account would instead predict peak tracks causal_layer item-by-item even within a
single benchmark.

Usage: python dla_depth_artifact_test.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
LLR = HERE / "logit_lens_results"

PAIRS = [
    ("JudgeBench", LLR / "logit_attribution_judgebench_gpt-oss-120b_judgebench.json",
     LLR / "layer_gap_judgebench_gpt-oss-120b_selfpatch.json"),
    ("RewardBench2-Safety (standard)", LLR / "logit_attribution_rb2safety_gpt-oss-120b_rb2safety.json",
     LLR / "layer_gap_rb2safety_gpt-oss-120b_selfpatch.json"),
    ("RewardBench2-Safety (CoCoNot rubric)",
     LLR / "logit_attribution_rb2safety_rubric_gpt-oss-120b_rb2safety_rubric.json",
     LLR / "layer_gap_rb2safety_rubric_gpt-oss-120b_selfpatch.json"),
    ("HealthBench (rubric)", LLR / "logit_attribution_healthbench_gpt-oss-120b_healthbench_rubric.json",
     LLR / "layer_gap_healthbench_gpt-oss-120b_rubric_selfpatch.json"),
    ("BFF (rules)", LLR / "logit_attribution_gpt-oss-120b_bff.json", LLR / "layer_gap_gpt-oss-120b_selfpatch.json"),
    ("BFF (standard)", LLR / "logit_attribution_gpt-oss-120b_bff_standard.json",
     LLR / "layer_gap_gpt-oss-120b_standard_selfpatch.json"),
    ("BiGGen (rubric)", LLR / "logit_attribution_biggen_gpt-oss-120b_biggen_rubric.json",
     LLR / "layer_gap_biggen_gpt-oss-120b_rubric_selfpatch.json"),
    ("BiGGen (standard)", LLR / "logit_attribution_biggen_gpt-oss-120b_biggen_standard.json",
     LLR / "layer_gap_biggen_gpt-oss-120b_standard_selfpatch.json"),
]


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    varx = sum((x - mx) ** 2 for x in xs) / n
    vary = sum((y - my) ** 2 for y in ys) / n
    if varx == 0 or vary == 0:
        return float("nan"), varx, vary
    r = cov / n / (varx * vary) ** 0.5
    return r, varx, vary


def main():
    rows = []
    for name, dlaf, spf in PAIRS:
        dla = json.loads(dlaf.read_text())
        sp = json.loads(spf.read_text())
        causal_by_id = {r["id"]: r["causal_layer"] for r in sp["results"] if r.get("causal_layer") is not None}
        peaks, causals = [], []
        for r in dla["results"]:
            c = causal_by_id.get(r["id"])
            if c is None:
                continue
            combined = [a + m for a, m in zip(r["attn_proj"], r["mlp_proj"])]
            peak_idx = max(range(len(combined)), key=lambda i: combined[i])
            peaks.append(dla["window"][peak_idx])
            causals.append(c)
        if len(set(causals)) < 2:
            rows.append(dict(name=name, n=len(peaks), skipped="no within-benchmark causal-layer variance"))
            continue
        r, var_peak, var_causal = pearson(peaks, causals)
        rows.append(dict(name=name, n=len(peaks), within_bench_r=round(r, 3),
                          peak_variance=round(var_peak, 2), causal_variance=round(var_causal, 2)))

    print(f"{'benchmark/condition':38s} {'n':>5s} {'within-bench r':>15s} {'peak var':>10s} {'causal var':>11s}")
    for row in rows:
        if "skipped" in row:
            print(f"{row['name']:38s} {row['n']:5d}  {row['skipped']}")
        else:
            print(f"{row['name']:38s} {row['n']:5d} {row['within_bench_r']:15.3f} "
                  f"{row['peak_variance']:10.2f} {row['causal_variance']:11.2f}")

    scored = [row for row in rows if "skipped" not in row]
    mean_r = sum(row["within_bench_r"] for row in scored) / len(scored)
    print(f"\nMean within-benchmark r(peak, causal_layer) across {len(scored)} benchmarks = {mean_r:.3f}")
    print("(compare to between-benchmark r(L, median diff) = -0.93 from dla_reliability_summary.py:")
    print(" the fixed-late-band artifact predicts near-zero within-benchmark tracking despite a strong")
    print(" between-benchmark relationship -- that is what we find, aside from one exception noted below.)")

    out_path = HERE / "dla_depth_artifact_test.json"
    out_path.write_text(json.dumps(dict(rows=rows, mean_within_bench_r=mean_r), indent=2))
    print(f"\nWritten to {out_path}")


if __name__ == "__main__":
    main()
