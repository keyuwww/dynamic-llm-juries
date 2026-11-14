"""Score out_mmlu/PREREGISTRATION_gap_no_response.md (Llama-3.2-3B, Phi-4-mini): does a gap without a responsive verdict
give no gain from stretching? Run in the Cannon folder after the stretchT runs and the vLLM solves have finished.

Inputs per judge: out_mmlu/<judge>/steer_mmlu_stretchT_h{1,2}.jsonl (x2, x4, x11 and the formula strength; judge
direction Jc and random direction Rc), the capture (for KNOWS per group), out/esolves_mmlu_full_<judge>.jsonl (one
answer per question, thinking off; solved = final letter matches the key; an answer that hit the length cap = wrong).
Gain = ranking (within-question AUROC) after the stretch minus unedited, x100; 95% CI by resampling questions
(2000 draws, seed 0).

  python prereg_score_gnr.py -> out_mmlu/prereg_gap_no_response_outcome.md
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stretch_pipeline import center, dom  # noqa: E402

JUDGES = {  # dir -> (name, formula strength key, formula strength)
    "llama3.2-3b": ("Llama-3.2-3B", "amplify:15.0", 16),
    "phi4-mini": ("Phi-4-mini", "amplify:80.0", 81),
}
STR = {"amplify:1.0": 2, "amplify:3.0": 4, "amplify:10.0": 11}


def letter(text):
    m = re.findall(r"answer is:?\s*\**\s*\(?([A-J])\)?\b", text or "", re.I)
    return m[-1].upper() if m else None


def per_q(rows, key, same_src=False):
    by = defaultdict(lambda: ([], []))
    for r in rows:
        g = (r["qid"], r["src"] if same_src else "")
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


def wauc(y, s, q):
    by = defaultdict(lambda: ([], []))
    for yi, si, g in zip(y, s, q):
        by[g][int(yi)].append(si)
    num = den = 0.0
    for neg, pos in by.values():
        if pos and neg:
            P, N = np.array(pos)[:, None], np.array(neg)[None, :]
            num += (P > N).sum() + 0.5 * (P == N).sum()
            den += P.size * N.size
    return num / den


def knows_says(d, sol):
    """KNOWS / SAYS per group from the capture + unedited verdict (as the screen computed them for all answers)."""
    meta = [json.loads(l) for l in open(d / "meta_mmlu.jsonl")]
    layers = json.load(open(d / "layers_mmlu.json"))["layers"]
    ch = json.load(open(d / "direction_choice_mmlu.json"))
    X = np.asarray(np.load(d / "hidden_mmlu.npy", mmap_mode="r")[:, layers.index(int(ch["layer"]))], np.float32)
    y = np.array([m["gold"] for m in meta])
    q = np.array([m["qid"] for m in meta])
    h1 = np.array([x in set(ch["h1"]) for x in q])
    Xc = center(X, q)
    s = np.zeros(len(y))
    for tr, te in ((h1, ~h1), (~h1, h1)):
        s[te] = X[te] @ dom(Xc[tr], y[tr])
    v0 = {}
    for h in ("h1", "h2"):
        for l in open(d / f"steer_mmlu_{h}.jsonl"):
            r = json.loads(l)
            if r["dir"].startswith("Jc"):
                v0[r["aid"]] = r["margins"]["add:0.0"]
    v = np.array([v0[m["aid"]] for m in meta])
    out = {}
    for grp in ("all", "solved", "not solved"):
        k = np.ones(len(y), bool) if grp == "all" else np.array([sol.get(x) == (1 if grp == "solved" else 0) for x in q])
        out[grp] = (wauc(y[k], s[k], q[k]), wauc(y[k], v[k], q[k]))
    return out


def main():
    rng = np.random.default_rng(0)
    qs_key = {json.loads(l)["id"]: json.loads(l)["gold"] for l in open("inputs/mmlu_full.jsonl")}
    L = ["# Pre-registered test: a gap without a responsive verdict (Llama-3.2-3B, Phi-4-mini, MMLU-Redux): outcome\n",
         "Rule: verdict doesn't respond (RESPONDS < 0.10), so gain at ×11 < 3. Naive rule: gain ≈ 0.5 × GAP (±4).\n"]
    for jd, (name, fkey, fstr) in JUDGES.items():
        d = Path("out_mmlu") / jd
        sol = {}
        for l in open(f"out/esolves_mmlu_full_{jd}.jsonl"):
            r = json.loads(l)
            sol[r["qid"]] = 0 if r.get("capped") else int(letter(r["text"]) == qs_key[r["qid"]])
        rows = [json.loads(l) for h in ("h1", "h2") for l in open(d / f"steer_mmlu_stretchT_{h}.jsonl")]
        for r in rows:
            r["src"] = r["aid"].split("|")[1]
        ks = knows_says(d, sol)
        nsol = sum(sol.values())
        L += [f"\n## {name}\n", f"Solves {nsol} of {len(sol)} questions ({nsol / len(sol):.0%}), one answer each.\n",
              "### Gap rule (gain at ×11, judge direction)\n",
              "| Group | Knows | Says | Rule predicts | Naive predicts | Measured gain [95% CI] | Rule holds (< 3) | Naive holds (±4) | "
              "Random direction gain | Same-model pairs gain [95% CI] |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for grp in ("all", "solved", "not solved"):
            def sel(r):
                return grp == "all" or sol.get(r["qid"]) == (1 if grp == "solved" else 0)
            J = [r for r in rows if r["dir"].startswith("Jc") and sel(r)]
            R = [r for r in rows if r["dir"].startswith("Rc") and sel(r)]
            _, A = table(J, ["add:0.0", "amplify:10.0"])
            g, lo, hi = gain_ci(A["add:0.0"], A["amplify:10.0"], rng)
            _, B = table(R, ["add:0.0", "amplify:10.0"])
            gr, lor, hir = gain_ci(B["add:0.0"], B["amplify:10.0"], rng)
            qs, S = table(J, ["add:0.0", "amplify:10.0"], same_src=True)
            if len(qs) >= 30:
                gs, los, his = gain_ci(S["add:0.0"], S["amplify:10.0"], rng)
                ss = f"{gs:+.1f} [{los:+.1f}, {his:+.1f}] ({len(qs)} q)"
            else:
                ss = f"– ({len(qs)} q)"
            kn, sa = ks[grp]
            naive = 50 * (kn - sa)
            L.append(f"| {grp} | {kn:.3f} | {sa:.3f} | < 3 | {naive:+.1f} | {g:+.1f} [{lo:+.1f}, {hi:+.1f}] | "
                     f"**{'yes' if g < 3 else 'no'}** | {'yes' if abs(g - naive) <= 4 else 'no'} | "
                     f"{gr:+.1f} [{lor:+.1f}, {hir:+.1f}] | {ss} |")
        keys = ["add:0.0"] + list(STR) + [fkey]
        sm = dict(STR, **{fkey: fstr})
        J = [r for r in rows if r["dir"].startswith("Jc")]
        R = [r for r in rows if r["dir"].startswith("Rc")]
        _, A = table(J, keys)
        _, B = table(R, keys)
        L += [f"\n### Strength formula (all answers; formula predicts ×{fstr})\n",
              "| Strength | Ranking (judge) | Change vs unedited [95% CI] | Ranking (random) | Accept rate right / wrong (judge) |",
              "|---|---|---|---|---|"]
        au = {}
        for k in keys:
            s = 1 if k == "add:0.0" else sm[k]
            au[s] = 100 * auc(A[k])
            ch = "–" if s == 1 else "{:+.1f} [{:+.1f}, {:+.1f}]".format(*gain_ci(A["add:0.0"], A[k], rng))
            ar = np.mean([r["margins"][k] > 0 for r in J if r["gold"]])
            aw = np.mean([r["margins"][k] > 0 for r in J if not r["gold"]])
            L.append(f"| ×{s}{' (none)' if s == 1 else ''} | {auc(A[k]):.3f} | {ch} | {auc(B[k]):.3f} | {ar:.0%} / {aw:.0%} |")
        tested = {s: v for s, v in au.items() if s != 1}
        best = max(tested, key=tested.get)
        c1, c2 = au[fstr] >= tested[best] - 1, au[fstr] >= au[11] - 1
        L.append(f"\nBest tested: ×{best} ({tested[best]:.1f}); formula ×{fstr} = {au[fstr]:.1f}; ×11 = {au[11]:.1f}; "
                 f"none = {au[1]:.1f}. **Formula holds: {'yes' if c1 and c2 else 'no'}.**\n")
    Path("out_mmlu/prereg_gap_no_response_outcome.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
