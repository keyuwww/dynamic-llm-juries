"""Blinded human label check for the math replication (Nov 21 strict review, item B1). CPU only.

Why: the model auditor disputes the answer key for all 7 wrong responses some judge believes 7/7, and for 2-11% at
lower belief. If people agree, the math top bin is approval of answers the key gets wrong; if not, the auditor
over-disputes. Only humans can settle this; no model output may be recorded as an annotation.

Sample: every response at 7/7 (7) and 4-6 (19), and 20 each at 1-3 and 0/7 drawn at random (seed 20261121),
stratified by the highest belief any judge has in the wrong response, NOT by the auditor's verdict, so each stratum's
human dispute rate is unbiased for that stratum. Population sizes are kept for weighting.
Readers see the problem, the key's integer, the two responses in the order the judges saw them, and which one the
key marks wrong; no belief, judge verdict or audit verdict.

  python human_package.py   -> human_package/{items.jsonl, key.json, README.md}
"""
import collections
import json
import random

import analyze_math as M

OUT = M.HERE / "human_package"
PER = {"7/7": None, "4-6": None, "1-3": 20, "0/7": 20}  # None = all


def group(b):
    return None if b is None else "0/7" if b == 0 else "1-3" if b <= 3 else "4-6" if b <= 6 else "7/7"


def main():
    pairs = {p["qid"]: p for p in M.A.load(M.DATA / "pairs.jsonl") if 80 <= p["order"] < 1880}
    audit = {r["qid"]: r["verdict"] for r in M.A.load(M.DATA / "audit.jsonl")}
    R, _ = M.rows(80, 1800, audit)
    mb = {}
    for r in R:
        mb[r["qid"]] = max(mb.get(r["qid"], -1), round(7 * r["belief"]))
    strata = collections.defaultdict(list)
    for q in sorted(pairs):
        g = group(mb.get(q))
        if g:
            strata[g].append(q)
    rng = random.Random(20261121)
    pick = []
    for g, k in PER.items():
        pick += [(q, g) for q in (strata[g] if k is None else rng.sample(strata[g], k))]
    rng.shuffle(pick)
    OUT.mkdir(exist_ok=True)
    key = []
    with open(OUT / "items.jsonl", "w") as f:
        for n, (q, g) in enumerate(pick, 1):
            p = pairs[q]
            good = "B" if p["wrong_pos"] == "A" else "A"
            f.write(json.dumps(dict(n=n, question=p["question"], key_answer=p["gold"], key_response=good,
                                    marked_wrong_response=p["wrong_pos"], marked_wrong_answer=p["wrong_answer"],
                                    response_a=p["response_a"], response_b=p["response_b"])) + "\n")
            key.append(dict(n=n, qid=q, stratum=g, auditor=audit.get(q)))
    pop = {g: len(v) for g, v in strata.items()}
    sampled = {g: len(strata[g]) if k is None else k for g, k in PER.items()}
    json.dump(dict(items=key, population=pop, sampled=sampled, no_judge_with_5_answers=len(pairs) - sum(pop.values())),
              open(OUT / "key.json", "w"), indent=1)
    (OUT / "README.md").write_text(f"""# Human label check: math replication (not yet done)

{len(pick)} wrong-labelled responses, stratified by the highest belief any judge has in them (every response at 7/7
and 4-6; 20 each at 1-3 and 0/7; population sizes in key.json). Start with the 7/7 and 4-6 items. Readers get
items.jsonl only (or the annotation page), never key.json.

For each item, decide whether the response the DAPO-Math key marks WRONG really has a wrong final integer:
- clearly wrong: its final integer is wrong and the key's integer is right
- actually correct: its final integer is right (the key is wrong)
- ambiguous: the problem is unclear or admits more than one defensible answer
and write a one-line reason (a short derivation where the key is disputed). Use any reference or computation except
AI assistants. Two readers per item, independently; a third reader adjudicates disagreements. No model output may be
recorded as a human annotation.
""")
    print(len(pick), "items; population", pop, "; auditor verdicts in sample",
          dict(collections.Counter((k["stratum"], k["auditor"]) for k in key)))


if __name__ == "__main__":
    main()
