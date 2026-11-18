"""Every behavioural number in the paper, recomputed from the raw belief rows in ONE place (Nov 18).

Conventions (used everywhere unless a row says otherwise):
  approval   the verdict the judge states at the end of its transcript (spoken; agrees with the forced read at the
             transcript's end, acc_C, on 97-100% of rows); JudgeBench: picking the target response
  belief     share of the judge's 7 extra own answers (T=0.7) that reach the candidate's final answer
  labels     audited: a wrong-labelled answer is kept only if GLM-5.3 audits it as clearly wrong (LABEL_OK), on all three
             benchmarks (RB2 Math additionally had the value-match cleaning before); "released" = no audit
  intervals  95%, resampling whole questions (judge-independent question id), 2,000 draws
  effects    linear probability model, belief 0 -> 1 (= 0/7 -> 7/7), in points

  python3 experiments/anchoring_early_answer/validation/paper_numbers.py  -> validation/paper_numbers.md (+ .json)
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
OUT = {}


def audit(name):
    g = {}
    for line in open(HERE / "out" / name):
        r = json.loads(line)
        m = re.findall(r"AUDIT:\s*(LABEL_OK|LABEL_WRONG|CONTESTED)", r["text"])
        g[r["cache_key"].split("|", 2)[2]] = m[-1] if m else None
    return g


GLM = {**audit("ask_glm5.3_labelaudit.jsonl"), **audit("ask_glm5.3_labelauditrb2.jsonl")}  # BFF+JB, and RB2 Math (Nov 18)


def binof(b):
    k = round(b * 7)
    return "0/7" if k == 0 else "1-3" if k <= 3 else "4-6" if k <= 6 else "7/7"


def load(od, sfx):
    jobs = {(j["judge"], j["item_id"]): j for j in map(json.loads, gzip.open(HERE / "inputs" / f"readout_jobs{sfx}.jsonl.gz", "rt"))}
    R = []
    for r in json.load(open(HERE / od / "belief_rows_clean.json")):
        if r["spoken"] in (None, "None"):
            continue
        j = jobs[(r["judge"], r["item"])]
        R.append(dict(judge=r["judge"], item=r["item"], bench=r["bench"], qid=f"{r['bench']}|{j['qid']}",
                      ok=int(r["target_ok"]), y=int(r["spoken"]), yA=r["acc_A"], belief=float(r["belief"]),
                      b=binof(float(r["belief"])), match0=int(r["match0"]),
                      audited=int(r["target_ok"]) == 1 or GLM.get(r["item"]) == "LABEL_OK"))
    return R


def demean(v, fes):
    v = np.asarray(v, float).copy()
    for _ in range(60):
        for inv in fes:
            v = v - (np.bincount(inv, v) / np.maximum(np.bincount(inv), 1))[inv]
    return v


def ols(R, ycol, xcols, fe):
    y = np.array([r[ycol] for r in R], float)
    X = np.array([[r[c] for c in xcols] for r in R], float)
    fes = [np.unique([f(r) for r in R], return_inverse=True)[1] for f in fe]
    yd = demean(y, fes)
    Xd = np.column_stack([demean(X[:, i], fes) for i in range(X.shape[1])])
    return np.linalg.lstsq(Xd, yd, rcond=None)[0]


def boot(R, f, seed=0):
    by = collections.defaultdict(list)
    for r in R:
        by[r["qid"]].append(r)
    qs = list(by)
    rng = np.random.default_rng(seed)
    est = np.atleast_1d(f(R))
    d = []
    for _ in range(NB):
        smp = [r for i in rng.choice(len(qs), len(qs)) for r in by[qs[i]]]
        try:
            d.append(np.atleast_1d(f(smp)))
        except Exception:  # noqa: BLE001
            pass
    lo, hi = np.nanpercentile(np.array(d), [2.5, 97.5], axis=0)
    return est, lo, hi


def stair(R, key="y"):
    return np.array([np.mean([r[key] for r in R if r["b"] == b]) if any(r["b"] == b for r in R) else np.nan
                     for b in BINS])


def f_ci(t, i=0):
    e, lo, hi = t
    return f"{100 * e[i]:+.0f} [{100 * lo[i]:+.0f}, {100 * hi[i]:+.0f}]"


def main():
    L = ["# Paper numbers (single source)\n", __doc__.split("Conventions")[1].split("python3")[0], ""]
    JFE = [lambda r: f"{r['bench']}|{r['judge']}"]
    data = {name: load(od, sfx) for name, od, sfx in FAM}

    # ---- Table: audit by belief (Qwen rows, unique BFF/JudgeBench wrong answers, highest Qwen belief)
    W = [r for r in data["3 Qwens"] if r["ok"] == 0 and r["bench"] != "rb2math"]
    top = {}
    for r in W:
        top[r["item"]] = max(top.get(r["item"], 0), r["belief"])
    L += ["## T1. Label audit by belief (Qwen rows, unique BFF + JudgeBench wrong-labelled answers, highest Qwen belief)\n",
          "| belief | clearly wrong | actually correct | contested | no verdict | approval of 'actually correct' (judgments) |",
          "|---|---|---|---|---|---|"]
    t1 = {}
    for b in BINS:
        its = [i for i, v in top.items() if binof(v) == b]
        v = [GLM.get(i) for i in its]
        ac = [r["y"] for r in W if r["b"] == b and GLM.get(r["item"]) == "LABEL_WRONG"]
        t1[b] = dict(ok=v.count("LABEL_OK"), wrong=v.count("LABEL_WRONG"), cont=v.count("CONTESTED"), none=v.count(None),
                     acc_ac=float(np.mean(ac)) if ac else None, n_ac=len(ac))
        L.append(f"| {b} | {t1[b]['ok']} | {t1[b]['wrong']} | {t1[b]['cont']} | {t1[b]['none']} | "
                 + (f"{100 * np.mean(ac):.0f}% (n={len(ac)})" if ac else "–") + " |")
    OUT["t1"] = t1

    # ---- Table: staircase per family, audited and released
    L += ["", "## T2. Wrong answers approved by belief (stated verdict)\n",
          "| judge | labels | " + " | ".join(BINS) + " | gap 7/7 − 0/7 |", "|---|---|---|---|---|---|---|"]
    OUT["t2"] = {}
    for name, R in data.items():
        for lab, f in (("audited", lambda r: r["audited"]), ("released", lambda r: True)):
            S = [r for r in R if r["ok"] == 0 and f(r)]
            s = stair(S)
            g = boot(S, lambda X: stair(X)[3] - stair(X)[0])
            n = [sum(r["b"] == b for r in S) for b in BINS]
            OUT["t2"][f"{name}|{lab}"] = dict(stair=s.tolist(), n=n, gap=[float(g[0][0]), float(g[1][0]), float(g[2][0])])
            L.append(f"| {name} | {lab} | " + " | ".join(f"{100 * v:.0f}% (n={k})" for v, k in zip(s, n)) + f" | {f_ci(g)} |")

    # ---- belief vs one-sample label, judge FE, audited
    L += ["", "## R1. Belief vs the one-sample 'matches my answer' label (audited wrong answers, judge FE)\n",
          "| judge | belief alone | label alone | label, belief fixed | belief, label fixed | % believed-0/7 with label 'match' | % 7/7 with label 'differ' |",
          "|---|---|---|---|---|---|---|"]
    OUT["r1"] = {}
    for name, R in data.items():
        S = [r for r in R if r["ok"] == 0 and r["audited"]]
        a = boot(S, lambda X: ols(X, "y", ["belief"], JFE))
        m = boot(S, lambda X: ols(X, "y", ["match0"], JFE))
        both = boot(S, lambda X: ols(X, "y", ["match0", "belief"], JFE))
        z = np.mean([r["match0"] for r in S if r["b"] == "0/7"])
        o = np.mean([1 - r["match0"] for r in S if r["b"] == "7/7"])
        OUT["r1"][name] = dict(belief=f_ci(a), label=f_ci(m), label_fixed=f_ci(both, 0), belief_fixed=f_ci(both, 1))
        L.append(f"| {name} | {f_ci(a)} | {f_ci(m)} | {f_ci(both, 0)} | {f_ci(both, 1)} | {100 * z:.0f}% | {100 * o:.0f}% |")

    # ---- not authorship: same candidate, different Qwens (candidate FE + judge FE)
    S = [r for r in data["3 Qwens"] if r["ok"] == 0 and r["audited"]]
    cnt = collections.defaultdict(set)
    for r in S:
        cnt[r["item"]].add(r["belief"])
    ident = sum(len(v) > 1 for v in cnt.values())
    c = boot(S, lambda X: ols(X, "y", ["belief"], [lambda r: f"{r['bench']}|{r['judge']}", lambda r: r["item"]]))
    L += ["", "## R2. Same wrong answer, different Qwen judges (candidate + judge FE, audited)\n",
          f"Belief effect {f_ci(c)}; candidates believed to different degrees by the three Qwens: {ident}.\n"]
    OUT["r2"] = dict(effect=f_ci(c), n_ident=ident)

    # ---- where it forms: before writing (A) vs stated verdict, Qwens (A readout exists only for the Qwens' full ckpts)
    S = [r for r in data["3 Qwens"] if r["ok"] == 0 and r["audited"] and r["yA"] is not None]
    for r in S:
        r["yA"] = int(r["yA"])
    a = boot(S, lambda X: ols(X, "yA", ["belief"], JFE))
    cc = boot(S, lambda X: ols(X, "y", ["belief"], JFE))
    L += ["", "## R3. Before any reasoning (A: 'VERDICT:' appended to the prompt) vs the stated verdict (Qwens, audited)\n",
          f"Belief effect at A {f_ci(a)}; at the stated verdict {f_ci(cc)}; staircase at A "
          + " / ".join(f"{100 * v:.0f}%" for v in stair(S, "yA")) + "; stated " + " / ".join(f"{100 * v:.0f}%" for v in stair(S)) + ".\n"]
    OUT["r3"] = dict(A=f_ci(a), C=f_ci(cc))

    # ---- per-Qwen staircase (audited)
    L += ["## R4. Per Qwen judge (audited)\n", "| judge | " + " | ".join(BINS) + " | gap |", "|---|---|---|---|---|---|"]
    for j in ["qwen3.5-4b", "qwen3.5-9b", "qwen3.6-35b-a3b"]:
        S = [r for r in data["3 Qwens"] if r["ok"] == 0 and r["audited"] and r["judge"] == j]
        g = boot(S, lambda X: stair(X)[3] - stair(X)[0])
        L.append(f"| {j} | " + " | ".join(f"{100 * v:.0f}% (n={sum(r['b'] == b for r in S)})" for v, b in zip(stair(S), BINS)) + f" | {f_ci(g)} |")

    # ---- right answers by belief
    L += ["", "## R5. RIGHT answers approved by belief (labels as released for right answers)\n",
          "| judge | " + " | ".join(BINS) + " |", "|---|---|---|---|---|"]
    for name, R in data.items():
        S = [r for r in R if r["ok"] == 1]
        L.append(f"| {name} | " + " | ".join(f"{100 * v:.0f}% (n={sum(r['b'] == b for r in S)})" for v, b in zip(stair(S), BINS)) + " |")

    # ---- per benchmark, all four families pooled (audited)
    L += ["", "## R6. Per benchmark, four families pooled (audited)\n", "| benchmark | " + " | ".join(BINS) + " | gap |",
          "|---|---|---|---|---|---|"]
    ALL = [dict(r, judge=f"{n}|{r['judge']}") for n, R in data.items() for r in R]
    for bench in ("rb2math", "judgebench", "bff", None):
        S = [r for r in ALL if r["ok"] == 0 and r["audited"] and (bench is None or r["bench"] == bench)]
        g = boot(S, lambda X: stair(X)[3] - stair(X)[0])
        L.append(f"| {bench or 'all three'} | " + " | ".join(f"{100 * v:.0f}% (n={sum(r['b'] == b for r in S)})"
                                                          for v, b in zip(stair(S), BINS)) + f" | {f_ci(g)} |")

    # ---- counts for the setup section
    L += ["", "## C. Counts\n"]
    for name, R in data.items():
        L.append(f"- {name}: judgments with belief and a stated verdict {len(R)} (wrong {sum(r['ok'] == 0 for r in R)}, "
                 f"audited wrong {sum(r['ok'] == 0 and r['audited'] for r in R)}); by bench "
                 + ", ".join(f"{b} {sum(r['bench'] == b for r in R)}" for b in ('rb2math', 'judgebench', 'bff')))
    (V / "paper_numbers.md").write_text("\n".join(L) + "\n")
    json.dump(OUT, open(V / "paper_numbers.json", "w"), indent=1)
    print("\n".join(L))


if __name__ == "__main__":
    main()
