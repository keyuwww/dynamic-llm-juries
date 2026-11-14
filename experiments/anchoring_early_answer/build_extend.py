"""Find every Qwen output that was cut off by its token limit, so tinker_jobs.py --phase extend can let it
finish (no API calls here).

Cut off =
  solve, BBEH        the pool answer used all 16,384 tokens (tinker_pool/bbeh_results/answers.jsonl)
  solve, RB2/JB      our own solve used all 4,096 tokens or ended unclean (out/solves.jsonl)
  judge transcript   no VERDICT line and the pool call used its whole token budget (the cap of that
                     benchmark's run: 8,192 on BBEH); transcripts that simply forgot the line are left alone

Each job keeps the text written so far ("prefix"); the extend phase continues that same attempt.
Writes inputs/extend_jobs.jsonl.gz.

  python3 experiments/anchoring_early_answer/build_extend.py
"""
import collections
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
POOL = HERE.parent / "tinker_pool"
sys.path.insert(0, str(POOL))
from common import parse_pairwise_verdict, parse_verdict  # noqa: E402

QWENS = ["qwen3.5-4b", "qwen3.5-9b", "qwen3.6-35b-a3b"]


def main():
    jobs = []
    for line in open(POOL / "bbeh_results" / "answers.jsonl"):
        r = json.loads(line)
        if r["model"] in QWENS and r["n_out"] >= 16384:
            jobs.append(dict(kind="solve", bench="bbeh", model=r["model"], qid=r["item"], messages=r["messages"],
                             prefix=r["answer"] or "", used=r["n_out"]))
    solve_msgs = {(j["model"], j["qid"]): j["messages"] for j in map(json.loads, open(HERE / "inputs" / "solve_jobs.jsonl"))}
    for r in map(json.loads, open(HERE / "out" / "solves.jsonl")):
        # RB2/JB solves had a 4,096 cap; BFF solves already get the whole context, so only unclean ones count
        if not r["clean"] or (r["n_out"] >= 4096 and r["bench"] != "bff"):
            jobs.append(dict(kind="solve", bench=r["bench"], model=r["model"], qid=r["qid"],
                             messages=solve_msgs[(r["model"], r["qid"])], prefix=r["answer"] or "", used=r["n_out"]))

    pool_nout = {}
    for bench in ("bbeh", "rb2", "judgebench", "bff"):
        for line in open(POOL / f"{bench}_results" / "judgments.jsonl"):
            r = json.loads(line)
            if r["judge"] in QWENS and r["condition"] == "none":
                pool_nout[(r["judge"], r["item_id"])] = r["n_out"]
    cap = collections.defaultdict(int)
    with gzip.open(HERE / "inputs" / "readout_jobs.jsonl.gz", "rt") as f:
        readout = [json.loads(l) for l in f]
    for j in readout:
        cap[j["bench"]] = max(cap[j["bench"]], pool_nout.get((j["judge"], j["item_id"]), 0))
    for j in readout:
        no_verdict = (parse_pairwise_verdict if j["pairwise"] else parse_verdict)(j["transcript"]) is None
        used = pool_nout.get((j["judge"], j["item_id"]), 0)
        if no_verdict and used >= cap[j["bench"]]:
            jobs.append(dict(kind="judge", bench=j["bench"], model=j["judge"], qid=j["item_id"], messages=j["messages"],
                             prefix=j["transcript"], used=used))

    with gzip.open(HERE / "inputs" / "extend_jobs.jsonl.gz", "wt") as f:
        for j in jobs:
            f.write(json.dumps(j) + "\n")
    c = collections.Counter((j["kind"], j["bench"], j["model"]) for j in jobs)
    print(f"{len(jobs)} cut-off outputs; token caps of the judge runs: {dict(cap)}")
    for k, v in sorted(c.items()):
        print(f"  {k[0]:5s} {k[1]:10s} {k[2]:16s} {v}")


if __name__ == "__main__":
    main()
