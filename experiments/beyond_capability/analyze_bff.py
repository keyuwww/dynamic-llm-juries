"""BFF-Bench analysis (finance, open-ended answers, expert labels): judging quality by whether the judge can solve
the question, and what the reference conditions buy. Writes out/bff_tables.md and out/bff_summary.json.

Solved = at least 2 of the judge's 3 own answers (thinking off) are graded correct by GLM-5.3-Flash against the
expert reference. Gold for judging = the unanimous expert label from VERDICTS.

  python3 experiments/beyond_capability/analyze_bff.py
"""
import collections
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bc_common import JUDGES, STRONG  # noqa: E402
from bc_load import OUT, boot_ci, jl, metrics  # noqa: E402


def f2(x):
    return "–" if x is None or x != x else f"{x:.2f}"


def bff_judgments(judge, fill):
    seen, rows = set(), []
    for p in sorted(q for q in OUT.glob(f"bff_judge_{judge}[._]*") if q.suffix == ".jsonl"):
        for r in jl(p):
            if r["cache_key"] in seen:
                continue
            seen.add(r["cache_key"])
            vs = []
            for i, s in enumerate(r["samples"]):
                v = s["verdict"]
                if v is None:
                    v = {"CORRECT": 1, "INCORRECT": 0}.get(fill.get(f"{r['cache_key']}|{i}"))
                vs.append(v)
            known = [v for v in vs if v is not None]
            rows.append(dict(judge=judge, item=r["item"], qid=r["qid"], cond=r["cond"], gold=r["gold"],
                             examinee=r["examinee"], v=vs[0], share=float(np.mean(known)) if known else None,
                             n_in=r["n_in"], n_out=r["samples"][0]["n_out"], clean=r["samples"][0]["clean"]))
    return rows


def main():
    grades = {r["cache_key"]: r["verdict"] for r in jl(OUT / "bff_grades_glm.jsonl")}
    fill = {r["cache_key"]: r["verdict"] for r in jl(OUT / "fill_glm.jsonl")}
    solved = {}
    for j in JUDGES + [STRONG]:
        d = {}
        for r in jl(OUT / f"bff_solves_{j}.jsonl"):
            g = [grades.get(f"{r['cache_key']}|{i}") for i in range(len(r["samples"]))]
            if any(x is None for x in g):
                continue
            d[r["qid"]] = dict(p=float(np.mean(g)), maj=int(np.mean(g) > 0.5), first=g[0])
        solved[j] = d
    L, SUM = [], {}
    L += ["## A. How often each judge answers the BFF-Bench question correctly itself\n",
          "3 answers per question (thinking off; Kimi: 1, high reasoning), graded by GLM-5.3-Flash against the expert "
          "reference. Turn-2 questions are asked after the expert's turn-1 answer.\n",
          "| Model | Questions graded | Mean share correct | Solved (≥2 of 3 correct) |", "|---|---|---|---|"]
    for j, d in solved.items():
        if d:
            L.append(f"| {j} | {len(d)} | {np.mean([x['p'] for x in d.values()]):.2f} | {np.mean([x['maj'] for x in d.values()]):.2f} |")
    names = {"none": "No reference (baseline)", "human": "Expert reference", "strong": "Stronger model's answer as reference",
             "self": "Own earlier answer as reference", "verify": "Verify-the-steps prompt", "kimi_judge": "Route to the stronger judge (Kimi)"}
    L += ["\n## B. Judging quality by whether the judge solved the question, per condition\n",
          "Gold = unanimous expert label. Balanced accuracy (κ); Δ vs the no-reference baseline on the same items. "
          "Within-question AUROC (no reference only) compares answers by different models to the same question.\n",
          "| Condition | Judge | solved: n | solved: bal. acc. (κ) | Δ | **not solved**: n | not solved: bal. acc. (κ) | Δ |",
          "|---|---|---|---|---|---|---|---|"]
    kimi = {r["item"]: r for r in bff_judgments(STRONG, fill) if r["cond"] == "none"}
    pooled = collections.defaultdict(lambda: collections.defaultdict(list))
    for j in JUDGES:
        rows = bff_judgments(j, fill)
        base = {r["item"]: r for r in rows if r["cond"] == "none"}
        conds = {c: {r["item"]: r for r in rows if r["cond"] == c} for c in ("none", "human", "strong", "self", "verify")}
        conds["kimi_judge"] = {i: dict(base[i], v=k["v"]) for i, k in kimi.items() if i in base}
        for c, X in conds.items():
            if not X:
                continue
            cells = []
            for sv in (1, 0):
                ids = [i for i, r in X.items() if i in base and solved[j].get(r["qid"], {}).get("maj") == sv]
                m, mb = metrics([X[i] for i in ids]), metrics([base[i] for i in ids])
                cells += [str(m["n"]), f"{f2(m.get('bal'))} ({f2(m.get('kappa'))})",
                          f"{(m.get('bal', np.nan) - mb.get('bal', np.nan)) * 100:+.0f}" if m["n"] else "–"]
                for i in ids:
                    pooled[(c, sv)]["x"].append(dict(X[i], qid=X[i]["qid"]))
                    pooled[(c, sv)]["b"].append(base[i])
                SUM[f"{c}|{j}|{sv}"] = dict(n=m["n"], bal=m.get("bal"), kappa=m.get("kappa"), base=mb.get("bal"))
            L.append(f"| {names[c]} | {j} | " + " | ".join(cells) + " |")
    L += ["\n### B2. Pooled over the 4 judges\n", "| Condition | solved: bal. acc. | Δ | not solved: bal. acc. | Δ [95% CI] |",
          "|---|---|---|---|---|"]
    for c in names:
        cells = []
        for sv in (1, 0):
            X, B = pooled[(c, sv)]["x"], pooled[(c, sv)]["b"]
            if not X:
                cells += ["–", "–"]
                continue
            m, mb = metrics(X), metrics(B)
            P = [dict(qid=x["qid"], d=(x, b)) for x, b in zip(X, B)]
            ci = boot_ci(P, lambda Q: metrics([q["d"][0] for q in Q])["bal"] - metrics([q["d"][1] for q in Q])["bal"], n=400) if sv == 0 and c != "none" else None
            cells += [f2(m["bal"]), f"{(m['bal'] - mb['bal']) * 100:+.0f}" + (f" [{ci[0] * 100:+.0f}, {ci[1] * 100:+.0f}]" if ci else "")]
            SUM[f"pooled|{c}|{sv}"] = dict(bal=m["bal"], delta=m["bal"] - mb["bal"], ci=ci, n=m["n"])
        L.append(f"| {names[c]} | " + " | ".join(cells) + " |")

    L += ["\n### B3. No reference: TPR / FPR / within-question AUROC by solved\n",
          "| Judge | Questions | n (right / wrong) | TPR | FPR | Balanced acc. [95% CI] | Within-Q AUROC (pairs) |",
          "|---|---|---|---|---|---|---|"]
    for j in JUDGES:
        base = [r for r in bff_judgments(j, fill) if r["cond"] == "none"]
        for sv, nm in ((1, "solved"), (0, "**not solved**")):
            X = [r for r in base if solved[j].get(r["qid"], {}).get("maj") == sv]
            if not X:
                continue
            m = metrics(X, score="share")
            ci = boot_ci(X, lambda R: metrics(R).get("bal", np.nan))
            L.append(f"| {j} | {nm} | {m['n']} ({m['n_pos']} / {m['n_neg']}) | {f2(m['tpr'])} | {f2(m['fpr'])} | "
                     f"{f2(m['bal'])} [{f2(ci[0])}, {f2(ci[1])}] | {f2(m['wq'])} ({m['pairs']}) |")

    kr = [dict(r) for r in kimi.values()]
    for sv, nm in ((1, "solved"), (0, "**not solved**")):
        X = [r for r in kr if solved[STRONG].get(r["qid"], {}).get("first") == sv]
        if X:
            m = metrics(X)
            ci = boot_ci(X, lambda R: metrics(R).get("bal", np.nan))
            L.append(f"| {STRONG} (thinking, 1 vote) | {nm} | {m['n']} ({m['n_pos']} / {m['n_neg']}) | {f2(m['tpr'])} | {f2(m['fpr'])} | "
                     f"{f2(m['bal'])} [{f2(ci[0])}, {f2(ci[1])}] | {f2(m['wq'])} ({m['pairs']}) |")

    # strong reference: when Kimi's own answer is wrong
    L += ["\n### B4. Stronger model's answer as reference, split by whether that answer is itself right\n",
          "| Judge | Kimi's answer right: bal. acc. none → strong (n) | Kimi's answer wrong: none → strong (n) |", "|---|---|---|"]
    for j in JUDGES:
        rows = bff_judgments(j, fill)
        base = {r["item"]: r for r in rows if r["cond"] == "none"}
        X = {r["item"]: r for r in rows if r["cond"] == "strong"}
        cells = []
        for kok in (1, 0):
            ids = [i for i, r in X.items() if i in base and solved[STRONG].get(r["qid"], {}).get("first") == kok]
            cells.append(f"{f2(metrics([base[i] for i in ids]).get('bal'))} → {f2(metrics([X[i] for i in ids]).get('bal'))} ({len(ids)})")
        L.append(f"| {j} | {cells[0]} | {cells[1]} |")

    (OUT / "bff_tables.md").write_text("\n".join(L) + "\n")
    json.dump(SUM, open(OUT / "bff_summary.json", "w"), indent=1, default=float)
    print("\n".join(L))


if __name__ == "__main__":
    main()
