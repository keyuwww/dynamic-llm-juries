#!/usr/bin/env python3
"""
Step I for every benchmark: a question-completion contamination probe.

Show the first half of a benchmark question and ask the model to continue it word for word. Score the longest run
of words the continuation shares with the real second half. A model that saw the benchmark in training tends to
reproduce long runs; compare the judge (gpt-oss-120b) with a control (qwen3.5-4b), not against an absolute cut-off.
Benchmarks with built-in references were also probed on their references in tinker_pool/probe_contamination.py
(BFF-Bench).

  uv run python experiments/cross_benchmark/probe_xb.py --bench mtb --work <work folder>
Writes results/<bench>/contamination.jsonl.
"""
import argparse, asyncio, random, sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
from common import JsonlCache, call_cost, make_chats, run_jobs, select_models  # noqa: E402
from probe_contamination import longest_common_run, words  # noqa: E402

PROMPT = """The text below is the beginning of a question from a public benchmark dataset. Continue it exactly as it was originally written, word for word, from where it stops. Output only the continuation.

{prefix}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--models", default="gpt-oss-120b,qwen3.5-4b")
    ap.add_argument("--n", type=int, default=60)
    a = ap.parse_args()
    base = Path(a.work) / "cross_benchmark"
    it = pd.read_pickle(base / "data" / f"{a.bench}_items.pkl")
    qs = it.drop_duplicates("question_key")[["question_key", "question"]]
    qs = qs[qs.question.fillna("").str.split().str.len() >= 40]
    keys = list(qs.question_key)
    random.Random(0).shuffle(keys)
    keys = keys[: a.n]
    text = dict(zip(qs.question_key, qs.question))
    cache = JsonlCache(base / "results" / a.bench / "contamination.jsonl")
    chats = make_chats(select_models(a.models))

    async def probe(chat, k):
        ck = f"{chat.spec['key']}|{k}"
        if ck in cache:
            return
        w = text[k].split()
        w = w[:600]
        cut = len(w) // 2
        target = " ".join(w[cut:])
        r = await chat.chat([{"role": "user", "content": PROMPT.format(prefix=" ".join(w[:cut]))}],
                            max_tokens=2048, temperature=0.0)
        t = r["outputs"][0]["text"]
        run = longest_common_run(words(t), words(target))
        cache.put(dict(cache_key=ck, model=chat.spec["key"], key=k, lcr=run, target_words=len(target.split()),
                       cost=call_cost(chat.spec, r["n_in"], r["n_out"])))

    asyncio.run(run_jobs([lambda c=c, k=k: probe(c, k) for c in chats.values() for k in keys], 32, "probes"))
    df = pd.DataFrame(cache.rows.values())
    print(a.bench, df.groupby("model").lcr.agg(["mean", "median", lambda s: (s >= 13).mean()]).round(3).to_dict())


if __name__ == "__main__":
    main()
