"""Is belief just difficulty? (Nov 17)

Belief is a property of a (judge, answer) pair; difficulty is a property of a question (or of a judge on a question).
Three checks on audited wrong answers (thinking off, spoken verdict for the Qwens, checkpoint C for other families):

  1. Within the same question: approval on belief with judge x question fixed effects. Only questions where the same
     judge saw two or more wrong answers with different belief contribute; difficulty is identical within them.
  2. Holding the judge's own accuracy fixed: accuracy = how often the judge's 7 own answers reach the RIGHT answer on
     that question (the belief of the right-labelled answer on the same question). Approval on belief + accuracy
     (+ judge fixed effects), and the staircase within accuracy strata.
  3. The staircase on the hardest questions only (the judge never reaches the right answer, 0/7).

Intervals: 95%, resampling questions (2,000 draws).
  python3 experiments/anchoring_early_answer/validation/difficulty_check.py -> validation/difficulty_check.md
"""
import collections
import gzip
import json
import re
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
V = HERE / "validation"
FAM = [("3 Qwens", "out", ""), ("Nemotron-3-Super", "out_nemotron", "_nemotron"),
       ("DeepSeek-V4.1-Flash", "out_deepseek", "_deepseek"), ("Kimi-K2.6", "out_kimi", "_kimi"),
       ("Nemotron-3-Nano", "out_nano", "_nano")]
BINS = ["0/7", "1-3", "4-6", "7/7"]
NB = 2000


def glm_audit():
    g = {}
    for line in [l for f in ("ask_glm5.3_labelaudit.jsonl", "ask_glm5.3_labelauditrb2.jsonl") for l in open(HERE / "out" / f)]:
        r = json.loads(line)
        m = re.findall(r"AUDIT:\s*(LABEL_OK|LABEL_WRONG|CONTESTED)", r["text"])
        g[r["cache_key"].split("|", 2)[2]] = m[-1] if m else None
    return g


def binof(b):
    k = round(b * 7)
    return "0/7" if k == 0 else "1-3" if k <= 3 else "4-6" if k <= 6 else "7/7"


def demean(v, fes):
    v = v.astype(float).copy()
    for _ in range(50):
        for inv in fes:
            v = v - (np.bincount(inv, v) / np.maximum(np.bincount(inv), 1))[inv]
    return v


def ols_fe(y, X, fes):
    fes = [np.unique(f, return_inverse=True)[1] for f in fes]
    yd = demean(np.asarray(y, float), fes)
    Xd = np.column_stack([demean(X[:, i], fes) for i in range(X.shape[1])])
    return np.linalg.lstsq(Xd, yd, rcond=None)[0]


def boot(rows, f, n=NB, seed=0):
    rng = np.random.default_rng(seed)
    by = collections.defaultdict(list)
    for r in rows:
        by[r["qid"]].append(r)
    qs = list(by)
    est = f(rows)
    draws = []
    for _ in range(n):
        smp = [r for i in rng.choice(len(qs), len(qs)) for r in by[qs[i]]]
        try:
            draws.append(f(smp))
        except Exception:  # noqa: BLE001 -- a draw without enough variation
            pass
    lo, hi = np.nanpercentile(np.array(draws), [2.5, 97.5], axis=0)
    return est, lo, hi


def fmt(e, lo, hi):
    return f"{100 * e:+.0f} [{100 * lo:+.0f}, {100 * hi:+.0f}]"


def load(od, sfx, glm):
    rows = json.load(open(HERE / od / "belief_rows_clean.json"))
    jobs = {(j["judge"], j["item_id"]): j for j in map(json.loads, gzip.open(HERE / "inputs" / f"readout_jobs{sfx}.jsonl.gz", "rt"))}
    acc = {}  # (judge, qid) -> belief of the right-labelled answer = how often the judge reaches the right answer
    W = []
    for r in rows:
        j = jobs[(r["judge"], r["item"])]
        if int(r["target_ok"]) == 1:
            acc[(r["judge"], j["qid"])] = max(acc.get((r["judge"], j["qid"]), 0), float(r["belief"]))
    for r in rows:
        if int(r["target_ok"]) != 0:
            continue
        if glm.get(r["item"]) != "LABEL_OK":
            continue
        v = r["spoken"]  # the stated verdict for every judge (Nov 18; was acc_C for non-Qwen families)
        if v in (None, "None"):
            continue
        j = jobs[(r["judge"], r["item"])]
        W.append(dict(judge=r["judge"], qid=f"{r['bench']}|{j['qid']}", bench=r["bench"], belief=float(r["belief"]),
                      b=binof(float(r["belief"])), y=int(v), acc=acc.get((r["judge"], j["qid"]))))
    return W


def within_q(R):
    y = np.array([r["y"] for r in R], float)
    X = np.array([[r["belief"]] for r in R], float)
    return ols_fe(y, X, [[f"{r['judge']}|{r['qid']}" for r in R]])[0]


def with_acc(R):
    R = [r for r in R if r["acc"] is not None]
    y = np.array([r["y"] for r in R], float)
    X = np.array([[r["belief"], r["acc"]] for r in R], float)
    return ols_fe(y, X, [[r["judge"] for r in R]])


def stair(R):
    return [np.mean([r["y"] for r in R if r["b"] == b]) if any(r["b"] == b for r in R) else np.nan for b in BINS]


def main():
    glm = glm_audit()
    L = ["# Is belief just difficulty?\n",
         "Belief = how often the judge's 7 own answers reach this wrong answer. Difficulty = how often they reach the "
         "RIGHT answer to the same question (the judge's own accuracy there). Audited wrong answers, thinking off. "
         "Effects in points for belief 0/7 → 7/7 (a linear probability model), 95% intervals resampling questions.\n",
         "| judge | wrong answers | 1. within the same question (judge × question FE) | questions that contribute | "
         "2. belief, holding accuracy fixed | accuracy, holding belief fixed |", "|---|---|---|---|---|---|"]
    allW = []
    for name, od, sfx in FAM:
        W = load(od, sfx, glm)
        allW += [dict(r, judge=f"{name}|{r['judge']}") for r in W]
        cnt = collections.defaultdict(set)
        for r in W:
            cnt[(r["judge"], r["qid"])].add(r["b"])
        nq = sum(len(v) > 1 for v in cnt.values())
        e1 = boot(W, within_q)
        e2 = boot(W, with_acc)
        L.append(f"| {name} | {len(W)} | {fmt(*e1)} | {nq} | {fmt(e2[0][0], e2[1][0], e2[2][0])} | "
                 f"{fmt(e2[0][1], e2[1][1], e2[2][1])} |")
    e1 = boot(allW, within_q)
    e2 = boot(allW, with_acc)
    cnt = collections.defaultdict(set)
    for r in allW:
        cnt[(r["judge"], r["qid"])].add(r["b"])
    L.append(f"| **all four families** | {len(allW)} | **{fmt(*e1)}** | {sum(len(v) > 1 for v in cnt.values())} | "
             f"**{fmt(e2[0][0], e2[1][0], e2[2][0])}** | {fmt(e2[0][1], e2[1][1], e2[2][1])} |")

    L += ["", "## 3. The staircase within difficulty strata (all four families pooled)\n",
          "Strata by the judge's own accuracy on the question (its 7 answers reaching the right answer).\n",
          "| judge's accuracy on the question | " + " | ".join(BINS) + " | gap 7/7 − 0/7 |", "|---|---|---|---|---|---|"]
    for lab, f in [("never right (0/7): hardest", lambda a: a == 0), ("1–3 of 7", lambda a: 0 < a < 0.5),
                   ("4–7 of 7: easiest", lambda a: a >= 0.5)]:
        S = [r for r in allW if r["acc"] is not None and f(r["acc"])]
        s = stair(S)
        e = boot(S, lambda R: (lambda t: t[3] - t[0])(stair(R)))
        L.append(f"| {lab} | " + " | ".join(f"{100 * v:.0f}% (n={sum(r['b'] == b for r in S)})" for v, b in zip(s, BINS))
                 + f" | {fmt(*e)} |")
    (V / "difficulty_check.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
