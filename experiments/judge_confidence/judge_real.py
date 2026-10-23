#!/usr/bin/env python3
"""
Step 1.1: judge every real BFF answer (all 960, incl. the human-split ones) with the same confidence recording as
judge.py, so real errors can be compared with injected ones.

Raw output (git-ignored, kept for reuse): results/raw/judgments_real.jsonl, same fields as judgments.jsonl plus the
annotator labels (labels, n_correct, n_incorrect, gold_unanimous, gold_majority).

  python experiments/judge_confidence/judge_real.py --conds none
  python experiments/judge_confidence/judge_real.py --analyze
"""
import argparse, asyncio, collections, json

from jc_common import (HERE, RAW, JsonlCache, call_cost, load_bff_all, make_chats, run_jobs,
                       sample_with_verdict_probs, select_models)
from judge import JUDGES, build_prompt, parse_verdict


def run(a):
    cache = JsonlCache(RAW / "judgments_real.jsonl")
    chats = make_chats(select_models(a.judges))
    items = load_bff_all()
    if a.only_unanimous:
        items = [it for it in items if it["gold_unanimous"] is not None]
    conds = a.conds.split(",")
    print(f"{len(items)} real BFF answers x {len(conds)} conditions x {len(chats)} judges", flush=True)

    async def one(jk, chat, it, cond):
        ck = f"{jk}|{it['id']}|{cond}"
        if ck in cache or (cond == "human" and not it["ref"]):
            return
        prompt = build_prompt(it, it["conv"][-1]["content"], cond)
        r = await sample_with_verdict_probs(chat, [{"role": "user", "content": prompt}], n=a.samples,
                                            max_tokens=a.max_tokens, temperature=0.7, topk=5)
        samples = []
        for o in r["outputs"]:
            vt = o["verdict_tok"]
            samples.append(dict(text=o["text"], clean=o["clean"], n_out=o["n_out"], mean_logprob=o["mean_logprob"],
                                verdict=parse_verdict(o["text"]), p_correct=vt["p_correct"] if vt else None,
                                verdict_token=vt["token"] if vt else None, verdict_topk=vt["topk"] if vt else None))
        votes = [s["verdict"] for s in samples if s["verdict"] is not None]
        pcs = [s["p_correct"] for s in samples if s["p_correct"] is not None]
        cache.put(dict(cache_key=ck, judge=jk, model=chat.spec["model"], renderer=r["renderer"], item_id=it["id"],
                       qid=it["qid"], turn=it["turn"], examinee=it["examinee"], condition=cond,
                       labels=it["labels"], n_correct=it["n_correct"], n_incorrect=it["n_incorrect"],
                       gold_unanimous=it["gold_unanimous"], gold_majority=it["gold_majority"], prompt=prompt,
                       samples=samples, vote_share=sum(votes) / len(votes) if votes else None, n_parsed=len(votes),
                       p_correct_mean=sum(pcs) / len(pcs) if pcs else None,
                       sampling=dict(n=a.samples, temperature=0.7, max_tokens=a.max_tokens, topk=5),
                       n_in=r["n_in"], n_out=r["n_out"], latency=r["latency"],
                       cost=call_cost(chat.spec, r["n_in"], r["n_out"])))

    jobs = [lambda jk=jk, c=c, it=it, cond=cond: one(jk, c, it, cond)
            for jk, c in chats.items() for it in items for cond in conds]
    asyncio.run(run_jobs(jobs, a.concurrency, "judge_real"))
    analyze()


def analyze():
    rows = [json.loads(l) for l in open(RAW / "judgments_real.jsonl")]
    L = ["# Real BFF answers: verdicts and confidence", "",
         f"{len(rows)} requests, ${sum(r['cost'] for r in rows):.2f}. Gold = unanimous label; 'split' = annotators "
         "disagreed. Confident = all 5 samples agree.", "",
         "| Judge | Ref | Gold | n | Says INCORRECT | All 5 agree | Confidently wrong (all 5 agree, wrong) |",
         "|---|---|---|---|---|---|---|"]
    g = collections.defaultdict(list)
    for r in rows:
        if r["vote_share"] is None:
            continue
        gold = {1: "correct", 0: "incorrect", None: "split"}[r["gold_unanimous"]]
        g[(r["judge"], r["condition"], gold)].append(r)
    for (j, c, gold), rs in sorted(g.items()):
        inc = sum(1 - r["vote_share"] for r in rs) / len(rs)
        agree = sum(r["vote_share"] in (0.0, 1.0) for r in rs) / len(rs)
        wrong = "" if gold == "split" else \
            f"{sum((r['vote_share'] == 1.0 and gold == 'incorrect') or (r['vote_share'] == 0.0 and gold == 'correct') for r in rs) / len(rs):.2f}"
        L.append(f"| {j} | {c} | {gold} | {len(rs)} | {inc:.2f} | {agree:.2f} | {wrong} |")
    (HERE / "results" / "real_summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judges", default=JUDGES)
    ap.add_argument("--conds", default="none")
    ap.add_argument("--samples", type=int, default=5)
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--only-unanimous", action="store_true", help="skip answers the annotators split on")
    ap.add_argument("--analyze", action="store_true")
    a = ap.parse_args()
    analyze() if a.analyze else run(a)


if __name__ == "__main__":
    main()
