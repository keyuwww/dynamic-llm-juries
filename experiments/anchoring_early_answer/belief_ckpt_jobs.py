"""Inputs for capturing the Qwen judges' hidden states at every early-answering checkpoint (A, 25, 50, 75, C) of their
own thinking-off pool transcripts, RB2 Math + BFF. Cut-off transcripts use the from-scratch reruns (extended_judge).

  python3 experiments/anchoring_early_answer/belief_ckpt_jobs.py   -> cannon_belief/ckpt_jobs.jsonl.gz
"""
import gzip
import json
from pathlib import Path

from ckpts import checkpoints

HERE = Path(__file__).resolve().parent
ext = {}
for f in sorted((HERE / "out").glob("extended*.jsonl")):
    ext.update({r["cache_key"]: r["text"] for r in map(json.loads, open(f))})
n = 0
with gzip.open(HERE / "inputs" / "readout_jobs.jsonl.gz", "rt") as f, \
        gzip.open(HERE / "cannon_belief" / "ckpt_jobs.jsonl.gz", "wt") as out:
    for j in map(json.loads, f):
        if j["judge"] not in ("qwen3.5-4b", "qwen3.5-9b") or j["bench"] not in ("rb2math", "bff"):
            continue
        tr = ext.get(f"judge|{j['judge']}|{j['item_id']}", j["transcript"])
        cks = [(name, prefix) for name, prefix, _ in checkpoints(tr, j["pairwise"])]
        out.write(json.dumps(dict(judge=j["judge"], item_id=j["item_id"], bench=j["bench"], messages=j["messages"],
                                  ckpts=cks)) + "\n")
        n += 1
print(n, "judgments")
