"""GLM-5.3 label audit of every wrong-labelled BFF / JudgeBench answer in the belief rows, at every belief level (Nov 16).
Claude audited the 7/7 ones by hand-style reading (label_audit_7of7*.{jsonl,md}); this runs one rule on all levels so
the cleaned staircase is not biased toward the top bin. Output: inputs/ask_labelaudit.jsonl.gz (cache_key, prompt);
run with  modal_app.py::run --phase ask --pairs labelaudit --matcher glm5.3
"""
import gzip, json
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]

BFF = """You are auditing a benchmark label. A finance/accounting conversation, an AI assistant's final response, and the
benchmark's expert reference answer are given. The benchmark labels the assistant's response WRONG.

{prompt}

[EXPERT REFERENCE ANSWER]
{ref}
[END OF EXPERT REFERENCE ANSWER]

Work the problem yourself carefully from the question's own numbers (do the arithmetic). The reference itself may
contain errors (for example a number copied wrongly from the question). Then decide whether the label WRONG is right:
- LABEL_OK: the assistant's final answer or conclusion is substantively wrong.
- LABEL_WRONG: the assistant's final answer or conclusion is actually correct (or equivalent to a correct answer).
- CONTESTED: reasonable experts could disagree (a different but defensible method or assumption, an ambiguous
  question, or only a rounding/presentation difference).
End with exactly one line: "AUDIT: LABEL_OK", "AUDIT: LABEL_WRONG" or "AUDIT: CONTESTED"."""

JB = """You are auditing a benchmark label. A question and two AI responses are given. The benchmark says Response {good}
is the correct one (its final answer is the dataset's gold answer) and Response {bad} is wrong.

{prompt}

Solve the question yourself carefully. Then decide whether Response {bad}'s final answer is really wrong:
- LABEL_OK: Response {bad}'s final answer is wrong and the gold answer is right.
- LABEL_WRONG: Response {bad}'s final answer is actually correct (the gold is wrong, or both are correct).
- CONTESTED: the question is ambiguous or more than one option is defensible.
End with exactly one line: "AUDIT: LABEL_OK", "AUDIT: LABEL_WRONG" or "AUDIT: CONTESTED"."""

# job sets: the Qwens, plus any other judge whose belief rows exist (Nemotron, DeepSeek); same items share one audit
SETS = [("", "out"), ("_nemotron", "out_nemotron"), ("_deepseek", "out_deepseek")]
jobs, rows = {}, []
for sfx, od in SETS:
    if not (HERE / od / "belief_rows_clean.json").exists():
        continue
    jobs.update({(j["judge"], j["item_id"]): j for j in map(json.loads, gzip.open(HERE / "inputs" / f"readout_jobs{sfx}.jsonl.gz", "rt"))})
    rows += json.load(open(HERE / od / "belief_rows_clean.json"))
refs = {it["id"]: it["ref"] for it in map(json.loads, open(HERE.parent / "beyond_capability" / "inputs" / "bff_items.jsonl"))}
seen, out = set(), []
for r in rows:
    if r["bench"] not in ("bff", "judgebench") or int(r["target_ok"]) != 0 or r["item"] in seen:
        continue
    seen.add(r["item"])
    j = jobs[(r["judge"], r["item"])]
    p = j["messages"][0]["content"]
    if r["bench"] == "bff":
        if not refs.get(r["item"]):
            continue
        prompt = BFF.format(prompt=p, ref=refs[r["item"]])
    else:
        g = int(j["gold"])
        prompt = JB.format(prompt=p, good="A" if g == 1 else "B", bad="B" if g == 1 else "A")
    out.append(dict(cache_key=f"audit|{r['bench']}|{r['item']}", prompt=prompt))
with gzip.open(HERE / "inputs" / "ask_labelaudit.jsonl.gz", "wt") as f:
    f.write("".join(json.dumps(x) + "\n" for x in out))
print(len(out), sum(x["cache_key"].startswith("audit|bff") for x in out))
