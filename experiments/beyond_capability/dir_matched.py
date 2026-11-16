"""Matched-position check for "solving and judging use unrelated directions" (Nov 16).

The original study read the generate role (G) at the last token of the answer, but the judge (J) and self-check (S)
roles right after "VERDICT:". G and S frame the answer the same way (as the model's own) and still came out unrelated,
so the split may be about WHERE the state is read, not about solving vs judging. The neutral role N reads the answer
as the model's own at an S-like position (a follow-up turn + a fixed suffix, "FINAL:") without asking for a verdict.

  N ~ J (cosine near the J.S level)  -> the earlier split was the read position; soften the claim
  N ~ G, N far from J                -> solving-side and verdict-side correctness are encoded differently

For each model and benchmark, at every kept layer: question-centred "right minus wrong" directions per role
(difference of means), cosines between roles with split-half ceilings, and probe transfer (train on one role, test on
another, whole questions held out; within-question AUROC). The model's own pool answers are left out.

  python3 experiments/beyond_capability/dir_matched.py --key qwen3.5-9b --tags main,neutral
  python3 experiments/beyond_capability/dir_matched.py --key qwen3.6-35b-a3b --tags roles4
      -> out_dirs/matched_<key>.md
"""
import argparse
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from dir_analyze import center, cos, dom, load, probe_cv, transfer, wq  # noqa: E402

ROLES = ["J", "G", "S", "N"]
NAMES = {"J": "judge", "G": "generate (end of answer)", "S": "self-check (VERDICT:)", "N": "neutral (FINAL:)"}


def split_half(X, y, q, seed=0):
    u = sorted(set(q))
    rng = np.random.default_rng(seed)
    half = set(rng.permutation(u)[: len(u) // 2])
    a = np.array([x in half for x in q])
    return cos(dom(X[a], y[a]), dom(X[~a], y[~a]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--tags", required=True, help="capture tags to combine, e.g. main,neutral")
    a = ap.parse_args()
    parts = [load(a.key, t) for t in a.tags.split(",")]
    layers = parts[0][2]
    assert all(p[2] == layers for p in parts), "captures must keep the same layers"
    rows = {}  # (bench, role) -> (H rows list, meta list)
    for H, meta, _ in parts:
        for i, m in enumerate(meta):
            if m["mode"] not in ROLES or m["src"] == a.key:
                continue
            rows.setdefault((m["bench"], m["mode"]), ([], []))
            rows[(m["bench"], m["mode"])][0].append(H[i])
            rows[(m["bench"], m["mode"])][1].append(m)
    L = [f"# Matched-position check: {a.key}\n",
         "Cosine between question-centred 'right minus wrong' directions (1 = same, 0 = unrelated). Ceiling = the same "
         "role's direction from two random halves of the questions. Answers: the same texts in every role; the model's "
         "own pool answers left out.\n"]
    for bench in ("bbeh", "rb2math"):
        have = [r for r in ROLES if (bench, r) in rows]
        if len(have) < 2:
            continue
        # align the roles on the same answers
        aids = set.intersection(*[{m["aid"] for m in rows[(bench, r)][1]} for r in have])
        data = {}
        for r in have:
            Hs, ms = rows[(bench, r)]
            idx = sorted((m["aid"], i) for i, m in enumerate(ms) if m["aid"] in aids)
            X = np.stack([Hs[i] for _, i in idx]).astype(np.float32)  # [n, layers, d]
            meta = [ms[i] for _, i in idx]
            data[r] = (X, np.array([m["gold"] for m in meta]), np.array([m["qid"] for m in meta]))
        y, q = data[have[0]][1], data[have[0]][2]
        assert all((data[r][1] == y).all() and (data[r][2] == q).all() for r in have)
        pairs = [(r1, r2) for i, r1 in enumerate(have) for r2 in have[i + 1:]]
        L += [f"## {bench} ({len(y)} answers, {len(set(q))} questions, {int(y.sum())} right)\n",
              "| layer | " + " | ".join(f"{r1}·{r2}" for r1, r2 in pairs) + " | " +
              " | ".join(f"ceiling {r}" for r in have) + " |",
              "|---|" + "---|" * (len(pairs) + len(have))]
        best = {}
        for li, layer in enumerate(layers):
            D, ceil = {}, {}
            for r in have:
                Xc = center(data[r][0][:, li], q)
                D[r] = dom(Xc, y)
                ceil[r] = split_half(Xc, y, q)
            cells = [f"{cos(D[r1], D[r2]):+.2f}" for r1, r2 in pairs] + [f"{ceil[r]:.2f}" for r in have]
            L.append(f"| {layer} | " + " | ".join(cells) + " |")
            best[layer] = D
        # probe transfer at the judge role's best layer (within-question AUROC of a cross-validated judge probe)
        jl = max(range(len(layers)), key=lambda li: wq(y, probe_cv(data["J"][0][:, li], y, q), q)) if "J" in have else 0
        L += ["", f"Probe transfer at layer {layers[jl]} (the judge role's best): within-question AUROC, "
              "row = trained on, column = tested on (0.5 = chance).\n",
              "| trained on \\ tested on | " + " | ".join(have) + " |", "|---|" + "---|" * len(have)]
        for r1 in have:
            cells = []
            for r2 in have:
                X1, X2 = data[r1][0][:, jl], data[r2][0][:, jl]
                p = probe_cv(X1, y, q) if r1 == r2 else transfer(X1, y, q, X2, q)
                cells.append(f"{wq(y, p, q):.2f}")
            L.append(f"| {r1} {NAMES[r1]} | " + " | ".join(cells) + " |")
        L.append("")
    out = HERE / "out_dirs" / f"matched_{a.key}.md"
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    print("wrote", out)


if __name__ == "__main__":
    main()
