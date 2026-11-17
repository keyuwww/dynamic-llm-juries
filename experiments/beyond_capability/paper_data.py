"""One place for every per-answer score the paper compares, on the same answers.

Per answer: verdict (forced "VERDICT:", unedited), stretch (x4 / x11 / x21 at the rule's layer), direct (position along the
cross-fit correctness direction at that layer), cot (verdict after the judge reasons first, cot_modal.py), gold, src.

  pool_sets()  main answer pools, every stretched judge x benchmark   {(judge, bench): rows}
  sm_sets()    same-model test sets, questions the judge cannot solve {(judge, bench, answerer): rows}
               answerer: "qwen3.5-4b" (sm), "olmo2-7b" (sm2), "qwen3.5-4b strict" (Llama-3.1-8B, failed 9 of 9 tries)
"""
import json
from collections import defaultdict

import numpy as np

import allpairs_analyze as A

J4, J11, J21 = A.J4, A.J11, A.J21
BIG = {"llama3.1-70b"}  # scale check: reported on its own, never pooled with the small judges
SWEEP = {("llama3.1-8b", "math"): "out_math/layer_sweep", ("llama3.2-3b", "mmlu"): "out_mmlu/layer_sweep_llama3.2-3b"}


def _cot(path):
    return {r["aid"]: r["score"] for r in map(json.loads, open(path))} if path.exists() else {}


def _row(r, pc, cot):
    m = r["margins"]
    return dict(aid=r["aid"], qid=r["qid"], gold=r["gold"], src=r["src"], verdict=m["none"], x4=m.get(J4), x11=m[J11],
                x21=m.get(J21), random=m.get(A.R11), direct=pc, cot=cot.get(r["aid"]))


def pool_sets():
    R = json.load(open(A.D / "allpairs.json"))
    out = {}
    for k, o in R.items():
        if k.startswith("extra") or "layer" not in o:
            continue
        j, b = k.split("|")
        _, final = A.load_pair(j, b)
        d = A.HERE / SWEEP[(j, b)] if (j, b) in SWEEP else A.D / f"{j}_{b}"
        P = json.load(open(d / f"direct_{b}.json"))[str(o["layer"])]
        if (j, b) in SWEEP:  # load_pair drops the answer id for sweep pairs
            by = defaultdict(dict)
            for fs in sorted(d.glob(f"sweep_{b}_L*.jsonl")):
                for l in open(fs):
                    r = json.loads(l)
                    if r["layer"] == o["layer"]:
                        m = r["margins"]
                        by[r["aid"]].update({"none": m["none"]} | {f"{r['dir']}:{x}": v for x, v in m.items() if x != "none"})
                        by[r["aid"]]["_m"] = dict(aid=r["aid"], qid=r["qid"], gold=r["gold"], src=r["src"])
            final = [dict(v.pop("_m"), margins=v) for v in by.values()]
        cot = _cot(A.D / f"{j}_{b}" / "cot_main.jsonl")
        sol = A.labels(j, b)
        rows = [dict(_row(r, P[r["aid"]], cot), solved=sol.get(r["qid"])) for r in final if r["aid"] in P]
        out[(j, b)] = dict(rows=rows, layer=o["layer"], status=o["status"], gap=o["gap"])
    return out


def sm_sets():
    out = {}
    for prefix, xprefix, answerer, cotname in (("extra_", "xdirect_", "qwen3.5-4b", "cot_sm.jsonl"),
                                               ("sm2extra_", "sm2xdirect_", "olmo2-7b", "cot_sm2.jsonl")):
        for f in sorted(A.D.glob(f"*/{prefix}*.jsonl")):
            j, b = f.parent.name.rsplit("_", 1)
            raw = [json.loads(l) for l in open(f)]
            xf = f.parent / f"{xprefix}{b}.jsonl"
            if xf.exists():
                X = {r["aid"]: r["proj"] for r in map(json.loads, open(xf))}
            elif raw and "proj" in raw[0]:  # recorded in the same pass (sm2)
                X = {r["aid"]: r["proj"] for r in raw}
            else:
                continue
            cot = _cot(f.parent / cotname)
            rows = [_row(r, X[r["aid"]], cot) for r in raw if r["aid"] in X]
            own = A.labels(j, b)
            if own and not (j == "llama3.1-8b" and b in ("mmlu", "math")):
                rows = [r for r in rows if own.get(r["qid"]) == 0]  # (the 8B's MMLU/MATH sets are its unsolved already)
            out[(j, b, answerer)] = rows
    g8f, mf = A.OUT / "egrades_sm_math_q8.jsonl", A.D / "llama3.1-8b_math" / "extra_math.jsonl"
    if g8f.exists() and (A.D / "llama3.1-8b_math" / "xdirect_math.jsonl").exists():
        k8 = defaultdict(list)
        for r in A.jl(g8f):
            if r["verdict"] is not None:
                k8[r["cache_key"].split("|")[1].split("#")[0]].append(int(r["verdict"]))
        strict = {q for q, v in k8.items() if len(v) >= 6 and sum(v) == 0}
        out[("llama3.1-8b", "math", "qwen3.5-4b strict")] = [r for r in out[("llama3.1-8b", "math", "qwen3.5-4b")]
                                                             if r["qid"] in strict]
    return out


def add_sum(rows, group):
    """verdict + direction, each divided by its within-group spread (no tuning); same for cot + direction."""
    def wsd(key):
        by = defaultdict(list)
        for r in rows:
            if r[key] is not None:
                by[group(r)].append(r[key])
        return np.sqrt(np.mean([np.var(v) for v in by.values() if len(v) > 1]))
    sv, sp = wsd("verdict"), wsd("direct")
    sc = wsd("cot") if any(r["cot"] is not None for r in rows) else None
    for r in rows:
        r["sum"] = r["verdict"] / sv + r["direct"] / sp
        r["cot_sum"] = (r["cot"] / sc + r["direct"] / sp) if (sc and r["cot"] is not None) else None
    return rows
