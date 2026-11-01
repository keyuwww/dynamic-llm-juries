#!/usr/bin/env python3
"""
Joins a logit_attribution_*.json (DLA per-layer push) with the matching selfpatch results
(causal_layer per item) to compute: % MLP-dominant (total_mlp_push > total_attn_push), and the
DLA-vs-causal localization accuracy (median of "attribution's peak push layer" minus "the true
causal_layer from self-patch", over items where both exist).

Usage:
  python dla_accuracy.py --dla logit_lens_results/logit_attribution_gpt-oss-120b_bff_standard.json \
      --selfpatch logit_lens_results/layer_gap_gpt-oss-120b_standard_selfpatch.json
"""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dla", required=True)
    ap.add_argument("--selfpatch", required=True)
    a = ap.parse_args()

    dla = json.loads(Path(a.dla).read_text())
    sp = json.loads(Path(a.selfpatch).read_text())
    causal_by_id = {r["id"]: r["causal_layer"] for r in sp["results"] if r.get("causal_layer") is not None}

    res = dla["results"]
    n = len(res)
    mlp_dom = sum(1 for r in res if r["total_mlp_push"] > r["total_attn_push"])

    diffs = []
    for r in res:
        causal = causal_by_id.get(r["id"])
        if causal is None:
            continue
        combined = [a_ + m for a_, m in zip(r["attn_proj"], r["mlp_proj"])]
        peak_idx = max(range(len(combined)), key=lambda i: combined[i])
        peak_layer = r["window"][peak_idx]
        diffs.append(peak_layer - causal)

    diffs.sort()
    median_diff = diffs[len(diffs) // 2] if diffs else None
    out = dict(
        dla_file=a.dla, n_dla_items=n, mlp_dominant_pct=round(100 * mlp_dom / n, 1),
        n_joined_with_selfpatch=len(diffs), median_peak_minus_causal=median_diff,
        all_diffs=diffs,
    )
    print(json.dumps({k: v for k, v in out.items() if k != "all_diffs"}, indent=2))


if __name__ == "__main__":
    main()
