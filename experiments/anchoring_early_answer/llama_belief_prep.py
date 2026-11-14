"""Bring Llama-3.1-8B's belief generations (cannon_belief/llama_gen.py, pulled to cannon_belief/out_llama/) into the
pipeline:

  out_llama/generations_llama-3.1-8b-instruct.jsonl   + Llama's first own answer and judging transcripts on BFF
                                                         (then rerun open_ingest.py: solves / judgments / fill jobs)
  out_llama/solves_k.jsonl                             the 7 extra own answers per question, in tinker_jobs' belief
                                                         format (then tinker_jobs.py --phase belief --open llama3.1-8b)
  cannon_belief/ckpt_jobs_llama.jsonl.gz               checkpoints A / 25 / 50 / 75 / C of Llama's RB2 Math + BFF
                                                         transcripts, with the two verdict options to score (capture.py)

Llama often writes no "VERDICT:" line, so C is then the end of its transcript followed by "\\n\\nVERDICT:".

  python3 experiments/anchoring_early_answer/llama_belief_prep.py
"""
import gzip
import json
from pathlib import Path

from ckpts import checkpoints

HERE = Path(__file__).resolve().parent
KEY = "llama3.1-8b"
SRC = HERE / "cannon_belief" / "out_llama"
GEN = HERE / "out_llama" / "generations_llama-3.1-8b-instruct.jsonl"


def main():
    new = {}
    for p in sorted(SRC.glob("generations_*.jsonl")):
        for r in map(json.loads, open(p)):
            new[r["key"]] = r
    print(len(new), "new generations")
    have = {json.loads(l)["key"] for l in open(GEN)}
    add = [r for k, r in new.items() if not k.startswith("solve_k|") and k not in have]
    with open(GEN, "a") as f:
        f.write("".join(json.dumps(r) + "\n" for r in add))
    print(f"appended {len(add)} BFF answers / judgments to {GEN.name}")
    sk = []
    for k, r in new.items():
        if k.startswith("solve_k|"):
            _, bench, qid, s = k.split("|")
            sk.append(dict(cache_key=f"{KEY}|{qid}|{s}", model=KEY, qid=qid, bench=bench, sample=int(s[1:]),
                           answer=r["text"], n_out=r["n_out"], clean=r["finish"] == "stop",
                           termination="stop_sequence" if r["finish"] == "stop" else r["finish"]))
    with open(HERE / "out_llama" / "solves_k.jsonl", "w") as f:
        f.write("".join(json.dumps(x) + "\n" for x in sk))
    print(f"{len(sk)} extra own answers ({sum(x['clean'] for x in sk)} finished)")

    with gzip.open(HERE / "inputs" / "readout_jobs.jsonl.gz", "rt") as f:
        jobs = {j["item_id"]: j for j in map(json.loads, f) if j["judge"] == "qwen3.5-4b"}
    gens = {}
    for r in map(json.loads, open(GEN)):
        kind, bench, ident = r["key"].split("|", 2)
        if kind == "judge" and bench in ("rb2math", "bff"):
            gens[ident] = r
    n = no_c = 0
    with gzip.open(HERE / "cannon_belief" / "ckpt_jobs_llama.jsonl.gz", "wt") as out:
        for iid, r in sorted(gens.items()):
            j = jobs[iid]
            cks = [list(c) for c in checkpoints(r["text"], False)]
            if not any(c[0] == "C" for c in cks):
                cks.append(["C", r["text"].rstrip() + "\n\nVERDICT:", [" CORRECT", " INCORRECT"]])
                no_c += 1
            out.write(json.dumps(dict(judge=KEY, item_id=iid, bench=j["bench"], messages=j["messages"],
                                      ckpts=cks)) + "\n")
            n += 1
    print(f"{n} judgments for capture ({no_c} without a VERDICT line: C = end of transcript)")


if __name__ == "__main__":
    main()
