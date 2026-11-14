"""Same-source control: within-question ranking using only pairs of answers to the same question written by the SAME model.
Removes the "which model wrote it" clue. Knows = held-out direction score, Says = unedited verdict, x11 = stretched verdict.
Gain = x11 - Says (points), 95% CI by resampling questions. Also reports the equal-FPR TPR difference on the full set.

  python3 experiments/beyond_capability/check_same_source.py -> out_checks/same_source_mmlu.md
"""
import gzip
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out_checks"
NAME = {"qwen3.5-9b": "Qwen-9B", "llama3.1-8b": "Llama-8B"}


def per_group(rows, key):
    by = defaultdict(lambda: ([], []))
    for r in rows:
        by[(r["qid"], r["src"])][0 if r["gold"] else 1].append(r[key])
    out = {}
    for (q, s), (R, W) in by.items():
        if R and W:
            R, W = np.array(R)[:, None], np.array(W)[None, :]
            p = out.get(q, (0.0, 0))
            out[q] = (p[0] + (R > W).sum() + 0.5 * (R == W).sum(), p[1] + R.size * W.size)
    return out


def main():
    src = {}
    for line in gzip.open(HERE / "inputs" / "mmlu_full_items.jsonl.gz"):
        r = json.loads(line)
        src[r["aid"]] = r["src"]
    dump = [json.loads(x) for x in open(OUT / "dump_mmlu.jsonl")]
    sols = json.load(open(OUT / "sol_mmlu.json"))
    rng = np.random.default_rng(0)
    lines = ["| Judge | Questions | Questions with a same-model pair | Pairs | Knows | Says | Says after x11 | Gain [95% CI] |",
             "|---|---|---|---|---|---|---|---|"]
    for m in ("qwen3.5-9b", "llama3.1-8b"):
        rows = [dict(r, src=src[r["aid"]]) for r in dump if r["model"] == m and r["aid"] in src and r["verdict"] is not None]
        for g, val in (("solved", 1), ("not solved", 0)):
            rr = [r for r in rows if sols.get(m, {}).get(r["qid"], -1) == val]
            pq = {k: per_group(rr, k) for k in ("dirscore", "verdict", "x11")}
            qs = sorted(pq["verdict"])
            A = {k: np.array([pq[k][q] for q in qs]) for k in pq}
            au = lambda k, i=slice(None): A[k][i].sum(0)[0] / A[k][i].sum(0)[1]  # noqa: E731
            gain = lambda i=slice(None): 100 * (au("x11", i) - au("verdict", i))  # noqa: E731
            bs = [gain(rng.integers(0, len(qs), len(qs))) for _ in range(2000)]
            lo, hi = np.percentile(bs, [2.5, 97.5])
            lines.append(f"| {NAME[m]} | {g} | {len(qs)} | {int(A['verdict'][:, 1].sum())} | {au('dirscore'):.3f} | "
                         f"{au('verdict'):.3f} | {au('x11'):.3f} | {gain():+.1f} [{lo:+.1f}, {hi:+.1f}] |")
    out = "\n".join(lines)
    (OUT / "same_source_mmlu.md").write_text(out + "\n")
    print(out)


if __name__ == "__main__":
    main()
