"""Tinker jobs for the beyond-capability study (runs inside Modal, see modal_app.py). Every output gets the
whole context window as its token budget; a sample that still stops at the limit is rerun from scratch
(fresh sample, same prompt) up to --retries times, and the number of tries is recorded.

  solve  each model answers every BBEH question --k times (thinking off for the judges; Kimi with high
         reasoning)                                                     -> out/solves_<model>.jsonl
  judge  each judge grades every candidate under --conds (none | gold | strong | self | verify)
                                                                        -> out/judge_<model>.jsonl
  fill   GLM-5.3-Flash reads the verdict where a transcript has no parseable VERDICT line
                                                                        -> out/fill_glm.jsonl
"""
import argparse
import asyncio
import collections
import gzip
import json
import random
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
from bc_common import (BBEH_SUFFIX, BFF_GRADER, GLM, JUDGES, MODELS, STRONG, VERDICT_FILL_PROMPT,  # noqa: E402
                       bff_judge_messages, judge_messages, norm_answer, parse_verdict, render_conv, same_answer)
from common import JsonlCache, load_env  # noqa: E402


class Chat:
    def __init__(self, key, service):
        from tinker_cookbook import renderers
        model, rname, ctx = (GLM if key == "glm" else MODELS[key])
        self.key, self.ctx, self._r = key, ctx, renderers
        self.client = service.create_sampling_client(base_model=model)
        if "Kimi" in model:  # TML-renderer model: the cookbook's tokenizer adapter (custom HF code accepted via stdin)
            from tinker_cookbook import tokenizer_utils
            tok = tokenizer_utils.get_tokenizer(model.split(":")[0])
        else:
            tok = self.client.get_tokenizer()
        self.renderer = renderers.get_renderer(rname, tok, model_name=model.split(":")[0])
        self.stop = self.renderer.get_stop_sequences()

    async def sample(self, messages, n=1, temperature=0.7, max_tokens=None, retries=3):
        """n samples with budget = whole context; cut-off samples are redrawn from scratch (up to `retries`)."""
        from tinker import types
        prompt = self.renderer.build_generation_prompt(messages)
        n_in = prompt.length() if callable(prompt.length) else prompt.length
        budget = max_tokens or (self.ctx - n_in - 16)

        async def draw(k):
            for attempt in range(6):
                try:
                    params = types.SamplingParams(max_tokens=budget, temperature=temperature, stop=self.stop)
                    res = await self.client.sample_async(prompt=prompt, num_samples=k, sampling_params=params)
                    break
                except Exception as e:  # noqa: BLE001 -- transient API errors: back off and retry
                    if attempt == 5:
                        raise
                    print(f"[retry {attempt}] {self.key}: {type(e).__name__}: {str(e)[:200]}", flush=True)
                    await asyncio.sleep(10 * (attempt + 1) + random.random() * 10)
            out = []
            for seq in res.sequences:
                toks = list(seq.tokens)
                msg, term = self.renderer.parse_response(toks)
                text = self._r.get_text_content(msg)
                thinking = ""
                if isinstance(msg.get("content"), list):
                    thinking = "".join(p.get("thinking", "") for p in msg["content"] if p.get("type") == "thinking")
                out.append(dict(text=text, n_think=len(thinking), n_out=len(toks), clean=bool(term.is_clean)))
            return out

        samples = await draw(n)
        for i, s in enumerate(samples):
            tries = 1
            while not s["clean"] and tries <= retries:
                s = (await draw(1))[0]
                tries += 1
            samples[i] = dict(s, tries=tries)
        return dict(samples=samples, n_in=n_in, budget=budget)


def load_jsonl(p):
    p = Path(p)
    return [json.loads(l) for l in open(p)] if p.exists() else []


def pick_questions(qs, limit):
    """Pilot subset: spread across the 23 task blocks."""
    if not limit:
        return qs
    step = max(1, len(qs) // limit)
    return qs[::step][:limit]


async def run_all(coros, conc, label):
    sem = asyncio.Semaphore(conc)
    done = errors = 0
    t0 = time.time()

    async def wrap(c):
        nonlocal done, errors
        async with sem:
            try:
                await c
            except Exception as e:  # noqa: BLE001
                errors += 1
                print(f"[error] {type(e).__name__}: {str(e)[:300]}", flush=True)
            done += 1
            if done % 25 == 0 or done == len(coros):
                print(f"  {label}: {done}/{len(coros)} ({errors} errors, {time.time() - t0:.0f}s)", flush=True)

    await asyncio.gather(*(wrap(c) for c in coros))


def own_majority(solve_row):
    """Majority final answer over the model's samples (ties: first seen) and one sample text that gives it."""
    norms = [norm_answer(s["text"]) for s in solve_row["samples"]]
    groups = []  # [(rep_norm, [idx])]
    for i, a in enumerate(norms):
        if a is None:
            continue
        for g in groups:
            if same_answer(g[0], a):
                g[1].append(i)
                break
        else:
            groups.append((a, [i]))
    if not groups:
        return None, None, 0.0
    best = max(groups, key=lambda g: len(g[1]))
    return best[0], solve_row["samples"][best[1][0]]["text"], len(best[1]) / len(norms)


async def phase_solve(a, service, qs):
    for key in a.models.split(","):
        chat = Chat(key, service)
        cache = JsonlCache(Path(a.out) / f"solves_{key}.jsonl")

        async def one(q, chat=chat, cache=cache, key=key):
            ck = f"{key}|{q['id']}"
            if ck in cache:
                return
            # the exact prompt of the pool's BBEH answers: question + "...use the prefix 'The answer is:'"
            r = await chat.sample([{"role": "user", "content": q["input"] + BBEH_SUFFIX}], n=a.k, retries=a.retries)
            cache.put(dict(cache_key=ck, model=key, qid=q["id"], **r))

        await run_all([one(q) for q in qs], a.concurrency, f"solve {key}")


async def phase_judge(a, service, qs):
    qmap = {q["id"]: q for q in qs}
    with gzip.open(HERE / "inputs" / "candidates.jsonl.gz", "rt") as f:
        cands = [c for c in map(json.loads, f) if c["qid"] in qmap]
    conds = a.conds.split(",")
    strong = {r["qid"]: r for r in load_jsonl(Path(a.out) / f"solves_{STRONG}.jsonl")}
    for key in a.models.split(","):
        chat = Chat(key, service)
        cache = JsonlCache(Path(a.out) / f"judge_{key}{a.tag}.jsonl")
        # parallel apps write separate files (one per --tag); skip work already done in any of them
        done = {r["cache_key"] for p in Path(a.out).glob(f"judge_{key}[._]*") for r in load_jsonl(p)}
        own = {r["qid"]: r for r in load_jsonl(Path(a.out) / f"solves_{key}.jsonl")}
        jobs, skipped = [], collections.Counter()
        for cond in conds:
            for c in cands:
                if c["examinee"] == key.split("@")[0]:
                    continue  # never judge its own pool answer
                ref = None
                if cond == "gold":
                    ref = qmap[c["qid"]]["target"]
                elif cond == "strong":
                    s = strong.get(c["qid"])
                    if not s or not s["samples"][0]["clean"]:
                        skipped[cond] += 1
                        continue
                    ref = s["samples"][0]["text"]
                elif cond == "self":
                    s = own.get(c["qid"])
                    _, ref, _ = own_majority(s) if s else (None, None, 0)
                    if ref is None:
                        skipped[cond] += 1
                        continue
                n = a.votes_none if cond == "none" else 1
                jobs.append((cond, c, ref, n))
        print(f"judge {key}: {len(jobs)} jobs; skipped (no reference yet) {dict(skipped)}", flush=True)

        async def one(cond, c, ref, n, chat=chat, cache=cache, key=key):
            ck = f"{key}|{c['cid']}|{cond}"
            if ck in cache or ck in done:
                return
            msgs = judge_messages(cond, qmap[c["qid"]]["input"], c["answer"], ref)
            r = await chat.sample(msgs, n=n, retries=a.retries)
            for s in r["samples"]:
                s["verdict"] = parse_verdict(s["text"])
            cache.put(dict(cache_key=ck, judge=key, cid=c["cid"], qid=c["qid"], cond=cond, gold=c["gold"], **r))

        await run_all([one(*j) for j in jobs], a.concurrency, f"judge {key}")


async def phase_fill(a, service):
    chat = Chat("glm", service)
    cache = JsonlCache(Path(a.out) / "fill_glm.jsonl")
    todo = []
    for p in sorted(Path(a.out).glob("*judge_*.jsonl")):
        for r in load_jsonl(p):
            for i, s in enumerate(r["samples"]):
                if s["verdict"] is None and s["text"].strip():
                    todo.append((f"{r['cache_key']}|{i}", s["text"]))

    async def one(ck, text):
        if ck in cache:
            return
        r = await chat.sample([{"role": "user", "content": VERDICT_FILL_PROMPT.format(text=text[-6000:])}],
                              n=1, temperature=0.0, retries=a.retries)
        t = r["samples"][0]["text"].strip().upper()
        last = re.findall(r"\b(CORRECT|INCORRECT|NONE)\b", t)
        cache.put(dict(cache_key=ck, verdict=last[-1] if last else None, raw=t[-200:]))

    print(f"fill: {len(todo)} transcripts without a parseable verdict", flush=True)
    await run_all([one(*t) for t in todo], a.concurrency, "fill")


# ----------------------------------------------------------------------------- MMLU-Redux (moderate difficulty)
async def phase_esolve(a, service):
    """Answer every question in --qfile (rows with 'id' and 'prompt'), --k samples, whole context as budget."""
    qs = load_jsonl(HERE / a.qfile)
    for key in a.models.split(","):
        chat = Chat(key, service)
        cache = JsonlCache(Path(a.out) / f"esolves_{Path(a.qfile).stem}_{key}.jsonl")

        async def one(q, chat=chat, cache=cache, key=key):
            ck = f"{key}|{q['id']}"
            if ck in cache:
                return
            r = await chat.sample([{"role": "user", "content": q["prompt"]}], n=a.k, retries=a.retries)
            cache.put(dict(cache_key=ck, model=key, qid=q["id"], **r))

        await run_all([one(q) for q in qs], a.concurrency, f"esolve {key}")


MATH_EQ_PROMPT = """Two final answers to the same math problem are given. Decide whether they are mathematically equivalent
(same value or same set/expression; ignore formatting, LaTeX, units and equivalent forms such as 1/2 vs 0.5 vs \\frac{{1}}{{2}}).

[PROBLEM]
{problem}

[ANSWER 1 (reference)]
{gold}

[ANSWER 2]
{cand}

Reply with exactly one word: SAME or DIFFERENT."""


def math_final(text):
    """The final answer after the last 'The answer is:' (None if the response never states one)."""
    if not text or "answer is" not in text.lower():
        return None
    i = text.lower().rfind("answer is")
    a = text[i + len("answer is"):].lstrip(": ").strip().split("\n")[0].strip().rstrip(".")
    return a.strip("$ ") or None


def _canon(x):
    return re.sub(r"\\[dt]?frac", "frac", re.sub(r"[\s$\\{}()]", "", x or "")).lower() if x else None


async def phase_egrade(a, service):
    """GLM-5.3-Flash grades every MATH answer (all esolves_<stem>_*.jsonl) against the official answer."""
    qs = {q["id"]: q for q in load_jsonl(HERE / a.qfile)}
    stem = Path(a.qfile).stem
    chat = Chat("glm", service)
    cache = JsonlCache(Path(a.out) / f"egrades_{stem}.jsonl")
    todo = []
    for p in sorted(Path(a.out).glob(f"esolves_{stem}_*.jsonl")):
        if a.match and a.match not in p.name:
            continue
        for r in load_jsonl(p):
            for i, smp in enumerate(r["samples"] if "samples" in r else [dict(text=r["text"])]):
                todo.append((f"{p.stem}|{r['qid']}|{i}", qs[r["qid"]], smp["text"]))

    async def one(ck, q, text):
        if ck in cache:
            return
        cand = math_final(text)
        if cand is None:
            cache.put(dict(cache_key=ck, verdict=0, how="no final answer"))
            return
        if _canon(cand) == _canon(q["gold"]):
            cache.put(dict(cache_key=ck, verdict=1, how="exact"))
            return
        msg = MATH_EQ_PROMPT.format(problem=q["prompt"].split("\n\nThink step by step")[0][-4000:], gold=q["gold"], cand=cand[-2000:])
        r = await chat.sample([{"role": "user", "content": msg}], n=1, temperature=0.0, retries=a.retries)
        t = r["samples"][0]["text"].strip().upper()
        last = re.findall(r"\b(SAME|DIFFERENT)\b", t)
        cache.put(dict(cache_key=ck, verdict=None if not last else int(last[-1] == "SAME"), how="glm", cand=cand[-300:]))

    print(f"egrade: {len(todo)} answers", flush=True)
    await run_all([one(*t) for t in todo], a.concurrency, "egrade")


# ----------------------------------------------------------------------------- BFF-Bench
async def phase_bff_solve(a, service):
    qs = load_jsonl(HERE / "inputs" / "bff_questions.jsonl")
    for key in a.models.split(","):
        chat = Chat(key, service)
        cache = JsonlCache(Path(a.out) / f"bff_solves_{key}.jsonl")

        async def one(q, chat=chat, cache=cache, key=key):
            ck = f"{key}|{q['id']}"
            if ck in cache:
                return
            r = await chat.sample(q["messages"], n=a.k, retries=a.retries)
            cache.put(dict(cache_key=ck, model=key, qid=q["id"], **r))

        await run_all([one(q) for q in qs], a.concurrency, f"bff solve {key}")


async def phase_bff_grade(a, service):
    """GLM-5.3-Flash grades every BFF solve sample against the expert reference (the 'did it solve it' label)."""
    qs = {q["id"]: q for q in load_jsonl(HERE / "inputs" / "bff_questions.jsonl")}
    chat = Chat("glm", service)
    cache = JsonlCache(Path(a.out) / "bff_grades_glm.jsonl")
    todo = []
    for p in sorted(Path(a.out).glob("bff_solves_*.jsonl")):
        for r in load_jsonl(p):
            q = qs[r["qid"]]
            if not q["ref"]:
                continue
            for i, smp in enumerate(r["samples"]):
                todo.append((f"{r['cache_key']}|{i}", q, smp["text"]))

    async def one(ck, q, text):
        if ck in cache:
            return
        conv = q["messages"] + [{"role": "assistant", "content": text}]
        msg = BFF_GRADER.format(conversation=render_conv(conv), ref=q["ref"])
        r = await chat.sample([{"role": "user", "content": msg}], n=1, temperature=0.0, retries=a.retries)
        cache.put(dict(cache_key=ck, verdict=parse_verdict(r["samples"][0]["text"]), raw=r["samples"][0]["text"][-400:]))

    print(f"bff grade: {len(todo)} answers", flush=True)
    await run_all([one(*t) for t in todo], a.concurrency, "bff grade")


async def phase_bff_judge(a, service):
    items = load_jsonl(HERE / "inputs" / "bff_items.jsonl")
    conds = a.conds.split(",")
    strong = {r["qid"]: r for r in load_jsonl(Path(a.out) / f"bff_solves_{STRONG}.jsonl")}
    for key in a.models.split(","):
        chat = Chat(key, service)
        cache = JsonlCache(Path(a.out) / f"bff_judge_{key}{a.tag}.jsonl")
        done = {r["cache_key"] for p in Path(a.out).glob(f"bff_judge_{key}[._]*") for r in load_jsonl(p)}
        own = {r["qid"]: r for r in load_jsonl(Path(a.out) / f"bff_solves_{key}.jsonl")}
        jobs, skipped = [], collections.Counter()
        for cond in conds:
            for it in items:
                qk = f"{it['uid']}|{it['turn']}"
                ref = None
                if cond == "human":
                    ref = it["ref"]
                elif cond in ("strong", "self"):
                    s = (strong if cond == "strong" else own).get(qk)
                    if not s or not s["samples"][0]["clean"]:
                        skipped[cond] += 1
                        continue
                    ref = s["samples"][0]["text"]
                jobs.append((cond, it, ref, a.votes_none if cond == "none" else 1))
        print(f"bff judge {key}: {len(jobs)} jobs; skipped {dict(skipped)}", flush=True)

        async def one(cond, it, ref, n, chat=chat, cache=cache, key=key):
            ck = f"{key}|{it['id']}|{cond}"
            if ck in cache or ck in done:
                return
            r = await chat.sample(bff_judge_messages(cond, it["conv"], ref), n=n, retries=a.retries)
            for smp in r["samples"]:
                smp["verdict"] = parse_verdict(smp["text"])
            cache.put(dict(cache_key=ck, judge=key, item=it["id"], qid=f"{it['uid']}|{it['turn']}", cond=cond,
                           gold=it["human"], examinee=it["examinee"], **r))

        await run_all([one(*j) for j in jobs], a.concurrency, f"bff judge {key}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True, choices=["solve", "judge", "fill", "bff_solve", "bff_grade", "bff_judge", "esolve", "egrade"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--models", default=",".join(JUDGES))
    ap.add_argument("--conds", default="none,gold,verify")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--votes-none", type=int, default=3)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--concurrency", type=int, default=64)
    ap.add_argument("--qfile", default="inputs/mmlu_questions.jsonl")
    ap.add_argument("--tag", default="", help="suffix of the output file, so parallel apps never share a file")
    ap.add_argument("--match", default="", help="egrade: only grade answer files whose name contains this")
    a = ap.parse_args()
    load_env()
    import tinker
    service = tinker.ServiceClient()
    qs = pick_questions(load_jsonl(HERE / "inputs" / "questions.jsonl"), a.limit)
    if a.phase == "esolve":
        asyncio.run(phase_esolve(a, service))
    elif a.phase == "egrade":
        asyncio.run(phase_egrade(a, service))
    elif a.phase.startswith("bff_"):
        asyncio.run({"bff_solve": phase_bff_solve, "bff_grade": phase_bff_grade, "bff_judge": phase_bff_judge}[a.phase](a, service))
    elif a.phase == "solve":
        asyncio.run(phase_solve(a, service, qs))
    elif a.phase == "judge":
        asyncio.run(phase_judge(a, service, qs))
    else:
        asyncio.run(phase_fill(a, service))


if __name__ == "__main__":
    main()
