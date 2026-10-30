"""Ask judges directly how likely a strong expert judge is to get a pairwise item right (test 3).

Two variants per item:
  q    question only (no answers): can the judge predict expert difficulty before any answer is shown?
       Deduplicated by question text, so pairs that share a question share one call.
  qa   question + both answers (first presentation order only)
The judge is told not to judge the answers itself, only to estimate P(expert picks the better answer), 0-100,
on a final "EXPERT_CORRECT: <n>" line.
Output: results/difficulty/<bench>/judgments.jsonl (append-only cache; rerun to resume), raw text kept.
Usage (from experiments/cross_benchmark):
  python run_difficulty.py --bench bffpair --limit 3          # smoke test
  python run_difficulty.py --bench bffpair --models all
"""
import argparse, asyncio, hashlib, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
sys.path.insert(0, str(HERE.parent / "jev_bff"))
from common import JsonlCache, call_cost, make_chats, run_jobs, select_models  # noqa: E402
from run_confidence import load_items  # noqa: E402

PRED_RE = re.compile(r"EXPERT_CORRECT:\s*\**\s*(\d{1,3}(?:\.\d+)?)\s*%?", re.I)
TAIL = ('Do not decide which answer is better yourself. Estimate how likely the expert judge is to pick the truly '
        'better answer. Reason briefly, then end with exactly one line: "EXPERT_CORRECT: <a number from 0 to 100>".')

Q_PROMPT = """A strong expert AI judge will be shown the question below together with two candidate answers written by other AI assistants, and asked which answer is better (correctness first, then helpfulness). You will not see the answers.

[QUESTION]
{q}

""" + TAIL

QA_PROMPT = """A strong expert AI judge will compare the two answers below and decide which one is better (correctness first, then helpfulness).

{body}

""" + TAIL


def render_conv(conv):
    return "\n\n".join(f"[{m['role'].upper()}]\n{m['content']}" for m in conv)


def texts(bench, it):
    """(question-only text, question+answers body)."""
    if bench == "bffpair":
        return (render_conv(it["conv_a"][:-1]),
                f"[CONVERSATION WITH ASSISTANT A]\n{render_conv(it['conv_a'])}\n\n[CONVERSATION WITH ASSISTANT B]\n{render_conv(it['conv_b'])}")
    if bench == "mtbhuman":
        return (render_conv(it["resp_a"][:-1]),
                f"[CONVERSATION WITH ASSISTANT A]\n{render_conv(it['resp_a'])}\n\n[CONVERSATION WITH ASSISTANT B]\n{render_conv(it['resp_b'])}")
    return it["question"], f"[USER REQUEST]\n{it['question']}\n\n[RESPONSE A]\n{it['resp_a']}\n\n[RESPONSE B]\n{it['resp_b']}"


def parse(text):
    m = PRED_RE.findall(text or "")
    return min(100.0, float(m[-1])) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True, choices=["bffpair", "judgebench", "alpacafarm", "mtbhuman"])
    ap.add_argument("--models", default="all")
    ap.add_argument("--variants", default="q,qa")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--max-tokens", type=int, default=4096, help="raise to retry items that ran out of tokens")
    a = ap.parse_args()

    items, _ = load_items(a.bench)
    first = [it for it in items if it["order"] in ("ab", 0)]          # one presentation per pair
    if a.limit:
        first = first[: a.limit]
    jobs_spec = []
    seen_q = set()
    for it in first:
        q, body = texts(a.bench, it)
        if "q" in a.variants.split(","):
            qk = hashlib.sha1(q.encode()).hexdigest()[:16]
            if qk not in seen_q:
                seen_q.add(qk)
                jobs_spec.append(("q", qk, Q_PROMPT.format(q=q), a.max_tokens, None))
        if "qa" in a.variants.split(","):
            jobs_spec.append(("qa", it["pair_id"], QA_PROMPT.format(body=body), a.max_tokens, it["pair_id"]))
    # map pair -> question key so analysis can join q-predictions back to pairs
    qmap = {it["pair_id"]: hashlib.sha1(texts(a.bench, it)[0].encode()).hexdigest()[:16] for it in first}

    out = HERE / "results" / "difficulty" / a.bench
    cache = JsonlCache(out / "judgments.jsonl")
    import json
    (out / "pair_to_question.json").write_text(json.dumps(qmap))
    chats = make_chats(select_models(a.models), "off")

    async def run(chat, variant, key, prompt, max_tokens, pair_id):
        m = chat.spec["key"]
        k = f"{m}|{variant}|{key}"
        if k in cache and cache.get(k)["pred"] is not None:
            return
        r = await chat.chat([{"role": "user", "content": prompt}], max_tokens=max_tokens, temperature=a.temperature)
        text = r["outputs"][0]["text"]
        cache.put(dict(cache_key=k, judge=m, variant=variant, key=key, pair_id=pair_id, bench=a.bench,
                       pred=parse(text), raw=text, n_in=r["n_in"], n_out=r["n_out"],
                       cost=call_cost(chat.spec, r["n_in"], r["n_out"])))

    jobs = [lambda c=c, s=s: run(c, *s) for c in chats.values() for s in jobs_spec]
    print(f"{a.bench}: {len(jobs_spec)} prompts x {len(chats)} judges = {len(jobs)} calls", flush=True)
    asyncio.run(run_jobs(jobs, a.concurrency, "predictions"))
    rows = list(cache.rows.values())
    for j in sorted({r["judge"] for r in rows}):
        rs = [r for r in rows if r["judge"] == j]
        print(f"{j}: n={len(rs)} parsed={sum(r['pred'] is not None for r in rs)} ${sum(r['cost'] for r in rs):.2f}", flush=True)


if __name__ == "__main__":
    main()
