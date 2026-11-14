"""Score the steering runs (probe_steer.py --phase steer): does pushing the position-A state along a
probe direction change the verdict more than a random direction of the same size, and does it act on
the anchoring errors specifically or just make the judge more/less lenient everywhere?

alpha is in standard deviations of the projections onto the direction (alpha = 0 is the unsteered judge).
  correctness = mean(correct candidates) - mean(wrong)          at the best mid-depth correctness-probe layer
  agreement   = mean(wrong & matches own answer) - mean(wrong & differs), at the best mid-depth agreement layer
  random      = random direction, same size as correctness, same layer

  python3 experiments/anchoring_early_answer/steer_analysis.py --judge qwen3.5-4b
"""
import argparse
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", default="qwen3.5-4b")
    ap.add_argument("--rows", default=str(HERE / "out" / "rows.json"), help="labels (out_llama/rows.json for Llama)")
    a = ap.parse_args()
    d = HERE / "out_probe" / a.judge
    meta = {m["item_id"]: m for m in map(json.loads, open(d / "meta.jsonl"))}
    rows = {r["item"]: r for r in json.load(open(a.rows)) if r["judge"] == a.judge}

    def group(iid):
        m, r = meta[iid], rows.get(iid)
        if m["gold"] == 1:
            return "correct"
        if r and r["group"] in ("match", "differ"):
            return f"wrong, own answer {'matches' if r['group'] == 'match' else 'differs'}"
        return None

    L = [f"# Steering at position A — {a.judge}\n",
         "Share of candidates the judge accepts (verdict at A says CORRECT) when its hidden state at one layer is "
         "pushed by alpha standard deviations along a direction. alpha = 0 is the unsteered judge.\n"]
    for name in ("agreement", "correctness", "random"):
        f = d / f"steer_{name}.jsonl"
        if not f.exists():
            continue
        R = [json.loads(l) for l in open(f)]
        alphas = sorted(R[0]["margins"], key=float)
        L.append(f"## {name} direction (layer {R[0]['layer']})\n")
        L.append("| Candidates | n | " + " | ".join(f"α={float(x):+g}" for x in alphas) + " |")
        L.append("|---|---|" + "---|" * len(alphas))
        for g in ("wrong, own answer matches", "wrong, own answer differs", "correct"):
            S = [r for r in R if group(r["item_id"]) == g]
            if S:
                L.append(f"| {g} | {len(S)} | " + " | ".join(
                    f"{np.mean([r['margins'][x] > 0 for r in S]):.2f}" for x in alphas) + " |")
        # selectivity: change in accept rate on anchoring-type items minus change on correct items
        def acc(g, x):
            S = [r for r in R if group(r["item_id"]) == g]
            return np.mean([r["margins"][x] > 0 for r in S]) if S else float("nan")
        z = next(x for x in alphas if float(x) == 0)
        lo = alphas[0]
        L.append(f"\nAt α={float(lo):+g}: wrong-and-matching accept rate changes by "
                 f"{acc('wrong, own answer matches', lo) - acc('wrong, own answer matches', z):+.2f}, "
                 f"wrong-and-differing by {acc('wrong, own answer differs', lo) - acc('wrong, own answer differs', z):+.2f}, "
                 f"correct by {acc('correct', lo) - acc('correct', z):+.2f}.\n")
    (d / "steering.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
