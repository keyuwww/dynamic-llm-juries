"""Fresh-question replication on MMLU-Pro (protocol: PROTOCOL.md, frozen before data collection).

Phases (each resumes from its cache; a hard Tinker spending cap is checked before every call):
  build   questions: MMLU-Pro test minus JudgeBench, fixed shuffle         -> data/questions.jsonl
  gen     Nemotron-3.5-Super writes 6 answers per question; eligible pairs      -> data/gen.jsonl, data/pairs.jsonl
  judge   each judge picks the better response of each pair                -> data/judge.jsonl
  solve   each judge answers each paired question 8 times                  -> data/solve.jsonl
  audit   Kimi-K3.1-Pro audits wrong responses any judge believes >= 4/7   -> data/audit.jsonl
  cost    print spend by phase / model from the caches

  python mmlupro.py --phase gen --start 0 --n 80 --cap 450      (pilot = questions 0..79)
Run with a Python that has tinker + tinker-cookbook + datasets (see README in this folder).
"""
import argparse
import asyncio
import json
import random
import re
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
sys.path.insert(0, str(HERE.parents[1] / "tinker_pool"))
from common import POOL_BY_KEY, JsonlCache, call_cost, load_env, run_jobs  # noqa: E402

SUFFIX = ("\nIf you cannot determine the correct multiple-choice answer, take your best guess. Once you have your "
          "answer, please duplicate that letter five times in a single string. For example, if the answer is K, then "
          "write KKKKK.\nLet's think step by step.")
JUDGE_PROMPT = """You are comparing two AI assistant responses to the same question. Decide which response is better.

[QUESTION]
{question}

[RESPONSE A]
{response_a}

[RESPONSE B]
{response_b}

Which response is better -- more correct, more complete, more rigorous? Judge substance, not style or length.
Reason briefly, then end with exactly one line: "VERDICT: A" or "VERDICT: B"."""
AUDIT_PROMPT = """You are auditing a benchmark label. A question and two AI responses are given. The benchmark says Response {good}
is the correct one (its final answer is the dataset's gold answer) and Response {bad} is wrong.

{prompt}

Solve the question yourself carefully. Then decide whether Response {bad}'s final answer is really wrong:
- LABEL_OK: Response {bad}'s final answer is wrong and the gold answer is right.
- LABEL_WRONG: Response {bad}'s final answer is actually correct (the gold is wrong, or both are correct).
- CONTESTED: the question is ambiguous or more than one option is defensible.
End with exactly one line: "AUDIT: LABEL_OK", "AUDIT: LABEL_WRONG" or "AUDIT: CONTESTED"."""  # verbatim: validation/build_glm_audit.py JB (importing it would rerun that script)
JUDGES = ["qwen3.6-35b-a3b", "qwen3.5-9b", "deepseek-v4.1-flash", "kimi-k2.6"]  # no NVIDIA judge: the writer is NVIDIA
TIMEOUT = 1200  # seconds per call; a timed-out call is retried on the next run (Kimi calls sometimes hang)
CTX = 65536  # as the main study's own-answer budget
WRITER = dict(key="nemotron3.5-super", model="nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16", price_in=0.57, price_out=1.44)
WRITER_RENDERER = "nemotron3_ultra_disable_thinking"
AUDITOR = dict(key="kimi3.1pro", model="moonshotai/Kimi-K3.1-Pro:peft:262144", price_in=6.00, price_out=25.00)
PRICES = {**{k: POOL_BY_KEY[k] for k in JUDGES}, "nemotron3.5-super": WRITER, "kimi3.1pro": AUDITOR}
# list prices (Nov 18 pricing page) where common.py is stale
PRICES["qwen3.6-35b-a3b"] = dict(PRICES["qwen3.6-35b-a3b"], price_in=0.45)
PRICES["qwen3.5-9b"] = dict(PRICES["qwen3.5-9b"], price_in=0.30, price_out=0.807)


def letter(text):
    x = re.findall(r"\b([A-J])\1{4}\b", text or "")
    return x[-1] if x else None


def verdict(text):
    m = re.findall(r"VERDICT:\s*\**\s*([AB])\b", text or "", re.I)
    return m[-1].upper() if m else None


def file_spend(caches):
    """Every billed call, including duplicate cache lines (two processes once wrote the same key)."""
    tot = 0.0
    for c in caches:
        if c.path.exists():
            tot += sum(json.loads(l).get("cost", 0.0) for l in open(c.path) if l.strip())
    return tot


class Budget:
    """Hard cap: spent (from every cache) + reserved (worst case of in-flight calls) must stay under the cap."""

    def __init__(self, cap, caches):
        self.cap, self.reserved = cap, 0.0
        self.spent = file_spend(caches)
        to = DATA / "timeouts.jsonl"
        self.spent += sum(json.loads(l)["worst_cost"] for l in open(to)) if to.exists() else 0.0

    def reserve(self, amount):
        if self.spent + self.reserved + amount > self.cap:
            raise RuntimeError(f"budget cap ${self.cap} reached (spent ${self.spent:.2f}, reserved ${self.reserved:.2f})")
        self.reserved += amount

    def settle(self, reserved, actual):
        self.reserved -= reserved
        self.spent += actual


def make_chat(spec, renderer=None):
    import tinker
    from tinker_cookbook import renderers, tokenizer_utils
    from common import TinkerChat, pick_renderer
    chat = TinkerChat.__new__(TinkerChat)
    chat.spec, chat._renderers = spec, renderers
    chat.client = tinker.ServiceClient().create_sampling_client(base_model=spec["model"])
    base = spec["model"].split(":")[0]
    tok = tokenizer_utils.get_tokenizer(base) if "Kimi-K3" in base else chat.client.get_tokenizer()
    chat.renderer_name = renderer or pick_renderer(spec["model"], "off")
    chat.renderer = renderers.get_renderer(chat.renderer_name, tok, model_name=base if "Kimi-K3" in base else spec["model"])
    chat.stop = chat.renderer.get_stop_sequences()
    return chat


async def sample(chat, budget, messages, max_tokens, temperature, n):
    """One Tinker call with a worst-case reservation; returns (outputs, n_in, n_out, cost)."""
    from tinker import types
    prompt = chat.renderer.build_generation_prompt(messages)
    n_in = prompt.length() if callable(prompt.length) else prompt.length
    max_tokens = min(max_tokens, CTX - n_in - 16)
    spec = PRICES[chat.spec["key"]]
    worst = call_cost(spec, n_in, max_tokens * n)
    budget.reserve(worst)
    actual = 0.0
    try:
        res = await asyncio.wait_for(chat.client.sample_async(prompt=prompt, num_samples=n, sampling_params=types.SamplingParams(
            max_tokens=max_tokens, temperature=temperature, stop=chat.stop)), timeout=TIMEOUT)
        outs = []
        for seq in res.sequences:
            toks = list(seq.tokens)
            msg, term = chat.renderer.parse_response(toks)
            outs.append(dict(text=chat._renderers.get_text_content(msg), n_out=len(toks), clean=bool(term.is_clean)))
        n_out = sum(o["n_out"] for o in outs)
        actual = call_cost(spec, n_in, n_out)
        return outs, n_in, n_out, actual
    except asyncio.TimeoutError:
        actual = worst  # may still be billed: count the worst case against the cap
        with open(DATA / "timeouts.jsonl", "a") as f:
            f.write(json.dumps(dict(model=chat.spec["key"], worst_cost=worst)) + "\n")
        raise
    finally:
        budget.settle(worst, actual)


def build():
    from datasets import load_dataset
    sys.path.insert(0, str(HERE.parents[1] / "tinker_pool"))
    from data import load_judgebench
    norm = lambda s: re.sub(r"\s+", " ", s).strip().lower()
    jb = [norm(it["question"].split("\n(A)")[0]) for it in load_judgebench()]
    jb_set = set(jb)
    rows = []
    for r in load_dataset("TIGER-Lab/MMLU-Pro", split="test"):
        q = norm(r["question"])
        if q in jb_set or any(q and q in j for j in jb):
            continue
        opts = "\n".join(f"({chr(65 + i)}) {o}" for i, o in enumerate(r["options"]))
        rows.append(dict(qid=f"mmlupro-{r['question_id']}", category=r["category"], gold=r["answer"],
                         n_options=len(r["options"]), question=f"{r['question']}\n{opts}{SUFFIX}"))
    rows.sort(key=lambda x: int(x["qid"].split("-")[1]))
    random.Random(20261118).shuffle(rows)
    DATA.mkdir(exist_ok=True)
    with open(DATA / "questions.jsonl", "w") as f:
        for i, r in enumerate(rows):
            f.write(json.dumps(dict(r, order=i)) + "\n")
    print(f"{len(rows)} MMLU-Pro questions not in JudgeBench (excluded {12032 - len(rows)})")


def load_jsonl(p):
    return [json.loads(l) for l in open(p)] if Path(p).exists() else []


def pairs_from_gen(gen, questions):
    out = []
    for q in questions:
        g = gen.get(f"gen|{q['qid']}")
        if not g:
            continue
        L = [letter(t) for t in g["texts"]]
        right = [i for i, x in enumerate(L) if x == q["gold"]]
        wrong = [i for i, x in enumerate(L) if x and x != q["gold"]]
        if not right or not wrong:
            continue
        a_is_right = random.Random(zlib.crc32(q["qid"].encode())).random() < 0.5
        r, w = g["texts"][right[0]], g["texts"][wrong[0]]
        out.append(dict(qid=q["qid"], order=q["order"], category=q["category"], gold=q["gold"],
                        wrong_letter=L[wrong[0]], question=q["question"], response_a=r if a_is_right else w,
                        response_b=w if a_is_right else r, wrong_pos="B" if a_is_right else "A"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True, choices=["build", "gen", "judge", "solve", "audit", "cost"])
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--n", type=int, default=80)
    ap.add_argument("--cap", type=float, required=False, default=450.0)
    ap.add_argument("--concurrency", type=int, default=48)
    ap.add_argument("--judges", default=",".join(JUDGES))
    a = ap.parse_args()
    if a.phase == "build":
        return build()
    load_env()
    caches = {n: JsonlCache(DATA / f"{n}.jsonl") for n in ["gen", "judge", "solve", "audit"]}
    if a.phase == "cost":
        for n, c in caches.items():
            by = {}
            for r in c.rows.values():
                by[r["model"]] = by.get(r["model"], 0) + r.get("cost", 0)
            print(n, {k: round(v, 2) for k, v in by.items()}, round(sum(by.values()), 2))
        print("total billed (all cache lines + timeouts)", round(Budget(1e9, caches.values()).spent, 2))
        return
    budget = Budget(a.cap, caches.values())
    print(f"spent so far ${budget.spent:.2f} of cap ${a.cap}", flush=True)
    qs = [q for q in load_jsonl(DATA / "questions.jsonl") if a.start <= q["order"] < a.start + a.n]
    judges = a.judges.split(",")

    if a.phase == "gen":
        chat, cache = make_chat(WRITER, WRITER_RENDERER), caches["gen"]

        async def one(q):
            k = f"gen|{q['qid']}"
            if k in cache:
                return
            outs, n_in, n_out, cost = await sample(chat, budget, [{"role": "user", "content": q["question"]}], 8192, 1.0, 6)
            cache.put(dict(cache_key=k, model="nemotron3.5-super", qid=q["qid"], texts=[o["text"] for o in outs],
                           clean=[o["clean"] for o in outs], n_in=n_in, n_out=n_out, cost=cost))
        asyncio.run(run_jobs([lambda q=q: one(q) for q in qs], a.concurrency, "gen"))
        P = pairs_from_gen(cache.rows, qs)
        allp = {p["qid"]: p for p in load_jsonl(DATA / "pairs.jsonl")}
        allp.update({p["qid"]: p for p in P})
        with open(DATA / "pairs.jsonl", "w") as f:
            for p in sorted(allp.values(), key=lambda p: p["order"]):
                f.write(json.dumps(p) + "\n")
        print(f"eligible pairs in this range: {len(P)} of {len(qs)} questions")
        return

    pairs = [p for p in load_jsonl(DATA / "pairs.jsonl") if a.start <= p["order"] < a.start + a.n]
    if a.phase in ("judge", "solve"):
        chats = {j: make_chat(PRICES[j]) for j in judges}
        cache = caches[a.phase]

        async def judge_one(j, p):
            k = f"judge|{j}|{p['qid']}"
            if k in cache:
                return
            msg = JUDGE_PROMPT.format(question=p["question"], response_a=p["response_a"], response_b=p["response_b"])
            outs, n_in, n_out, cost = await sample(chats[j], budget, [{"role": "user", "content": msg}], 8192, 0.7, 1)
            cache.put(dict(cache_key=k, model=j, qid=p["qid"], text=outs[0]["text"], verdict=verdict(outs[0]["text"]),
                           clean=outs[0]["clean"], n_in=n_in, n_out=n_out, cost=cost))

        async def solve_one(j, p):
            k = f"solve|{j}|{p['qid']}"
            if k in cache:
                return
            outs, n_in, n_out, cost = await sample(chats[j], budget, [{"role": "user", "content": p["question"]}], CTX, 0.7, 8)
            cache.put(dict(cache_key=k, model=j, qid=p["qid"], texts=[o["text"] for o in outs],
                           letters=[letter(o["text"]) for o in outs], clean=[o["clean"] for o in outs],
                           n_in=n_in, n_out=n_out, cost=cost))
        fn = judge_one if a.phase == "judge" else solve_one
        asyncio.run(run_jobs([lambda j=j, p=p: fn(j, p) for p in pairs for j in judges], a.concurrency, a.phase))
        return

    if a.phase == "audit":
        solve = caches["solve"].rows
        chat, cache = make_chat(AUDITOR, "kimi_k31_pro_high_reasoning"), caches["audit"]

        def believed(p):
            for j in JUDGES:
                s = solve.get(f"solve|{j}|{p['qid']}")
                if not s:
                    continue
                L = [x for x in s["letters"][1:] if x]
                if len(L) >= 5 and round(7 * sum(x == p["wrong_letter"] for x in L) / len(L)) >= 4:
                    return True
            return False

        async def audit_one(p):
            k = f"audit|{p['qid']}"
            if k in cache:
                return
            good = "B" if p["wrong_pos"] == "A" else "A"
            body = f"[QUESTION]\n{p['question']}\n\n[RESPONSE A]\n{p['response_a']}\n\n[RESPONSE B]\n{p['response_b']}"
            msg = AUDIT_PROMPT.format(good=good, bad=p["wrong_pos"], prompt=body)
            outs, n_in, n_out, cost = await sample(chat, budget, [{"role": "user", "content": msg}], 32768, 0.0, 1)
            m = re.findall(r"AUDIT:\s*\**\s*(LABEL_OK|LABEL_WRONG|CONTESTED)", outs[0]["text"] or "")
            cache.put(dict(cache_key=k, model="kimi3.1pro", qid=p["qid"], text=outs[0]["text"],
                           verdict=m[-1] if m else None, n_in=n_in, n_out=n_out, cost=cost))
        todo = [p for p in pairs if believed(p)]
        print(f"{len(todo)} wrong responses believed >= 4/7 by some judge", flush=True)
        asyncio.run(run_jobs([lambda p=p: audit_one(p) for p in todo], a.concurrency, "audit"))


if __name__ == "__main__":
    main()
