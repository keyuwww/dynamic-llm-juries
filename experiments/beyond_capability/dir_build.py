"""Inputs for the solve-vs-judge direction study (no API calls). The SAME answer text is shown to the model in
different roles, so any difference in its internal "this is right" signal comes from the role, not the content.

Modes (one row per answer x mode; the hidden state is taken at the last token):
  J  judge:      [user: "grade this answer" prompt (no reference)] + "VERDICT:"      (someone else's answer)
  G  generate:   [user: the question] [assistant: the answer ...]                    (as if the model wrote it)
  S  self-check: [user: question] [assistant: answer] [user: "is your answer correct?"] + "VERDICT:"
  P  pre-solve:  [user: the question] at the start of the assistant turn (one row per question; "will I solve it")

Benchmarks: BBEH (the 2,244 pool candidates) and RB2 Math (the anchoring study's 732 responses).
Qwen3.5-9B also gets its own 5 thinking-off BBEH answers per question (from bc_jobs solve) in modes G and S.

  python3 experiments/beyond_capability/dir_build.py
"""
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANC = HERE.parent / "anchoring_early_answer"
sys.path.insert(0, str(HERE))
from bc_common import BBEH_SUFFIX, judge_prompt  # noqa: E402
from bc_load import OUT, candidates, jl, questions  # noqa: E402

SELF_CHECK = ("Is your final answer above correct? Check it, then end with exactly one line: "
              "\"VERDICT: CORRECT\" or \"VERDICT: INCORRECT\".")


def rows_for(bench, qid, aid, question_msg, judge_msg, answer, gold, src):
    base = dict(bench=bench, qid=qid, aid=aid, gold=gold, src=src)
    return [
        dict(base, mode="J", messages=[{"role": "user", "content": judge_msg}], suffix="VERDICT:"),
        dict(base, mode="G", messages=[{"role": "user", "content": question_msg}], suffix=answer.rstrip()),
        dict(base, mode="S", messages=[{"role": "user", "content": question_msg}, {"role": "assistant", "content": answer.rstrip()},
                                       {"role": "user", "content": SELF_CHECK}], suffix="VERDICT:"),
    ]


def main():
    qs, C = questions(), candidates()
    rows = []
    for c in C.values():
        q = qs[c["qid"]]
        rows += rows_for("bbeh", c["qid"], c["cid"], q["input"] + BBEH_SUFFIX, judge_prompt("none", q["input"], c["answer"]),
                         c["answer"], c["gold"], c["examinee"])
    with gzip.open(ANC / "inputs" / "readout_jobs.jsonl.gz", "rt") as f:
        rb = [j for j in map(json.loads, f) if j["judge"] == "qwen3.5-9b" and j["bench"] == "rb2math"]
    for j in rb:
        rows += rows_for("rb2math", j["qid"], j["item_id"], j["question"], j["messages"][0]["content"],
                         j["candidates"][0], int(j["gold"]), "rb2")
    seen = set()
    for r in list(rows):
        if r["qid"] not in seen:
            seen.add(r["qid"])
            qmsg = r["messages"][0]["content"] if r["mode"] == "G" else None
            if qmsg is None:
                qmsg = next(x["messages"][0]["content"] for x in rows if x["qid"] == r["qid"] and x["mode"] == "G")
            rows.append(dict(bench=r["bench"], qid=r["qid"], aid=f"{r['qid']}|pre", gold=-1, src="-", mode="P",
                             messages=[{"role": "user", "content": qmsg}], suffix=""))
    # Qwen3.5-9B's own thinking-off answers (5 per BBEH question): generation + self-check modes only
    own = []
    import sys as _s
    _s.path.insert(0, str(HERE.parent / "tinker_pool"))
    from data import bbeh_correct
    from bc_common import has_final
    for r in jl(OUT / "solves_qwen3.5-9b.jsonl"):
        q = qs[r["qid"]]
        for i, s in enumerate(r["samples"]):
            if not has_final(s["text"]):
                continue
            g = int(bbeh_correct(s["text"], q["target"]))
            for x in rows_for("bbeh", r["qid"], f"{r['qid']}|own{i}", q["input"] + BBEH_SUFFIX, "", s["text"], g, "own"):
                if x["mode"] != "J":
                    own.append(x)
    (HERE / "inputs").mkdir(exist_ok=True)
    with gzip.open(HERE / "inputs" / "dir_items.jsonl.gz", "wt") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    with gzip.open(HERE / "inputs" / "dir_items_own_qwen3.5-9b.jsonl.gz", "wt") as f:
        for r in own:
            f.write(json.dumps(r) + "\n")
    import collections
    print(collections.Counter((r["bench"], r["mode"]) for r in rows), len(own))


if __name__ == "__main__":
    main()
