"""Does Llama-3.1-8B's MATH verdict respond to its judge direction at some other layer? (layer_sweep_modal.py)

Per layer, for the judge direction and a random direction, on all / solved / not-solved MATH questions:
  knows        held-out within-question ranking of the direction (same split as stretch_pipeline.py)
  says         within-question ranking of the unedited verdict score
  responds     accept rate at a -8 sd push vs a +8 sd push along the direction
  sensitivity  (verdict change per 1 sd pushed, from +-8) / (verdict's within-question sd); stretch_pipeline used +-4
  gain x11/x21 ranking after stretching minus unedited, x100, 95% CI resampling questions (paired)
  same-model   the x11 gain counting only right-vs-wrong pairs written by the same answering model

  python3 experiments/beyond_capability/layer_sweep_analyze.py [math|mmlu3b] -> <run folder>/layer_sweep.md
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from stretch_analyze import solve_labels  # noqa: E402

RUNS = {  # run -> (folder, tag, solve-label stem, judge key, folder holding the judge's solve file, title)
    "math": ("out_math/layer_sweep", "math", "math_full", "llama3.1-8b", "out_math", "MATH, Llama-3.1-8B"),
    "mmlu3b": ("out_mmlu/layer_sweep_llama3.2-3b", "mmlu", "mmlu_full", "llama3.2-3b", "out_mmlu", "MMLU-Redux, Llama-3.2-3B"),
}
D = HERE / RUNS["math"][0]


def pairs_by_q(rows, key):
    """per question: (points, pairs) for ranking right above wrong."""
    by = defaultdict(lambda: ([], []))
    for r in rows:
        by[r["qid"]][r["gold"]].append(r["margins"][key])
    out = {}
    for q, (neg, pos) in by.items():
        if pos and neg:
            a = np.array(pos)[:, None]
            b = np.array(neg)[None, :]
            out[q] = (float((a > b).sum() + 0.5 * (a == b).sum()), a.size * b.size)
    return out


def gain(rows, key, n=1000, seed=0):
    b, s = pairs_by_q(rows, "none"), pairs_by_q(rows, key)
    qs = sorted(b)
    B = np.array([b[q] for q in qs])
    S = np.array([s[q] for q in qs])
    g = lambda i: 100 * (S[i, 0].sum() / S[i, 1].sum() - B[i, 0].sum() / B[i, 1].sum())  # noqa: E731
    rng = np.random.default_rng(seed)
    bs = [g(rng.integers(0, len(qs), len(qs))) for _ in range(n)]
    return g(slice(None)), np.percentile(bs, 2.5), np.percentile(bs, 97.5), B[:, 0].sum() / B[:, 1].sum()


def sensitivity(rows):
    m = lambda k: np.array([r["margins"][k] for r in rows])  # noqa: E731
    slope = np.mean((m("add:8.0") - m("add:-8.0")) / 16)
    byq = defaultdict(list)
    for r in rows:
        byq[r["qid"]].append(r["margins"]["none"])
    return slope / np.sqrt(np.mean([np.var(v) for v in byq.values() if len(v) > 1]))


def accept(rows, key):
    return 100 * np.mean([r["margins"][key] > 0 for r in rows])


def main():
    run = sys.argv[1] if len(sys.argv) > 1 else "math"
    folder, tag, stem, judge, sdir, title = RUNS[run]
    D = HERE / folder
    rows = [json.loads(l) for f in sorted(D.glob(f"sweep_{tag}_L*.jsonl")) for l in open(f)]
    knows = {int(L): v["knows"] for L, v in json.load(open(D / f"sweep_dirs_{tag}.json"))["layers"].items()}
    sol = solve_labels(stem, judge, HERE / sdir)
    groups = {"all": lambda q: True, "solved": lambda q: sol.get(q) == 1, "not solved": lambda q: sol.get(q) == 0}
    lines = [f"# {title}: stretching at every other layer", "",
             f"{len({r['aid'] for r in rows})} answers. Ranking = within-question AUROC (0.50 = coin flip). "
             "Gain = ranking change x100 after stretching, 95% CI resampling questions. "
             "Accept rates are the share of all answers the verdict calls CORRECT.", ""]
    for gname, gf in groups.items():
        lines += [f"## {gname}", "",
                  "| Layer | Knows | Says | Accept at −8 sd → +8 sd | Sensitivity | Gain ×11 [95% CI] | Gain ×21 [95% CI] | Random ×11 |",
                  "|---|---|---|---|---|---|---|---|"]
        for L in sorted({r["layer"] for r in rows}):
            J = [r for r in rows if r["layer"] == L and r["dir"] == "Jc" and gf(r["qid"])]
            R = [r for r in rows if r["layer"] == L and r["dir"] == "Rc" and gf(r["qid"])]
            g11, l11, h11, says = gain(J, "amplify:10.0")
            g21, l21, h21, _ = gain(J, "amplify:20.0")
            r11 = gain(R, "amplify:10.0", n=1)[0]
            kn = f"{knows[L]:.3f}" if gname == "all" else "–"
            lines.append(f"| {L} | {kn} | {says:.3f} | {accept(J, 'add:-8.0'):.0f}% → {accept(J, 'add:8.0'):.0f}% | "
                         f"{sensitivity(J):+.2f} | {g11:+.1f} [{l11:+.1f}, {h11:+.1f}] | {g21:+.1f} [{l21:+.1f}, {h21:+.1f}] | "
                         f"{r11:+.1f} |")
        lines.append("")
    # same-model pairs: compare right vs wrong answers only within one answering model (removes "who wrote it")
    sm = [dict(r, qid=r["qid"] + "|" + r["src"], q0=r["qid"]) for r in rows]
    lines += ["## Same-model pairs only (right vs wrong answers from the same answering model to the same question)", "",
              "| Layer | Questions | Says | Gain ×11 [95% CI] | Random ×11 |", "|---|---|---|---|---|"]
    for L in sorted({r["layer"] for r in rows}):
        for gname in ("solved", "not solved"):
            gf = groups[gname]
            J = [r for r in sm if r["layer"] == L and r["dir"] == "Jc" and gf(r["q0"])]
            R = [r for r in sm if r["layer"] == L and r["dir"] == "Rc" and gf(r["q0"])]
            g, lo, hi, says = gain(J, "amplify:10.0")
            lines.append(f"| {L} | {gname} | {says:.3f} | {g:+.1f} [{lo:+.1f}, {hi:+.1f}] | {gain(R, 'amplify:10.0', n=1)[0]:+.1f} |")
    lines.append("")
    (D / "layer_sweep.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
