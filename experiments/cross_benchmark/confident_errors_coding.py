"""A6 analysis: merge blind codes with the key and summarise by cell.

Inputs (results/confident_errors/): coding_sheet.csv, coding_key.csv, claude_codes.json (120 blind codes from four
LLM coders who saw neither the key nor the confidence numbers), optionally janys_codes.csv (30-item check).
Outputs: coded.csv, coding_summary.md, janys_sheet.csv (30 items, 5 per cell, Claude's codes left out).
Usage: python confident_errors_coding.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "confident_errors"
CELLS = ["HW", "MW", "LW", "HF", "HR", "LR"]
FIELDS = ["judge_right", "error_type", "gold_questionable", "noticed_decisive_difference", "hedging_or_self_correction",
          "says_answers_close", "perceived_confidence"]


def kappa(a, b):
    a, b = pd.Series(a).astype(str), pd.Series(b).astype(str)
    cats = sorted(set(a) | set(b))
    po = (a.values == b.values).mean()
    pe = sum((a == c).mean() * (b == c).mean() for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else np.nan


def main():
    sheet = pd.read_csv(OUT / "coding_sheet.csv")
    key = pd.read_csv(OUT / "coding_key.csv")
    codes = pd.DataFrame(json.load(open(OUT / "claude_codes.json")))
    D = key.merge(sheet[["code_id", "gold", "judge_verdict"]], on="code_id").merge(codes, on="code_id", how="left")
    D["level"] = D.cell.str[0].map({"H": "high", "M": "mid", "L": "low"})
    # verdict-only reasoning can't be coded for reasoning features; reasoning over 6,000 chars was cut for the coders
    rl = sheet.set_index("code_id").judge_reasoning.fillna("").str.replace(r"(?i)\**VERDICT\**\s*:\s*\w", "", regex=True).str.strip().str.len()
    D["no_reasoning"] = D.code_id.map(rl < 40)
    D["truncated"] = D.code_id.map(sheet.set_index("code_id").judge_reasoning.fillna("").str.len() > 6000)
    for f in ["noticed_decisive_difference", "hedging_or_self_correction", "says_answers_close", "perceived_confidence"]:
        D.loc[D.no_reasoning, f] = np.nan
    D.to_csv(OUT / "coded.csv", index=False)
    yes = lambda s: (s.dropna() == "yes").mean()  # noqa: E731
    by = D.groupby("cell").agg(n=("code_id", "size"),
                               gold_questionable=("gold_questionable", yes),
                               noticed_decisive=("noticed_decisive_difference", yes),
                               hedging=("hedging_or_self_correction", yes),
                               says_close=("says_answers_close", yes),
                               reads_high=("perceived_confidence", lambda s: (s.dropna() == "high").mean()),
                               reads_low=("perceived_confidence", lambda s: (s.dropna() == "low").mean()),
                               no_reasoning=("no_reasoning", "sum"), truncated=("truncated", "sum")).reindex(CELLS)
    wrong = D[D.judge_verdict != D.gold]
    et = pd.crosstab(wrong.cell, wrong.error_type, normalize="index").reindex([c for c in CELLS if c in wrong.cell.unique()])
    et.insert(0, "n", wrong.cell.value_counts())
    # can a blind reader tell the level from the reasoning? perceived confidence vs true level, within outcome
    pc = D.perceived_confidence.map({"low": 0, "medium": 1, "high": 2})
    tell = []
    for hi, lo in [("HW", "LW"), ("HR", "LR"), ("HW", "HR"), ("LW", "LR")]:
        a, b = pc[D.cell == hi].dropna(), pc[D.cell == lo].dropna()
        # P(score_hi > score_lo) + 0.5 ties  (AUROC)
        auc = np.mean([(x > y) + 0.5 * (x == y) for x in a for y in b]) if len(a) and len(b) else np.nan
        tell.append(dict(contrast=f"{hi} vs {lo}", auc_perceived_confidence=auc, n=f"{len(a)}/{len(b)}"))
    check = pd.DataFrame(dict(right_recoded=(D.judge_right == "yes"), right_true=(D.judge_verdict == D.gold)))
    agree_right = float((check.right_recoded == check.right_true).mean())
    L = ["# A6 qualitative coding: summary", "",
         "120 verdicts, 20 per cell, coded blind to confidence level and flips by four LLM coders (Claude).",
         f"Coders' judge_right matches the data on {agree_right:.0%} of records. Reasoning-based codes are left blank for "
         f"{int(D.no_reasoning.sum())} verdict-only records; {int(D.truncated.sum())} records had reasoning cut at 6,000 characters.", "",
         "## Share of records with each code, by cell", "", by.round(2).to_markdown(), "",
         "## Error type among wrong verdicts (row shares)", "", et.round(2).to_markdown(), "",
         "## Can a blind reader tell the confidence level from the reasoning? (AUROC of perceived confidence)", "",
         pd.DataFrame(tell).round(2).to_markdown(index=False), ""]
    if (OUT / "janys_codes.csv").exists():
        J = pd.read_csv(OUT / "janys_codes.csv").merge(D, on="code_id", suffixes=("_j", ""))
        L += ["## Agreement with Janys (Cohen's kappa)", "",
              pd.DataFrame([dict(field=f, n=int(J[f + "_j"].notna().sum()), kappa=kappa(J[f + "_j"], J[f]))
                            for f in FIELDS if f + "_j" in J]).round(2).to_markdown(index=False), ""]
    (OUT / "coding_summary.md").write_text("\n".join(L))
    # 30-item sheet for Janys: 5 per cell, without Claude's codes
    pick = D.groupby("cell", group_keys=False).apply(lambda x: x.sample(5, random_state=2)).code_id
    js = sheet[sheet.code_id.isin(pick)].copy()
    for f in FIELDS + ["notes"]:
        js[f] = ""
    js.to_csv(OUT / "janys_sheet.csv", index=False)
    print("\n".join(L))


if __name__ == "__main__":
    main()
