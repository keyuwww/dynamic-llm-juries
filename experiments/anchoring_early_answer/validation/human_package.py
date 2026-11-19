"""Blinded human-annotation package for the belief paper's labels (reviewer item B4, Nov 18). CPU only.

Nothing here is annotated by a model. The package is for two human readers (finance background for BFF-Bench items).
Items (each shows only the question, the candidate the benchmark marks wrong, and the benchmark's reference; no judge
identity, belief, approval or audit verdict):
  A  every wrong-labelled answer some judge believes 7/7 that an auditor did NOT call clearly wrong (reclassifications)
  B  every answer on which GLM-5.3 and Kimi-K3.1-Pro disagree
  C  a stratified random sample of RETAINED answers (GLM-5.3: clearly wrong): up to 8 per cell of
     benchmark x highest belief bin over judges (0/7, 1-3, 4-6, 7/7), with each cell's population size so
     weighted summaries are possible
Items are shuffled together (seed 20261118) and renumbered. Writes validation/human_package/{items.jsonl, key.json,
README.md}. The key file must not be given to readers.
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

OUT = V / "human_package"
PER_CELL = 8


def verdicts(name):
    v = {}
    for suf in ["labelaudit", "labelauditrb2"]:
        for l in open(HERE / "out" / f"ask_{name}_{suf}.jsonl"):
            d = json.loads(l)
            m = re.findall(r"AUDIT:\s*\**\s*(LABEL_OK|LABEL_WRONG|CONTESTED)", d.get("text") or "")
            v[d["cache_key"].split("|", 2)[2]] = m[-1] if m else None
    return v


def main():
    prompts = {}
    for f in ["ask_labelaudit.jsonl.gz", "ask_labelauditrb2.jsonl.gz"]:
        for l in gzip.open(HERE / "inputs" / f, "rt"):
            d = json.loads(l)
            prompts[d["cache_key"].split("|", 2)[2]] = (d["cache_key"].split("|")[1], d["prompt"])
    glm, kimi = verdicts("glm5.3"), verdicts("kimi3.1pro")
    best = collections.defaultdict(float)  # item -> highest belief over judges (wrong-labelled answers)
    for fam, od, sfx in P.FAM:
        for r in P.load(od, sfx):
            if not r["ok"]:
                best[r["item"]] = max(best[r["item"]], r["belief"])
    rng = random.Random(20261118)
    pick = {}
    for it, b in best.items():
        not_clear = glm.get(it) != "LABEL_OK" or (kimi.get(it) is not None and kimi[it] != "LABEL_OK")
        if it in prompts and round(7 * b) == 7 and not_clear:
            pick[it] = "A"
    for it in prompts:
        if glm.get(it) and kimi.get(it) and (glm[it] == "LABEL_OK") != (kimi[it] == "LABEL_OK"):
            pick.setdefault(it, "B")
    cells = collections.defaultdict(list)
    for it, b in best.items():
        if it in prompts and glm.get(it) == "LABEL_OK" and it not in pick:
            cells[(prompts[it][0], P.binof(b))].append(it)
    strata = {}
    for cell, items in sorted(cells.items()):
        items = sorted(items)
        s = rng.sample(items, min(PER_CELL, len(items)))
        strata[f"{cell[0]}|{cell[1]}"] = dict(population=len(items), sampled=len(s))
        for it in s:
            pick[it] = f"C|{cell[0]}|{cell[1]}"
    order = sorted(pick)
    rng.shuffle(order)
    OUT.mkdir(exist_ok=True)
    key = []
    with open(OUT / "items.jsonl", "w") as f:
        for n, it in enumerate(order, 1):
            bench, prompt = prompts[it]
            body = prompt.rsplit("\n\n", 1)[0]  # drop the final paragraph: the auditor's verdict options
            f.write(json.dumps(dict(n=n, benchmark=bench, material=body)) + "\n")
            key.append(dict(n=n, item=it, reason=pick[it], glm=glm.get(it), kimi=kimi.get(it), max_belief=best.get(it)))
    json.dump(dict(items=key, strata=strata), open(OUT / "key.json", "w"), indent=1)
    c = collections.Counter(k["reason"][0] for k in key)
    (OUT / "README.md").write_text(f"""# Human label check (not yet done)

{len(order)} items: {c['A']} high-belief reclassifications, {c['B']} auditor disagreements, {c['C']} stratified retained
answers ({PER_CELL} per benchmark x belief cell; population sizes in key.json for weighting). Give readers only
items.jsonl. For each item a reader records: clearly wrong / actually correct / ambiguous, and a short reason.
Two readers per item; BFF-Bench items need finance background. Disagreements are adjudicated by a third reader.
No model output may be recorded as a human annotation.
""")
    print(f"{len(order)} items", dict(c), "strata:", strata)


if __name__ == "__main__":
    main()
