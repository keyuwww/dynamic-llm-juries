"""Tinker calls for the early-answering anchoring experiment. Runs inside the Modal CPU image
(tinker is not installable on this laptop); see modal_app.py.

Phases (each resumes from its cache; rerunning only pays for what is missing):
  solve    each Qwen answers each RB2-Math / JudgeBench question once (thinking off, T=0.7, 4096
           tokens: the pool's BBEH settings)                                  -> out/solves.jsonl
  match    GLM-5.3-Flash decides whether the judge's own answer and each candidate reach the same
           final answer (RB2-Math, JudgeBench; BBEH is matched exactly in analyze.py) -> out/matches.jsonl
  readout  early answering: the judge's own pool transcript is cut at 0% (position A), 25%, 50%, 75%
           and at its real verdict line (position C); "VERDICT:" is appended and the log-probability
           of each verdict word is read with compute_logprobs              -> out/readouts.jsonl
  extend   every Qwen output cut off by its token limit (build_extend.py) is generated again FROM SCRATCH,
           same prompt and settings, with the whole 64K context as budget  -> out/extended.jsonl
  fill     (Llama) GLM-5.3-Flash reads the verdicts / BBEH answers Llama did not write in the requested
           format (inputs/fill_jobs_<key>.jsonl from open_ingest.py)  -> out/fill_glm5.3-flash_<key>.jsonl
  think    the 3 Qwens with THINKING ON: their own answers and judging transcripts generated again (each output may
           fill the whole context: 262K ids for the 4B and 35B, 64K for the 9B), then early answering on each
           judging transcript at A, 25/50/75% of the thinking, E (end of thinking) and C (verdict); see ckpts.py.
           A is the same text as the thinking-off A (empty think block + "VERDICT:").
                                                         -> out/think_gen.jsonl, out/think_readouts.jsonl
  --extended  (match, readout) redo only the items whose own answer / transcript was extended, using the
           finished text                                  -> out/matches_glm5.3-flash_ext.jsonl, out/readouts_ext.jsonl

  python tinker_jobs.py --phase readout --out /vol/anchoring_early_answer [--limit 5] [--models ...]
"""
import argparse
import asyncio
import collections
import gzip
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
from common import POOL_BY_KEY, JsonlCache, make_chats, run_jobs  # noqa: E402
sys.path.insert(0, str(HERE))
from ckpts import FINAL_RE, FRACS, checkpoints  # noqa: E402,F401

QWENS = ["qwen3.5-4b", "qwen3.5-9b", "qwen3.6-35b-a3b"]
# Answer matcher: GLM-5.3-Flash (high reasoning). Not a Qwen, so the judges' own family never decides what
# counts as a match. Only the 256K-context id is sampleable on this Tinker org.
MATCHERS = {
    "glm5.3-flash": dict(spec=dict(key="glm5.3-flash", model="zai-org/GLM-5.3-Flash:peft:262144", price_in=0.84, price_out=2.11),
                         renderer="glm5_3_high_reasoning", max_tokens=8192, file="matches_glm5.3-flash.jsonl"),
}
CTX = 65536  # context window of the Qwen3.5/3.6 ids used here; an extension may fill all of it

MATCH_PROMPT = """Two people answered the same question. Decide whether their FINAL answers are the same.
Ignore the reasoning, wording, formatting and rounding differences; compare only the final answer(s).
If a question has several parts, the answers are the same only if every part matches.

[QUESTION]
{question}

[ANSWER 1 (end)]
{a}

[ANSWER 2 (end)]
{b}

Reply with exactly one word: SAME or DIFFERENT. If either answer gives no final answer, reply NONE."""


VERDICT_PROMPT = """Below is the end of an evaluation written by a grader. The grader was asked to {task}
What final verdict did the grader give? Judge only from what the grader wrote; do not grade the problem yourself.

[GRADER'S EVALUATION (end)]
{text}

Reply with exactly one word: {opts}, or NONE if the grader gave no clear verdict."""


async def verdict_one(chat, key, transcript, pairwise, cache, max_tokens):
    """Read the verdict a grader gave when it did not write the requested `VERDICT:` line (used for Llama)."""
    if key in cache:
        return
    task = ("decide which of two responses, A or B, is better." if pairwise
            else "decide whether a candidate answer is CORRECT or INCORRECT.")
    opts = "A or B" if pairwise else "CORRECT or INCORRECT"
    prompt = VERDICT_PROMPT.format(task=task, text=transcript[-4000:], opts=opts)
    r = await chat.chat([{"role": "user", "content": prompt}], max_tokens=max_tokens, temperature=0.0)
    t = r["outputs"][0]["text"].strip().upper()
    pat = r"\b(A|B|NONE)\b" if pairwise else r"\b(CORRECT|INCORRECT|NONE)\b"
    last = re.findall(pat, t)
    v = last[-1] if last else None
    cache.put(dict(cache_key=key, verdict=v, raw=t[-200:], n_in=r["n_in"], n_out=r["n_out"]))


# Thinking-on runs: the long-context id where Tinker has one, so a long thinking trace is not cut off
THINK_IDS = {"qwen3.5-4b": ("Qwen/Qwen3.5-4B:peft:262144", 262144), "qwen3.5-9b": ("Qwen/Qwen3.5-9B", 65536),
             "qwen3.6-35b-a3b": ("Qwen/Qwen3.6-35B-A3B:peft:262144", 262144)}


def make_think_chat(key):
    import tinker
    from tinker_cookbook import renderers
    from common import TinkerChat, load_env
    load_env()
    model, _ = THINK_IDS[key]
    chat = TinkerChat(dict(POOL_BY_KEY[key], model=model), tinker.ServiceClient(), thinking="off")
    base = model.split(":")[0]
    chat.renderer_name = "qwen3_5"  # thinking on: the prompt ends with "<think>\n"
    chat.renderer = renderers.get_renderer("qwen3_5", chat.client.get_tokenizer(), model_name=base)
    chat.stop = chat.renderer.get_stop_sequences()
    return chat


async def think_one(chat, key, job, ctx, judge_job, gcache, rcache):
    """Generate (cached) one thinking-on output, then read the verdict at every checkpoint of a judging transcript."""
    from tinker import types
    from ckpts import checkpoints_think
    tok = chat.client.get_tokenizer()
    prompt = chat.renderer.build_generation_prompt(job["messages"]).to_ints()
    gk = f"{key}|{job['key']}"
    if gk not in gcache:
        budget = ctx - len(prompt) - 16
        params = types.SamplingParams(max_tokens=budget, temperature=0.7, stop=chat.stop)
        res = await chat.client.sample_async(prompt=types.ModelInput.from_ints(prompt), num_samples=1,
                                             sampling_params=params)
        toks = list(res.sequences[0].tokens)
        _, term = chat.renderer.parse_response(toks)
        text = tok.decode([t for t in toks if t not in chat.stop])  # raw: starts inside <think>, keeps </think>
        gcache.put(dict(cache_key=gk, judge=key, key=job["key"], text=text, n_in=len(prompt), n_out=len(toks),
                        budget=budget, finish="stop" if term.is_clean else "length", model=chat.spec["model"]))
    if judge_job is None:
        return
    text = gcache.get(gk)["text"]
    for name, prefix, opts in checkpoints_think(text, judge_job["pairwise"]):
        rk = f"{key}|{judge_job['item_id']}|{name}"
        if rk in rcache:
            continue
        if name == "A":  # identical to the thinking-off position A: empty think block
            prefix = "\n</think>\n\nVERDICT:"
        pre = tok.encode(prefix, add_special_tokens=False)
        lps = []
        for o in opts:
            ot = tok.encode(o, add_special_tokens=False)
            r = await chat.client.compute_logprobs_async(types.ModelInput.from_ints(prompt + pre + ot))
            lps.append(sum(x for x in r[-len(ot):] if x is not None))
        rcache.put(dict(cache_key=rk, judge=key, item_id=judge_job["item_id"], bench=judge_job["bench"], ckpt=name,
                        margin=lps[0] - lps[1], n_prefix=len(pre)))


def load_gz(path):
    with gzip.open(path, "rt") as f:
        return [json.loads(l) for l in f]


async def readout_one(chat, job, ck, cache):
    name, prefix, opts = ck
    key = f"{job['judge']}|{job['item_id']}|{name}"
    if key in cache:
        return
    from tinker import types
    tok = chat.client.get_tokenizer()
    prompt = chat.renderer.build_generation_prompt(job["messages"]).to_ints()
    pre = tok.encode(prefix, add_special_tokens=False)
    lps = []
    for o in opts:
        ot = tok.encode(o, add_special_tokens=False)
        res = await chat.client.compute_logprobs_async(types.ModelInput.from_ints(prompt + pre + ot))
        lps.append(sum(x for x in res[-len(ot):] if x is not None))
    cache.put(dict(cache_key=key, judge=job["judge"], bench=job["bench"], item_id=job["item_id"], ckpt=name,
                   lp1=lps[0], lp2=lps[1], margin=lps[0] - lps[1], n_prompt=len(prompt), pool_n_in=job["pool_n_in"],
                   n_prefix=len(pre)))


async def solve_one(chat, job, cache):
    key = f"{job['model']}|{job['qid']}"
    if key in cache:
        return
    n = chat.renderer.build_generation_prompt(job["messages"]).length
    n = n() if callable(n) else n
    # whole context as budget (the first RB2/JB solves used 4,096 and were rerun from scratch when cut off)
    r = await chat.chat(job["messages"], max_tokens=CTX - n - 16, temperature=0.7)
    o = r["outputs"][0]
    cache.put(dict(cache_key=key, model=job["model"], qid=job["qid"], bench=job["bench"], answer=o["text"],
                   n_out=o["n_out"], clean=o["clean"], termination=o["termination"]))


async def match_one(chat, key, question, own, cand, cache, max_tokens):
    if key in cache:
        return
    prompt = MATCH_PROMPT.format(question=question[-4000:], a=own[-3000:], b=cand[-3000:])
    r = await chat.chat([{"role": "user", "content": prompt}], max_tokens=max_tokens, temperature=0.0)
    t = r["outputs"][0]["text"].strip().upper()
    last = re.findall(r"\b(SAME|DIFFERENT|NONE)\b", t)  # reasoning models: take the final word they give
    v = last[-1] if last else None
    cache.put(dict(cache_key=key, verdict=v, raw=t[-200:], n_in=r["n_in"], n_out=r["n_out"]))


def redo_cut(cache, mt, new_mt):
    """Forget cached GLM outputs that used the whole max_tokens budget, so they are asked again with new_mt."""
    # cut = used exactly a token cap (the default or an earlier, smaller redo budget); a finished redo is never 2^k
    cut = [k for k, r in cache.rows.items()
           if mt <= r.get("n_out", 0) < new_mt and r["n_out"] & (r["n_out"] - 1) == 0]
    for k in cut:
        del cache.rows[k]
    print(f"{len(cut)} GLM outputs cut at {mt} tokens: asking again with {new_mt}", flush=True)
    return new_mt


def letter_of(text):
    """JudgeBench multiple-choice answers end with the letter written five times (same rule as analyze.letter)."""
    x = re.findall(r"\b([A-J])\1{4}\b", text or "")
    return x[-1] if x else None


def make_matcher(name):
    m = MATCHERS[name]
    import tinker
    from tinker_cookbook import renderers
    from common import TinkerChat, load_env
    load_env()
    chat = TinkerChat(m["spec"], tinker.ServiceClient())
    tok = chat.client.get_tokenizer()
    chat.renderer_name = m["renderer"]
    chat.renderer = renderers.get_renderer(m["renderer"], tok, model_name=m["spec"]["model"])
    chat.stop = chat.renderer.get_stop_sequences()
    return chat


async def extend_one(chat, job, cache):
    """Rerun a cut-off output from the beginning: same prompt, T=0.7, budget = everything the context allows."""
    key = f"{job['kind']}|{job['model']}|{job['qid']}"
    if key in cache:
        return
    from tinker import types
    prompt = chat.renderer.build_generation_prompt(job["messages"]).to_ints()
    budget = CTX - len(prompt) - 16
    params = types.SamplingParams(max_tokens=budget, temperature=0.7, stop=chat.stop)
    res = await chat.client.sample_async(prompt=types.ModelInput.from_ints(prompt), num_samples=1,
                                         sampling_params=params)
    toks = list(res.sequences[0].tokens)
    msg, term = chat.renderer.parse_response(toks)
    cache.put(dict(cache_key=key, kind=job["kind"], bench=job["bench"], model=job["model"], qid=job["qid"],
                   text=chat._renderers.get_text_content(msg), n_out=len(toks), budget=budget,
                   clean=bool(term.is_clean), n_prompt=len(prompt)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["solve", "match", "readout", "extend", "fill", "think", "belief", "audit"], required=True)
    ap.add_argument("--extended", action="store_true", help="match/readout: only items with extended text")
    ap.add_argument("--kinds", default="solve,judge", help="extend: which cut-off outputs to rerun")
    ap.add_argument("--open", default="", help="match/fill: an open judge outside Tinker, e.g. llama3.1-8b or "
                    "olmo3-7b-instruct (its own answers from open_ingest.py)")
    ap.add_argument("--out", default=str(HERE / "out"))
    ap.add_argument("--models", default=",".join(QWENS))
    ap.add_argument("--benches", default="bbeh,rb2math,judgebench")
    ap.add_argument("--limit", type=int, default=0, help="per (bench, judge) for a pilot")
    ap.add_argument("--concurrency", type=int, default=48)
    ap.add_argument("--ckpts", default="A,25,50,75,C", help="which checkpoints to read")
    ap.add_argument("--matcher", default="glm5.3-flash", choices=list(MATCHERS))
    ap.add_argument("--redo-cut", type=int, default=0, help="fill/belief (open judges): GLM outputs that hit the "
                    "matcher's max_tokens are asked again FROM SCRATCH with this many tokens (the newer row wins)")
    ap.add_argument("--samples", type=int, default=8, help="belief: own answers per question in total (sample 0 "
                    "is the existing solve)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    models = [m for m in a.models.split(",") if m]
    benches = set(a.benches.split(","))

    if a.phase == "solve":
        chats = make_chats([POOL_BY_KEY[m] for m in models])
        jobs = [j for j in map(json.loads, open(HERE / "inputs" / "solve_jobs.jsonl"))
                if j["model"] in models and j["bench"] in benches]
        if a.limit:
            jobs = [j for j in jobs if sum(1 for k in jobs[:jobs.index(j)] if k["model"] == j["model"]
                                           and k["bench"] == j["bench"]) < a.limit]
        cache = JsonlCache(out / "solves.jsonl")
        asyncio.run(run_jobs([lambda j=j: solve_one(chats[j["model"]], j, cache) for j in jobs],
                             a.concurrency, "solves"))
        return

    if a.phase == "extend":
        jobs = [j for j in load_gz(HERE / "inputs" / "extend_jobs.jsonl.gz")
                if j["model"] in models and j["bench"] in benches and j["kind"] in a.kinds.split(",")]
        if a.limit:
            jobs = jobs[: a.limit]
        chats = make_chats([POOL_BY_KEY[m] for m in models])
        # one file per kind, so solve and judge reruns can run at the same time without sharing a file
        cache = JsonlCache(out / ("extended.jsonl" if a.kinds == "solve" else f"extended_{a.kinds.replace(',', '_')}.jsonl"))
        print(f"{len(jobs)} outputs to rerun from scratch", flush=True)
        asyncio.run(run_jobs([lambda j=j: extend_one(chats[j["model"]], j, cache) for j in jobs],
                             a.concurrency, "extend"))
        return

    if a.phase == "think":
        from gen_vllm import build_jobs, pilot
        gjobs = build_jobs()
        if a.limit:
            gjobs = pilot(gjobs, a.limit)
        with gzip.open(HERE / "inputs" / "readout_jobs.jsonl.gz", "rt") as f:
            jj = {f"judge|{j['bench']}|{j['item_id']}": j for j in map(json.loads, f) if j["judge"] == "qwen3.5-4b"}
        gcache, rcache = JsonlCache(out / "think_gen.jsonl"), JsonlCache(out / "think_readouts.jsonl")
        cut = None
        if a.extended:  # outputs that used the whole context without finishing: generate again FROM SCRATCH
            cut = {k for k, r in gcache.rows.items() if r["finish"] != "stop" or "</think>" not in r["text"]}
            gcache, rcache = JsonlCache(out / "think_gen_rerun.jsonl"), JsonlCache(out / "think_readouts_rerun.jsonl")
            print(f"{len(cut)} cut-off thinking-on outputs to rerun", flush=True)
        jobs = []
        for m in models:
            chat, ctx = make_think_chat(m), THINK_IDS[m][1]
            for g in gjobs:
                if cut is not None and f"{m}|{g['key']}" not in cut:
                    continue
                jobs.append(lambda chat=chat, m=m, g=g, ctx=ctx: think_one(chat, m, g, ctx, jj.get(g["key"]), gcache, rcache))
        print(f"{len(jobs)} thinking-on generations ({len(models)} Qwens)", flush=True)
        asyncio.run(run_jobs(jobs, a.concurrency, "think"))
        return

    if a.phase == "fill":  # open judges: GLM settles the answers / verdicts exact parsing could not (open_ingest.py)
        chat, mt = make_matcher(a.matcher), MATCHERS[a.matcher]["max_tokens"]
        cache = JsonlCache(out / f"fill_glm5.3-flash_{a.open}.jsonl")
        if a.redo_cut:
            mt = redo_cut(cache, mt, a.redo_cut)
        fill = [json.loads(l) for l in open(HERE / "inputs" / f"fill_jobs_{a.open}.jsonl")]
        jobs = [(lambda x=x: match_one(chat, x["key"], x["question"], x["own"], x["cand"], cache, mt))
                if x["kind"] == "match" else
                (lambda x=x: verdict_one(chat, x["key"], x["transcript"], x["pairwise"], cache, mt)) for x in fill]
        asyncio.run(run_jobs(jobs, a.concurrency, "fill"))
        return

    ext = {}
    if a.extended:
        for f in sorted(out.glob("extended*.jsonl")):
            ext.update({r["cache_key"]: r["text"] for r in map(json.loads, open(f))})
    readout = [j for j in load_gz(HERE / "inputs" / "readout_jobs.jsonl.gz")
               if j["judge"] in models and j["bench"] in benches]
    if a.open:  # judge prompts/candidates are judge-independent: reuse qwen3.5-4b's, relabelled
        readout = [dict(j, judge=a.open) for j in load_gz(HERE / "inputs" / "readout_jobs.jsonl.gz")
                   if j["judge"] == "qwen3.5-4b" and j["bench"] in benches]
    if a.limit:
        seen, keep = {}, []
        for j in readout:
            k = (j["bench"], j["judge"])
            if seen.get(k, 0) < a.limit:
                keep.append(j)
                seen[k] = seen.get(k, 0) + 1
        readout = keep

    if a.phase == "audit":
        # Label audit (Nov 13): many RB2-Math "rejected" answers reach the same value as the "chosen" one, written
        # differently (rounding, notation, units). GLM compares each wrong candidate's final answer with each right
        # candidate's of the same question; candidate texts don't depend on the judge, so each pair is asked once.
        chat, mt = make_matcher(a.matcher), MATCHERS[a.matcher]["max_tokens"]
        cache = JsonlCache(out / "label_audit_glm5.3-flash.jsonl")
        by_q = collections.defaultdict(dict)  # qid -> item_id -> (gold, candidate text, question)
        for j in readout:
            if j["bench"] == "rb2math" and not j["pairwise"]:
                by_q[j["qid"]][j["item_id"]] = (j["gold"], j["candidates"][0], j["question"])
        jobs = []
        for qid, items in by_q.items():
            for w, (gw, cw, q) in items.items():
                for r, (gr, cr, _) in items.items():
                    if gw == 0 and gr == 1:
                        jobs.append(lambda key=f"audit|{w}|vs|{r}", q=q, cr=cr, cw=cw: match_one(chat, key, q, cr, cw, cache, mt))
        print(f"{len(jobs)} wrong-vs-right pairs", flush=True)
        asyncio.run(run_jobs(jobs, a.concurrency, "audit"))
        return

    if a.phase == "belief":
        # Belief strength: each judge answers each question samples-1 more times (same prompt and settings as the
        # first solve: T=0.7, whole context as budget); every new answer is compared with every candidate.
        # JudgeBench answers ending in a 5x letter are compared exactly in the analysis, so GLM sees only the rest.
        solve_jobs = {(j["model"], j["qid"]): j for j in map(json.loads, open(HERE / "inputs" / "solve_jobs.jsonl"))}
        cands = collections.defaultdict(list)  # (judge, qid) -> [(match key stem, question, candidate)]
        for j in readout:
            if j["bench"] == "bbeh":
                continue
            for ci, cand in enumerate(j["candidates"]):
                cands[(j["judge"], j["qid"])].append((f"{j['judge']}|{j['item_id']}|{ci}", j["question"], cand))
        matcher, mt = make_matcher(a.matcher), MATCHERS[a.matcher]["max_tokens"]
        if a.open:  # an open judge: its extra own answers were generated on GPU (cannon_belief/llama_gen.py) and
            # written to <its dir>/solves_k.jsonl by llama_belief_prep.py; only the GLM matching runs here
            odir = HERE / ("out_llama" if a.open == "llama3.1-8b" else f"out_open/{a.open}")
            chats = {}
            solve_jobs = {(a.open, q): j for (_, q), j in solve_jobs.items()}
            # matches go to the run's output dir (the Modal volume), not the container's copy of the repo
            scache, mcache = JsonlCache(odir / "solves_k.jsonl"), JsonlCache(out / f"matches_glm5.3-flash_k_{a.open}.jsonl")
        else:
            chats = make_chats([POOL_BY_KEY[m] for m in models])
            scache, mcache = JsonlCache(out / "solves_k.jsonl"), JsonlCache(out / "matches_glm5.3-flash_k.jsonl")
        if a.open and a.redo_cut:
            mt = redo_cut(mcache, mt, a.redo_cut)
        redo = None
        if a.extended:  # answers that used the whole context without finishing: answer again FROM SCRATCH
            redo = {k for k, r in scache.rows.items() if r["termination"] != "stop_sequence"}
            scache = JsonlCache(out / "solves_k_rerun.jsonl")
            mcache = JsonlCache(out / "matches_glm5.3-flash_k_rerun.jsonl")
            print(f"{len(redo)} cut-off own answers to answer again", flush=True)

        async def belief_one(jm, qid, s):
            job = solve_jobs[(jm, qid)]
            key = f"{jm}|{qid}|s{s}"
            if a.open and (key not in scache or not scache.rows[key]["clean"]):
                return  # cut off at the context limit: rerun from scratch on GPU first, matched afterwards
            if key not in scache:
                chat = chats[jm]
                n = chat.renderer.build_generation_prompt(job["messages"]).length
                n = n() if callable(n) else n
                r = await chat.chat(job["messages"], max_tokens=CTX - n - 16, temperature=0.7)
                o = r["outputs"][0]
                scache.put(dict(cache_key=key, model=jm, qid=qid, bench=job["bench"], sample=s, answer=o["text"],
                                n_out=o["n_out"], clean=o["clean"], termination=o["termination"]))
            own = scache.rows[key]["answer"]
            for stem, question, cand in cands[(jm, qid)]:
                if job["bench"] == "judgebench" and letter_of(own) and letter_of(cand):
                    continue
                await match_one(matcher, f"{stem}|s{s}", question, own, cand, mcache, mt)

        jobs = [lambda jm=jm, qid=qid, s=s: belief_one(jm, qid, s)
                for (jm, qid) in cands if (jm, qid) in solve_jobs for s in range(1, a.samples)
                if redo is None or f"{jm}|{qid}|s{s}" in redo]
        print(f"{len(cands)} (judge, question) pairs, {len(jobs)} new own answers", flush=True)
        asyncio.run(run_jobs(jobs, a.concurrency, "belief"))
        return

    if a.phase == "match":
        if not (out / "solves.jsonl").exists():  # a pilot dir has no solves: read the full run's
            out_solves = Path(str(out).replace("_pilot", "")) / "solves.jsonl"
        else:
            out_solves = out / "solves.jsonl"
        if a.open:
            out_solves = HERE / ("out_llama" if a.open == "llama3.1-8b" else f"out_open/{a.open}") / "solves.jsonl"
        solves = {r["cache_key"]: r for r in map(json.loads, open(out_solves))}
        if a.extended:  # only judges whose own answer was cut off, now with the finished answer
            solves = {k: dict(v, answer=ext[f"solve|{k}"]) for k, v in solves.items() if f"solve|{k}" in ext}
        chat, mt = make_matcher(a.matcher), MATCHERS[a.matcher]["max_tokens"]
        fname = MATCHERS[a.matcher]["file"].replace(
            ".jsonl", "_ext.jsonl" if a.extended else f"_{a.open}.jsonl" if a.open else ".jsonl")
        cache = JsonlCache(out / fname)
        jobs = []
        for j in readout:
            if j["bench"] == "bbeh":
                continue
            own = solves.get(f"{j['judge']}|{j['qid']}")
            if not own:
                continue
            for ci, cand in enumerate(j["candidates"]):
                key = f"{j['judge']}|{j['item_id']}|{ci}"
                jobs.append(lambda key=key, j=j, own=own, cand=cand: match_one(
                    chat, key, j["question"], own["answer"], cand, cache, mt))
        asyncio.run(run_jobs(jobs, a.concurrency, "matches"))
        return

    if a.extended:  # judgments whose transcript was cut off: read them again on the finished transcript
        readout = [dict(j, transcript=ext[f"judge|{j['judge']}|{j['item_id']}"]) for j in readout
                   if f"judge|{j['judge']}|{j['item_id']}" in ext]
    chats = make_chats([POOL_BY_KEY[m] for m in models])
    cache = JsonlCache(out / ("readouts_ext.jsonl" if a.extended else "readouts.jsonl"))
    jobs = [lambda j=j, ck=ck: readout_one(chats[j["judge"]], j, ck, cache)
            for j in readout for ck in checkpoints(j["transcript"], j["pairwise"]) if ck[0] in a.ckpts.split(",")]
    print(f"{len(readout)} judgments, {len(jobs)} checkpoint readouts", flush=True)
    asyncio.run(run_jobs(jobs, a.concurrency, "readouts"))


if __name__ == "__main__":
    main()
