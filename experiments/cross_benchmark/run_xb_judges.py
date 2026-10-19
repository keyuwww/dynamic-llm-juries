#!/usr/bin/env python3
"""
Run the 8 Tinker judges on the benchmarks added in the cross-benchmark analysis (see loaders.py).

Same judging setup as tinker_pool/run_judges.py (1 sample, T = 0.7, thinking off where possible, a verdict
line at the end, unparseable counts as the "negative" verdict) and the same JsonlCache, so reruns resume and
nothing is paid for twice.

  uv run python experiments/cross_benchmark/run_xb_judges.py --bench judgebench --limit 10   # pilot
  uv run python experiments/cross_benchmark/run_xb_judges.py --bench judgebench
Benches: judgebench, rb2, alpacafarm, mtbhuman, dpo5k.  Output: --out (default results/<bench>/judgments.jsonl).
"""
import argparse, asyncio, random, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
from common import JsonlCache, call_cost, make_chats, parse_verdict, run_jobs, select_models  # noqa: E402
from loaders import LOADERS  # noqa: E402

PAIR_RE = re.compile(r"VERDICT:\s*\**\s*(A|B)\b", re.I)


def parse_pair(text):
    m = PAIR_RE.findall(text or "")
    return None if not m else int(m[-1].upper() == "A")


PAIR_JUDGE = """You are comparing two AI assistants' responses to the same user request.

[USER REQUEST]
{question}

[RESPONSE A]
{a}

[RESPONSE B]
{b}

Which response is better? If the request has a correct answer, correctness comes first: a wrong final answer, fact or calculation is worse than any style issue. Otherwise prefer the response that is more helpful, accurate and better follows the request. Do not let the order of the responses or their length influence you.
Reason briefly, then end with exactly one line: "VERDICT: A" or "VERDICT: B"."""

CONV_PAIR_JUDGE = """You are comparing two AI assistants' answers in a conversation. Each assistant had its own conversation with the same user; compare only their FINAL responses to the user's final message.

[CONVERSATION WITH ASSISTANT A]
{a}

[CONVERSATION WITH ASSISTANT B]
{b}

Which assistant's FINAL response is better? If the request has a correct answer, correctness comes first. Otherwise prefer the more helpful, accurate response that better follows the request. Do not let the order of the answers or their length influence you.
Reason briefly, then end with exactly one line: "VERDICT: A" or "VERDICT: B"."""

CRITIQUE_JUDGE = """Two evaluators wrote a critique of the same AI response, following the grading instruction below.

[GRADING INSTRUCTION AND RESPONSE BEING GRADED]
{question}

[CRITIQUE A]
{a}

[CRITIQUE B]
{b}

Which critique is more accurate and better calibrated (catches real problems, does not reward length or confident tone, gives a fair score)?
Reason briefly, then end with exactly one line: "VERDICT: A" or "VERDICT: B"."""

SINGLE_JUDGE = """You are grading an AI assistant's response.

[USER REQUEST]
{prompt}

[ASSISTANT'S RESPONSE]
{response}

Is this a good response? It must be factually correct, answer exactly what was asked, follow every instruction and constraint in the request, and stay on topic. A response with a factual error, a wrong final answer, a violated constraint or that answers a different question is not good.
Reason briefly, then end with exactly one line: "VERDICT: CORRECT" or "VERDICT: INCORRECT"."""


def render_conv(conv):
    return "\n\n".join(f"[{m['role'].upper()}]\n{m['content']}" for m in conv)


def build_prompt(it):
    if it["bench"] == "dpo5k":
        return CRITIQUE_JUDGE.format(question=it["question"], a=it["resp_a"], b=it["resp_b"])
    if it["bench"] == "mtbhuman":
        return CONV_PAIR_JUDGE.format(a=render_conv(it["resp_a"]), b=render_conv(it["resp_b"]))
    if it["fmt"] == "pair":
        return PAIR_JUDGE.format(question=it["question"], a=it["resp_a"], b=it["resp_b"])
    return SINGLE_JUDGE.format(prompt=it["prompt"], response=it["response"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", choices=sorted(LOADERS), required=True)
    ap.add_argument("--models", default="all")
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--limit", type=int, default=None, help="random subset of groups (pilot)")
    ap.add_argument("--concurrency", type=int, default=32)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None)
    ap.add_argument("--mock", action="store_true")
    a = ap.parse_args()

    items = [it for it in LOADERS[a.bench]() if not it.get("skip")]
    if a.limit:
        groups = sorted({it["group"] for it in items})
        random.Random(a.seed).shuffle(groups)
        keep = set(groups[: a.limit])
        items = [it for it in items if it["group"] in keep]
    out = Path(a.out) if a.out else HERE / "results" / a.bench
    cache = JsonlCache(out / ("judgments_mock.jsonl" if a.mock else "judgments.jsonl"))
    models = select_models(a.models)
    chats = make_chats(models, "off", a.mock)

    async def judge(chat, it):
        m = chat.spec["key"]
        k = f"{m}|{it['id']}|none"
        if k in cache:
            return
        r = await chat.chat([{"role": "user", "content": build_prompt(it)}], max_tokens=a.max_tokens,
                            temperature=a.temperature)
        text = r["outputs"][0]["text"]
        v = parse_pair(text) if it["fmt"] == "pair" else parse_verdict(text)
        cache.put(dict(cache_key=k, judge=m, item_id=it["id"], condition="none", bench=a.bench, gold=it["gold"],
                       votes=[v] if v is not None else [], n_parsed=int(v is not None),
                       vote_share=float(v) if v is not None else None, raw=[text], n_in=r["n_in"], n_out=r["n_out"],
                       cost=call_cost(chat.spec, r["n_in"], r["n_out"]), clean=r["outputs"][0]["clean"]))

    jobs = [lambda c=c, it=it: judge(c, it) for c in chats.values() for it in items]
    print(f"{a.bench}: {len(items)} items x {len(chats)} judges = {len(jobs)} judgments", flush=True)
    asyncio.run(run_jobs(jobs, a.concurrency, "judgments"))
    rows = [r for r in cache.rows.values()]
    by = {}
    for r in rows:
        by.setdefault(r["judge"], []).append(r)
    print("| judge | n | parse | acc | $ |")
    for j, rs in sorted(by.items()):
        acc = sum(((r["vote_share"] or 0) > 0.5) == (r["gold"] == 1) for r in rs) / len(rs)
        print(f"| {j} | {len(rs)} | {sum(r['n_parsed'] for r in rs) / len(rs):.3f} | {acc:.3f} | "
              f"{sum(r['cost'] for r in rs):.2f} |")


if __name__ == "__main__":
    main()
