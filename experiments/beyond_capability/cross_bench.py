"""One table across benchmarks: judging quality on questions the judge solved vs did not solve (no reference).
Reads out/bbeh_summary.json, out/bff_summary.json (written by analyze_bbeh.py / analyze_bff.py) and
out/existing_rows.jsonl (RB2 Math, JudgeBench). Writes out/cross_bench.md.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bc_load import OUT, boot_ci, jl, metrics  # noqa: E402


def f2(x):
    return "–" if x is None or x != x else f"{x:.2f}"


def main():
    L = ["| Benchmark | Judge | solved: n | solved | not solved: n | not solved | gap (points) |", "|---|---|---|---|---|---|---|"]
    bb = json.load(open(OUT / "bbeh_summary.json"))
    for k in sorted({k.split("|")[0] for k in bb["char"]}, key=lambda x: (x.startswith("kimi"), x)):
        a, b = bb["char"].get(f"{k}|1"), bb["char"].get(f"{k}|0")
        if a and b:
            L.append(f"| BBEH | {k} | {a['n']} | {f2(a['bal'])} | {b['n']} | {f2(b['bal'])} | {100 * (a['bal'] - b['bal']):+.0f} |")
    bf = json.load(open(OUT / "bff_summary.json"))
    for j in ("qwen3.5-4b", "qwen3.5-9b", "qwen3.6-35b-a3b", "nemotron3-super-120b"):
        a, b = bf.get(f"none|{j}|1"), bf.get(f"none|{j}|0")
        if a and b and a["n"] and b["n"]:
            L.append(f"| BFF-Bench | {j} | {a['n']} | {f2(a['bal'])} | {b['n']} | {f2(b['bal'])} | {100 * (a['bal'] - b['bal']):+.0f} |")
    ex = jl(OUT / "existing_rows.jsonl")
    for bench, nm in (("rb2math", "RB2 Math"), ("judgebench", "JudgeBench (pairwise; accuracy)")):
        for j in ("qwen3.5-4b", "qwen3.5-9b", "qwen3.6-35b-a3b"):
            cells = []
            for sv in (1, 0):
                R = [r for r in ex if r["bench"] == bench and r["judge"] == j and r["solved"] == sv and r["verdict"] is not None]
                if bench == "rb2math":
                    m = metrics([dict(r, v=r["verdict"]) for r in R])
                    cells.append((len(R), m["bal"]))
                else:
                    cells.append((len(R), float(np.mean([r["verdict"] for r in R]))))
            L.append(f"| {nm} | {j} | {cells[0][0]} | {f2(cells[0][1])} | {cells[1][0]} | {f2(cells[1][1])} | {100 * (cells[0][1] - cells[1][1]):+.0f} |")
    (OUT / "cross_bench.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
