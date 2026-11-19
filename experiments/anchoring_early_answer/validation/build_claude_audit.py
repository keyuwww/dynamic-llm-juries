"""Third label auditor: Claude Opus 5.5 (Nov 18). Replaces the planned human check of the 60-answer blind sample.
Audits (a) the 60-answer blind sample in human_check_key.json and (b) every answer on which GLM-5.3 and Kimi-K3.1-Pro
disagree (clearly-wrong vs not). Writes one prompt file per answer (the exact GLM/Kimi audit prompt) to OUT/prompts and
the id map to OUT/map.json; the auditing agents see only the prompt files.
usage: python build_claude_audit.py OUTDIR
"""
import gzip, json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]); (OUT / "prompts").mkdir(parents=True, exist_ok=True)

P = {}
for f in ["ask_labelaudit.jsonl.gz", "ask_labelauditrb2.jsonl.gz"]:
    for l in gzip.open(HERE / "inputs" / f, "rt"):
        d = json.loads(l); P[d["cache_key"]] = d["prompt"]

def verdicts(name):
    v = {}
    for suf in ["labelaudit", "labelauditrb2"]:
        for l in open(HERE / "out" / f"ask_{name}_{suf}.jsonl"):
            d = json.loads(l)
            m = re.findall(r"AUDIT:\s*\**\s*(LABEL_OK|LABEL_WRONG|CONTESTED)", d.get("text") or "")
            v[d["cache_key"]] = m[-1] if m else None
    return v

glm, kimi = verdicts("glm5.3"), verdicts("kimi3.1pro")
by_item = {k.split("|", 2)[2]: k for k in P}
sample = [by_item[e["id"]] for e in json.load(open(HERE / "validation" / "human_check_key.json"))]
dis = [k for k in P if glm.get(k) and kimi.get(k) and (glm[k] == "LABEL_OK") != (kimi[k] == "LABEL_OK")]
keys = list(dict.fromkeys(sample + sorted(dis)))
m = []
for i, k in enumerate(keys):
    (OUT / "prompts" / f"{i:03d}.txt").write_text(P[k])
    m.append({"i": i, "cache_key": k, "in_sample": k in sample, "disagree": k in dis, "glm": glm.get(k), "kimi": kimi.get(k)})
json.dump(m, open(OUT / "map.json", "w"), indent=1)
print(f"{len(keys)} prompts: {len(sample)} sample, {len(dis)} GLM/Kimi disagreements, overlap {len(set(sample) & set(dis))}")
