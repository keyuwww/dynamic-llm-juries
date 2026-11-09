"""Step 1 on data that already exists: RB2 Math and JudgeBench judged by the three Qwens (thinking off), split by
whether the judge solved the question itself. Reads the anchoring study's outputs (read-only):

  solves.jsonl + extended.jsonl      the judge's own answer (cut-off answers rerun with the 64K budget)
  matches_glm5.3-flash*.jsonl        GLM-5.3-Flash: does the judge's own answer equal each candidate's?
  inputs/readout_jobs.jsonl.gz       the pool judging transcripts; extended.jsonl replaces cut-off ones
  readouts*.jsonl                    log-prob margin CORRECT-vs-INCORRECT (A-vs-B) at the verdict word (C)

Writes out/existing_rows.jsonl (one row per judged item) for analyze.py.
"""
import collections
import gzip
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANC = HERE.parent / "anchoring_early_answer"
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
from common import parse_pairwise_verdict, parse_verdict  # noqa: E402


def load(p):
    return [json.loads(l) for l in open(p)] if Path(p).exists() else []


def letter(text):
    x = re.findall(r"\b([A-J])\1{4}\b", text or "")
    return x[-1] if x else None


def main():
    out = ANC / "out"
    with gzip.open(ANC / "inputs" / "readout_jobs.jsonl.gz", "rt") as f:
        jobs = {(j["judge"], j["item_id"]): j for j in map(json.loads, f) if j["bench"] != "bbeh"}
    ext = {}
    for p in sorted(out.glob("extended*.jsonl")):
        ext.update({r["cache_key"]: r for r in load(p)})
    solves = {r["cache_key"]: r for r in load(out / "solves.jsonl")}
    for k, r in solves.items():
        if f"solve|{k}" in ext:
            solves[k] = dict(r, answer=ext[f"solve|{k}"]["text"])
    matches = {}
    for p in ("matches_glm5.3-flash.jsonl", "matches_glm5.3-flash_ext.jsonl"):
        matches.update({r["cache_key"]: r["verdict"] for r in load(out / p)})
    margin = {}
    for p in ("readouts.jsonl", "readouts_ext.jsonl"):
        for r in load(out / p):
            if r["ckpt"] == "C":
                margin[(r["judge"], r["item_id"])] = r["margin"]

    # RB2 Math: solved(question) = the judge's own answer equals the chosen (correct) response's answer
    solved_rb2 = {}
    for (judge, iid), j in jobs.items():
        if j["bench"] == "rb2math" and "-chosen" in iid:
            v = matches.get(f"{judge}|{iid}|0")
            if v in ("SAME", "DIFFERENT"):
                solved_rb2[(judge, j["qid"])] = int(v == "SAME")

    rows = []
    for (judge, iid), j in jobs.items():
        text = ext.get(f"judge|{judge}|{iid}", {}).get("text", j["transcript"])
        pairwise = j["pairwise"]
        spoken = (parse_pairwise_verdict if pairwise else parse_verdict)(text)
        m = margin.get((judge, iid))
        gold = int(j["gold"])
        if j["bench"] == "rb2math":
            solved = solved_rb2.get((judge, j["qid"]))
            match = matches.get(f"{judge}|{iid}|0")
            rows.append(dict(bench="rb2math", judge=judge, item=iid, qid=j["qid"], gold=gold, solved=solved,
                             own_matches=None if match not in ("SAME", "DIFFERENT") else int(match == "SAME"),
                             verdict=spoken, score=m))
        else:  # JudgeBench, pairwise: "correct verdict" = picks the better response; score = margin toward it
            own_l = letter(solves.get(f"{judge}|{j['qid']}", {}).get("answer"))
            better = 0 if gold == 1 else 1  # index of the better response
            cl = letter(j["candidates"][better])
            if own_l and cl:
                solved = int(own_l == cl)
            else:
                v = matches.get(f"{judge}|{iid}|{better}")
                solved = None if v not in ("SAME", "DIFFERENT") else int(v == "SAME")
            correct = None if spoken is None else int(spoken == gold)
            rows.append(dict(bench="judgebench", judge=judge, item=iid, qid=j["qid"], gold=1, solved=solved,
                             verdict=correct, score=None if m is None else (m if gold == 1 else -m)))
    (HERE / "out").mkdir(exist_ok=True)
    with open(HERE / "out" / "existing_rows.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    c = collections.Counter((r["bench"], r["judge"], r["solved"]) for r in rows)
    for k in sorted(c, key=str):
        print(k, c[k])


if __name__ == "__main__":
    main()
