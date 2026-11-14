"""Turn an open model's raw generations (llama_gen_modal.py for Llama, gen_vllm.py for OLMo) into the files the
matcher and the analysis read.

  <dst>/solves.jsonl     its own answer per question, same schema as out/solves.jsonl
                         (cache_key "<key>|<qid>"; clean = finished before the 64K limit)
  <dst>/judgments.jsonl  its judging transcript per candidate + its spoken verdict (1/0/None)

Thinking models: the answer / verdict is read from the text after </think> only (none if the thinking never ended);
the whole text is kept as the transcript for the checkpoint readouts.

Also writes inputs/fill_jobs_<key>.jsonl: what exact parsing cannot settle, for GLM-5.3-Flash
(tinker_jobs.py --phase fill --open <key>). Llama often skips the requested formats ("The assistant's answer is
CORRECT." instead of "VERDICT: CORRECT"; a BBEH answer without "The answer is"), so
  match    BBEH items whose answer has no "The answer is" line: same final answer as the candidate?
  verdict  judging transcripts with no parseable verdict line: which verdict did the judge give?

  python3 experiments/anchoring_early_answer/open_ingest.py                                   # Llama
  python3 experiments/anchoring_early_answer/open_ingest.py --key olmo3-7b-instruct           # OLMo stage
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
from common import parse_pairwise_verdict, parse_verdict  # noqa: E402
sys.path.insert(0, str(HERE))
from analyze import norm  # noqa: E402

LLAMA = "llama3.1-8b"


def paths(key):
    """(generations file, output dir) for a judge key."""
    if key == LLAMA:
        return HERE / "out_llama" / "generations_llama-3.1-8b-instruct.jsonl", HERE / "out_llama"
    return HERE / "out_open" / key / "generations.jsonl", HERE / "out_open" / key


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=LLAMA)
    ap.add_argument("--think", action="store_true", help="thinking model: the generated text starts inside <think>")
    a = ap.parse_args()
    KEY = a.key
    src, dst = paths(KEY)
    vis = (lambda t: t.split("</think>", 1)[1] if "</think>" in t else "") if a.think else (lambda t: t)
    solves, judg = [], []
    for r in map(json.loads, open(src)):
        kind, bench, ident = r["key"].split("|", 2)
        if kind == "solve":
            solves.append(dict(cache_key=f"{KEY}|{ident}", model=KEY, qid=ident, bench=bench, answer=vis(r["text"]),
                               n_out=r["n_out"], clean=r["finish"] == "stop"))
        else:
            v = (parse_pairwise_verdict if bench == "judgebench" else parse_verdict)(vis(r["text"]))
            judg.append(dict(judge=KEY, item_id=ident, bench=bench, transcript=r["text"], spoken=v,
                             visible=vis(r["text"]), n_out=r["n_out"], finish=r["finish"]))
    for name, rows in (("solves.jsonl", solves), ("judgments.jsonl", judg)):
        with open(dst / name, "w") as f:
            for x in rows:
                f.write(json.dumps(x) + "\n")
    # jobs for GLM: what the exact parsers cannot settle
    with gzip.open(HERE / "inputs" / "readout_jobs.jsonl.gz", "rt") as f:
        jobs = {j["item_id"]: j for j in map(json.loads, f) if j["judge"] == "qwen3.5-4b"}
    pool = {}
    for line in open(HERE.parent / "tinker_pool" / "bbeh_results" / "answers.jsonl"):
        r = json.loads(line)
        pool[(r["model"], r["item"])] = norm(r["answer"])
    own = {s["qid"]: s["answer"] for s in solves if s["bench"] == "bbeh"}
    fill = []
    for iid, j in jobs.items():
        if j["bench"] != "bbeh":
            continue
        q, exam = iid.split("|")
        if q in own and norm(own[q]) is None and pool.get((exam, q)) is not None:
            # BBEH judge prompts show only the candidate's extracted final answer, after the question
            body = j["messages"][-1]["content"]
            question, cand = body.split("[ASSISTANT'S ANSWER]")
            cand = cand.split("Is the assistant's final answer correct?")[0].strip()
            fill.append(dict(kind="match", key=f"{KEY}|{iid}|0", question=question, own=own[q], cand=cand))
    for x in judg:
        if x["spoken"] is None:
            if x["visible"].strip():  # a thinking model that never closed its thinking gave no verdict
                fill.append(dict(kind="verdict", key=f"{KEY}|{x['item_id']}", pairwise=x["bench"] == "judgebench",
                                 transcript=x["visible"]))
    with open(HERE / "inputs" / f"fill_jobs_{KEY}.jsonl", "w") as f:
        for x in fill:
            f.write(json.dumps(x) + "\n")
    print(f"GLM fill jobs: {sum(x['kind'] == 'match' for x in fill)} BBEH matches, "
          f"{sum(x['kind'] == 'verdict' for x in fill)} verdicts")
    fin = sum(s["clean"] for s in solves)
    parsed = sum(j["spoken"] is not None for j in judg)
    print(f"{len(solves)} solves ({fin} finished), {len(judg)} judgments ({parsed} with a verdict)")


if __name__ == "__main__":
    main()
