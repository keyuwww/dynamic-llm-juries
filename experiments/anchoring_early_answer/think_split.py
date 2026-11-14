"""Split the thinking-on Qwen run (tinker_jobs.py --phase think) into one folder per judge, in the format the open-model
pipeline reads, so open_ingest.py / tinker_jobs.py --open / open_analysis.py / probes need no special case:

  out_open/<qwen>-think/generations.jsonl   key, text (starts inside <think>), n_in, n_out, finish
  out_open/<qwen>-think/readouts.jsonl      item_id, ckpt (A, 25, 50, 75, E, C), margin

  python3 experiments/anchoring_early_answer/think_split.py [--pilot]
"""
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    src = HERE / ("out_pilot" if "--pilot" in sys.argv else "out")
    gens, reads = collections.defaultdict(list), collections.defaultdict(list)
    rerun = {}  # cut-off outputs generated again from scratch (tinker_jobs.py --phase think --extended): they replace
    if (src / "think_gen_rerun.jsonl").exists():  # the cut-off text and all its readouts
        rerun = {r["cache_key"]: r for r in map(json.loads, open(src / "think_gen_rerun.jsonl"))}
    rr_reads = collections.defaultdict(list)
    if (src / "think_readouts_rerun.jsonl").exists():
        for r in map(json.loads, open(src / "think_readouts_rerun.jsonl")):
            rr_reads[(r["judge"], r["item_id"])].append(r)
    for r in map(json.loads, open(src / "think_gen.jsonl")):
        r = rerun.get(r["cache_key"], r)
        gens[r["judge"]].append(dict(key=r["key"], text=r["text"], n_in=r["n_in"], n_out=r["n_out"],
                                     finish=r["finish"], budget=r["budget"], model=r["model"]))
    if (src / "think_readouts.jsonl").exists():
        replaced = set(rr_reads)
        for r in map(json.loads, open(src / "think_readouts.jsonl")):
            if (r["judge"], r["item_id"]) in replaced:
                continue
            reads[r["judge"]].append(dict(judge=f"{r['judge']}-think", item_id=r["item_id"], bench=r["bench"],
                                          ckpt=r["ckpt"], margin=r["margin"]))
    for (judge, _), rs in rr_reads.items():
        for r in rs:
            reads[judge].append(dict(judge=f"{judge}-think", item_id=r["item_id"], bench=r["bench"], ckpt=r["ckpt"],
                                     margin=r["margin"]))
    print(f"{len(rerun)} rerun outputs replace cut-off ones")
    for judge, rows in gens.items():
        d = HERE / "out_open" / (f"{judge}-think" + ("_pilot" if "--pilot" in sys.argv else ""))
        d.mkdir(parents=True, exist_ok=True)
        for name, data in (("generations.jsonl", rows), ("readouts.jsonl", reads[judge])):
            with open(d / name, "w") as f:
                for x in data:
                    f.write(json.dumps(x) + "\n")
        cut = sum(x["finish"] != "stop" for x in rows)
        no_close = sum("</think>" not in x["text"] for x in rows)
        print(f"{judge}-think: {len(rows)} outputs ({cut} hit the budget, {no_close} never closed </think>), "
              f"{len(reads[judge])} readouts -> {d}")


if __name__ == "__main__":
    main()
