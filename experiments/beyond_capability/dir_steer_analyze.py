"""Steering results (dir_capture.py --phase steer): does pushing the judge's hidden state along a "this is right"
direction make it SEPARATE right from wrong answers better, or only change how lenient it is?

Directions are computed on one half of the questions and applied to the other half (dir_analyze.py writes both).
For every direction and strength: within-question AUROC of the verdict log-odds, and acceptance rates of right and
wrong answers, on questions the model solved / did not solve.

  python3 experiments/beyond_capability/dir_steer_analyze.py --key qwen3.5-9b
"""
import argparse
import collections
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bc_load import within_auc  # noqa: E402
from dir_analyze import solved_labels  # noqa: E402

NAMES = {"J": "judge-role direction", "G": "generate-role direction", "R": "random direction",
         "Jc": "judge-role direction, question-centred", "Gc": "generate-role direction, question-centred",
         "Rc": "random direction (centred run)"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default="qwen3.5-9b")
    a = ap.parse_args()
    d = HERE / "out_dirs" / a.key
    rows = [json.loads(l) for p in sorted(d.glob("steer_*.jsonl")) for l in open(p)]
    solved = solved_labels(a.key)
    L = [f"# Steering the judge — {a.key}\n",
         "*add* = h + α·v (same push for every answer); *amplify* = h + β·((h·v) − μ)·v (stretches answers apart along v). "
         "Cells: within-question AUROC of the verdict / share of right answers accepted / share of wrong answers accepted.\n"]
    for bench in sorted({r["bench"] for r in rows}):
        L += [f"\n## {bench}\n", "| Direction | Edit | solved: AUROC / acc. right / acc. wrong | **not solved**: AUROC / acc. right / acc. wrong |",
              "|---|---|---|---|"]
        R = [r for r in rows if r["bench"] == bench]
        by_dir = collections.defaultdict(list)
        for r in R:
            by_dir[r["dir"].split("_")[0]].append(r)
        for dn, X in sorted(by_dir.items()):
            keys = sorted(X[0]["margins"], key=lambda k: (k.split(":")[0] != "add", float(k.split(":")[1])))
            for k in keys:
                cells = []
                for sv in (1, 0):
                    S = [r for r in X if solved.get((bench, r["qid"])) == sv]
                    y = [r["gold"] for r in S]
                    s = [r["margins"][k] for r in S]
                    auc = within_auc(y, s, [r["qid"] for r in S])[0]
                    ar = np.mean([m > 0 for m, g in zip(s, y) if g == 1])
                    aw = np.mean([m > 0 for m, g in zip(s, y) if g == 0])
                    cells.append(f"{auc:.2f} / {ar:.2f} / {aw:.2f}")
                L.append(f"| {NAMES.get(dn, dn)} | {k.replace(':', ' ')} | " + " | ".join(cells) + " |")
    (HERE / "out_dirs" / f"steer_tables_{a.key}.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
