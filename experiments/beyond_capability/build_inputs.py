"""Build the BBEH inputs for the beyond-capability runs (no API calls).

  inputs/questions.jsonl      460 BBEH Mini questions (id, task, input = prompt the solver sees, target)
  inputs/candidates.jsonl.gz  candidate responses to judge = every pool model's BBEH answer that reaches a
                              final answer ("The answer is ..."). Answers cut off at the pool's 16K token cap
                              never state an answer, are trivially wrong, and are dropped.
                              gold = official BBEH auto-grader.

  python3 experiments/beyond_capability/build_inputs.py
"""
import collections
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
POOL = HERE.parent / "tinker_pool"
sys.path.insert(0, str(POOL))
sys.path.insert(0, str(HERE))
from data import bbeh_correct, load_bbeh_mini  # noqa: E402
from bc_common import has_final, norm_answer  # noqa: E402


def main():
    (HERE / "inputs").mkdir(exist_ok=True)
    qs = load_bbeh_mini()
    with open(HERE / "inputs" / "questions.jsonl", "w") as f:
        for q in qs:
            f.write(json.dumps(q) + "\n")
    target = {q["id"]: q["target"] for q in qs}
    cands = []
    for line in open(POOL / "bbeh_results" / "answers.jsonl"):
        r = json.loads(line)
        if not has_final(r["answer"]):
            continue
        cands.append(dict(cid=f"{r['item']}|{r['model']}", qid=r["item"], task=r["task"], examinee=r["model"],
                          answer=r["answer"], norm=norm_answer(r["answer"]),
                          gold=int(bbeh_correct(r["answer"], target[r["item"]]))))
    with gzip.open(HERE / "inputs" / "candidates.jsonl.gz", "wt") as f:
        for c in cands:
            f.write(json.dumps(c) + "\n")
    by_m = collections.Counter((c["examinee"], c["gold"]) for c in cands)
    print(f"{len(qs)} questions, {len(cands)} candidates ({sum(c['gold'] for c in cands)} correct)")
    for m in sorted({k[0] for k in by_m}):
        print(f"  {m:22s} right {by_m[(m, 1)]:4d}  wrong {by_m[(m, 0)]:4d}")


if __name__ == "__main__":
    main()
