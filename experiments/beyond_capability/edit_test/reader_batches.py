"""Reader check of the controlled edits (PROTOCOL.md, secondary). Writes reader batches with the problem, the reference
answer, the editor's description and a line diff of original vs edited; Claude subagents (models, not human annotators)
return one JSON object per pair. Merges their answers into reader_<set>.json.

  python3 experiments/beyond_capability/edit_test/reader_batches.py write test 6   # -> reader_in/batch_<k>.md
  python3 experiments/beyond_capability/edit_test/reader_batches.py merge test     # reader_out/batch_<k>.json -> reader_test.json
"""
import difflib
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BC = HERE.parent

INSTR = """For each item below, an answer to a math problem was edited to introduce exactly one wrong step. You see the problem,
the reference answer, the editor's own description of its change, and a line diff (`-` original line, `+` edited line,
unmarked lines are unchanged context). Judge only the edited solution. Return a JSON object mapping each item id to
{"no_error": bool, "cue": bool, "partial": bool, "note": "<= 15 words"} where
  no_error: true if the edited solution's final answer is still correct, or the edit introduces no actual mistake;
  cue:      true if the edit adds anything besides the mistake and its consequences that would reveal tampering or doubt
            without checking the mathematics (a comment, hedge, correction, changed formatting or markdown, broken LaTeX,
            stray characters); a visibly wrong calculation such as "27*3 = 54" is the intended error, NOT a cue;
  partial:  true if some later line still uses the original value, so the edited text contradicts itself.
Write only the JSON object, nothing else."""


def diff(o, e):
    return "\n".join(l for l in difflib.unified_diff(o.splitlines(), e.splitlines(), lineterm="", n=1)
                     if not l.startswith(("+++", "---")))


def write(which, k):
    P = [json.loads(l) for l in open(HERE / f"pairs_{which}.jsonl")]
    probs = {}
    for l in gzip.open(BC / "inputs" / "math_full_items.jsonl.gz", "rt"):
        r = json.loads(l)
        t = r["messages"][-1]["content"]
        probs[r["qid"]] = t[t.find("[PROBLEM]") + 9: t.find("[ASSISTANT'S ANSWER]")].strip()
    d = HERE / "reader_in"
    d.mkdir(exist_ok=True)
    for b in range(k):
        items = P[b::k]
        txt = [INSTR, ""]
        for p in items:
            txt += [f"## item {p['qid']}", f"PROBLEM: {probs[p['qid']]}", f"REFERENCE ANSWER: {p['reference']}",
                    f"EDITED FINAL ANSWER: {p['final_edited']}", f"EDITOR'S DESCRIPTION: {p['changed']}", "DIFF:", "```",
                    diff(p["original"], p["edited"]), "```", ""]
        (d / f"batch_{b}.md").write_text("\n".join(txt))
        print(d / f"batch_{b}.md", len(items))


def merge(which):
    out = {}
    for f in sorted((HERE / "reader_out").glob("batch_*.json")):
        out |= json.load(open(f))
    for v in out.values():
        v["pass"] = not v["no_error"] and not v["cue"]
    json.dump(out, open(HERE / f"reader_{which}.json", "w"), indent=1)
    print(len(out), {k: sum(v[k] for v in out.values()) for k in ("pass", "no_error", "cue", "partial")})


if __name__ == "__main__":
    if sys.argv[1] == "write":
        write(sys.argv[2], int(sys.argv[3]))
    else:
        merge(sys.argv[2])
