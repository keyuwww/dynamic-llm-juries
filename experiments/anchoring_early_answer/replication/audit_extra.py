"""Complete the replication's label audit (Nov 20 review: the first audit covered only wrong responses some judge
believes >= 4/7 under the strict parser, so the audit-filtered result was selective).

Audits, with the same auditor (Kimi-K3.1-Pro, high reasoning), prompt and settings as `mmlupro.py --phase audit`,
every remaining wrong response in the confirmatory range (questions 80..6079):
  lenient_high   believed >= 4/7 by some judge only under the post-hoc lenient parser
  low            every other wrong response (no judge believes it >= 4/7 under either parser, or no judge has
                 five parsed own answers); audited in full, so no sampling weights are needed
After this, every one of the 1,336 wrong responses has an audit verdict (data/audit.jsonl + data/audit_extra.jsonl).

  python audit_extra.py --cap 460      (cap = total replication spend incl. all earlier caches, in dollars)
"""
import argparse
import asyncio
import json
import re

import importlib.util
from pathlib import Path

import mmlupro as M

_spec = importlib.util.spec_from_file_location("rep_analyze", Path(__file__).resolve().parent / "analyze.py")
_A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_A)  # this folder's analyze.py (mmlupro puts tinker_pool, which has its own, first on sys.path)
JUDGES, lenient_letter = _A.JUDGES, _A.lenient_letter


def max_bin(p, S, lenient):
    m = None
    for j in JUDGES:
        s = S.get(f"solve|{j}|{p['qid']}")
        if not s:
            continue
        L = [lenient_letter(t) for t in s["texts"]] if lenient else s["letters"]
        L = [x for x in L[1:] if x]
        if len(L) < 5:
            continue
        b = round(7 * sum(x == p["wrong_letter"] for x in L) / len(L))
        m = b if m is None else max(m, b)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=float, required=True)
    ap.add_argument("--concurrency", type=int, default=24)
    a = ap.parse_args()
    M.load_env()
    caches = {n: M.JsonlCache(M.DATA / f"{n}.jsonl") for n in ["gen", "judge", "solve", "audit", "audit_extra"]}
    budget = M.Budget(a.cap, caches.values())
    print(f"spent so far ${budget.spent:.2f} of cap ${a.cap}", flush=True)
    pairs = [p for p in M.load_jsonl(M.DATA / "pairs.jsonl") if 80 <= p["order"] < 6080]
    S, done = caches["solve"].rows, {r["qid"] for r in caches["audit"].rows.values()}
    todo = []
    for p in pairs:
        if p["qid"] in done:
            continue
        hi = max_bin(p, S, True)
        todo.append((p, "lenient_high" if (hi or 0) >= 4 else "low"))
    print({s: sum(t[1] == s for t in todo) for s in ("lenient_high", "low")}, flush=True)
    chat, cache = M.make_chat(M.AUDITOR, "kimi_k31_pro_high_reasoning"), caches["audit_extra"]

    async def one(p, stratum):
        k = f"audit|{p['qid']}"
        if k in cache:
            return
        good = "B" if p["wrong_pos"] == "A" else "A"
        body = f"[QUESTION]\n{p['question']}\n\n[RESPONSE A]\n{p['response_a']}\n\n[RESPONSE B]\n{p['response_b']}"
        msg = M.AUDIT_PROMPT.format(good=good, bad=p["wrong_pos"], prompt=body)
        outs, n_in, n_out, cost = await M.sample(chat, budget, [{"role": "user", "content": msg}], 32768, 0.0, 1)
        m = re.findall(r"AUDIT:\s*\**\s*(LABEL_OK|LABEL_WRONG|CONTESTED)", outs[0]["text"] or "")
        cache.put(dict(cache_key=k, model="kimi3.1pro", qid=p["qid"], stratum=stratum, text=outs[0]["text"],
                       verdict=m[-1] if m else None, n_in=n_in, n_out=n_out, cost=cost))
    asyncio.run(M.run_jobs([lambda p=p, s=s: one(p, s) for p, s in todo], a.concurrency, "audit_extra"))
    print("total billed (replication caches + timeouts)", round(M.Budget(1e9, caches.values()).spent, 2))


if __name__ == "__main__":
    main()
