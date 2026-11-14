"""Rows for Llama-3.1-8B's belief analysis (belief.py --judge=llama3.1-8b), after:
  cannon_belief/capture_llama.sh   -> cannon_belief/out/llama3.1-8b/meta_ckpt.jsonl (verdict margin per checkpoint)
  llama_belief_prep.py + open_ingest.py + tinker_jobs.py --phase fill / match / belief --open llama3.1-8b

Verdict margins: RB2 Math + BFF from the Cannon capture (A, 25, 50, 75, C); JudgeBench keeps the position-A readout
from the Nov 8 Modal run (out_probe/llama3.1-8b). Both are written to out_llama/readouts.jsonl, which
open_analysis.build_rows reads. acc_C here = Llama's SPOKEN verdict (exact parse, else GLM); the readout at C is
kept as acc_Cr.

  python3 experiments/anchoring_early_answer/llama_belief_rows.py
"""
import collections
import json
from pathlib import Path

from analyze import MAIN
from open_analysis import build_rows
from open_ingest import LLAMA

HERE = Path(__file__).resolve().parent


def main():
    cap = [json.loads(l) for l in open(HERE / "cannon_belief" / "out" / LLAMA / "meta_ckpt.jsonl")]
    have = {m["item_id"] for m in cap}
    rr = [dict(item_id=m["item_id"], ckpt=m["ckpt"], margin=m["margin"]) for m in cap if "margin" in m]
    for m in map(json.loads, open(HERE / "out_probe" / LLAMA / "meta.jsonl")):
        if m["item_id"] not in have:
            rr.append(dict(item_id=m["item_id"], ckpt="A", margin=m["margin"]))
    with open(HERE / "out_llama" / "readouts.jsonl", "w") as f:
        f.write("".join(json.dumps(r) + "\n" for r in rr))
    margin = collections.defaultdict(dict)
    for r in rr:
        margin[r["item_id"]][r["ckpt"]] = r["margin"]
    rows, *_ = build_rows(LLAMA)
    out = []
    for r in rows:
        if r["bench"] not in MAIN:
            continue
        r = dict(r, acc_Cr=r["acc_C"], acc_C=r["acc_S"])
        if r["bench"] != "judgebench":
            for ck in ("A", "25", "50", "75", "C"):
                r[f"m_{ck}"] = margin[r["item"]].get(ck)
        out.append(r)
    json.dump(out, open(HERE / "out_llama" / "belief_base_rows.json", "w"))
    print(len(out), "rows", dict(collections.Counter((r["bench"], r["group"]) for r in out)))


if __name__ == "__main__":
    main()
