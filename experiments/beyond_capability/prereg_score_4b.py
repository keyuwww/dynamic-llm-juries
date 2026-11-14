"""Score the pre-registered Qwen3.5-4B predictions (out_mmlu/qwen3.5-4b/PREREGISTRATION.md) on the stretch run.

Inputs: out_mmlu/qwen3.5-4b/steer_mmlu_stretchT_h{1,2}.jsonl (job 59930641, gpu_test copy of 59736975; strengths
x2, x4, x9, x11 = amplify 1, 3, 8, 10), out_checks/sol_mmlu_4b.json (solve labels, majority of 3), source model
from the answer id. Ranking = within-question AUROC (pairs of one right and one wrong answer to the same question).
Gain = ranking after the stretch minus unedited, x100; 95% CI by resampling questions (2000 draws, seed 0).
Same-model secondary: only pairs whose two answers come from the same answering model.

  python3 experiments/beyond_capability/prereg_score_4b.py -> out_mmlu/qwen3.5-4b/prereg_outcome.md
"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
D = HERE / "out_mmlu" / "qwen3.5-4b"
M = "qwen3.5-4b"
STR = {"amplify:1.0": 2, "amplify:3.0": 4, "amplify:8.0": 9, "amplify:10.0": 11}
PRED = {  # group -> (predicted gain at x11, lo, hi), from PREREGISTRATION.md
    ("with own answers", "all"): (0.6, -3.4, 4.6), ("with own answers", "solved"): (0.6, -3.4, 4.6),
    ("with own answers", "not solved"): (0.6, -3.4, 4.6), ("without own answers", "all"): (-1.3, -5.3, 2.7),
    ("without own answers", "solved"): (-1.7, -5.7, 2.3), ("without own answers", "not solved"): (-0.6, -4.6, 3.4)}


def per_q(rows, key, same_src=False):
    """question -> (wins, pairs) for ranking right above wrong by margins[key]."""
    by = defaultdict(lambda: ([], []))
    for r in rows:
        g = (r["qid"], r["src"]) if same_src else (r["qid"], "")
        by[g][0 if r["gold"] else 1].append(r["margins"][key])
    out = defaultdict(lambda: np.zeros(2))
    for (q, _), (R, W) in by.items():
        if R and W:
            R, W = np.array(R)[:, None], np.array(W)[None, :]
            out[q] += [(R > W).sum() + 0.5 * (R == W).sum(), R.size * W.size]
    return out


def table(rows, keys, same_src=False):
    pq = {k: per_q(rows, k, same_src) for k in keys}
    qs = sorted(pq[keys[0]])
    return qs, {k: np.array([pq[k][q] for q in qs]) for k in keys}


def auc(A, i=slice(None)):
    s = A[i].sum(0)
    return s[0] / s[1]


def gain_ci(A0, A1, rng):
    n = len(A0)
    g = 100 * (auc(A1) - auc(A0))
    bs = [100 * (auc(A1, i) - auc(A0, i)) for i in (rng.integers(0, n, n) for _ in range(2000))]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return g, lo, hi


def main():
    rng = np.random.default_rng(0)
    sol = json.load(open(HERE / "out_checks" / "sol_mmlu_4b.json"))[M]
    rows = [json.loads(l) for h in ("h1", "h2") for l in open(D / f"steer_mmlu_stretchT_{h}.jsonl")]
    for r in rows:
        r["src"] = r["aid"].split("|")[1]
    # sanity: the unedited verdict should match the earlier shift-only run (different GPU)
    old = {json.loads(l)["aid"]: json.loads(l)["margins"]["add:0.0"]
           for h in ("h1", "h2") for l in open(D / f"steer_mmlu_{h}.jsonl") if json.loads(l)["dir"].startswith("Jc")}
    jc = [r for r in rows if r["dir"].startswith("Jc")]
    diff = np.array([r["margins"]["add:0.0"] - old[r["aid"]] for r in jc if r["aid"] in old])
    keys = ["add:0.0"] + list(STR)
    L = ["# Pre-registered test, Qwen3.5-4B on MMLU-Redux: outcome\n",
         f"Stretch run: job 59930641 (gpu_test, A100 MIG slice). {len(jc)} answers per direction. Unedited verdict vs "
         f"the earlier shift-only run (different GPU): same within 0.25 for {np.mean(np.abs(diff) <= 0.25):.1%}, "
         f"same accept/reject for {np.mean([(r['margins']['add:0.0'] > 0) == (old[r['aid']] > 0) for r in jc if r['aid'] in old]):.1%}.\n",
         "## 1. Gap rule (gain at x11, judge direction)\n",
         "| Group | Predicted | Measured gain [95% CI] | In range? | CI includes 0? | Rule holds | Random direction gain | Same-model pairs: gain [95% CI] |",
         "|---|---|---|---|---|---|---|---|"]
    held = []
    for (own, grp), (p, lo_ok, hi_ok) in PRED.items():
        def sel(r):
            return (own == "with own answers" or r["src"] != M) and (grp == "all" or sol.get(r["qid"]) == (1 if grp == "solved" else 0))
        J = [r for r in rows if r["dir"].startswith("Jc") and sel(r)]
        R = [r for r in rows if r["dir"].startswith("Rc") and sel(r)]
        _, A = table(J, ["add:0.0", "amplify:10.0"])
        g, lo, hi = gain_ci(A["add:0.0"], A["amplify:10.0"], rng)
        _, B = table(R, ["add:0.0", "amplify:10.0"])
        gr, lor, hir = gain_ci(B["add:0.0"], B["amplify:10.0"], rng)
        qs, S = table(J, ["add:0.0", "amplify:10.0"], same_src=True)
        if len(qs) >= 30:
            gs, los, his = gain_ci(S["add:0.0"], S["amplify:10.0"], rng)
            ss = f"{gs:+.1f} [{los:+.1f}, {his:+.1f}] ({len(qs)} q, {int(S['add:0.0'][:, 1].sum())} pairs)"
        else:
            ss = f"– ({len(qs)} questions with a same-model pair)"
        inr, inc0 = lo_ok <= g <= hi_ok, lo <= 0 <= hi
        held.append(inr and inc0)
        L.append(f"| {own}, {grp} | {p:+.1f} | {g:+.1f} [{lo:+.1f}, {hi:+.1f}] | {'yes' if inr else 'no'} | "
                 f"{'yes' if inc0 else 'no'} | **{'yes' if inr and inc0 else 'no'}** | {gr:+.1f} [{lor:+.1f}, {hir:+.1f}] | {ss} |")
    L.append(f"\nGap rule holds in {sum(held)} of {len(held)} groups.\n")

    L += ["## 2. Strength formula (all answers, with own answers; formula predicts x9)\n",
          "| Strength | Ranking (judge) | Change vs unedited [95% CI] | Ranking (random) | Accept rate right / wrong (judge) |",
          "|---|---|---|---|---|"]
    J = [r for r in rows if r["dir"].startswith("Jc")]
    R = [r for r in rows if r["dir"].startswith("Rc")]
    _, A = table(J, keys)
    _, B = table(R, keys)
    au = {}
    for k in keys:
        s = 1 if k == "add:0.0" else STR[k]
        au[s] = 100 * auc(A[k])
        ch = "–" if s == 1 else "{:+.1f} [{:+.1f}, {:+.1f}]".format(*gain_ci(A["add:0.0"], A[k], rng))
        acc_r = np.mean([r["margins"][k] > 0 for r in J if r["gold"]])
        acc_w = np.mean([r["margins"][k] > 0 for r in J if not r["gold"]])
        L.append(f"| x{s}{' (none)' if s == 1 else ''} | {auc(A[k]):.3f} | {ch} | {auc(B[k]):.3f} | {acc_r:.0%} / {acc_w:.0%} |")
    tested = {s: v for s, v in au.items() if s != 1}
    best = max(tested, key=tested.get)
    c1 = au[9] >= tested[best] - 1
    c2 = au[9] >= au[11] - 1
    L.append(f"\nBest tested strength: x{best} ({tested[best]:.1f}). x9 = {au[9]:.1f}: within 1 point of best: "
             f"{'yes' if c1 else 'no'}; at least as good as x11 (within 1): {'yes' if c2 else 'no'}. "
             f"**Formula holds: {'yes' if c1 and c2 else 'no'}.** No stretch (x1) = {au[1]:.1f}.\n")
    (D / "prereg_outcome.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
