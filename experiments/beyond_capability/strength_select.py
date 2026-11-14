"""Choose the stretch strength without peeking: pick it on one half of the questions, score it on the other half.
The two halves already exist (each half is steered with the direction learned on the other half), so this needs no new runs.

For each judge x benchmark:
  - candidates: x1 (no edit) and every stretch that was run (x2, x4, x11; MMLU-Redux also x21..x101)
  - on half A pick the candidate with the best ranking (within-question AUROC); report its ranking on half B; swap halves
  - pooled over both test halves: ranking with the chosen strength vs x1, 95% CI by resampling questions
  - for comparison: the fixed x11 gain on the same answers

Second method, a formula from the shift runs only (no stretch runs needed):
  sensitivity = (verdict change per 1 sd pushed along the direction) / (verdict's within-question sd), from add:+-4
  strength    = 1 + 1/sensitivity  (stretch until an answer 1 sd out along the direction moves its verdict by about one
                verdict sd); no stretch if sensitivity <= 0. Found after seeing these 8 cases: needs a fresh test.

  python3 experiments/beyond_capability/strength_select.py   -> out_strength_select.md
"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CASES = [  # (benchmark, model, [file prefixes], direction prefix)
    ("MMLU-Redux", "qwen3.5-9b", ["out_mmlu/qwen3.5-9b/steer_mmlu", "out_mmlu/qwen3.5-9b/steer_mmlu_big"], "Jc"),
    ("MMLU-Redux", "llama3.1-8b", ["out_mmlu/llama3.1-8b/steer_mmlu", "out_mmlu/llama3.1-8b/steer_mmlu_big"], "Jc"),
    ("MATH", "qwen3.5-9b", ["out_math/qwen3.5-9b/steer_math"], "Jc"),
    ("MATH", "llama3.1-8b", ["out_math/llama3.1-8b/steer_math"], "Jc"),
    ("BBEH", "qwen3.5-9b", ["out_dirs/qwen3.5-9b/steer_c_bbeh"], "Jc"),
    ("BBEH", "llama3.1-8b", ["out_dirs/llama3.1-8b/steer_c_bbeh"], "Jc"),
    ("RB2 Safety", "qwen3.5-9b", ["out_rb2safety/qwen3.5-9b/steer_rb2safety"], "Jc"),
    ("RB2 Safety", "llama3.1-8b", ["out_rb2safety/llama3.1-8b/steer_rb2safety"], "Jc"),
]
NAME = {"qwen3.5-9b": "Qwen-9B", "llama3.1-8b": "Llama-8B"}


def label(k):  # margins key -> "x<n>"
    return "x1" if k == "add:0.0" else f"x{int(float(k.split(':')[1])) + 1}"


def load(prefixes, dprefix, half):
    rows = defaultdict(dict)  # aid -> {qid, gold, margins}
    for p in prefixes:
        f = HERE / f"{p}_{half}.jsonl"
        if not f.exists():
            continue
        for line in open(f):
            r = json.loads(line)
            if not r["dir"].startswith(dprefix + "_"):
                continue
            d = rows[r["aid"]]
            d.update(qid=r["qid"], gold=r["gold"])
            d.setdefault("m", {}).update({label(k): v for k, v in r["margins"].items()
                                          if k == "add:0.0" or k.startswith("amplify:")})
    return list(rows.values())


def per_question(rows, cond):
    """qid -> (points, pairs) for within-question AUROC of the given condition."""
    by = defaultdict(lambda: ([], []))
    for r in rows:
        by[r["qid"]][0 if r["gold"] else 1].append(r["m"][cond])
    out = {}
    for q, (R, W) in by.items():
        if R and W:
            R, W = np.array(R)[:, None], np.array(W)[None, :]
            out[q] = ((R > W).sum() + 0.5 * (R == W).sum(), R.size * W.size)
    return out


def auroc(pq):
    pts = sum(v[0] for v in pq.values())
    n = sum(v[1] for v in pq.values())
    return pts / n


def main():
    rng = np.random.default_rng(0)
    lines = ["| Benchmark | Judge | Strength picked on half 1 / half 2 | Ranking x1 | Ranking at picked strength | Gain, picked [95% CI] | Gain, fixed x11 [95% CI] |",
             "|---|---|---|---|---|---|---|"]
    for bench, model, prefixes, dp in CASES:
        halves = {h: load(prefixes, dp, h) for h in ("h1", "h2")}
        if not all(halves.values()):
            continue
        conds = sorted(set.intersection(*[set(r["m"]) for h in halves.values() for r in h]), key=lambda s: int(s[1:]))
        pick = {}
        for h in halves:
            pick[h] = max(conds, key=lambda c: (auroc(per_question(halves[h], c)), -int(c[1:])))  # tie -> weaker
        # score each half with the strength picked on the OTHER half
        test = {"base": {}, "picked": {}, "x11": {}}
        for h, other in (("h1", "h2"), ("h2", "h1")):
            test["base"].update(per_question(halves[h], "x1"))
            test["picked"].update(per_question(halves[h], pick[other]))
            test["x11"].update(per_question(halves[h], "x11"))
        qs = sorted(test["base"])
        A = {k: np.array([test[k][q] for q in qs]) for k in test}  # (n_q, 2)

        def gain(k, idx=None):
            idx = np.arange(len(qs)) if idx is None else idx
            a = A[k][idx].sum(0)
            b = A["base"][idx].sum(0)
            return 100 * (a[0] / a[1] - b[0] / b[1])

        def ci(k):
            bs = [gain(k, rng.integers(0, len(qs), len(qs))) for _ in range(2000)]
            return np.percentile(bs, [2.5, 97.5])

        gp, gx = gain("picked"), gain("x11")
        (pl, ph), (xl, xh) = ci("picked"), ci("x11")
        b = A["base"].sum(0)
        p = A["picked"].sum(0)
        lines.append(f"| {bench} | {NAME[model]} | {pick['h1'].replace('x', '×')} / {pick['h2'].replace('x', '×')} | "
                     f"{b[0] / b[1]:.3f} | {p[0] / p[1]:.3f} | {gp:+.1f} [{pl:+.1f}, {ph:+.1f}] | {gx:+.1f} [{xl:+.1f}, {xh:+.1f}] |")
    lines += ["", "| Benchmark | Judge | Sensitivity | Formula strength | Nearest tested | Gain there [95% CI] | Best tested (gain) |",
              "|---|---|---|---|---|---|---|"]
    for bench, model, prefixes, dp in CASES:
        rows = [json.loads(x) for h in ("h1", "h2") for x in open(HERE / f"{prefixes[0]}_{h}.jsonl")]
        rows = [r for r in rows if r["dir"].startswith(dp + "_")]
        m = lambda k: np.array([r["margins"][k] for r in rows])  # noqa: E731
        slope = np.mean((m("add:4.0") - m("add:-4.0")) / 8)
        byq = defaultdict(list)
        for r, v in zip(rows, m("add:0.0")):
            byq[r["qid"]].append(v)
        sens = slope / np.sqrt(np.mean([np.var(v) for v in byq.values() if len(v) > 1]))
        allrows = load(prefixes, dp, "h1") + load(prefixes, dp, "h2")
        conds = sorted(set.intersection(*[set(r["m"]) for r in allrows]), key=lambda c: int(c[1:]))
        pq = {c: per_question(allrows, c) for c in conds}
        qs = sorted(pq["x1"])
        A = {c: np.array([pq[c][q] for q in qs]) for c in conds}

        def g(c, idx=slice(None)):
            a, b = A[c][idx].sum(0), A["x1"][idx].sum(0)
            return 100 * (a[0] / a[1] - b[0] / b[1])
        if sens <= 0:
            f, near = "none (verdict doesn't respond)", "x1"
        else:
            fs = 1 + 1 / sens
            f = f"×{fs:.0f}"
            near = min(conds, key=lambda c: abs(np.log(int(c[1:])) - np.log(fs)))
        lo, hi = np.percentile([g(near, rng.integers(0, len(qs), len(qs))) for _ in range(2000)], [2.5, 97.5])
        best = max(conds, key=g)
        lines.append(f"| {bench} | {NAME[model]} | {sens:.2f} | {f} | {near.replace('x', '×')} | {g(near):+.1f} [{lo:+.1f}, {hi:+.1f}] | "
                     f"{best.replace('x', '×')} ({g(best):+.1f}) |")
    out = "\n".join(lines)
    (HERE / "out_strength_select.md").write_text(out + "\n")
    print(out)


if __name__ == "__main__":
    main()
