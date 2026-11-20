"""Second fresh-question replication: open-ended math with integer answers (protocol: PROTOCOL.md, fixed before
the confirmatory run). Same writer, judges, judge prompt, audit prompt and Tinker plumbing as ../replication
(MMLU-Pro); only the questions and the answer parser differ.

Phases (each resumes from its cache; a hard spending cap is checked before every call):
  build   DAPO-Math-17k (deduplicated), minus RewardBench 2 Math prompts, fixed shuffle -> data/questions.jsonl
  gen     Nemotron-3.5-Super writes 6 answers per question; eligible pairs             -> data/gen.jsonl, pairs.jsonl
  judge   each judge picks the better response of each pair                           -> data/judge.jsonl
  solve   each judge answers each paired question 8 times                             -> data/solve.jsonl
  audit   Kimi-K3.1-Pro audits every wrong response                                   -> data/audit.jsonl
  cost    spend by phase / model

  python math_rep.py --phase gen --start 0 --n 80 --cap 300
"""
import argparse
import asyncio
import importlib.util
import json
import random
import re
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
_spec = importlib.util.spec_from_file_location("mmlupro", HERE.parent / "replication" / "mmlupro.py")
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
M.DATA = DATA  # timeouts.jsonl (counted against the cap) goes to this folder
from common import JsonlCache, load_env, run_jobs  # noqa: E402  (tinker_pool, put on sys.path by mmlupro)

JUDGES = M.JUDGES
PRE = ("Solve the following math problem step by step. The last line of your response should be of the form "
       "Answer: $Answer (without quotes) where $Answer is the answer to the problem.\n\n")
POST = "\n\nRemember to put your answer on its own line after \"Answer:\"."
OWN_TOKENS = 16384  # own answers (the MMLU-Pro run used the whole context; math answers are bounded here for cost)


def answer(text):
    """Parser (fixed on the pilot, before the confirmatory run): find the LAST answer marker in the text -- "Answer:",
    "answer is" or "\\boxed{" -- and read the integer that immediately follows it. $, *, \\( \\), \\boxed, \\text,
    spaces and thousands commas are ignored; "12.0" counts as 12. If what follows is not a plain integer (a fraction,
    an expression, "x = 5"), the answer is unparsed: no fallback to an earlier marker.
    Returns a canonical integer string or None."""
    t = text or ""
    hits = list(re.finditer(r"answer\s*:|answer\s+is\b|\\boxed\{", t, re.I))
    if not hits:
        return None
    seg = t[hits[-1].end():].split("\n\n")[0][:200]
    seg = re.sub(r"\\boxed\{|\\text\{|\\mathbf\{|\\[()\[\]]|[\$\*:]|\\[,!;]", "", seg).lstrip()
    seg = re.sub(r"(?<=\d)[, ](?=\d{3}(?!\d))", "", seg)
    m = re.match(r"\(?(-?\d+)(?:\.0+)?(?!\d|\.\d|/|\^|[A-Za-z])", seg)
    return str(int(m.group(1))) if m else None


def build():
    from datasets import load_dataset
    norm = lambda s: re.sub(r"\s+", " ", s).strip().lower()
    rb2 = load_dataset("allenai/reward-bench-2", split="test").to_pandas()
    rb2 = [norm(str(p)) for p, s in zip(rb2["prompt"], rb2["subset"]) if s == "Math"]
    rows, seen, dropped = [], set(), 0
    for i, r in enumerate(load_dataset("open-r1/DAPO-Math-17k-Processed", "en", split="train")):
        p, g = r["prompt"].strip(), str(r["solution"]).strip()
        q = norm(p)
        if q in seen or not re.fullmatch(r"-?\d+", g):
            continue
        seen.add(q)
        if any(q[:200] in x or x[:200] in q for x in rb2):
            dropped += 1
            continue
        rows.append(dict(qid=f"dapo-{i}", gold=str(int(g)), problem=p, question=PRE + p + POST))
    random.Random(20261120).shuffle(rows)
    DATA.mkdir(exist_ok=True)
    with open(DATA / "questions.jsonl", "w") as f:
        for k, r in enumerate(rows):
            f.write(json.dumps(dict(r, order=k)) + "\n")
    print(f"{len(rows)} questions; {dropped} dropped as RewardBench 2 Math overlaps")


def pairs_from_gen(gen, questions):
    out = []
    for q in questions:
        g = gen.get(f"gen|{q['qid']}")
        if not g:
            continue
        L = [answer(t) for t in g["texts"]]
        right = [i for i, x in enumerate(L) if x == q["gold"]]
        wrong = [i for i, x in enumerate(L) if x is not None and x != q["gold"]]
        if not right or not wrong:
            continue
        a_is_right = random.Random(zlib.crc32(q["qid"].encode())).random() < 0.5
        r, w = g["texts"][right[0]], g["texts"][wrong[0]]
        out.append(dict(qid=q["qid"], order=q["order"], gold=q["gold"], wrong_answer=L[wrong[0]], question=q["question"],
                        response_a=r if a_is_right else w, response_b=w if a_is_right else r,
                        wrong_pos="B" if a_is_right else "A"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True, choices=["build", "gen", "judge", "solve", "audit", "cost"])
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--n", type=int, default=80)
    ap.add_argument("--cap", type=float, default=300.0)
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
        print("total billed (all cache lines + timeouts)", round(M.Budget(1e9, caches.values()).spent, 2))
        return
    budget = M.Budget(a.cap, caches.values())
    print(f"spent so far ${budget.spent:.2f} of cap ${a.cap}", flush=True)
    qs = [q for q in M.load_jsonl(DATA / "questions.jsonl") if a.start <= q["order"] < a.start + a.n]
    judges = a.judges.split(",")

    if a.phase == "gen":
        chat, cache = M.make_chat(M.WRITER, M.WRITER_RENDERER), caches["gen"]

        async def one(q):
            k = f"gen|{q['qid']}"
            if k in cache:
                return
            outs, n_in, n_out, cost = await M.sample(chat, budget, [{"role": "user", "content": q["question"]}], 8192, 1.0, 6)
            cache.put(dict(cache_key=k, model="nemotron3.5-super", qid=q["qid"], texts=[o["text"] for o in outs],
                           clean=[o["clean"] for o in outs], n_in=n_in, n_out=n_out, cost=cost))
        asyncio.run(run_jobs([lambda q=q: one(q) for q in qs], a.concurrency, "gen"))
        P = pairs_from_gen(cache.rows, qs)
        allp = {p["qid"]: p for p in M.load_jsonl(DATA / "pairs.jsonl")}
        allp.update({p["qid"]: p for p in P})
        with open(DATA / "pairs.jsonl", "w") as f:
            for p in sorted(allp.values(), key=lambda p: p["order"]):
                f.write(json.dumps(p) + "\n")
        print(f"eligible pairs in this range: {len(P)} of {len(qs)} questions")
        return

    pairs = [p for p in M.load_jsonl(DATA / "pairs.jsonl") if a.start <= p["order"] < a.start + a.n]
    if a.phase in ("judge", "solve"):
        chats = {j: M.make_chat(M.PRICES[j]) for j in judges}
        cache = caches[a.phase]

        async def judge_one(j, p):
            k = f"judge|{j}|{p['qid']}"
            if k in cache:
                return
            msg = M.JUDGE_PROMPT.format(question=p["question"], response_a=p["response_a"], response_b=p["response_b"])
            outs, n_in, n_out, cost = await M.sample(chats[j], budget, [{"role": "user", "content": msg}], 8192, 0.7, 1)
            cache.put(dict(cache_key=k, model=j, qid=p["qid"], text=outs[0]["text"], verdict=M.verdict(outs[0]["text"]),
                           clean=outs[0]["clean"], n_in=n_in, n_out=n_out, cost=cost))

        async def solve_one(j, p):
            k = f"solve|{j}|{p['qid']}"
            if k in cache:
                return
            outs, n_in, n_out, cost = await M.sample(chats[j], budget, [{"role": "user", "content": p["question"]}],
                                                     OWN_TOKENS, 0.7, 8)
            cache.put(dict(cache_key=k, model=j, qid=p["qid"], texts=[o["text"] for o in outs],
                           answers=[answer(o["text"]) for o in outs], clean=[o["clean"] for o in outs],
                           n_in=n_in, n_out=n_out, cost=cost))
        fn = judge_one if a.phase == "judge" else solve_one
        asyncio.run(run_jobs([lambda j=j, p=p: fn(j, p) for p in pairs for j in judges], a.concurrency, a.phase))
        return

    if a.phase == "audit":
        chat, cache = M.make_chat(M.AUDITOR, "kimi_k31_pro_high_reasoning"), caches["audit"]

        async def audit_one(p):
            k = f"audit|{p['qid']}"
            if k in cache:
                return
            good = "B" if p["wrong_pos"] == "A" else "A"
            body = f"[QUESTION]\n{p['question']}\n\n[RESPONSE A]\n{p['response_a']}\n\n[RESPONSE B]\n{p['response_b']}"
            msg = M.AUDIT_PROMPT.format(good=good, bad=p["wrong_pos"], prompt=body)
            outs, n_in, n_out, cost = await M.sample(chat, budget, [{"role": "user", "content": msg}], 32768, 0.0, 1)
            m = re.findall(r"AUDIT:\s*\**\s*(LABEL_OK|LABEL_WRONG|CONTESTED)", outs[0]["text"] or "")
            cache.put(dict(cache_key=k, model="kimi3.1pro", qid=p["qid"], text=outs[0]["text"],
                           verdict=m[-1] if m else None, n_in=n_in, n_out=n_out, cost=cost))
        asyncio.run(run_jobs([lambda p=p: audit_one(p) for p in pairs], a.concurrency, "audit"))


if __name__ == "__main__":
    main()
