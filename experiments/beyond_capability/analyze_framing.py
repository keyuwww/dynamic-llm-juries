"""'Your own answer' framing and thinking on vs off. Writes out/framing_tables.md.

Conditions: none (baseline), selfturn (candidate shown as the model's own reply, then "is your answer correct?"),
saidit ("here is the answer you gave earlier"), otherturn (selfturn's layout, but the answer is relayed as another AI's:
the control that separates "yours" from the conversational follow-up). Thinking off for 4 judges; Qwen3.5-9B also
with thinking on (no otherturn run there).
Cells: balanced accuracy, and accept rates of right / wrong answers (TPR / FPR).

  python3 experiments/beyond_capability/analyze_framing.py
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from analyze_bff import bff_judgments  # noqa: E402
from bc_common import JUDGES  # noqa: E402
from bc_load import OUT, boot_ci, jl, judgments, metrics, questions, solve_stats  # noqa: E402

NAMES = {"none": "no framing (baseline)", "selfturn": "shown as its own reply + 'is your answer correct?'",
         "saidit": "'here is the answer you gave earlier'",
         "otherturn": "same layout, relayed as another AI's answer + 'is that assistant's answer correct?'"}


def acc_rate(rows, gold):
    """Share accepted among answers with this gold label (unparseable = rejected)."""
    v = [0 if r["v"] is None else r["v"] for r in rows if r["gold"] == gold]
    return float(np.mean(v)) if v else float("nan")


def own_vs_other(pairs):
    """pairs: (selfturn row, otherturn row) on the same answer and judge. Δ accept rate (own − other), x100, with CI."""
    P = [dict(qid=s["qid"], d=(s, o)) for s, o in pairs]
    out = []
    for gold in (0, 1):
        f = lambda Q: acc_rate([q["d"][0] for q in Q], gold) - acc_rate([q["d"][1] for q in Q], gold)  # noqa: E731
        lo, hi = boot_ci(P, f, n=400)
        out.append(f"{100 * f(P):+.0f} [{100 * lo:+.0f}, {100 * hi:+.0f}]")
    return out  # [wrong answers, right answers]


def cell(rows):
    m = metrics(rows)
    return f"{m['bal']:.2f} ({m['tpr']:.2f} / {m['fpr']:.2f})" if m["n"] else "–"


def delta_ci(X, B):
    P = [dict(qid=x["qid"], d=(x, b)) for x, b in zip(X, B)]
    f = lambda Q: metrics([q["d"][0] for q in Q])["bal"] - metrics([q["d"][1] for q in Q])["bal"]  # noqa: E731
    lo, hi = boot_ci(P, f, n=400)
    return f"{100 * f(P):+.0f} [{100 * lo:+.0f}, {100 * hi:+.0f}]"


def main():
    qs = questions()
    L = ["# 'Your own answer' framing, and thinking on vs off\n",
         "Cells: balanced accuracy (accept rate of right answers / of wrong answers). Δ vs the no-framing baseline, "
         "thinking off, on the same answers, with question-resampled 95% intervals.\n"]
    # ---- BBEH, thinking off, pooled over judges
    S = {j: solve_stats(jl(OUT / f"solves_{j}.jsonl"), qs) for j in JUDGES}
    rows = {j: {(r["cid"], r["cond"]): dict(r, solved=S[j][r["qid"]]["maj_ok"]) for r in judgments(j)} for j in JUDGES}
    L += ["## BBEH, thinking off (4 judges pooled)\n", "| Framing | solved | not solved | Δ not solved |", "|---|---|---|---|"]
    for c in NAMES:
        cells, X0, B0 = [], [], []
        for sv in (1, 0):
            X = [r for j in JUDGES for (cid, cc), r in rows[j].items() if cc == c and r["solved"] == sv and (cid, "none") in rows[j]]
            B = [rows[j][(r["cid"], "none")] for j in JUDGES for r in X if r["judge"] == j]
            X = [r for j in JUDGES for r in X if r["judge"] == j]
            cells.append(cell(X))
            if sv == 0:
                X0, B0 = X, B
        L.append(f"| {NAMES[c]} | {cells[0]} | {cells[1]} | {delta_ci(X0, B0) if c != 'none' else '—'} |")
    # ---- BBEH: "yours" vs "another AI's", same conversation layout (selfturn − otherturn), per judge and pooled
    L += ["\n## BBEH, thinking off: own reply vs another AI's (same layout)\n",
          "Δ accept rate, own − another AI's, same answers and judge, ×100 [95% CI].\n",
          "| Judge | solved: wrong answers | solved: right answers | not solved: wrong answers | not solved: right answers |",
          "|---|---|---|---|---|"]
    for name, js in [(j, [j]) for j in JUDGES] + [("4 judges pooled", JUDGES)]:
        cells = []
        for sv in (1, 0):
            pairs = [(r, rows[j][(cid, "otherturn")]) for j in js for (cid, cc), r in rows[j].items()
                     if cc == "selfturn" and r["solved"] == sv and (cid, "otherturn") in rows[j]]
            cells += own_vs_other(pairs)
        L.append(f"| {name} | " + " | ".join(cells) + " |")
    # ---- BBEH, Qwen-9B thinking on
    j = "qwen3.5-9b"
    T = {(r["cid"], r["cond"]): dict(r, solved=S[j][r["qid"]]["maj_ok"]) for r in judgments(f"{j}@think")}
    L += ["\n## BBEH, Qwen3.5-9B with thinking ON (one sample each)\n",
          "| Condition | solved | not solved | Δ not solved vs thinking-off baseline |", "|---|---|---|---|"]
    for c in [k for k in NAMES if any(cc == k for _, cc in T)]:  # no "another AI" run with thinking on
        cells = []
        for sv in (1, 0):
            X = [r for (cid, cc), r in T.items() if cc == c and r["solved"] == sv and (cid, "none") in rows[j]]
            cells.append(cell(X))
            if sv == 0:
                d = delta_ci(X, [rows[j][(r["cid"], "none")] for r in X])
        L.append(f"| thinking on, {NAMES[c]} | {cells[0]} | {cells[1]} | {d} |")
    X = [r for r in rows[j].values() if r["cond"] == "none"]
    L.append(f"| thinking off, {NAMES['none']} | {cell([r for r in X if r['solved'] == 1])} | {cell([r for r in X if r['solved'] == 0])} | — |")
    # ---- BFF
    grades = {r["cache_key"]: r["verdict"] for r in jl(OUT / "bff_grades_glm.jsonl")}
    fill = {r["cache_key"]: r["verdict"] for r in jl(OUT / "fill_glm.jsonl")}
    L += ["\n## BFF-Bench (finance, expert labels)\n", "| Judges | Condition | solved | not solved | Δ not solved |", "|---|---|---|---|---|"]
    OV = []
    for name, js in (("4 judges, thinking off", [(x, x) for x in JUDGES]), ("Qwen3.5-9B, thinking on", [("qwen3.5-9b@think", "qwen3.5-9b")])):
        R, base = [], {}
        for jj, js_ in js:
            sol = {}
            for r in jl(OUT / f"bff_solves_{js_}.jsonl"):
                g = [grades.get(f"{r['cache_key']}|{i}") for i in range(len(r["samples"]))]
                if None not in g:
                    sol[r["qid"]] = int(np.mean(g) > 0.5)
            for r in bff_judgments(jj, fill):
                if r["qid"] in sol:
                    R.append(dict(r, solved=sol[r["qid"]], j=js_))
            for r in bff_judgments(js_, fill):
                if r["cond"] == "none":
                    base[(js_, r["item"])] = r
        for c in NAMES:
            X = [r for r in R if r["cond"] == c and (r["j"], r["item"]) in base]
            X0 = [r for r in X if r["solved"] == 0]
            if not X0:  # no "another AI" run with thinking on
                continue
            B0 = [base[(r["j"], r["item"])] for r in X0]
            L.append(f"| {name} | {NAMES[c]} | {cell([r for r in X if r['solved'] == 1])} | {cell(X0)} | "
                     f"{delta_ci(X0, B0) if (c != 'none' or 'think' in name) else '—'} |")
        own = {(r["j"], r["item"]): r for r in R if r["cond"] == "selfturn"}
        oth = {(r["j"], r["item"]): r for r in R if r["cond"] == "otherturn"}
        if oth:
            cells = []
            for sv in (1, 0):
                cells += own_vs_other([(own[k], oth[k]) for k in own if k in oth and own[k]["solved"] == sv])
            OV.append(f"| {name} | " + " | ".join(cells) + " |")
    L += ["\n## BFF-Bench, thinking off: own reply vs another AI's (same layout)\n",
          "Δ accept rate, own − another AI's, ×100 [95% CI].\n",
          "| Judges | solved: wrong answers | solved: right answers | not solved: wrong answers | not solved: right answers |",
          "|---|---|---|---|---|"] + OV
    (OUT / "framing_tables.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
