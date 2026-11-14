"""Belief bias on minimal pairs (JudgeBench, answer-only template, every option letter; see minimal_pairs_prep.py).

Within a question the response text is identical except the letter, so comparing WRONG letters the judge believes with
WRONG letters it never reaches isolates belief from correctness, style, length and question difficulty.

  1. Behaviour: verdict margin (log p CORRECT - log p INCORRECT at "VERDICT:") and accept rate (margin > 0) by belief,
     wrong letters vs the correct letter; within-question slope (question fixed effects, letter fixed effects).
  2. Pair-difference direction: for each question, mean state of believed wrong letters (>= 4/7) minus mean state of
     never-reached wrong letters (0/7); averaged over training questions, per layer. Scored on held-out questions
     (2 halves, swapped): AUROC believed vs never among wrong letters, and how it ranks the correct letter.
  3. Cosine with the natural-data ridge belief direction (steer_dirs.json, RB2 Math / BFF, fitted at the verdict word).

  python3 experiments/anchoring_early_answer/minimal_pairs_analysis.py
"""
import collections
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
SRC = HERE / "cannon_belief" / "out_pairs"
JUDGES = ["qwen3.5-9b", "qwen3.5-4b"]


def boot(groups, f, n=1000, seed=0):
    rng = np.random.default_rng(seed)
    u = np.array(sorted(set(groups)))
    idx = {g: np.where(groups == g)[0] for g in u}
    bs = [f(np.concatenate([idx[g] for g in rng.choice(u, len(u))])) for _ in range(n)]
    return np.nanpercentile(bs, [2.5, 97.5])


def demean(y, g):
    out = y.astype(float).copy()
    for q in set(g):
        m = g == q
        out[m] -= out[m].mean()
    return out


def fe_slope(y, x, g, letters):
    """Slope of y on x with question fixed effects and letter fixed effects (Frisch-Waugh: residualise on both)."""
    X = np.column_stack([x] + [(letters == L).astype(float) for L in sorted(set(letters))[1:]])
    yd, Xd = demean(y, g), np.column_stack([demean(X[:, i], g) for i in range(X.shape[1])])
    beta = np.linalg.lstsq(Xd, yd, rcond=None)[0]
    return beta[0]


def main():
    meta_all = [json.loads(l) for l in open(HERE / "out" / "minimal_pairs_meta.jsonl")]
    dirs = json.load(open(HERE / "cannon_belief" / "steer_dirs.json"))
    L = ["# Belief bias on minimal pairs (JudgeBench, answer-only)\n",
         "Same question, same response text (\"The answer is (X).\" + XXXXX); only the letter X changes. Belief = share "
         "of the judge's own 7 solves ending in X. Margin = log p(CORRECT) - log p(INCORRECT) right after \"VERDICT:\" "
         "(no written reasoning). Accept = margin > 0. 95% intervals resample whole questions.\n"]
    for judge in JUDGES:
        d = SRC / judge
        if not (d / "meta_ckpt.jsonl").exists():
            L.append(f"\n## {judge}: no capture yet\n")
            continue
        cap = [json.loads(l) for l in open(d / "meta_ckpt.jsonl")]
        H = np.load(d / "hidden_ckpt.npy", mmap_mode="r")
        row = {m["item_id"]: i for i, m in enumerate(cap)}
        M = [m for m in meta_all if m["judge"] == judge and m["item"] in row]
        idx = np.array([row[m["item"]] for m in M])
        mar = np.array([cap[i]["margin"] for i in idx])
        cor = np.array([m["correct"] for m in M])
        k = np.array([m["k"] for m in M])
        bel = np.array([m["belief"] for m in M])
        g = np.array([m["qid"] for m in M])
        let = np.array([m["letter"] for m in M])
        acc = (mar > 0).astype(float)
        L.append(f"\n## {judge}: {len(set(g))} questions, {len(M)} letters\n")
        # 1. behaviour by belief bin
        L.append("| letter | n | accept | mean margin |")
        L.append("|---|---|---|---|")
        bins = [("wrong, 0/7", (cor == 0) & (k == 0)), ("wrong, 1-3/7", (cor == 0) & (k >= 1) & (bel < 4 / 7)),
                ("wrong, 4-6/7", (cor == 0) & (bel >= 4 / 7) & (bel < 1)), ("wrong, 7/7", (cor == 0) & (bel == 1)),
                ("correct, < 4/7", (cor == 1) & (bel < 4 / 7)), ("correct, >= 4/7", (cor == 1) & (bel >= 4 / 7))]
        for name, m in bins:
            if m.sum():
                lo, hi = boot(g[m], lambda ii, a=acc[m]: a[ii].mean())
                L.append(f"| {name} | {m.sum()} | {100 * acc[m].mean():.0f}% [{100 * lo:.0f}, {100 * hi:.0f}] | "
                         f"{mar[m].mean():+.2f} |")
        w = cor == 0
        gw, lw = g[w], let[w]
        s_acc = fe_slope(acc[w], bel[w], gw, lw)
        s_mar = fe_slope(mar[w], bel[w], gw, lw)
        # resampled questions can repeat: their fixed effects merge, which only makes the interval slightly conservative
        lo_a, hi_a = boot(gw, lambda ii: fe_slope(acc[w][ii], bel[w][ii], gw[ii], lw[ii]), n=300)
        lo_m, hi_m = boot(gw, lambda ii: fe_slope(mar[w][ii], bel[w][ii], gw[ii], lw[ii]), n=300)
        L.append(f"\nWithin-question slope among WRONG letters (question + letter fixed effects), belief 0 -> 1: "
                 f"accept {100 * s_acc:+.0f} points [{100 * lo_a:+.0f}, {100 * hi_a:+.0f}], margin {s_mar:+.2f} "
                 f"[{lo_m:+.2f}, {hi_m:+.2f}].\n")
        # 2. pair-difference direction, two halves of questions
        qs = sorted(set(g))
        half = {q: i % 2 for i, q in enumerate(np.random.default_rng(0).permutation(qs))}
        h = np.array([half[q] for q in g])
        believed = w & (bel >= 4 / 7)
        never = w & (k == 0)
        both = [q for q in qs if believed[g == q].any() and never[g == q].any()]
        L.append(f"Pair-difference direction: {len(both)} questions have both a believed (>= 4/7) and a never-reached "
                 f"wrong letter. Held-out score = AUROC believed vs never among wrong letters of the other half "
                 f"(0.5 = chance); 'correct vs never' = how the same direction ranks the correct letter.\n")
        L.append("| layer | believed vs never (held out) | correct vs never (held out) | margin alone, believed vs never | "
                 "cos with ridge belief dir (RB2 / BFF) |")
        L.append("|---|---|---|---|---|")
        nl = H.shape[1]
        Xall = None
        for layer in range(2, nl, 2):
            X = np.asarray(H[idx, layer], np.float32)
            sc = np.full(len(M), np.nan)
            vs = []
            for hh in (0, 1):
                diffs = []
                for q in both:
                    if half[q] != hh:
                        continue
                    m = g == q
                    diffs.append(X[m & believed].mean(0) - X[m & never].mean(0))
                v = np.mean(diffs, 0)
                v /= np.linalg.norm(v) + 1e-9
                vs.append(v)
                sc[h != hh] = X[h != hh] @ v
            sel = believed | never
            a1 = roc_auc_score(believed[sel], sc[sel])
            sel2 = (cor == 1) | never
            a2 = roc_auc_score(cor[sel2], sc[sel2])
            a0 = roc_auc_score(believed[sel], mar[sel])
            v = vs[0] + vs[1]
            v /= np.linalg.norm(v)
            cs = []
            for bench in ("rb2math", "bff"):
                key = f"{bench}|belief|h0|L{layer}"
                cs.append(f"{float(np.dot(v, np.array(dirs[key]['vec']) / np.linalg.norm(dirs[key]['vec']))):+.2f}"
                          if key in dirs and len(dirs[key]['vec']) == len(v) else "–")
            L.append(f"| {layer} | {a1:.2f} | {a2:.2f} | {a0:.2f} | {' / '.join(cs)} |")
        print(f"done {judge}", flush=True)
    (HERE / "out" / "minimal_pairs.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
