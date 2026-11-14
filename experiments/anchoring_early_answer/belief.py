"""Belief strength: does a judge accept a wrong answer more the more strongly it believes that answer itself?

The match/differ split used so far rests on ONE own answer per question (T=0.7), a noisy stand-in for what the judge
believes. tinker_jobs.py --phase belief has each Qwen answer every main-set question 7 more times (same prompt and
settings); every answer is compared with every candidate (GLM-5.3-Flash; JudgeBench 5x letters exactly). For each
(judge, candidate):

  belief = share of the 7 NEW answers that reach the candidate's final answer (0/7 .. 7/7)

Sample 0 (the one that defined match/differ) is left out of `belief`, so belief and the old match label are two
independent measurements of the same thing; the horse race in section 3 relies on that.

JudgeBench is pairwise: the row's target (as in analyze.py) is the response that reaches the judge's own answer
(match) or the wrong response (differ); "accepts" = prefers the target, belief = belief in the target.

  python3 experiments/anchoring_early_answer/belief.py [--pilot]   (needs out/rows.json from analyze.py)
  python3 experiments/anchoring_early_answer/belief.py --judge=llama3.1-8b
      Llama-3.1-8B (open judge): rows from out_llama/belief_base_rows.json (llama_belief_rows.py), own answers and
      matches from out_llama/; writes out/belief_llama3.1-8b.md + out/belief_rows_llama3.1-8b.json. For Llama
      acc_C is its spoken verdict (it often skips the VERDICT line, so there is no exact verdict position).
"""
import collections
import gzip
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from analyze import MAIN, _cluster_boot, letter  # noqa: E402
from clean_labels import same_value_items  # noqa: E402

OPEN = next((a.split("=")[1] for a in sys.argv if a.startswith("--judge=")), "")
SRC = HERE / ("out_pilot" if "--pilot" in sys.argv else "out_llama" if OPEN == "llama3.1-8b" else "out")
DST = HERE / "out"
CLEAN = "--clean" in sys.argv  # drop RB2-Math wrong answers that reach the right value (clean_labels.py)
TAG = (f"_{OPEN}" if OPEN else "") + ("_clean" if CLEAN else "")
NB = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--nb=")), 2000))


def load(p):
    return [json.loads(l) for l in open(p)] if p.exists() else []


def build():
    rows = [r for r in json.load(open(SRC / "belief_base_rows.json" if OPEN else DST / "rows.json")) if r["bench"] in MAIN]
    with gzip.open(HERE / "inputs" / "readout_jobs.jsonl.gz", "rt") as f:
        if OPEN:  # judge prompts are judge-independent: qwen3.5-4b's, relabelled
            jobs = {(OPEN, j["item_id"]): j for j in map(json.loads, f) if j["bench"] in MAIN and j["judge"] == "qwen3.5-4b"}
        else:
            jobs = {(j["judge"], j["item_id"]): j for j in map(json.loads, f) if j["bench"] in MAIN}
    own = collections.defaultdict(dict)  # (judge, qid) -> {sample: answer}
    for s in load(SRC / "solves_k.jsonl"):
        own[(s["model"], s["qid"])][s["sample"]] = s
    glm = {r["cache_key"]: r["verdict"] for r in load(SRC / "matches_glm5.3-flash_k.jsonl")}
    # answers that hit the 64K limit were answered again from scratch (tinker_jobs.py --phase belief --extended)
    for s in load(SRC / "solves_k_rerun.jsonl"):
        own[(s["model"], s["qid"])][s["sample"]] = s
    glm.update({r["cache_key"]: r["verdict"] for r in load(SRC / "matches_glm5.3-flash_k_rerun.jsonl")})

    def votes(judge, j, ci):
        """SAME / DIFFERENT for each new own answer vs candidate ci (None where undecided)."""
        out = []
        cand = j["candidates"][ci]
        for s, o in sorted(own[(judge, j["qid"])].items()):
            if j["bench"] == "judgebench" and letter(o["answer"]) and letter(cand):
                out.append(letter(o["answer"]) == letter(cand))
            else:
                v = glm.get(f"{judge}|{j['item_id']}|{ci}|s{s}")
                out.append(None if v not in ("SAME", "DIFFERENT") else v == "SAME")
        return [v for v in out if v is not None]

    R = []
    for r in rows:
        j = jobs[(r["judge"], r["item"])]
        if j["bench"] == "judgebench":
            gold = int(j["gold"])
            ti = 0 if ((gold == 1) if r["target_ok"] else (gold == 0)) else 1
        else:
            ti = 0
        v = votes(r["judge"], j, ti)
        if len(v) < 5:  # need at least 5 of the 7 new answers decided
            continue
        x = dict(r, belief=float(np.mean(v)), n_votes=len(v), match0=int(r["group"] == "match"))
        if j["bench"] == "judgebench":
            vo = votes(r["judge"], j, 1 - ti)
            x["belief_other"] = float(np.mean(vo)) if len(vo) >= 5 else None
        R.append(x)
    return R


def bins(b):
    return "0/7" if b == 0 else "all 7" if b == 1 else "1-3 of 7" if b < 0.5 else "4-6 of 7"


BINS = ["0/7", "1-3 of 7", "4-6 of 7", "all 7"]


def demean(v, fes):
    v = v.astype(float).copy()
    for _ in range(60):
        for inv in fes:
            v = v - (np.bincount(inv, v) / np.bincount(inv))[inv]
    return v


def ols_fe(R, ycol, xcols, fe_keys):
    """Linear probability model with fixed effects; returns the coefficients on xcols."""
    if len(R) < 3:
        return np.full(len(xcols), np.nan)
    y = np.array([r[ycol] for r in R], float)
    X = np.array([[r[c] for c in xcols] for r in R], float)
    fes = [np.unique([k(r) for r in R], return_inverse=True)[1] for k in fe_keys]
    yd = demean(y, fes)
    Xd = np.column_stack([demean(X[:, i], fes) for i in range(X.shape[1])])
    if np.linalg.matrix_rank(Xd) < Xd.shape[1]:
        return np.full(len(xcols), np.nan)
    return np.linalg.lstsq(Xd, yd, rcond=None)[0]


def ci(R, f):
    est, lo, hi = _cluster_boot(R, f, NB)
    return f"{100 * est:+.0f} [{100 * lo:+.0f}, {100 * hi:+.0f}]"


def pct(x):
    return f"{100 * np.mean(x):.0f}%" if len(x) else "–"


JFE = (lambda r: f"{r['bench']}|{r['judge']}",)
CFE = (lambda r: f"{r['bench']}|{r['judge']}", lambda r: f"{r['bench']}|{r['item']}")  # same candidate


def main():
    R = build()
    n_bad = 0
    if CLEAN:
        bad = same_value_items()
        n_bad = sum(r["target_ok"] == 0 and r["item"] in bad for r in R)
        R = [r for r in R if not (r["target_ok"] == 0 and r["item"] in bad)]
    L = ["# Belief strength: acceptance vs how often the judge itself reaches the candidate's answer\n",
         "belief = share of 7 fresh own answers (T=0.7, same prompt) that reach the candidate's final answer. "
         "Sample 0, which defined match/differ, is not part of it. Accepts at A = before reasoning; at C = at the "
         "verdict (readout). Effects in percentage points, 95% intervals resample whole questions.\n",
         f"Rows with a belief score: {len(R)} (of the main-set rows in rows.json).\n"]
    if CLEAN:
        L.append(f"Clean labels: {n_bad} rows dropped, RB2-Math 'wrong' answers that reach the right value "
                 "(GLM audit, clean_labels.py).\n")
    W = [r for r in R if r["target_ok"] == 0]
    Cr = [r for r in R if r["target_ok"] == 1]
    sets = [("main", lambda r: True)] + [(b, lambda r, b=b: r["bench"] == b) for b in MAIN]

    L.append("## 1. How stable is the judge's own answer? (wrong candidates)\n")
    L.append("| set | n | belief 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | old label 'match' among belief 0/7 | "
             "old 'differ' among all 7 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for name, f in sets:
        X = [r for r in W if f(r)]
        c = collections.Counter(bins(r["belief"]) for r in X)
        z = [r["match0"] for r in X if r["belief"] == 0]
        o = [1 - r["match0"] for r in X if r["belief"] == 1]
        L.append(f"| {name} | {len(X)} | " + " | ".join(f"{c[b]}" for b in BINS) + f" | {pct(z)} | {pct(o)} |")

    for ck in ("A", "C"):
        L.append(f"\n## 2{'a' if ck == 'A' else 'b'}. Wrong candidates accepted at {ck}, by belief\n")
        L.append("| set | " + " | ".join(f"{b}" for b in BINS) + " | slope (all 7 vs 0/7, judge FE) |")
        L.append("|---|---|---|---|---|---|")
        for name, f in sets:
            X = [r for r in W if f(r) and r[f"acc_{ck}"] is not None]
            cells = []
            for b in BINS:
                xs = [r[f"acc_{ck}"] for r in X if bins(r["belief"]) == b]
                cells.append(f"{pct(xs)} (n={len(xs)})")
            sl = ci(X, lambda S, ck=ck: ols_fe(S, f"acc_{ck}", ["belief"], JFE)[0])
            L.append(f"| {name} | " + " | ".join(cells) + f" | {sl} |")

    L.append("\n## 3. Which matters: belief, or the single answer that defined match/differ?\n")
    L.append("Wrong candidates, both in one model (judge FE). If anchoring is about what the judge believes, belief "
             "should carry the effect and the old single-sample label should add little once belief is known.\n")
    L.append("| set | checkpoint | old label alone | belief alone | old label, belief held fixed | "
             "belief, old label held fixed |")
    L.append("|---|---|---|---|---|---|")
    for name, f in sets:
        for ck in ("A", "C"):
            X = [r for r in W if f(r) and r[f"acc_{ck}"] is not None]
            y = f"acc_{ck}"
            L.append(f"| {name} | {ck} | {ci(X, lambda S: ols_fe(S, y, ['match0'], JFE)[0])} | "
                     f"{ci(X, lambda S: ols_fe(S, y, ['belief'], JFE)[0])} | "
                     f"{ci(X, lambda S: ols_fe(S, y, ['match0', 'belief'], JFE)[0])} | "
                     f"{ci(X, lambda S: ols_fe(S, y, ['match0', 'belief'], JFE)[1])} |")

    L.append("\n## 4. Same wrong candidate, different judges (candidate FE + judge FE)\n")
    L.append("Is it the judge's OWN belief, or a belief every Qwen shares? Only candidates the three Qwens believe to "
             "different degrees identify this.\n")
    L.append("| set | belief effect at A | at C | C minus A |")
    L.append("|---|---|---|---|")
    for name, f in sets:
        X = [r for r in W if f(r) and r["acc_A"] is not None and r["acc_C"] is not None]
        a = ci(X, lambda S: ols_fe(S, "acc_A", ["belief"], CFE)[0])
        c = ci(X, lambda S: ols_fe(S, "acc_C", ["belief"], CFE)[0])
        d = ci(X, lambda S: ols_fe(S, "acc_C", ["belief"], CFE)[0] - ols_fe(S, "acc_A", ["belief"], CFE)[0])
        L.append(f"| {name} | {a} | {c} | {d} |")

    L.append("\n## 5. Correct candidates: does low belief make the judge reject a right answer?\n")
    L.append("| set | " + " | ".join(BINS) + " | slope at A | slope at C |")
    L.append("|---|---|---|---|---|---|---|")
    for name, f in sets:
        X = [r for r in Cr if f(r) and r["acc_A"] is not None and r["acc_C"] is not None]
        cells = []
        for b in BINS:
            xs = [r for r in X if bins(r["belief"]) == b]
            cells.append(f"{pct([r['acc_A'] for r in xs])}→{pct([r['acc_C'] for r in xs])} (n={len(xs)})")
        L.append(f"| {name} | " + " | ".join(cells) + f" | {ci(X, lambda S: ols_fe(S, 'acc_A', ['belief'], JFE)[0])}"
                 f" | {ci(X, lambda S: ols_fe(S, 'acc_C', ['belief'], JFE)[0])} |")

    (DST / f"belief{TAG}.md").write_text("\n".join(L) + "\n")
    json.dump(R, open(DST / f"belief_rows{TAG}.json", "w"))
    print("\n".join(L))


if __name__ == "__main__":
    main()
