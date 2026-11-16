"""Same-model test items: many right and wrong answers from ONE answering model (Qwen3.5-4B, 12 fresh samples, thinking
off, Tinker) to questions the judge (Llama-3.1-8B) cannot solve. Comparing a right and a wrong answer written by the
same model removes "which model wrote it", so a stretching gain here is checking, not authorship.

Per question: up to 3 right and 3 wrong answers that state a final answer (distinct texts; wrong answers with distinct
final answers first), only questions with at least one of each. Judge prompt identical to mmlu_build_items.py.
Grades: MMLU = final letter vs the expert key; MATH = GLM-5.3-Flash (egrades_sm_math_q.jsonl, bc_jobs.py egrade).

  python3 experiments/beyond_capability/sm_build_items.py -> inputs/sm_{mmlu,math}_items.jsonl.gz
"""
import collections
import gzip
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bc_load import OUT, jl  # noqa: E402
from mmlu_build_items import MATH_JUDGE, MC_JUDGE, letter, math_final  # noqa: E402

M = "qwen3.5-4b"


def main():
    for bench in ("mmlu", "math"):
        stem = f"sm_{bench}_q"
        f = OUT / f"esolves_{stem}_{M}.jsonl"
        if not f.exists():
            print(f"{bench}: no samples yet")
            continue
        qs = {q["id"]: q for q in jl(HERE / "inputs" / f"{stem}.jsonl")}
        grades = {r["cache_key"]: r["verdict"] for r in jl(OUT / f"egrades_{stem}.jsonl")} if bench == "math" else {}
        rows, stat = [], collections.Counter()
        rnd = random.Random(0)
        for r in jl(f):
            q = qs[r["qid"]]
            right, wrong = [], []
            for k, s in enumerate(r["samples"]):
                fa = math_final(s["text"]) if bench == "math" else letter(s["text"])
                if fa is None or not s.get("clean", True):
                    continue
                if bench == "math":
                    g = grades.get(f"esolves_{stem}_{M}|{r['qid']}|{k}")
                    if g is None:
                        continue
                else:
                    g = int(fa == q["gold"])
                (right if g else wrong).append((k, fa, s["text"]))
            if not right or not wrong:
                stat["one-sided"] += 1
                continue
            rnd.shuffle(right)
            seen, w1, w2 = set(), [], []
            for x in wrong:  # distinct wrong final answers first
                (w2 if x[1] in seen else w1).append(x)
                seen.add(x[1])
            pick = right[:3] + (w1 + w2)[:3]
            qtext = q["prompt"].split("\n\nThink step by step")[0].replace(
                "Answer the following multiple-choice question.\n\n", "")
            tmpl = MATH_JUDGE if bench == "math" else MC_JUDGE
            for k, fa, text in pick:
                g = int(any(k == x[0] for x in right))
                rows.append(dict(bench=bench, qid=q["id"], aid=f"{q['id']}|{M}|sm{k}", gold=g, src=M, mode="J",
                                 messages=[{"role": "user", "content": tmpl.format(question=qtext, answer=text)}],
                                 suffix="VERDICT:", letter=fa))
            stat["mixed"] += 1
        with gzip.open(HERE / "inputs" / f"sm_{bench}_items.jsonl.gz", "wt") as fh:
            for x in rows:
                fh.write(json.dumps(x) + "\n")
        pairs = collections.defaultdict(lambda: [0, 0])
        for x in rows:
            pairs[x["qid"]][x["gold"]] += 1
        print(f"{bench}: {len(rows)} answers on {stat['mixed']} questions with both right and wrong "
              f"({stat['one-sided']} one-sided); {sum(a * b for a, b in pairs.values())} same-model pairs")


if __name__ == "__main__":
    main()
