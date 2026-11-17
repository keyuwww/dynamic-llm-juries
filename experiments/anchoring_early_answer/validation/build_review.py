"""Build two review files for a second-reader check (Nov 16):
  validation/matcher_sample.jsonl  50 GLM-5.3-Flash SAME/DIFFERENT decisions (RB2 Math 20, BFF 30), stratified so
                                   SAME and DIFFERENT are balanced and high-belief wrong answers are oversampled.
  validation/label_audit_7of7.jsonl every wrong-labelled answer that some Qwen believes 7/7 (BFF, JudgeBench).
"""
import gzip, json, random
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]
V = HERE / "validation"
random.seed(16)
jobs = {(j["judge"], j["item_id"]): j for j in map(json.loads, gzip.open(HERE / "inputs" / "readout_jobs.jsonl.gz", "rt"))}
rows = json.load(open(HERE / "out" / "belief_rows_clean.json"))
solves = {r["cache_key"]: r["answer"] for r in map(json.loads, open(HERE / "out" / "solves.jsonl"))}
solves.update({r["cache_key"]: r["answer"] for r in map(json.loads, open(HERE / "out" / "solves_k.jsonl"))})
for f in ("solves_k_rerun.jsonl",):
    if (HERE / "out" / f).exists():
        solves.update({r["cache_key"]: r["answer"] for r in map(json.loads, open(HERE / "out" / f))})
M = {}
for f in ("matches_glm5.3-flash.jsonl", "matches_glm5.3-flash_k.jsonl", "matches_glm5.3-flash_k_rerun.jsonl"):
    p = HERE / "out" / f
    if p.exists():
        M.update({r["cache_key"]: r["verdict"] for r in map(json.loads, open(p))})
row = {(r["judge"], r["item"]): r for r in rows}
pool = defaultdict(list)
for k, v in M.items():
    if v not in ("SAME", "DIFFERENT"):
        continue
    parts = k.split("|")
    judge, item = parts[0], parts[1]
    s = parts[3] if len(parts) > 3 else None
    r, j = row.get((judge, item)), jobs.get((judge, item))
    if not r or not j or r["bench"] not in ("rb2math", "bff"):
        continue
    own = solves.get(f"{judge}|{j['qid']}|{s}" if s else f"{judge}|{j['qid']}")
    if not own:
        continue
    hi = int(r["target_ok"]) == 0 and float(r["belief"]) >= 4 / 7
    pool[(r["bench"], v, hi)].append(dict(key=k, bench=r["bench"], glm=v, question=j["question"][-4000:],
                                          own_end=own[-3000:], cand_end=j["candidates"][0][-3000:]))
plan = {("rb2math", "SAME", True): 6, ("rb2math", "SAME", False): 4, ("rb2math", "DIFFERENT", True): 4, ("rb2math", "DIFFERENT", False): 6,
        ("bff", "SAME", True): 9, ("bff", "SAME", False): 6, ("bff", "DIFFERENT", True): 6, ("bff", "DIFFERENT", False): 9}
out = []
for cell, n in plan.items():
    pick = random.sample(pool[cell], min(n, len(pool[cell])))
    for p in pick:
        p["stratum"] = f"{cell[0]}|{cell[1]}|{'high-belief wrong' if cell[2] else 'other'}"
    out += pick
random.shuffle(out)
with open(V / "matcher_sample.jsonl", "w") as f:
    for i, p in enumerate(out):
        f.write(json.dumps(dict(n=i + 1, **p)) + "\n")
print("matcher sample", len(out), {c: len(pool[c]) for c in plan})

refs = {it["id"]: it["ref"] for it in map(json.loads, open(HERE.parent / "beyond_capability" / "inputs" / "bff_items.jsonl"))}
seen, aud = {}, []
for r in rows:
    if r["bench"] in ("bff", "judgebench") and int(r["target_ok"]) == 0 and round(float(r["belief"]) * 7) == 7:
        seen.setdefault((r["bench"], r["item"]), []).append(r["judge"])
for (bench, item), judges in sorted(seen.items()):
    j = jobs[(judges[0], item)]
    d = dict(bench=bench, item=item, believed_7of7_by=judges, judge_prompt=j["messages"][0]["content"])
    if bench == "bff":
        d["expert_reference"] = refs.get(item)
        d["label"] = "the candidate response is labelled WRONG by BFF-Bench's experts"
    else:
        g = int(j["gold"])
        d["label"] = (f"JudgeBench says Response {'A' if g == 1 else 'B'} is the correct one; the 7/7-believed WRONG "
                      f"response is Response {'B' if g == 1 else 'A'}")
    aud.append(d)
with open(V / "label_audit_7of7.jsonl", "w") as f:
    f.write("".join(json.dumps(d) + "\n" for d in aud))
print("audit items", len(aud), sum(d["bench"] == "bff" for d in aud))
