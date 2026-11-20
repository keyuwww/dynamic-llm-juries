"""Blinded human label check for the MMLU-Pro replication (Nov 20 self-review, item 1). CPU only.

Why: the model auditor disputes the answer key for 9% of wrong responses no judge reaches and 51% of those some judge
reaches 7/7 (lenient parser). If people agree, much of the "approval of believed wrong answers" at the top of the
staircase is approval of answers the key gets wrong; if they do not, the auditor over-disputes. Only humans can
settle this; no model output may be recorded as an annotation.

Sample: stratified by the highest belief any judge has in the wrong response (lenient parser), NOT by the auditor's
verdict, so each stratum's human dispute rate is an unbiased estimate for that stratum and directly comparable with
the auditor's: 7/7 50, 4-6 40, 1-3 30, 0/7 30 (seed 20261120). Population sizes are kept for weighting.
Readers see the question with its options, the response the key marks correct (and the key letter) and the response
it marks wrong (and its letter), in random A/B order as the judges saw them; no belief, judge verdict or audit verdict.

  python human_package.py   -> human_package/{items.jsonl, key.json, README.md}
"""
import collections
import json
import random

import analyze as A
from sensitivity import max_bins

OUT = A.HERE / "human_package"
PER = {"7/7": 50, "4-6": 40, "1-3": 30, "0/7": 30}


def group(b):
    return None if b is None else "0/7" if b == 0 else "1-3" if b <= 3 else "4-6" if b <= 6 else "7/7"


def main():
    pairs = {p["qid"]: p for p in A.load(A.DATA / "pairs.jsonl") if 80 <= p["order"] < 6080}
    audit = {r["qid"]: r["verdict"] for f in ("audit.jsonl", "audit_extra.jsonl") for r in A.load(A.DATA / f)}
    mb = max_bins(True)
    strata = collections.defaultdict(list)
    for q in sorted(pairs):
        g = group(mb.get(q))
        if g:
            strata[g].append(q)
    rng = random.Random(20261120)
    pick = []
    for g, k in PER.items():
        pick += [(q, g) for q in rng.sample(strata[g], k)]
    rng.shuffle(pick)
    OUT.mkdir(exist_ok=True)
    key = []
    with open(OUT / "items.jsonl", "w") as f:
        for n, (q, g) in enumerate(pick, 1):
            p = pairs[q]
            good = "B" if p["wrong_pos"] == "A" else "A"
            f.write(json.dumps(dict(n=n, question=p["question"].split("\nIf you cannot determine")[0],
                                    key_answer=p["gold"], key_response=good, marked_wrong_response=p["wrong_pos"],
                                    marked_wrong_answer=p["wrong_letter"],
                                    response_a=p["response_a"], response_b=p["response_b"])) + "\n")
            key.append(dict(n=n, qid=q, stratum=g, auditor=audit.get(q), category=p["category"]))
    pop = {g: len(v) for g, v in strata.items()}
    json.dump(dict(items=key, population=pop, sampled=PER, no_judge_with_5_answers=len(pairs) - sum(pop.values())),
              open(OUT / "key.json", "w"), indent=1)
    (OUT / "README.md").write_text(f"""# Human label check: MMLU-Pro replication (not yet done)

{len(pick)} wrong-labelled responses, stratified by the highest belief any judge has in them (7/7 50, 4-6 40,
1-3 30, 0/7 30; population sizes in key.json). Readers get items.jsonl only (or the annotation page), never key.json.

For each item, decide whether the response the MMLU-Pro key marks WRONG really has a wrong final answer:
- clearly wrong: its final option is wrong and the key's option is right
- actually correct: its final option is right (the key is wrong, or both options are defensible as right)
- ambiguous: the question is unclear or more than one option is defensible
and write a one-line reason. Use any reference except AI assistants. Two readers per item, independently; a third
reader adjudicates disagreements. No model output may be recorded as a human annotation.
""")
    print(len(pick), "items; population", pop, "; auditor verdicts in sample",
          dict(collections.Counter((k["stratum"], k["auditor"]) for k in key)))


if __name__ == "__main__":
    main()
