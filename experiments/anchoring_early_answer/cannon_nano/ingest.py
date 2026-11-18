"""Bring Nemotron-3-Nano's Cannon generations (cannon_nano/out/generations_*.jsonl) into both pipelines (Nov 17).

  out_open/nemotron3-nano-30b/solves.jsonl     first own answer per main-set question (tinker_jobs format)
  out_open/nemotron3-nano-30b/solves_k.jsonl   7 more own answers (belief)
      -> then on Modal: tinker_jobs.py --phase match / belief --open nemotron3-nano-30b --set nano (GLM matching only)
  out_nano/readouts.jsonl                      the pool verdict (Tinker transcript from when Nano was still served),
                                               written as a checkpoint-C "readout" with margin +/-5 so analyze.py /
                                               belief.py run unchanged: for Nano acc_C IS the spoken verdict
  ../beyond_capability/out/solves_nemotron3-nano-30b.jsonl   5 own BBEH answers per question (dir_belief.py)

  python3 experiments/anchoring_early_answer/cannon_nano/ingest.py
"""
import collections
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANC = HERE.parent
KEY = "nemotron3-nano-30b"
sys.path.insert(0, str(ANC.parent / "tinker_pool"))
from common import parse_pairwise_verdict, parse_verdict  # noqa: E402


def main():
    gen = {}
    for p in sorted((HERE / "out").glob("generations_*.jsonl")):
        for r in map(json.loads, open(p)):
            gen[r["key"]] = r
    print(len(gen), "generations")
    od = ANC / "out_open" / KEY
    od.mkdir(parents=True, exist_ok=True)
    s0, sk, bb = [], [], collections.defaultdict(list)
    cut = collections.Counter()
    for k, r in gen.items():
        clean = r["finish"] == "stop"
        cut[(r["bench"], clean)] += 1
        base = dict(model=KEY, qid=r["qid"], bench=r["bench"], answer=r["text"], n_out=r["n_out"], clean=clean,
                    termination="stop_sequence" if clean else "length")
        if k.startswith("solve|"):
            s0.append(dict(cache_key=f"{KEY}|{r['qid']}", **base))
        elif k.startswith("solve_k|"):
            sk.append(dict(cache_key=f"{KEY}|{r['qid']}|s{r['sample']}", sample=r["sample"], **base))
        elif k.startswith("bbeh|"):
            bb[r["qid"]].append((r["sample"], dict(text=r["text"], n_think=0, n_out=r["n_out"], clean=clean, tries=1),
                                 r["n_in"]))
    for name, rows in (("solves.jsonl", s0), ("solves_k.jsonl", sk)):
        with open(od / name, "w") as f:
            f.write("".join(json.dumps(x) + "\n" for x in rows))
    with open(ANC.parent / "beyond_capability" / "out" / f"solves_{KEY}.jsonl", "w") as f:
        for qid, xs in bb.items():
            xs.sort(key=lambda t: t[0])
            f.write(json.dumps(dict(cache_key=f"{KEY}|{qid}", model=KEY, qid=qid, samples=[x[1] for x in xs],
                                    n_in=xs[0][2], budget=65536 - xs[0][2] - 16)) + "\n")
    print(f"solves {len(s0)}, solves_k {len(sk)}, bbeh questions {len(bb)}; finished vs cut by bench: {dict(cut)}")

    # pool verdicts -> checkpoint-C readouts
    on = ANC / "out_nano"
    on.mkdir(exist_ok=True)
    n, miss = 0, 0
    with gzip.open(ANC / "inputs" / "readout_jobs_nano.jsonl.gz", "rt") as f, open(on / "readouts.jsonl", "w") as g:
        for j in map(json.loads, f):
            if j["judge"] != KEY or j["bench"] == "bbeh":
                continue
            v = (parse_pairwise_verdict if j["pairwise"] else parse_verdict)(j["transcript"])
            if v is None:
                miss += 1
                continue
            g.write(json.dumps(dict(cache_key=f"{KEY}|{j['item_id']}|C", judge=KEY, bench=j["bench"],
                                    item_id=j["item_id"], ckpt="C", margin=5.0 if v == 1 else -5.0,
                                    n_prompt=j.get("pool_n_in"), pool_n_in=j.get("pool_n_in"), n_prefix=None,
                                    note="spoken pool verdict")) + "\n")
            n += 1
    print(f"verdict readouts {n}, unparsed verdicts {miss}")
    for name in ("solves.jsonl", "solves_k.jsonl"):  # analyze.py / belief.py read them from the set's folder too
        (on / name).write_text((od / name).read_text())


if __name__ == "__main__":
    main()
