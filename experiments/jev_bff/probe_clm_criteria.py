#!/usr/bin/env python3
"""
Probe: is CLM-8B's noref miscalibration (see docs/findings_zeroshot_juries.md #1b) an inverted
true/false criteria mapping, or a genuine "no signal" failure?

For a small sample of items, call CLM's is_correct noul TWICE per item: once with the normal
criteria (true = correct, false = incorrect), once with the true/false text SWAPPED. If the
swapped version's (1 - p) tracks the human label better than the normal version's p does,
that's evidence of an inverted mapping (fixable); if both orientations are equally uninformative,
that's evidence of a genuine no-signal failure on this domain.

Usage (run against a live CLM server, e.g. from inside experiments/clm_modal.py or with
CLM_URL pointed at one):
  CLM_URL=http://127.0.0.1:8700 uv run python experiments/jev_bff/probe_clm_criteria.py --limit 60
"""
import argparse
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))
from run_jev_bff import load_data, build_items, INSTR, CRITERIA
from backends import Backend, get_noul


def auroc(y, s):
    pos = [a for a, t in zip(s, y) if t == 1]
    neg = [a for a, t in zip(s, y) if t == 0]
    if not pos or not neg:
        return float("nan")
    wins = sum((p > q) + 0.5 * (p == q) for p in pos for q in neg)
    return wins / (len(pos) * len(neg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--clm-url", default=None)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None, help="dir to write probe_clm_criteria_results.csv + summary.md into")
    a = ap.parse_args()

    v, b = load_data()
    items, _ = build_items(v, b, "unanimous")
    import random
    random.Random(a.seed).shuffle(items)
    items = items[: a.limit]
    print(f"probing {len(items)} items, noref only", file=sys.stderr)

    backend = Backend("clm", None, a.clm_url)
    swapped_criteria = {"true": CRITERIA["false"], "false": CRITERIA["true"]}

    rows = []
    for it in items:
        state = {"conversation": it["conv"]}
        q_normal = {"is_correct": backend.Noul(instructions=INSTR, criteria=CRITERIA)}
        q_swapped = {"is_correct": backend.Noul(instructions=INSTR, criteria=swapped_criteria)}
        res_n, _ = backend.ask(state, q_normal)
        res_s, _ = backend.ask(state, q_swapped)
        rows.append(dict(id=it["id"], human=it["human"],
                          p_normal=get_noul(res_n, "is_correct"), p_swapped=get_noul(res_s, "is_correct")))
        if len(rows) % 20 == 0:
            print(f"  {len(rows)}/{len(items)}", file=sys.stderr)

    out_dir = Path(a.out) if a.out else Path(__file__).resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "probe_clm_criteria_results.csv", index=False)
    y = df["human"].tolist()
    lines = ["# CLM criteria-inversion probe", "", f"n={len(df)}",
             f"AUROC, normal criteria (p directly):        {auroc(y, df['p_normal'].tolist()):.3f}",
             f"AUROC, swapped criteria (p directly):        {auroc(y, df['p_swapped'].tolist()):.3f}",
             f"AUROC, swapped criteria (1-p, un-swapped):   {auroc(y, (1 - df['p_swapped']).tolist()):.3f}",
             f"Mean p, normal:  {df['p_normal'].mean():.3f}   Mean p, swapped: {df['p_swapped'].mean():.3f}",
             f"Human base rate (share correct): {sum(y) / len(y):.3f}", "",
             "If 'swapped (1-p)' AUROC >> 'normal' AUROC, the criteria mapping is inverted (fixable).",
             "If both hover near 0.5, it's a genuine no-signal failure, not a phrasing bug."]
    (out_dir / "summary.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
