"""Blinded check of the post-hoc lenient letter parser (Nov 20 review). CPU only.

Own answers in the confirmatory range fall into three groups: the strict parser finds a five-letter string (the
lenient parser then returns the same letter by construction), only the lenient parser finds a letter ("recovered"),
or neither does ("unparsed"). We sample 25 recovered and 10 unparsed own answers per judge (seed 20261120) and show a
reader the question's options and the last 3,000 characters of the answer, without either parser's output. The
reader writes the final letter the answer commits to, or NONE (no final choice) or AMBIGUOUS (more than one).
The reader is a model (Claude Opus 5.5 subagents), not a person.

  python parser_check.py build      -> parser_check/items.jsonl, parser_check/key.json
  python parser_check.py analyze    (needs parser_check/labels.json: {"<n>": "C" | "NONE" | "AMBIGUOUS"})
"""
import collections
import json
import random
import re
import sys
from pathlib import Path

from analyze import DATA, JUDGES, lenient_letter, load

OUT = Path(__file__).resolve().parent / "parser_check"
PER = dict(recovered=25, unparsed=10)


def options(q):
    return "\n".join(l for l in q.splitlines() if re.match(r"^\([A-J]\) ", l))


def build():
    pairs = {p["qid"]: p for p in load(DATA / "pairs.jsonl") if 80 <= p["order"] < 6080}
    pool = collections.defaultdict(list)
    for r in load(DATA / "solve.jsonl"):
        if r["qid"] not in pairs:
            continue
        for i, (t, s) in enumerate(zip(r["texts"], r["letters"])):
            if i == 0 or s:
                continue
            g = "recovered" if lenient_letter(t) else "unparsed"
            pool[(r["model"], g)].append((r["qid"], i))
    rng = random.Random(20261120)
    pick = []
    for j in JUDGES:
        for g, k in PER.items():
            pick += [(j, g, q, i) for q, i in rng.sample(sorted(pool[(j, g)]), min(k, len(pool[(j, g)])))]
    rng.shuffle(pick)
    S = {(r["model"], r["qid"]): r for r in load(DATA / "solve.jsonl")}
    OUT.mkdir(exist_ok=True)
    key = []
    with open(OUT / "items.jsonl", "w") as f:
        for n, (j, g, q, i) in enumerate(pick, 1):
            t = S[(j, q)]["texts"][i] or ""
            f.write(json.dumps(dict(n=n, options=options(pairs[q]["question"]), answer_end=t[-3000:])) + "\n")
            key.append(dict(n=n, judge=j, group=g, qid=q, sample=i, lenient=lenient_letter(t)))
    json.dump(key, open(OUT / "key.json", "w"), indent=1)
    print(len(pick), "items;", {g: sum(k["group"] == g for k in key) for g in PER},
          "pool", {f"{j}|{g}": len(v) for (j, g), v in pool.items()})


def analyze():
    key = json.load(open(OUT / "key.json"))
    lab = json.load(open(OUT / "labels.json"))
    res = {}
    for g in PER:
        K = [k for k in key if k["group"] == g]
        c = collections.Counter()
        for k in K:
            r = lab[str(k["n"])]
            if g == "recovered":
                c["reader same letter" if r == k["lenient"] else
                  "reader NONE/AMBIGUOUS" if r in ("NONE", "AMBIGUOUS") else "reader different letter"] += 1
            else:
                c["reader NONE/AMBIGUOUS" if r in ("NONE", "AMBIGUOUS") else "reader finds a letter"] += 1
        res[g] = dict(n=len(K), **c)
        res[g + "_by_judge"] = {j: dict(collections.Counter(
            (lab[str(k["n"])] == k["lenient"]) if g == "recovered" else (lab[str(k["n"])] in ("NONE", "AMBIGUOUS"))
            for k in K if k["judge"] == j)) for j in JUDGES}
    json.dump(res, open(OUT / "results.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    {"build": build, "analyze": analyze}[sys.argv[1]]()
