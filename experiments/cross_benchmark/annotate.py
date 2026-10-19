#!/usr/bin/env python3
"""
Step B of the plan: code every question's demands with one shared rubric, from the question text only (never the
candidate answers or labels), so aspect analyses compare across benchmarks.

Coder A (gpt-oss-120b) codes every question; coder B (qwen3.6-35b-a3b) independently codes a 20% sample, giving the
blind double-coding agreement (weighted κ per aspect) the plan requires before an aspect is used.

These are AI-authored research annotations, like the BFF codebook's, not expert labels.

  uv run python experiments/cross_benchmark/annotate.py --bench mtb
Reads data/<bench>_items.pkl, writes results/<bench>/annotations.jsonl (cache) and data/<bench>_aspects.pkl.
"""
import argparse, asyncio, json, random, re, sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
from common import JsonlCache, call_cost, make_chats, run_jobs, select_models  # noqa: E402

ASPECTS = ["knowledge", "reasoning", "constraints", "open_endedness", "context_load", "risk"]

RUBRIC = """You are annotating what a benchmark question demands of a model that must answer it. Read ONLY the user request below (earlier user turns, if any, are included). Do not try to answer it.

Score each aspect 0-3:
- knowledge: specialist knowledge needed. 0 = none beyond what is given; 1 = common knowledge; 2 = specialised (a field's standard methods, standards, APIs); 3 = niche rules, exceptions or expert detail.
- reasoning: multi-step reasoning or calculation needed. 0 = none (recall or rewrite); 1 = one or two simple steps; 2 = several linked steps; 3 = long chains, search over cases, or complex solving.
- constraints: explicit instructions the answer must satisfy (format, length, words to use or avoid, style, persona). 0 = none; 1 = one; 2 = a few; 3 = many or tightly interacting.
- open_endedness: how many different answers would be acceptable. 0 = exactly one correct answer; 1 = one answer, flexible wording; 2 = several acceptable answers; 3 = creative or subjective, judged on quality.
- context_load: how much input must be tracked. 0 = short self-contained request; 1 = a paragraph of facts; 2 = long input or several earlier turns that matter; 3 = very long input, tables, code or many details to select from.
- risk: harm if a model complied naively. 0 = none; 1 = mild (sensitive topic); 2 = could enable harm or is deceptive; 3 = clearly dangerous or illegal.

Also give "topic": 1-3 words naming the subject area.

[USER REQUEST]
{question}

Answer with ONLY a JSON object, for example:
{{"topic": "tax accounting", "knowledge": 2, "reasoning": 1, "constraints": 0, "open_endedness": 1, "context_load": 1, "risk": 0}}"""

JSON_RE = re.compile(r"\{[^{}]*\}", re.S)


def parse(text):
    for m in reversed(JSON_RE.findall(text or "")):
        try:
            d = json.loads(m)
        except json.JSONDecodeError:
            continue
        if all(k in d for k in ASPECTS):
            try:
                return {k: int(max(0, min(3, int(d[k])))) for k in ASPECTS} | {"topic": str(d.get("topic", ""))[:40]}
            except (TypeError, ValueError):
                continue
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True)
    ap.add_argument("--coder-a", default="gpt-oss-120b")
    ap.add_argument("--coder-b", default="qwen3.6-35b-a3b")
    ap.add_argument("--b-share", type=float, default=0.2)
    ap.add_argument("--max-chars", type=int, default=8000)
    ap.add_argument("--concurrency", type=int, default=32)
    ap.add_argument("--work", default=str(HERE))
    a = ap.parse_args()
    work = Path(a.work)
    items = pd.read_pickle(work / "data" / f"{a.bench}_items.pkl")
    qs = items.drop_duplicates("question_key")[["question_key", "question"]]
    qs = qs[qs.question.fillna("").str.len() > 0]
    keys = list(qs.question_key)
    rng = random.Random(0)
    b_keys = set(rng.sample(keys, max(1, int(round(a.b_share * len(keys))))))
    text = dict(zip(qs.question_key, qs.question))
    cache = JsonlCache(work / "results" / a.bench / "annotations.jsonl")
    chats = make_chats(select_models(f"{a.coder_a},{a.coder_b}"))

    async def code(chat, k):
        ck = f"{chat.spec['key']}|{k}"
        if ck in cache and cache.get(ck)["parsed"]:
            return
        q = text[k]
        q = q if len(q) <= a.max_chars else q[: a.max_chars] + "\n[... truncated ...]"
        r = await chat.chat([{"role": "user", "content": RUBRIC.format(question=q)}], max_tokens=2048, temperature=0.0)
        t = r["outputs"][0]["text"]
        p = parse(t)
        cache.put(dict(cache_key=ck, coder=chat.spec["key"], question_key=k, parsed=p is not None, scores=p, raw=t[-600:],
                       cost=call_cost(chat.spec, r["n_in"], r["n_out"])))

    jobs = [lambda k=k: code(chats[a.coder_a], k) for k in keys]
    jobs += [lambda k=k: code(chats[a.coder_b], k) for k in sorted(b_keys)]
    print(f"{a.bench}: {len(keys)} questions (coder B: {len(b_keys)})", flush=True)
    asyncio.run(run_jobs(jobs, a.concurrency, "annotations"))
    rows = [r for r in cache.rows.values() if r["coder"] == a.coder_a and r["parsed"]]
    out = pd.DataFrame([dict(question_key=r["question_key"], **r["scores"]) for r in rows])
    out.to_pickle(work / "data" / f"{a.bench}_aspects.pkl")
    rb = [r for r in cache.rows.values() if r["coder"] == a.coder_b and r["parsed"]]
    pd.DataFrame([dict(question_key=r["question_key"], **r["scores"]) for r in rb]).to_pickle(
        work / "data" / f"{a.bench}_aspects_b.pkl")
    print(f"coded {len(out)}/{len(keys)} (A), {len(rb)} (B); cost ${sum(r['cost'] for r in cache.rows.values()):.2f}")


if __name__ == "__main__":
    main()
