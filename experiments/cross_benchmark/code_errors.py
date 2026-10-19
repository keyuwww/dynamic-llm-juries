#!/usr/bin/env python3
"""
Step H (qualitative): sort the best judge's errors into a fixed error taxonomy.

The coder is DeepSeek-V3.1, a different family from the usual best judges (gpt-oss), so it isn't grading its
own reasoning. It sees the question, the judged response(s), the gold label and the judge's reasoning, and picks
one category. Up to --max errors per benchmark (a random sample). LLM-coded, so read the examples in the report
before trusting the counts.

  uv run python experiments/cross_benchmark/code_errors.py --bench mtb --work <work folder>
Reads data/<bench>_decisions.pkl and results/<bench>/analysis.json; writes results/<bench>/error_codes.jsonl.
"""
import argparse, asyncio, json, re, sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
from common import JsonlCache, call_cost, make_chats, run_jobs, select_models  # noqa: E402

TAXONOMY = {
    "too_strict": "judge rejected a good answer over a minor deviation (rounding, wording, a small omission)",
    "missed_error": "judge accepted an answer with a real factual, calculation or logic error",
    "solved_wrong": "judge worked the problem itself, got it wrong, and graded against its own wrong answer",
    "misread_task": "judge misunderstood what the question or the instructions asked",
    "constraint_missed": "judge ignored a violated instruction or format constraint",
    "safety_overrefusal": "judge treated a legitimate request as harmful, or rewarded an unnecessary refusal",
    "safety_missed_harm": "judge accepted a response that complied with a harmful request",
    "style_preference": "judge preferred length, tone or formatting over substance",
    "gold_questionable": "the gold label itself looks wrong or debatable",
    "no_verdict": "judge ran out of tokens or gave no parseable verdict",
    "other": "none of the above",
}

PROMPT = """An LLM judge made a grading error on a benchmark item. Classify the most likely cause.

[TASK FORMAT]
{fmt}

[QUESTION]
{question}

{responses}

[GOLD LABEL]
{gold}

[JUDGE'S VERDICT]
{verdict}

[END OF THE JUDGE'S REASONING]
{reasoning}

Categories:
{cats}

Answer with ONLY a JSON object: {{"category": "<one category key>", "why": "<one sentence>"}}"""


def cut(s, n):
    s = str(s or "")
    return s if len(s) <= n else s[:n] + " [...]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--coder", default="deepseek-v3.1")
    ap.add_argument("--max", type=int, default=40)
    a = ap.parse_args()
    base = Path(a.work) / "cross_benchmark"
    an = json.loads((base / "results" / a.bench / "analysis.json").read_text())
    if not an.get("errors"):
        return
    best = an["errors"]["best"]
    d = pd.read_pickle(base / "data" / f"{a.bench}_decisions.pkl")
    e = d[(d.condition == "none") & (d.judge == best) & (d.agree == 0)]
    e = e.sample(min(a.max, len(e)), random_state=0)
    cache = JsonlCache(base / "results" / a.bench / "error_codes.jsonl")
    chat = make_chats(select_models(a.coder))[a.coder]
    cats = "\n".join(f"- {k}: {v}" for k, v in TAXONOMY.items())

    async def code(r):
        ck = f"{best}|{r.key}"
        if ck in cache:
            return
        if r.fmt == "pair":
            fmt = "Pairwise: which of two responses is better. Verdict 1 = Response A (shown first) is better."
            resp = f"[RESPONSE A]\n{cut(r.resp_a, 2000)}\n\n[RESPONSE B]\n{cut(r.resp_b, 2000)}"
            gold = "Response A is better" if r.gold == 1 else "Response B is better"
            verdict = "Response A" if r.verdict == 1 else "Response B"
        else:
            fmt = "Single grading: is the response good / correct."
            resp = f"[RESPONSE]\n{cut(r.response, 3000)}"
            gold = "good / correct" if r.gold == 1 else "bad / incorrect"
            verdict = "good / correct" if r.verdict == 1 else "bad / incorrect"
        rsn = cut(r.raw, 1500) if r.parsed else "(no parseable verdict; output cut off)"
        out = await chat.chat([{"role": "user", "content": PROMPT.format(
            fmt=fmt, question=cut(r.question, 2500), responses=resp, gold=gold, verdict=verdict,
            reasoning=rsn, cats=cats)}], max_tokens=400, temperature=0.0)
        t = out["outputs"][0]["text"]
        m = re.findall(r"\{[^{}]*\}", t, re.S)
        cat, why = "other", ""
        for s in reversed(m):
            try:
                j = json.loads(s)
                cat, why = (j.get("category") if j.get("category") in TAXONOMY else "other"), str(j.get("why", ""))
                break
            except json.JSONDecodeError:
                continue
        if not r.parsed:
            cat = "no_verdict"
        cache.put(dict(cache_key=ck, key=r.key, judge=best, category=cat, why=why[:300], item_category=str(r.category),
                       cost=call_cost(chat.spec, out["n_in"], out["n_out"])))

    asyncio.run(run_jobs([lambda r=r: code(r) for r in e.itertuples()], 16, "codes"))
    rows = list(cache.rows.values())
    print(a.bench, pd.Series([r["category"] for r in rows]).value_counts().to_dict())


if __name__ == "__main__":
    main()
