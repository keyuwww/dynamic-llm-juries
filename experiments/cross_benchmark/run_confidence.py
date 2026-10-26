"""
Judging with a stated confidence and the verdict-token probability (order-flip and confidence study).

Same prompts as the stored runs (tinker_pool/run_judges.py for bffpair and bffctrl, run_xb_judges.py for the
others), with the final instruction extended to ask for a CONFIDENCE line (0-100). Pairwise items are judged in
both orders, as before; rb2 is single-answer grading (CORRECT / INCORRECT). K samples per call (--samples); the
per-sample fields are lists and the scalar fields hold sample 0. For each call we keep:
  verdict      1 = A (first shown) better, 0 = B, None = unparsed
  conf         stated confidence 0-100 (None if missing)
  p_verdict    P(chosen letter) / (P(A) + P(B)) at the verdict token, from the top-k sampled logprobs
  raw_full     the whole decoded generation, including the reasoning channel (the stored runs kept only the
               final text, so gpt-oss reasoning traces were lost)
Output: results/<out-dir>/<bench>/judgments.jsonl (append-only cache; rerun to resume).

Usage (from experiments/cross_benchmark):
  python run_confidence.py --bench bffpair --samples 3 --out-dir confidence_pilot \\
      --models gpt-oss-120b,gpt-oss-20b,nemotron3-nano-30b                       # pilot
  python run_confidence.py --bench mtbhuman --models all                         # full run (K = 1)
  python run_confidence.py --bench bffctrl --models all                          # controlled pairs
  python run_confidence.py --bench rb2 --models all                              # single-answer grading
"""
import argparse, asyncio, json, math, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
sys.path.insert(0, str(HERE.parent / "jev_bff"))
from common import JsonlCache, call_cost, load_env, run_jobs, select_models  # noqa: E402

CONF_TAIL = ('Reason briefly, then end with exactly two lines: "VERDICT: A" or "VERDICT: B", and then '
             '"CONFIDENCE: <a number from 0 to 100>", your probability in percent that your verdict picks the better answer.')
OLD_TAIL = 'Reason briefly, then end with exactly one line: "VERDICT: A" or "VERDICT: B".'
PAIR_RE = re.compile(r"VERDICT:\s*\**\s*(A|B)\b", re.I)
SINGLE_OLD = 'Reason briefly, then end with exactly one line: "VERDICT: CORRECT" or "VERDICT: INCORRECT".'
SINGLE_TAIL = ('Reason briefly, then end with exactly two lines: "VERDICT: CORRECT" or "VERDICT: INCORRECT", and then '
               '"CONFIDENCE: <a number from 0 to 100>", your probability in percent that your verdict is right.')
SINGLE_RE = re.compile(r"VERDICT:\s*\**\s*(CORRECT|INCORRECT)\b", re.I)
CONF_RE = re.compile(r"CONFIDENCE:\s*\**\s*(\d{1,3}(?:\.\d+)?)\s*%?", re.I)


def load_items(bench):
    """Returns (items, prompt_fn). Item ids match the stored runs so verdicts can be joined.
    bffpair / bffctrl use the BFF pairwise prompt from tinker_pool/run_judges.py; the others use run_xb_judges.py
    (rb2 is single-answer grading, the rest are pairwise)."""
    if bench in ("bffpair", "bffctrl"):
        import run_judges as rj
        if bench == "bffpair":
            from data import load_pairwise_items
            items = load_pairwise_items()
        else:                     # controlled BFF pairs built by build_ctrl_pairs.py
            items = json.load(open(HERE / "data" / "bffctrl_items.json"))
        return items, lambda it: rj.PAIR_JUDGE.format(conv_a=rj.render_conv(it["conv_a"]),
                                                      conv_b=rj.render_conv(it["conv_b"]), reference="")
    import run_xb_judges as xj
    from loaders import LOADERS
    fmt = "single" if bench == "rb2" else "pair"
    items = [it for it in LOADERS[bench]() if not it.get("skip") and it["fmt"] == fmt]
    return items, xj.build_prompt


def parse(text, single=False):
    if single:
        v = SINGLE_RE.findall(text or "")
        c = CONF_RE.findall(text or "")
        return (None if not v else int(v[-1].upper() == "CORRECT")), (min(100.0, float(c[-1])) if c else None)
    v = PAIR_RE.findall(text or "")
    c = CONF_RE.findall(text or "")
    conf = min(100.0, float(c[-1])) if c else None
    return (None if not v else int(v[-1].upper() == "A")), conf


def verdict_prob(tok, tokens, topk, single=False):
    """P(chosen option) normalised over the two alternatives at the last 'VERDICT: X' token."""
    pieces = [tok.decode([t]) for t in tokens]
    text, starts = "", []
    for p in pieces:
        starts.append(len(text))
        text += p
    m = list((SINGLE_RE if single else PAIR_RE).finditer(text))
    if not m or topk is None:
        return None, text
    pos = m[-1].start(1)
    idx = max(i for i, s in enumerate(starts) if s <= pos)
    alts = topk[idx] or []
    if single:   # first sub-token of CORRECT vs INCORRECT
        isA = lambda x: x.startswith("C")
        isB = lambda x: x.startswith("I")
        chosen = "A" if m[-1].group(1).upper() == "CORRECT" else "B"
    else:
        isA = lambda x: x == "A"
        isB = lambda x: x == "B"
        chosen = m[-1].group(1).upper()
    pa = sum(math.exp(lp) for t, lp in alts if isA(tok.decode([t]).strip().upper()))
    pb = sum(math.exp(lp) for t, lp in alts if isB(tok.decode([t]).strip().upper()))
    if pa + pb == 0:
        return None, text
    return (pa if chosen == "A" else pb) / (pa + pb), text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True, choices=["bffpair", "judgebench", "alpacafarm", "mtbhuman", "bffctrl", "rb2"])
    ap.add_argument("--models", default="gpt-oss-120b,gpt-oss-20b,nemotron3-nano-30b")
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--limit", type=int, default=None, help="first N items (smoke test)")
    ap.add_argument("--samples", type=int, default=1, help="samples per call (K); per-sample fields are lists")
    ap.add_argument("--out-dir", default="confidence", help="results/<out-dir>/<bench>/judgments.jsonl")
    a = ap.parse_args()

    items, prompt_fn = load_items(a.bench)
    if a.limit:
        items = items[: a.limit]
    out = HERE / "results" / a.out_dir / a.bench
    cache = JsonlCache(out / "judgments.jsonl")

    load_env()
    import tinker
    from tinker import types
    from tinker_cookbook import renderers
    from common import TinkerChat
    service = tinker.ServiceClient()
    chats = {m["key"]: TinkerChat(m, service, "off") for m in select_models(a.models)}

    async def judge(chat, it):
        m = chat.spec["key"]
        k = f"{m}|{it['id']}|conf"
        if k in cache:
            return
        prompt_text = prompt_fn(it)
        single = a.bench == "rb2"
        old, new = (SINGLE_OLD, SINGLE_TAIL) if single else (OLD_TAIL, CONF_TAIL)
        assert old in prompt_text, "prompt tail changed; update OLD_TAIL / SINGLE_OLD"
        prompt_text = prompt_text.replace(old, new)
        prompt = chat.renderer.build_generation_prompt([{"role": "user", "content": prompt_text}])
        params = types.SamplingParams(max_tokens=a.max_tokens, temperature=a.temperature, stop=chat.stop)
        res = await asyncio.wait_for(chat.client.sample_async(prompt=prompt, num_samples=a.samples, sampling_params=params,
                                                              topk_sample_logprobs=5), 900)
        tok = chat.client.get_tokenizer()
        V, C, PV, RAW, FULL, NOUT = [], [], [], [], [], []
        for seq in res.sequences:
            toks = list(seq.tokens)
            msg, _ = chat.renderer.parse_response(toks)
            final = renderers.get_text_content(msg)
            v, conf = parse(final, single)
            pv, full = verdict_prob(tok, toks, seq.topk_logprobs, single)
            V.append(v); C.append(conf); PV.append(pv); RAW.append(final); FULL.append(full); NOUT.append(len(toks))
        n_in = prompt.length() if callable(prompt.length) else prompt.length
        cache.put(dict(cache_key=k, judge=m, item_id=it["id"], bench=a.bench, gold=it["gold"], verdict=V[0],
                       conf=C[0], p_verdict=PV[0], verdicts=V, confs=C, p_verdicts=PV, raw=RAW, raw_full=FULL,
                       n_in=n_in, n_out=sum(NOUT), cost=call_cost(chat.spec, n_in, sum(NOUT))))

    jobs = [lambda c=c, it=it: judge(c, it) for c in chats.values() for it in items]
    print(f"{a.bench}: {len(items)} items x {len(chats)} judges = {len(jobs)} calls", flush=True)
    asyncio.run(run_jobs(jobs, a.concurrency, "judgments"))
    rows = [r for r in cache.rows.values()]
    for j in sorted({r["judge"] for r in rows}):
        rs = [r for r in rows if r["judge"] == j]
        print(f"{j}: n={len(rs)} parsed={sum(r['verdict'] is not None for r in rs)} "
              f"conf={sum(r['conf'] is not None for r in rs)} p={sum(r['p_verdict'] is not None for r in rs)} "
              f"${sum(r['cost'] for r in rs):.2f}", flush=True)


if __name__ == "__main__":
    main()
