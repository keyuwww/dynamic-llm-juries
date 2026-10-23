#!/usr/bin/env python3
"""
Judge original and edited BFF answers (inject.py) with the Tinker judges, recording confidence.

For every (judge, text, condition) one request draws --samples verdicts (prefill paid once). Per sample we keep the
full text, the parsed verdict and the top-k log-probs at the verdict token, so three confidence signals are
available later without new calls: vote share, mean P(CORRECT) at the verdict token, and per-sample margin.

Texts: ORIG (unchanged answer) for every item that has at least one passing variant, plus every variant with
ok=True. Conditions: none (no reference) and human (expert reference), same prompt as experiments/tinker_pool.

Raw output (git-ignored, kept for reuse): results/raw/judgments.jsonl
Summary (committed):                      results/pilot_summary.md, results/pilot_summary.json

  python experiments/judge_confidence/judge.py --limit-items 30
  python experiments/judge_confidence/judge.py --analyze
"""
import argparse, asyncio, collections, json, sys

from jc_common import (HERE, RAW, REPO, JsonlCache, call_cost, load_bff_correct, make_chats, run_jobs,
                       sample_with_verdict_probs, select_models)

sys.path.insert(0, str(REPO / "experiments" / "tinker_pool"))
from run_judges import BFF_JUDGE, REF_BLOCK, render_conv  # noqa: E402
from common import parse_verdict  # noqa: E402

JUDGES = "gpt-oss-120b,qwen3.6-35b-a3b,deepseek-v3.1"
CONDS = ("none", "human")
ORDER = ["ORIG", "C2", "C1", "V1", "V2-x10", "V2-10", "V2-lead", "V2-1"]


def texts(limit_items=None):
    """[(text_id, item, vtype, answer_text)] for ORIG + passing variants."""
    items = {it["id"]: it for it in load_bff_correct()}
    var = [json.loads(l) for l in open(RAW / "variants.jsonl")]
    ok = [v for v in var if v.get("ok")]
    item_ids = sorted({v["item_id"] for v in ok})
    if limit_items:
        # keep the generator's order: the first N items it processed
        seen = []
        for v in var:
            if v["item_id"] not in seen:
                seen.append(v["item_id"])
        keep = set(seen[:limit_items])
        item_ids = [i for i in item_ids if i in keep]
    out = []
    for iid in item_ids:
        it = items[iid]
        out.append((f"{iid}|ORIG", it, "ORIG", it["conv"][-1]["content"]))
        for v in ok:
            if v["item_id"] == iid:
                out.append((f"{iid}|{v['vtype']}", it, v["vtype"], v["new"]))
    return out


def build_prompt(it, answer, cond):
    conv = it["conv"][:-1] + [{"role": "assistant", "content": answer}]
    ref = "" if cond == "none" else REF_BLOCK.format(note=" (written by an expert)", ref=it["ref"])
    return BFF_JUDGE.format(conversation=render_conv(conv), reference=ref)


def run(a):
    cache = JsonlCache(RAW / "judgments.jsonl")
    chats = make_chats(select_models(a.judges))
    ts = texts(a.limit_items)
    print(f"{len(ts)} texts x {len(CONDS)} conditions x {len(chats)} judges = {len(ts) * len(CONDS) * len(chats)} "
          f"requests ({a.samples} samples each)", flush=True)

    async def one(jk, chat, tid, it, vtype, answer, cond):
        ck = f"{jk}|{tid}|{cond}"
        if ck in cache:
            return
        prompt = build_prompt(it, answer, cond)
        r = await sample_with_verdict_probs(chat, [{"role": "user", "content": prompt}], n=a.samples,
                                            max_tokens=a.max_tokens, temperature=0.7, topk=5)
        samples = []
        for o in r["outputs"]:
            vt = o["verdict_tok"]
            samples.append(dict(text=o["text"], clean=o["clean"], n_out=o["n_out"], mean_logprob=o["mean_logprob"],
                                verdict=parse_verdict(o["text"]),
                                p_correct=vt["p_correct"] if vt else None,
                                verdict_token=vt["token"] if vt else None,
                                verdict_topk=vt["topk"] if vt else None,
                                verdict_covered_mass=vt["covered_mass"] if vt else None))
        votes = [s["verdict"] for s in samples if s["verdict"] is not None]
        pcs = [s["p_correct"] for s in samples if s["p_correct"] is not None]
        cache.put(dict(cache_key=ck, judge=jk, model=chat.spec["model"], renderer=r["renderer"], text_id=tid,
                       item_id=it["id"], examinee=it["examinee"], vtype=vtype, condition=cond,
                       gold=1 if vtype in ("ORIG", "C1", "C2") else 0, prompt=prompt, samples=samples,
                       vote_share=sum(votes) / len(votes) if votes else None, n_parsed=len(votes),
                       p_correct_mean=sum(pcs) / len(pcs) if pcs else None,
                       sampling=dict(n=a.samples, temperature=0.7, max_tokens=a.max_tokens, topk=5),
                       n_in=r["n_in"], n_out=r["n_out"], latency=r["latency"],
                       cost=call_cost(chat.spec, r["n_in"], r["n_out"])))

    jobs = [lambda jk=jk, c=c, t=t, cond=cond: one(jk, c, *t, cond)
            for jk, c in chats.items() for t in ts for cond in CONDS]
    asyncio.run(run_jobs(jobs, a.concurrency, "judge"))
    analyze()


def analyze():
    rows = [json.loads(l) for l in open(RAW / "judgments.jsonl")]
    cost = sum(r["cost"] for r in rows)
    g = collections.defaultdict(list)
    for r in rows:
        g[(r["judge"], r["condition"], r["vtype"])].append(r)
    res, L = [], ["# Error-injection pilot: verdicts and confidence", "",
                  f"{len(rows)} judge requests, {sum(len(r['samples']) for r in rows)} samples, ${cost:.2f}.", "",
                  "Detection = share of samples with verdict INCORRECT. For ORIG/C1/C2 the answer is still correct, so "
                  "detection there is a false alarm. P(CORRECT) = probability on the verdict word, averaged over "
                  "samples. Confident = all 5 samples agree.", ""]
    for (j, c, v), rs in sorted(g.items(), key=lambda kv: (kv[0][0], kv[0][1], ORDER.index(kv[0][2]))):
        votes = [s["verdict"] for r in rs for s in r["samples"] if s["verdict"] is not None]
        pcs = [s["p_correct"] for r in rs for s in r["samples"] if s["p_correct"] is not None]
        unanimous_miss = sum(1 for r in rs if r["n_parsed"] and r["vote_share"] == 1.0)
        res.append(dict(judge=j, condition=c, vtype=v, n_texts=len(rs),
                        detect=1 - sum(votes) / len(votes) if votes else None,
                        p_correct=sum(pcs) / len(pcs) if pcs else None,
                        p_coverage=len(pcs) / max(1, sum(len(r["samples"]) for r in rs)),
                        all5_say_correct=unanimous_miss / len(rs)))
    L += ["| Judge | Reference | Text | n | Detected (INCORRECT) | Mean P(CORRECT) | All 5 say CORRECT | P read for |",
          "|---|---|---|---|---|---|---|---|"]
    f = lambda x: "n/a" if x is None else f"{x:.2f}"
    for r in res:
        L.append(f"| {r['judge']} | {r['condition']} | {r['vtype']} | {r['n_texts']} | {f(r['detect'])} | "
                 f"{f(r['p_correct'])} | {f(r['all5_say_correct'])} | {r['p_coverage']:.0%} |")
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "pilot_summary.md").write_text("\n".join(L) + "\n")
    (HERE / "results" / "pilot_summary.json").write_text(json.dumps(res, indent=1))
    print("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judges", default=JUDGES)
    ap.add_argument("--limit-items", type=int, default=None)
    ap.add_argument("--samples", type=int, default=5)
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--analyze", action="store_true")
    a = ap.parse_args()
    analyze() if a.analyze else run(a)


if __name__ == "__main__":
    main()
