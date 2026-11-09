"""Moderate-difficulty benchmarks for the stretching study: judges should solve MOST questions, not all.
Builds a stratified pilot (no API calls):

  MATH         EleutherAI/hendrycks_math test, 40 per difficulty level (1-5), gold = the \\boxed{} answer
  MMLU-Redux   edinburgh-dawg/mmlu-redux-2.0, only questions experts marked 'ok' (no flagged key or wording errors)
  MMLU-Pro     TIGER-Lab/MMLU-Pro test, stratified by its 14 categories

Writes inputs/easy_pilot.jsonl: id, bench, prompt (what the solver sees), gold, meta.

  .venv/bin/python experiments/beyond_capability/easy_build.py --per 200
"""
import argparse
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
LETTERS = "ABCDEFGHIJ"
MC_SUFFIX = ("\n\nThink step by step, then end with exactly one line \"The answer is: X\" where X is the letter of the "
             "correct option.")
MATH_SUFFIX = ("\n\nThink step by step, then end with exactly one line \"The answer is: \" followed by the final answer "
               "only (no words, no \\boxed).")


def boxed(sol):
    """Last \\boxed{...} in a MATH solution (balanced braces)."""
    i = sol.rfind("\\boxed")
    if i < 0:
        return None
    j = sol.find("{", i)
    depth, k = 0, j
    while k < len(sol):
        depth += sol[k] == "{"
        depth -= sol[k] == "}"
        if depth == 0:
            return sol[j + 1:k]
        k += 1
    return None


def mc_prompt(q, choices):
    opts = "\n".join(f"({LETTERS[i]}) {c}" for i, c in enumerate(choices))
    return f"Answer the following multiple-choice question.\n\n{q}\n\n{opts}{MC_SUFFIX}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per", type=int, default=200, help="questions per benchmark")
    ap.add_argument("--out", default=str(HERE / "inputs" / "easy_pilot.jsonl"))
    a = ap.parse_args()
    from datasets import get_dataset_config_names, load_dataset
    rng = random.Random(0)
    rows = []
    # MATH, stratified by level
    by_level = {}
    for cfg in get_dataset_config_names("EleutherAI/hendrycks_math"):
        for r in load_dataset("EleutherAI/hendrycks_math", cfg, split="test"):
            g = boxed(r["solution"])
            if g:
                by_level.setdefault(r["level"], []).append(dict(r, gold=g, topic=cfg))
    levels = sorted(by_level)
    for lv in levels:
        for i, r in enumerate(rng.sample(by_level[lv], a.per // len(levels))):
            rows.append(dict(id=f"math-{lv.split()[-1]}-{i:03d}", bench="math", prompt=r["problem"] + MATH_SUFFIX, gold=r["gold"],
                             meta=dict(level=r["level"], topic=r["topic"])))
    # MMLU-Redux 2.0, 'ok' questions only, stratified by subject
    pool = []
    for cfg in get_dataset_config_names("edinburgh-dawg/mmlu-redux-2.0"):
        for i, r in enumerate(load_dataset("edinburgh-dawg/mmlu-redux-2.0", cfg, split="test")):
            if r["error_type"] == "ok":
                ch = r["choices"] if isinstance(r["choices"], list) else eval(r["choices"])  # noqa: S307 (dataset field)
                pool.append(dict(id=f"redux-{cfg}-{i:03d}", subject=cfg, prompt=mc_prompt(r["question"], ch),
                                 gold=LETTERS[int(r["answer"])]))
    subj = sorted({p["subject"] for p in pool})
    pick = []
    for s in subj:
        pick += rng.sample([p for p in pool if p["subject"] == s], 4)
    for p in rng.sample(pick, min(a.per, len(pick))):
        rows.append(dict(id=p["id"], bench="mmlu_redux", prompt=p["prompt"], gold=p["gold"], meta=dict(subject=p["subject"])))
    # MMLU-Pro, stratified by category
    pro = list(load_dataset("TIGER-Lab/MMLU-Pro", split="test"))
    cats = sorted({r["category"] for r in pro})
    per_cat = -(-a.per // len(cats))
    pick = []
    for c in cats:
        pick += rng.sample([r for r in pro if r["category"] == c], per_cat)
    for r in rng.sample(pick, a.per):
        rows.append(dict(id=f"pro-{r['question_id']}", bench="mmlu_pro", prompt=mc_prompt(r["question"], r["options"]),
                         gold=LETTERS[r["answer_index"]], meta=dict(category=r["category"])))
    Path(a.out).parent.mkdir(exist_ok=True)
    with open(a.out, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    import collections
    print(collections.Counter(r["bench"] for r in rows))


if __name__ == "__main__":
    main()
