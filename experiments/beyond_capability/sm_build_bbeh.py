"""Same-model test items for BBEH from answers that already exist: each of four answering models (Qwen3.5-4B,
Qwen3.5-9B, Qwen3.6-35B, Nemotron-3-Super; 5 samples per question, thinking off, Tinker) gives up to 2 right and 2 wrong
answers per question where its samples include both. Right/wrong = BBEH's own answer checker vs the target. Judge prompt
identical to the main BBEH items (bc_common.judge_prompt "none").

  python3 experiments/beyond_capability/sm_build_bbeh.py -> inputs/sm_bbeh_items.jsonl.gz
"""
import collections
import gzip
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
from bc_common import judge_prompt  # noqa: E402
from bc_load import OUT, jl, questions  # noqa: E402
from data import bbeh_correct  # noqa: E402

MODELS = ["qwen3.5-4b", "qwen3.5-9b", "qwen3.6-35b-a3b", "nemotron3-super-120b"]


def main():
    qs = questions()
    keep = {json.loads(l)["qid"] for l in gzip.open(HERE / "inputs" / "bbeh_items.jsonl.gz", "rt")}
    rnd = random.Random(0)
    rows, stat = [], collections.Counter()
    for m in MODELS:
        for r in jl(OUT / f"solves_{m}.jsonl"):
            if r["qid"] not in keep:
                continue
            q = qs[r["qid"]]
            right, wrong = [], []
            for k, s in enumerate(r["samples"]):
                if not s.get("clean", True) or not s["text"].strip():
                    continue
                (right if bbeh_correct(s["text"], q["target"]) else wrong).append((k, s["text"]))
            if not right or not wrong:
                continue
            rnd.shuffle(right)
            rnd.shuffle(wrong)
            for g, picks in ((1, right[:2]), (0, wrong[:2])):
                for k, text in picks:
                    rows.append(dict(bench="bbeh", qid=r["qid"], aid=f"{r['qid']}|{m}|sm{k}", gold=g, src=m, mode="J",
                                     messages=[{"role": "user", "content": judge_prompt("none", q["input"], text)}],
                                     suffix="VERDICT:"))
            stat[m] += 1
    with gzip.open(HERE / "inputs" / "sm_bbeh_items.jsonl.gz", "wt") as fh:
        for x in rows:
            fh.write(json.dumps(x) + "\n")
    pairs = collections.defaultdict(lambda: [0, 0])
    for x in rows:
        pairs[(x["qid"], x["src"])][x["gold"]] += 1
    print(f"{len(rows)} answers; mixed (model, question) groups: {dict(stat)}; "
          f"{len({x['qid'] for x in rows})} questions; {sum(a * b for a, b in pairs.values())} same-model pairs")


if __name__ == "__main__":
    main()
