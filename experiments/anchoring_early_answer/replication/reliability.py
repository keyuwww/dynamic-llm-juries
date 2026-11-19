"""Belief re-measurement on the ORIGINAL JudgeBench questions (Nov 18; protocol at the bottom of PROTOCOL.md).

Each original judge that Tinker still serves answers every JudgeBench question 7 more times with exactly the original
own-answer prompt (inputs/solve_jobs*.jsonl), thinking off, T = 0.7, whole remaining context. Letters are compared
exactly, so no matcher is needed. Nemotron-3-Nano is retired on Tinker and is not re-measured.
  python reliability.py --phase collect --cap 100
  python reliability.py --phase analyze           (CPU; uses the paper's audited rows)
"""
import argparse
import asyncio
import collections
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
JUDGES = {"qwen3.5-4b": "", "qwen3.5-9b": "", "qwen3.6-35b-a3b": "", "nemotron3-super-120b": "_nemotron",
          "deepseek-v4.1-flash": "_deepseek", "kimi-k2.6": "_kimi"}


def collect(cap, concurrency):
    import mmlupro as M
    from common import JsonlCache, load_env, run_jobs
    load_env()
    M.PRICES["qwen3.5-4b"] = M.POOL_BY_KEY["qwen3.5-4b"]
    M.PRICES["nemotron3-super-120b"] = M.POOL_BY_KEY["nemotron3-super-120b"]
    cache = JsonlCache(M.DATA / "resolve.jsonl")
    budget = M.Budget(cap, [cache])
    print(f"spent so far ${budget.spent:.2f} of cap ${cap}", flush=True)
    jobs = []
    for j, sfx in JUDGES.items():
        for s in map(json.loads, open(ROOT / "inputs" / f"solve_jobs{sfx}.jsonl")):
            if s["model"] == j and s["bench"] == "judgebench":
                jobs.append(s)
    chats = {j: M.make_chat(M.PRICES[j]) for j in JUDGES}

    async def one(s):
        k = f"resolve|{s['model']}|{s['qid']}"
        if k in cache:
            return
        outs, n_in, n_out, cost = await M.sample(chats[s["model"]], budget, s["messages"], M.CTX, 0.7, 7)
        cache.put(dict(cache_key=k, model=s["model"], qid=s["qid"], letters=[M.letter(o["text"]) for o in outs],
                       texts=[o["text"] for o in outs], clean=[o["clean"] for o in outs], n_in=n_in, n_out=n_out, cost=cost))
    asyncio.run(run_jobs([lambda s=s: one(s) for s in jobs], concurrency, "resolve"))


def analyze():
    import numpy as np
    sys.path.insert(0, str(ROOT / "validation"))
    import paper_numbers as P
    from sample_budget import letter
    new = {}
    for l in open(HERE / "data" / "resolve.jsonl"):
        r = json.loads(l)
        new[(r["model"], r["qid"])] = r["letters"]
    R = []
    for fam, od, sfx in P.FAM:
        if fam == "Nemotron-3-Nano":
            continue
        jobs = {(j["judge"], j["item_id"]): j for j in map(json.loads, gzip.open(ROOT / "inputs" / f"readout_jobs{sfx}.jsonl.gz", "rt"))}
        raw = {(r["judge"], r["item"]): r for r in json.load(open(ROOT / od / "belief_rows_clean.json"))}
        for r in P.load(od, sfx):
            if r["bench"] != "judgebench" or r["ok"] or not r["audited"]:
                continue
            j = jobs[(r["judge"], r["item"])]
            gold = int(j["gold"])
            ti = 0 if ((gold == 1) if raw[(r["judge"], r["item"])]["target_ok"] else (gold == 0)) else 1
            cl = letter(j["candidates"][ti])
            L = [x for x in new.get((r["judge"], j["qid"]), []) if x]
            if cl is None or len(L) < 5:
                continue
            nb = sum(x == cl for x in L) / len(L)
            R.append(dict(r, belief_old=r["belief"], belief_new=nb, belief_avg=(r["belief"] + nb) / 2, b_new=P.binof(nb)))
    out = dict(n=len(R), questions=len({r["qid"] for r in R}))
    old, nw = np.array([r["belief_old"] for r in R]), np.array([r["belief_new"] for r in R])
    out["corr_old_new"] = float(np.corrcoef(old, nw)[0, 1])
    out["bin_agreement"] = float(np.mean([r["b"] == r["b_new"] for r in R]))
    out["transition"] = {b: dict(collections.Counter(r["b_new"] for r in R if r["b"] == b)) for b in P.BINS}
    JFE = [lambda r: f"{r['bench']}|{r['judge']}"]
    for k in ("belief_old", "belief_new", "belief_avg"):
        e, lo, hi = P.boot(R, lambda X, k=k: P.ols([dict(x, belief=x[k]) for x in X], "y", ["belief"], JFE))
        out[f"slope_{k}"] = [float(e[0]), float(lo[0]), float(hi[0])]
    stair_new = [float(np.mean([r["y"] for r in R if r["b_new"] == b])) if any(r["b_new"] == b for r in R) else None for b in P.BINS]
    out["staircase_new"], out["counts_new"] = stair_new, {b: sum(r["b_new"] == b for r in R) for b in P.BINS}
    out["staircase_old"] = [float(np.mean([r["y"] for r in R if r["b"] == b])) for b in P.BINS]
    (HERE / "reliability_results.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["collect", "analyze"], required=True)
    ap.add_argument("--cap", type=float, default=100.0)
    ap.add_argument("--concurrency", type=int, default=48)
    a = ap.parse_args()
    collect(a.cap, a.concurrency) if a.phase == "collect" else analyze()
