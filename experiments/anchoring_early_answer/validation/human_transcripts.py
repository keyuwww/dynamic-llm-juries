"""Blinded human-annotation package for judge transcripts (reviewer item B4, Nov 18). CPU only; nothing is annotated.

Thinking-on Qwen transcripts of AUDITED WRONG answers (RewardBench 2 Math, BFF-Bench), 20 per belief bin
(0/7, 1-3, 4-6, 7/7; seed 20261118), sampled without looking at the verdict. Each item shows the question, the
answer being graded and the judge's transcript with every "VERDICT:" line removed (the reasoning itself can still
reveal the judge's leaning; full blinding is not possible). Readers label, separately:
  PROCESS   independent derivation / checking the candidate's steps / paraphrasing / unclear
  RESULT    the transcript's own final result equals the candidate's / differs / no own result
A written derivation does not show what computation produced the verdict internally.
Writes validation/human_package/transcripts.jsonl and transcripts_key.json (the key holds judge, item and belief).
"""
import collections
import gzip
import json
import random
import re
import sys
from pathlib import Path

V = Path(__file__).resolve().parent
HERE = V.parent
sys.path.insert(0, str(V))
import paper_numbers as P  # noqa: E402

PER_BIN = 20


def main():
    rows = {(r["judge"], r["item"]): r for r in P.load("out", "") if not r["ok"] and r["audited"]}
    byb = collections.defaultdict(list)
    prompts = {}
    for d in map(json.loads, gzip.open(HERE / "inputs" / "ask_transcripts_think.jsonl.gz", "rt")):
        _, judge, item = d["cache_key"].split("|", 2)
        r = rows.get((judge, item))
        if r is None:
            continue
        body = d["prompt"].split("\n\n", 1)[1]                       # drop the first instruction line
        body = body.split("\nQ1 RESOLVE:")[0]                        # drop the model-labelling questions
        body = re.sub(r"^.*VERDICT:.*$\n?", "", body, flags=re.M)    # remove verdict lines
        prompts[(judge, item)] = body
        byb[r["b"]].append((judge, item))
    rng = random.Random(20261118)
    pick = []
    for b in P.BINS:
        pool = sorted(byb[b])
        pick += [(k, b) for k in rng.sample(pool, min(PER_BIN, len(pool)))]
    rng.shuffle(pick)
    out = V / "human_package"
    out.mkdir(exist_ok=True)
    key = []
    with open(out / "transcripts.jsonl", "w") as f:
        for n, ((judge, item), b) in enumerate(pick, 1):
            f.write(json.dumps(dict(n=n, material=prompts[(judge, item)])) + "\n")
            key.append(dict(n=n, judge=judge, item=item, belief_bin=b, belief=rows[(judge, item)]["belief"]))
    json.dump(key, open(out / "transcripts_key.json", "w"), indent=1)
    print(len(pick), "transcripts;", {b: sum(k["belief_bin"] == b for k in key) for b in P.BINS},
          "pool sizes", {b: len(v) for b, v in byb.items()})


if __name__ == "__main__":
    main()
