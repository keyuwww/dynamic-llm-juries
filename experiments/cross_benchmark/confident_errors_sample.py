"""A6 sample for qualitative coding (docs/confident_errors_plan.md).

20 verdicts per cell (HW, MW, LW, HR, LR, HF), 5 per benchmark, one verdict per item within a cell, from
results/confident_errors/states.csv (primary scheme: within-judge thirds). For each verdict the sheet shows the
question, both answers (first presentation order), the gold label, the judge's verdict and reasoning in that order
with every stated confidence number masked, and a second judge's reasoning on the same item that reached the opposite verdict when one
exists (contrast). Coders see correctness but not the confidence level or flip status.
Outputs (results/confident_errors/):
  coding_sheet.csv / coding_sheet.md   blind sheet, one row per code_id, with empty coding columns
  coding_key.csv                       code_id -> judge, cell, conf, pair_id (do not open while coding)
Usage: python confident_errors_sample.py
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from conf_analysis import read  # noqa: E402
from order_consistency import SHORT  # noqa: E402
from run_confidence import load_items  # noqa: E402
from run_difficulty import texts  # noqa: E402

OUT = HERE / "results" / "confident_errors"
CELLS = {"HW": ("high", "W"), "MW": ("mid", "W"), "LW": ("low", "W"), "HR": ("high", "R"), "LR": ("low", "R"),
         "HF": ("high", "F")}
PER_BENCH = 5
CODE_COLS = ["error_type", "noticed_decisive_difference", "hedging_or_self_correction", "says_answers_close",
             "gold_questionable", "notes"]


def clean(text):
    text = text[0] if isinstance(text, list) else (text or "")
    text = re.sub(r"<\|[^>]*\|>", "", text)
    text = re.sub(r"(?im)^\s*\**CONFIDENCE\**\s*:.*$", "", text)
    # reasoning models also state their confidence inside the reasoning; mask the number
    return re.sub(r"(?i)confiden\w*[^\n]{0,60}",
                  lambda m: re.sub(r"\d+(?:\.\d+)?\s*%?", "[masked]", m.group()), text).strip()


def main():
    S = pd.read_csv(OUT / "states.csv")
    rng = np.random.default_rng(0)
    rows, used = [], set()
    for b in ["bffpair", "judgebench", "alpacafarm", "mtbhuman"]:
        items = {it["pair_id"]: it for it in load_items(b)[0] if it["order"] in ("ab", 0)}
        t = read("confidence", b)
        t = t[t.order == "ab"].set_index(["judge", "pair_id"])
        x = S[S.bench == b]
        for cell, (lev, out) in CELLS.items():
            pool = x[(x.third == lev) & (x.outcome == out) & x.pair_id.isin(items)]
            pool = pool.sample(frac=1, random_state=int(rng.integers(1e9)))
            k = 0
            for _, r in pool.iterrows():
                if k == PER_BENCH or (cell, r.pair_id) in used:
                    continue
                used.add((cell, r.pair_id))
                k += 1
                it = items[r.pair_id]
                q, _ = texts(b, it)
                if b == "bffpair":
                    a = "\n\n".join(m["content"] for m in it["conv_a"][-1:])
                    bb = "\n\n".join(m["content"] for m in it["conv_b"][-1:])
                elif b == "mtbhuman":
                    a = "\n\n".join(m["content"] for m in it["resp_a"][-1:])
                    bb = "\n\n".join(m["content"] for m in it["resp_b"][-1:])
                else:
                    a, bb = it["resp_a"], it["resp_b"]
                # contrast: another judge on the same item with the opposite pick
                same = x[(x.pair_id == r.pair_id) & (x.judge != r.judge) & ((x["pick"] - r["pick"]).abs() == 1)]
                cj = same.judge.iloc[0] if len(same) else None
                rows.append(dict(cell=cell, judge=SHORT[r.judge], conf=r.conf, pair_id=r.pair_id, bench=b,
                                 question=q, answer_A=a, answer_B=bb, gold="A" if it["gold"] == 1 else "B",
                                 judge_verdict="A" if t.verdict.get((r.judge, r.pair_id)) == 1 else "B",  # this order
                                 judge_reasoning=clean(t.raw_full.get((r.judge, r.pair_id), "")),
                                 contrast_judge=SHORT.get(cj, ""),
                                 contrast_reasoning=clean(t.raw_full.get((cj, r.pair_id), "")) if cj else ""))
    D = pd.DataFrame(rows).sample(frac=1, random_state=1).reset_index(drop=True)
    D.insert(0, "code_id", [f"c{i:03d}" for i in range(len(D))])
    D[["code_id", "cell", "judge", "conf", "pair_id", "bench"]].to_csv(OUT / "coding_key.csv", index=False)
    sheet = D.drop(columns=["cell", "judge", "conf", "pair_id"]).assign(**{c: "" for c in CODE_COLS})
    sheet.to_csv(OUT / "coding_sheet.csv", index=False)
    md = ["# A6 coding sheet (blind to confidence level and flips)", "",
          "Codebook: docs/confident_errors_plan.md (A6). Fill the columns in coding_sheet.csv.", ""]
    for _, r in sheet.iterrows():
        md += [f"## {r.code_id} · {r.bench} · gold {r.gold} · judge picked {r.judge_verdict}", "",
               "**Question**", "", r.question[:3000], "", "**Answer A**", "", str(r.answer_A)[:3000], "",
               "**Answer B**", "", str(r.answer_B)[:3000], "", "**Judge reasoning**", "", r.judge_reasoning[:4000], ""]
        if r.contrast_reasoning:
            md += ["**Another judge, opposite verdict**", "", r.contrast_reasoning[:3000], ""]
        md += ["---", ""]
    (OUT / "coding_sheet.md").write_text("\n".join(md))
    print(D.groupby(["cell", "bench"]).size().unstack(), "\ncontrast available:", (D.contrast_reasoning != "").mean())


if __name__ == "__main__":
    main()
