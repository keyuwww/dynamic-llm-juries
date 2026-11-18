"""GLM-5.3 audit prompts for the BBEH wrong answers Nemotron-3-Nano believes (>= half of its 5 own answers) that the
earlier audit (Qwen-believed answers, inputs/ask_labelauditbbeh.jsonl.gz) did not cover. Same prompt template, checked
by rebuilding existing prompts exactly. Output: inputs/ask_labelauditbbehnano.jsonl.gz; then
  modal_app.py::run --phase ask --pairs labelauditbbehnano --matcher glm5.3
and append the results to out/ask_glm5.3_labelauditbbeh.jsonl (dir_belief.audited_bad reads that file).
"""
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
BC = HERE.parent / "beyond_capability"
sys.path.insert(0, str(BC))
import dir_belief as db  # noqa: E402
from bc_load import candidates, questions  # noqa: E402

KEY = "nemotron3-nano-30b"
old = {j["cache_key"]: j["prompt"] for j in map(json.loads, gzip.open(HERE / "inputs" / "ask_labelauditbbeh.jsonl.gz", "rt"))}
ex = next(iter(old.values()))
head = ex.split("[QUESTION]\n")[0]
tail = "\n\nDecide whether" + ex.split("\n\nDecide whether")[1]


def prompt(q, target, resp):
    return f"{head}[QUESTION]\n{q}\n\n[OFFICIAL TARGET ANSWER]\n{target}\n\n[AI RESPONSE]\n{resp}{tail}"


Q, C = questions(), candidates()
# check the template on existing prompts
ok = 0
for k, p in list(old.items())[:50]:
    cid = k.split("|", 2)[2]
    c = C[cid]
    q = Q[c["qid"]]
    ok += prompt(q["input"], q["target"], c["answer"]) == p
print(f"template reproduces {ok}/50 existing prompts")
assert ok == 50
belief, thr = db.beliefs(KEY, "bbeh")
new = []
for cid, b in belief.items():
    c = C[cid]
    if int(c["gold"]) == 0 and b >= thr - 1e-9 and f"audit|bbeh|{cid}" not in old:
        q = Q[c["qid"]]
        new.append(dict(cache_key=f"audit|bbeh|{cid}", prompt=prompt(q["input"], q["target"], c["answer"])))
with gzip.open(HERE / "inputs" / "ask_labelauditbbehnano.jsonl.gz", "wt") as f:
    f.write("".join(json.dumps(x) + "\n" for x in new))
believed = sum(1 for cid, b in belief.items() if int(C[cid]["gold"]) == 0 and b >= thr - 1e-9)
print(f"Nano believes {believed} wrong BBEH answers; {believed - len(new)} already audited; {len(new)} new prompts")
