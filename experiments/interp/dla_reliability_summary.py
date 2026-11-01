#!/usr/bin/env python3
"""
Pulls together every (DLA, self-patch) pair run so far into one table, and tests two candidate
predictors of DLA's attribution-reliability (median DLA-peak-layer minus true causal-layer):
(1) % MLP-dominant flip items (the first correction's hypothesis), (2) the best_layer L itself
(how early the logit-lens-identified best layer is) -- the second correction's hypothesis, after
BFF-standard (low MLP-dominance, 22.6%, yet the worst mislocalization in the project, median +21)
broke (1).

Usage: python dla_reliability_summary.py
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


def dla_row(dla_path, sp_path):
    dla = json.loads(dla_path.read_text())
    sp = json.loads(sp_path.read_text())
    causal_by_id = {r["id"]: r["causal_layer"] for r in sp["results"] if r.get("causal_layer") is not None}
    res = dla["results"]
    mlp_dom = sum(1 for r in res if r["total_mlp_push"] > r["total_attn_push"])
    diffs = []
    for r in res:
        c = causal_by_id.get(r["id"])
        if c is None:
            continue
        combined = [a + m for a, m in zip(r["attn_proj"], r["mlp_proj"])]
        peak_idx = max(range(len(combined)), key=lambda i: combined[i])
        diffs.append(dla["window"][peak_idx] - c)
    diffs.sort()
    median = diffs[len(diffs) // 2] if diffs else None
    return dict(best_layer=dla["best_layer"], n_dla=len(res), n_joined=len(diffs),
                mlp_dominant_pct=round(100 * mlp_dom / len(res), 1), median_diff=median)


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    varx = sum((x - mx) ** 2 for x in xs)
    vary = sum((y - my) ** 2 for y in ys)
    r = cov / (varx * vary) ** 0.5
    slope = cov / varx
    intercept = my - slope * mx
    return r, slope, intercept


def main():
    rows = {}
    for name, dlaf, spf in PAIRS:
        if not dlaf.exists() or not spf.exists():
            print(f"[skip] {name}: missing file")
            continue
        rows[name] = dla_row(dlaf, spf)

    print(f"{'benchmark/condition':38s} {'L':>4s} {'MLP%':>6s} {'median diff':>12s}")
    for name, row in rows.items():
        print(f"{name:38s} {row['best_layer']:4d} {row['mlp_dominant_pct']:5.1f}% {row['median_diff']:12d}")

    Ls = [row["best_layer"] for row in rows.values()]
    mlps = [row["mlp_dominant_pct"] for row in rows.values()]
    diffs = [row["median_diff"] for row in rows.values()]

    r_L, slope_L, b_L = pearson(Ls, diffs)
    r_mlp, slope_mlp, b_mlp = pearson(mlps, diffs)
    print(f"\nPearson r(best_layer L, median diff) = {r_L:.3f} (R^2={r_L**2:.3f}); "
          f"fit: diff ~= {b_L:.1f} + {slope_L:.2f}*L")
    print(f"Pearson r(MLP-dominant %, median diff) = {r_mlp:.3f} (R^2={r_mlp**2:.3f})")

    out = dict(rows=rows, pearson_L_vs_diff=dict(r=r_L, r2=r_L ** 2, slope=slope_L, intercept=b_L),
               pearson_mlp_vs_diff=dict(r=r_mlp, r2=r_mlp ** 2))
    out_path = HERE / "dla_reliability_summary.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nWritten to {out_path}")


if __name__ == "__main__":
    main()
