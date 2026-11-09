"""BBEH analysis: how judging quality depends on whether the judge can solve the question, and what helps.

Writes out/bbeh_tables.md (all tables) and out/bbeh_summary.json.

  python3 experiments/beyond_capability/analyze_bbeh.py
"""
import collections
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bc_common import JUDGES, STRONG, norm_answer, same_answer  # noqa: E402
from bc_load import (OUT, boot_ci, candidates, jl, judgments, metrics, pool_difficulty, questions,  # noqa: E402
                     solve_stats, think_solves)

COND_NAMES = {"none": "no reference (baseline)", "gold": "official answer as reference",
              "strong": "stronger model's answer as reference", "self": "own earlier answer as reference",
              "verify": "verify-the-steps prompt"}


def f2(x):
    return "–" if x is None or x != x else f"{x:.2f}"


def bal_of(rows, key="v"):
    m = metrics(rows, key)
    return m.get("bal", float("nan"))


def main():
    qs, C = questions(), candidates()
    diff = pool_difficulty(qs)
    S = {j: solve_stats(jl(OUT / f"solves_{j}.jsonl"), qs) for j in JUDGES}
    K = solve_stats(jl(OUT / f"solves_{STRONG}.jsonl"), qs)
    T = think_solves(qs)
    J = {j: judgments(j) for j in JUDGES}
    KJ = {r["cid"]: r for r in judgments(STRONG) if r["cond"] == "none"}
    L, SUM = [], {}

    # ------------------------------------------------------------------ A. solve rates
    L += ["## A. How often each judge solves BBEH itself\n",
          "Thinking off (the mode it judges in), 5 samples per question, whole 64K context as budget. "
          "*Solved* = the majority answer of the 5 samples is correct.\n",
          "| Model | Questions | Mean share of samples correct | Majority answer correct (= solved) | At least 1 of 5 correct | Thinking-on, 1 sample (questions) | Cut-off samples left |",
          "|---|---|---|---|---|---|---|"]
    for j in JUDGES + [STRONG]:
        s = S.get(j) or K
        if not s:
            continue
        t = T.get(j, {})
        L.append(f"| {j} | {len(s)} | {np.mean([x['p'] for x in s.values()]):.2f} | {np.mean([x['maj_ok'] for x in s.values()]):.2f} | "
                 f"{np.mean([x['any_ok'] for x in s.values()]):.2f} | "
                 f"{(f2(np.mean(list(t.values()))) + f' ({len(t)})') if t else ('high reasoning' if j == STRONG else '–')} | "
                 f"{sum(x['n_cut'] for x in s.values())} |")
        SUM.setdefault("solve", {})[j] = dict(n=len(s), p=float(np.mean([x['p'] for x in s.values()])),
                                              maj=float(np.mean([x['maj_ok'] for x in s.values()])))

    # rows with solve info attached (candidates of the judge's own pool answer are never judged)
    def attach(j, cond):
        out = []
        for r in J[j]:
            if r["cond"] != cond or r["qid"] not in S[j]:
                continue
            s = S[j][r["qid"]]
            c = C[r["cid"]]
            out.append(dict(r, solved=s["maj_ok"], p=s["p"], share_own=s["share"], diff=diff[r["qid"]],
                            matches_own=int(same_answer(c["norm"], s["maj"])),
                            in_own=int(any(same_answer(c["norm"], n) for n in s["norms"])),
                            think=T.get(j, {}).get(r["qid"])))
        return out

    # ------------------------------------------------------------------ B. characterise
    L += ["\n## B. Judging quality on questions the judge solved vs did not solve (no reference)\n",
          "TPR = share of right answers the judge accepts; FPR = share of wrong answers it accepts; balanced "
          "accuracy = (TPR + (1 − FPR)) / 2, 0.5 = chance; κ = Cohen's kappa vs the official grader; within-question "
          "AUROC = over pairs of a right and a wrong answer to the same question, how often the judge's vote share "
          "(3 samples) is higher for the right one.\n",
          "| Judge | Questions | n (right / wrong) | TPR | FPR | Balanced acc. [95% CI] | κ | Within-Q AUROC (pairs) |",
          "|---|---|---|---|---|---|---|---|"]
    for j in JUDGES:
        R = attach(j, "none")
        if not R:
            continue
        for sv, name in ((1, "solved"), (0, "**not solved**")):
            X = [r for r in R if r["solved"] == sv]
            m = metrics(X, score="share")
            ci = boot_ci(X, bal_of)
            L.append(f"| {j} | {name} | {m['n']} ({m['n_pos']} / {m['n_neg']}) | {f2(m['tpr'])} | {f2(m['fpr'])} | "
                     f"{f2(m['bal'])} [{f2(ci[0])}, {f2(ci[1])}] | {f2(m['kappa'])} | {f2(m['wq'])} ({m['pairs']}) |")
            SUM.setdefault("char", {})[f"{j}|{sv}"] = m

    # the strong judge, split by ITS OWN solve (1 sample, high reasoning; 1 verdict sample)
    KR = [dict(r, solved=K[r["qid"]]["maj_ok"]) for r in KJ.values() if r["qid"] in K]
    for sv, name in ((1, "solved"), (0, "**not solved**")):
        X = [r for r in KR if r["solved"] == sv]
        if X:
            m = metrics(X)
            ci = boot_ci(X, bal_of)
            L.append(f"| {STRONG} (thinking, 1 vote) | {name} | {m['n']} ({m['n_pos']} / {m['n_neg']}) | {f2(m['tpr'])} | {f2(m['fpr'])} | "
                     f"{f2(m['bal'])} [{f2(ci[0])}, {f2(ci[1])}] | {f2(m['kappa'])} | {f2(m['wq'])} ({m['pairs']}) |")
            SUM.setdefault("char", {})[f"{STRONG}|{sv}"] = m

    L += ["\n### B2. Finer: by how many of its 5 samples the judge got right\n",
          "| Judge | 0 of 5 | 1–2 of 5 | 3–4 of 5 | 5 of 5 |", "|---|---|---|---|---|"]
    bins = [(0, 0.01), (0.19, 0.41), (0.59, 0.81), (0.99, 1.01)]
    for j in JUDGES:
        R = attach(j, "none")
        if not R:
            continue
        cells = []
        for lo, hi in bins:
            X = [r for r in R if lo <= r["p"] < hi]
            m = metrics(X)
            cells.append(f"{f2(m.get('bal'))} (n={m['n']})")
        L.append(f"| {j} | " + " | ".join(cells) + " |")

    L += ["\n### B3. Is it solving ability or just difficulty? Same outside difficulty, solved vs not\n",
          "Outside difficulty = share of the 8 pool models (thinking on) that answered the question correctly. "
          "Cells: balanced accuracy (n) for solved / not solved, pooled over the 4 judges.\n",
          "| Pool solve rate | solved | not solved |", "|---|---|---|"]
    allR = [r for j in JUDGES for r in attach(j, "none")]
    for lo, hi, nm in ((0, 0.13, "0–1 of 8 (hardest)"), (0.13, 0.38, "2–3 of 8"), (0.38, 0.63, "4–5 of 8"), (0.63, 1.01, "6–8 of 8 (easiest)")):
        cells = []
        for sv in (1, 0):
            X = [r for r in allR if lo <= r["diff"] < hi and r["solved"] == sv]
            m = metrics(X)
            cells.append(f"{f2(m.get('bal'))} (n={m['n']})")
        L.append(f"| {nm} | " + " | ".join(cells) + " |")
    # regression-style check: logistic of "verdict correct" on solved + difficulty, per judge (linear prob model)
    L += ["\nLinear-probability fit of *verdict matches the grader* on solved (0/1) and outside difficulty, "
          "with question-resampled 95% intervals (balanced weights so right/wrong count equally):\n",
          "| Judge | effect of solved (points) | effect of difficulty, easiest vs hardest (points) |", "|---|---|---|"]
    for j in JUDGES:
        R = [r for r in attach(j, "none") if r["v"] is not None]
        if len(R) < 50:
            continue

        def fit(rows):
            y = np.array([r["v"] == r["gold"] for r in rows], float)
            X = np.column_stack([np.ones(len(rows)), [r["solved"] for r in rows], [r["diff"] for r in rows]])
            pos = np.array([r["gold"] for r in rows])
            w = np.where(pos == 1, 0.5 / max(pos.mean(), 1e-9), 0.5 / max(1 - pos.mean(), 1e-9))
            beta = np.linalg.lstsq(X * np.sqrt(w)[:, None], y * np.sqrt(w), rcond=None)[0]
            return beta
        b = fit(R)
        by = collections.defaultdict(list)
        for r in R:
            by[r["qid"]].append(r)
        keys = list(by)
        rng = np.random.default_rng(0)
        bs = np.array([fit([r for k in rng.choice(len(keys), len(keys)) for r in by[keys[k]]]) for _ in range(300)])
        lo, hi = np.percentile(bs, [2.5, 97.5], axis=0)
        L.append(f"| {j} | {100 * b[1]:+.0f} [{100 * lo[1]:+.0f}, {100 * hi[1]:+.0f}] | {100 * b[2]:+.0f} [{100 * lo[2]:+.0f}, {100 * hi[2]:+.0f}] |")

    # same candidate, different judges: candidate fixed effects (difficulty, gold, wording all cancel) + judge dummies
    L += ["\n### B3b. Strongest control: the same answer judged by a judge that solved the question and one that did not\n",
          "Linear model: verdict-is-right ~ solved + judge + candidate (a separate intercept for every candidate answer, so "
          "the question, its difficulty and the answer itself cancel out; judge dummies absorb overall judge quality). "
          "Only candidates judged by ≥2 of the 4 judges with different solve status contribute. 95% interval: questions resampled.\n"]
    FR = [dict(r, ok=float(r["v"] == r["gold"])) for r in allR if r["v"] is not None]

    def fe_beta(rows):
        by = collections.defaultdict(list)
        for r in rows:
            by[r["cid"]].append(r)
        Y, X = [], []
        for cid, G in by.items():
            if len({r["solved"] for r in G}) < 2:
                continue
            my = np.mean([r["ok"] for r in G])
            ms = np.mean([r["solved"] for r in G])
            mj = {j: np.mean([r["judge"] == j for r in G]) for j in JUDGES}
            for r in G:
                Y.append(r["ok"] - my)
                X.append([r["solved"] - ms] + [(r["judge"] == j) - mj[j] for j in JUDGES[1:]])
        if len(Y) < 20:
            return float("nan"), 0
        b = np.linalg.lstsq(np.array(X), np.array(Y), rcond=None)[0]
        return float(b[0]), len(Y)
    b, n_fe = fe_beta(FR)
    ci = boot_ci(FR, lambda R: fe_beta(R)[0], n=300)
    L.append(f"Effect of having solved the question on getting the verdict right: **{100 * b:+.0f} points** "
             f"[{100 * ci[0]:+.0f}, {100 * ci[1]:+.0f}] ({n_fe} judgments). Qwens only: "
             + (lambda bb: f"{100 * bb[0]:+.0f} points ({bb[1]} judgments).")(fe_beta([r for r in FR if r["judge"].startswith("qwen")])) + "\n")
    SUM["fe_solved"] = dict(beta=b, ci=ci, n=n_fe)

    L += ["\n### B4. On questions it did not solve: what does the judge accept?\n",
          "| Judge | right answers accepted | wrong answers equal to its own (wrong) majority answer, accepted | other wrong answers accepted | right answers it never produced in 5 samples, accepted |",
          "|---|---|---|---|---|"]
    for j in JUDGES:
        R = [r for r in attach(j, "none") if r["solved"] == 0]
        if not R:
            continue
        acc = lambda X: f"{np.mean([r['v'] == 1 for r in X]):.2f} (n={len(X)})" if X else "–"  # noqa: E731
        L.append(f"| {j} | {acc([r for r in R if r['gold'] == 1])} | {acc([r for r in R if r['gold'] == 0 and r['matches_own']])} | "
                 f"{acc([r for r in R if r['gold'] == 0 and not r['matches_own']])} | {acc([r for r in R if r['gold'] == 1 and not r['in_own']])} |")

    L += ["\n### B4b. The cleanest test: can it recognise a right answer it could not produce?\n",
          "Only answers that differ from ALL of the judge's 5 own samples, on questions it did not solve. "
          "Gap = acceptance of right answers − acceptance of wrong answers (0 = cannot tell them apart), with "
          "question-resampled 95% intervals.\n",
          "| Judge | right answers accepted | wrong answers accepted | gap (points) [95% CI] |", "|---|---|---|---|"]
    for j in JUDGES:
        R = [r for r in attach(j, "none") if r["solved"] == 0 and not r["in_own"] and r["v"] is not None]
        if not R:
            continue
        gap = lambda X: (np.mean([r["v"] for r in X if r["gold"] == 1]) - np.mean([r["v"] for r in X if r["gold"] == 0])) if any(r["gold"] for r in X) and not all(r["gold"] for r in X) else float("nan")  # noqa: E731
        ci = boot_ci(R, gap)
        tp = np.mean([r["v"] for r in R if r["gold"] == 1])
        fp = np.mean([r["v"] for r in R if r["gold"] == 0])
        L.append(f"| {j} | {tp:.2f} (n={sum(r['gold'] for r in R)}) | {fp:.2f} (n={sum(1 - r['gold'] for r in R)}) | "
                 f"{100 * gap(R):+.0f} [{100 * ci[0]:+.0f}, {100 * ci[1]:+.0f}] |")
        SUM.setdefault("verify_gap", {})[j] = dict(gap=gap(R), ci=ci, tp=tp, fp=fp)

    L += ["\n### B5. Same split with the thinking-ON solve (1 sample) as the definition of solved\n",
          "| Judge | solved: balanced acc. (n) | not solved: balanced acc. (n) | agreement of the two solve labels |",
          "|---|---|---|---|"]
    for j in JUDGES:
        R = [r for r in attach(j, "none") if r["think"] is not None]
        if not R:
            continue
        a = metrics([r for r in R if r["think"] == 1])
        b = metrics([r for r in R if r["think"] == 0])
        qq = {r["qid"]: (r["think"], r["solved"]) for r in R}
        agree = np.mean([x == y for x, y in qq.values()])
        L.append(f"| {j} | {f2(a.get('bal'))} ({a['n']}) | {f2(b.get('bal'))} ({b['n']}) | {agree:.2f} |")

    # ------------------------------------------------------------------ C. interventions
    L += ["\n## C. Interventions: what each buys on unsolved questions, and what it costs on solved ones\n",
          "Balanced accuracy (κ in brackets). Δ = change vs the no-reference baseline on the same candidates. "
          "Rules (no extra LLM call): *solve-and-compare* = accept iff the candidate's final answer equals the judge's "
          "own 5-sample majority answer; *match the stronger model* = accept iff it equals Kimi-K3.1-Pro's answer.\n"]
    def plurality(answers):
        groups = []
        for a in answers:
            if a is None:
                continue
            for g in groups:
                if same_answer(g[0], a):
                    g[1] += 1
                    break
            else:
                groups.append([a, 1])
        return max(groups, key=lambda g: g[1])[0] if groups else None
    crowd = {q: plurality([n for j in JUDGES if q in S[j] for n in S[j][q]["norms"]]) for q in qs
             if all(q in S[j] for j in JUDGES)}
    by_q = collections.defaultdict(list)
    for c in C.values():
        by_q[c["qid"]].append(c["norm"])
    cand_plural = {q: plurality(v) for q, v in by_q.items()}
    methods = {}
    for j in JUDGES:
        base = {r["cid"]: r for r in attach(j, "none")}
        if not base:
            continue
        for cond in ("gold", "strong", "self", "verify", "selfturn", "saidit"):
            X = {r["cid"]: r for r in attach(j, cond)}
            if X:
                methods.setdefault(cond, {})[j] = X
        methods.setdefault("none", {})[j] = base
        sc, km, kj, jury = {}, {}, {}, {}
        for cid, r in base.items():
            sc[cid] = dict(r, v=r["matches_own"])
            k = K.get(r["qid"])
            if k is not None:
                km[cid] = dict(r, v=int(same_answer(C[cid]["norm"], k["maj"])))
            if cid in KJ:
                kj[cid] = dict(r, v=KJ[cid]["v"])
        methods.setdefault("rule_selfcompare", {})[j] = sc
        # confident solve-and-compare: decide by own majority only when >= 4/5 samples agree, else the judge's verdict
        methods.setdefault("rule_confident_sc", {})[j] = {cid: dict(r, v=r["matches_own"] if r["share_own"] >= 0.8 else r["v"])
                                                          for cid, r in base.items()}
        # weak crowd: plurality answer over the 4 judges' 20 thinking-off samples
        wc = {}
        for cid, r in base.items():
            pl = crowd.get(r["qid"])
            if pl is not None:
                wc[cid] = dict(r, v=int(same_answer(C[cid]["norm"], pl)))
        methods.setdefault("rule_weak_crowd", {})[j] = wc
        # candidate consensus: plurality final answer among all pool answers to this question
        cc = {}
        for cid, r in base.items():
            pl = cand_plural.get(r["qid"])
            if pl is not None:
                cc[cid] = dict(r, v=int(same_answer(C[cid]["norm"], pl)))
        methods.setdefault("rule_candidate_consensus", {})[j] = cc
        methods.setdefault("rule_kimi_match", {})[j] = km
        methods.setdefault("kimi_judge", {})[j] = kj
    # jury of the 4 judges (majority of sample-0 verdicts; ties -> reject), on candidates all 4 judged
    common = set.intersection(*[set(methods["none"][j]) for j in methods.get("none", {})]) if methods.get("none") else set()
    for j in methods.get("none", {}):
        jury = {}
        for cid in common:
            vs = [methods["none"][jj][cid]["v"] or 0 for jj in methods["none"]]
            jury[cid] = dict(methods["none"][j][cid], v=int(sum(vs) > len(vs) / 2))
        methods.setdefault("jury4", {})[j] = jury
    # deferral: keep own verdict when the judge is self-consistent (>= 4/5 samples agree), else defer to a source
    for tgt, src in (("defer_kimi_judge", "kimi_judge"), ("defer_strong_ref", "strong")):
        for j in methods.get("none", {}):
            D = {}
            for cid, r in methods["none"][j].items():
                if r["share_own"] >= 0.8:
                    D[cid] = r
                elif cid in methods.get(src, {}).get(j, {}):
                    D[cid] = dict(r, v=methods[src][j][cid]["v"])
            methods.setdefault(tgt, {})[j] = D
    names = {"none": "No reference (baseline)", "gold": "Official answer as reference (ceiling)",
             "strong": "Stronger model's answer as reference", "self": "Own earlier answer as reference",
             "verify": "Verify-the-steps prompt", "selfturn": "Framing: candidate shown as its own reply, then 'is your answer correct?'",
             "saidit": "Framing: 'here is the answer you gave earlier'", "rule_selfcompare": "Rule: solve-and-compare (own 5-sample majority)",
             "rule_kimi_match": "Rule: match the stronger model's answer",
             "rule_confident_sc": "Rule: solve-and-compare only when own samples agree (≥4/5), else own verdict",
             "rule_weak_crowd": "Rule: match the plurality answer of the 4 weak judges (20 samples)",
             "rule_candidate_consensus": "Rule: match the most common answer among all candidates", "kimi_judge": "Route everything to the stronger judge (Kimi)",
             "jury4": "Majority of the 4 judges", "defer_kimi_judge": "Defer to Kimi judge when own samples disagree (<4/5)",
             "defer_strong_ref": "Use the stronger model's reference when own samples disagree (<4/5)"}
    L += ["| Method | Judge | solved: bal. acc. (κ) | Δ | **not solved**: bal. acc. (κ) | Δ | n solved / not |",
          "|---|---|---|---|---|---|---|"]
    for meth, by_j in methods.items():
        for j, X in by_j.items():
            base = methods["none"][j]
            cells = []
            for sv in (1, 0):
                ids = [cid for cid, r in X.items() if r["solved"] == sv and cid in base]
                m = metrics([X[c] for c in ids])
                mb = metrics([base[c] for c in ids])
                cells += [f"{f2(m.get('bal'))} ({f2(m.get('kappa'))})", f"{(m.get('bal', np.nan) - mb.get('bal', np.nan)) * 100:+.0f}" if m["n"] else "–"]
                SUM.setdefault("interv", {})[f"{meth}|{j}|{sv}"] = dict(bal=m.get("bal"), kappa=m.get("kappa"), n=m["n"],
                                                                        base_bal=mb.get("bal"))
            nsv = sum(1 for r in X.values() if r["solved"] == 1)
            L.append(f"| {names[meth]} | {j} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} | {nsv} / {len(X) - nsv} |")

    # pooled summary over judges
    L += ["\n### C2. Pooled over the 4 judges\n",
          "| Method | solved: bal. acc. | Δ | not solved: bal. acc. | Δ [95% CI] |", "|---|---|---|---|---|"]
    for meth, by_j in methods.items():
        cells = []
        for sv in (1, 0):
            X, B = [], []
            for j, D in by_j.items():
                for cid, r in D.items():
                    if r["solved"] == sv and cid in methods["none"][j]:
                        X.append(dict(r, qid=f"{r['qid']}"))
                        B.append(methods["none"][j][cid])
            m, mb = metrics(X), metrics(B)
            if not X:
                cells += ["–", "–"]
                continue
            pairs = [dict(qid=x["qid"], d=(x, b)) for x, b in zip(X, B)]

            def dfn(P):
                return metrics([p["d"][0] for p in P]).get("bal", np.nan) - metrics([p["d"][1] for p in P]).get("bal", np.nan)
            ci = boot_ci(pairs, dfn, n=400) if sv == 0 else None
            cells += [f2(m["bal"]), f"{(m['bal'] - mb['bal']) * 100:+.0f}" + (f" [{ci[0] * 100:+.0f}, {ci[1] * 100:+.0f}]" if ci else "")]
            SUM.setdefault("pooled", {})[f"{meth}|{sv}"] = dict(bal=m["bal"], delta=m["bal"] - mb["bal"], ci=ci, n=m["n"])
        L.append(f"| {names[meth]} | " + " | ".join(cells) + " |")

    # ------------------------------------------------------------------ D. when is the reference wrong?
    if methods.get("strong"):
        L += ["\n### C3. Stronger model's reference: what happens when the reference itself is wrong\n",
              "| Judge | Questions | Kimi's answer right: bal. acc. none → strong-ref | Kimi's answer wrong: bal. acc. none → strong-ref |",
              "|---|---|---|---|"]
        for j, X in methods["strong"].items():
            base = methods["none"][j]
            for sv, nm in ((1, "solved"), (0, "not solved")):
                cells = []
                for kok in (1, 0):
                    ids = [c for c, r in X.items() if r["solved"] == sv and c in base and K.get(r["qid"], {}).get("maj_ok") == kok]
                    cells.append(f"{f2(metrics([base[c] for c in ids]).get('bal'))} → {f2(metrics([X[c] for c in ids]).get('bal'))} (n={len(ids)})")
                L.append(f"| {j} | {nm} | {cells[0]} | {cells[1]} |")

    # ------------------------------------------------------------------ E. self-consistency as an abstention signal
    L += ["\n## D. Knowing when not to trust the judge: own self-consistency as a warning light\n",
          "Share of the judge's 5 own solve samples that agree with its majority answer (1.0 = all five agree). "
          "Cells: balanced accuracy of the baseline verdict (n).\n",
          "| Judge | agreement 1.0 | 0.8 | 0.6 | ≤ 0.4 | AUROC of agreement for 'solved' |", "|---|---|---|---|---|---|"]
    from sklearn.metrics import roc_auc_score
    for j in JUDGES:
        R = attach(j, "none")
        if not R:
            continue
        cells = []
        for lo, hi in ((0.99, 1.01), (0.79, 0.81), (0.59, 0.61), (0, 0.41)):
            X = [r for r in R if lo <= r["share_own"] < hi]
            cells.append(f"{f2(metrics(X).get('bal'))} (n={len(X)})")
        qv = {q: (s["maj_ok"], s["share"]) for q, s in S[j].items()}
        au = roc_auc_score([a for a, _ in qv.values()], [b for _, b in qv.values()]) if len({a for a, _ in qv.values()}) == 2 else float("nan")
        L.append(f"| {j} | " + " | ".join(cells) + f" | {au:.2f} |")

    # ------------------------------------------------------------------ F. difficulty-aware thresholds (cross-fitted)
    L += ["\n## E. Difficulty-aware threshold on the judge's own vote share\n",
          "The baseline judge gave 3 votes per candidate. Instead of majority (≥ 2 of 3), pick the vote threshold "
          "separately for each level of the judge's own solve agreement, choosing it on the other half of the "
          "questions (2-fold, by question). Balanced accuracy on not-solved / solved questions.\n",
          "| Judge | majority vote: not solved | adaptive: not solved | majority: solved | adaptive: solved |",
          "|---|---|---|---|---|"]
    for j in JUDGES:
        R = [r for r in attach(j, "none") if r["share"] is not None]
        if not R:
            continue
        qids = sorted({r["qid"] for r in R})
        rng = np.random.default_rng(1)
        fold = dict(zip(qids, rng.permutation(len(qids)) % 2))
        lev = lambda r: min(3, int(round(r["share_own"] * 5)) - 2) if r["share_own"] > 0 else 0  # noqa: E731
        out = []
        for f in (0, 1):
            tr = [r for r in R if fold[r["qid"]] != f]
            te = [r for r in R if fold[r["qid"]] == f]
            thr = {}
            for lv in set(map(lev, tr)) | set(map(lev, te)):
                T_ = [r for r in tr if lev(r) == lv]
                best = max((0.01, 0.34, 0.67, 1.0), key=lambda t: bal_of([dict(r, v=int(r["share"] >= t)) for r in T_]) if T_ else 0)
                thr[lv] = best if T_ else 0.67
            out += [dict(r, v=int(r["share"] >= thr[lev(r)]), vmaj=int(r["share"] >= 0.67)) for r in te]
        cells = []
        for sv in (0, 1):
            X = [r for r in out if r["solved"] == sv]
            cells += [f2(bal_of(X, "vmaj")), f2(bal_of(X, "v"))]
        L.append(f"| {j} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} |")

    # ------------------------------------------------------------------ G. cascades to the stronger judge
    L += ["\n## G. Cascades: let the cheap judge decide only when a label-free signal says it is safe, else ask Kimi\n",
          "Each rule decides, without any gold labels, which candidates go to the stronger judge (Kimi-K3.1-Pro, high "
          "reasoning). Cells: balanced accuracy on questions the cheap judge solved / did not solve / all, and the share "
          "of candidates routed (the cost). Only candidates Kimi also judged.\n",
          "| Judge | Rule | routed | solved | not solved | all |", "|---|---|---|---|---|---|"]
    rules = {
        "never route (cheap judge alone)": lambda r: False,
        "always route (Kimi alone)": lambda r: True,
        "route if own 5 samples disagree (<4/5 agree)": lambda r: r["share_own"] < 0.8,
        "route if the judge's 3 verdict votes are not unanimous": lambda r: r["share"] not in (0.0, 1.0),
        "route if own majority answer ≠ most common candidate answer": lambda r: not same_answer(r["own_maj"], cand_plural.get(r["qid"])),
        "route if either of the last two": lambda r: (r["share"] not in (0.0, 1.0)) or not same_answer(r["own_maj"], cand_plural.get(r["qid"])),
    }
    for j in JUDGES:
        base = [dict(r, own_maj=S[j][r["qid"]]["maj"]) for r in attach(j, "none") if r["cid"] in KJ]
        if not base:
            continue
        for nm, fn in rules.items():
            X = [dict(r, v=KJ[r["cid"]]["v"]) if fn(r) else r for r in base]
            cells = [f2(metrics([x for x in X if x["solved"] == sv]).get("bal")) for sv in (1, 0)] + [f2(metrics(X).get("bal"))]
            L.append(f"| {j} | {nm} | {np.mean([fn(r) for r in base]):.0%} | " + " | ".join(cells) + " |")
            SUM.setdefault("cascade", {})[f"{j}|{nm}"] = dict(routed=float(np.mean([fn(r) for r in base])),
                                                               bal_s=metrics([x for x in X if x["solved"] == 1]).get("bal"),
                                                               bal_u=metrics([x for x in X if x["solved"] == 0]).get("bal"),
                                                               bal=metrics(X).get("bal"))

    # ------------------------------------------------------------------ G. cost
    L += ["\n## F. Cost of each condition (tokens per judgment, sample 0; the baseline drew 3 samples)\n",
          "| Judge | Condition | n | mean input tokens | mean output tokens | cut off after retries |", "|---|---|---|---|---|---|"]
    for j in JUDGES + [STRONG]:
        rows = judgments(j)
        for cond in ("none", "gold", "strong", "self", "verify"):
            X = [r for r in rows if r["cond"] == cond]
            if X:
                L.append(f"| {j} | {cond} | {len(X)} | {np.mean([r['n_in'] for r in X]):,.0f} | {np.mean([r['n_out'] for r in X]):,.0f} | {sum(not r['clean'] for r in X)} |")

    (OUT / "bbeh_tables.md").write_text("\n".join(L) + "\n")
    json.dump(SUM, open(OUT / "bbeh_summary.json", "w"), indent=1, default=float)
    print("\n".join(L))


if __name__ == "__main__":
    main()
