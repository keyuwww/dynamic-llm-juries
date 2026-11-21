"""Repeated verdicts from one judge: the self-consistency baseline for the majority-vote test (Nov 21 strict review,
item B4: "compare repeated judgments from one model, a cross-family vote, and a simple baseline"). Tinker calls.

For every original item on which all seven judges gave a parseable verdict, each judge still served on Tinker (all
but Nemotron-3-Nano, which the API no longer serves) grades the item TWICE MORE with exactly the messages of its
original verdict (inputs/readout_jobs*.jsonl.gz), thinking off, temperature 0.7 as in the original run, but with a
32K-token budget so that no output is cut off (the original cut-off outputs were regenerated with a 64K budget).
Both draws come from one request (prefill paid once). A draw with no parseable verdict is drawn again, up to twice.

Votes are stored in the frame of jury_vote.py: RewardBench 2 Math and BFF-Bench 1 = CORRECT (approve the graded
answer); JudgeBench 1 = picks the WRONG response of the pair (gold 1 = response A is the better one).
As a check, the same parser is applied to each original transcript in the jobs file and compared with the verdict the
paper uses. Transcripts that were cut off in the pool run (and regenerated before the paper's verdict was read) yield
no verdict here and are skipped: 315 of 9,138 (Qwens and Nemotron-3-Super).

  python validation/jury_repeat.py --cap 70        (a Python with tinker + tinker-cookbook; cap = dollars, all caches)
  python validation/jury_repeat.py --judges kimi-k2.6 --tag kimi --cap 70   (one judge per process, run in parallel;
                                                     each process writes its own cache, all caches are read)
  python validation/jury_repeat.py --summarize      (no calls: parse every cache -> votes file)
  -> validation/data/jury_repeat*.jsonl (raw outputs, git-ignored), validation/jury_repeat_votes.json (parsed votes)
"""
import argparse
import asyncio
import collections
import gzip
import json
import sys
from pathlib import Path

V = Path(__file__).resolve().parent
HERE = V.parent
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
from common import POOL_BY_KEY, JsonlCache, call_cost, make_chats, parse_pairwise_verdict, parse_verdict  # noqa: E402

sys.path.insert(0, str(V))
import paper_numbers as P  # noqa: E402

JUDGES = ["qwen3.5-4b", "qwen3.5-9b", "qwen3.6-35b-a3b", "nemotron3-super-120b", "deepseek-v4.1-flash", "kimi-k2.6"]
SFX = {"qwen3.5-4b": "", "qwen3.5-9b": "", "qwen3.6-35b-a3b": "", "nemotron3-super-120b": "_nemotron",
       "deepseek-v4.1-flash": "_deepseek", "kimi-k2.6": "_kimi"}
MAX_TOKENS = 32768
TIMEOUT = 1200


def vote(job, text):
    """Jury frame: RB2 Math / BFF 1 = approves; JudgeBench 1 = picks the wrong response."""
    if job["pairwise"]:
        v = parse_pairwise_verdict(text)
        return None if v is None else int(v != int(job["gold"]))
    return parse_verdict(text)


def eligible():
    by = collections.defaultdict(set)
    for _, od, sfx in P.FAM:
        for r in P.load(od, sfx):
            by[r["item"]].add(r["judge"])
    return sorted(i for i, js in by.items() if len(js) == 7)


def all_rows():
    rows = {}
    for f in sorted((V / "data").glob("jury_repeat*.jsonl")):
        for line in open(f):
            if line.strip():
                r = json.loads(line)
                rows[r["cache_key"]] = r
    return rows


async def main_async(a):
    items = set(eligible())
    judges = a.judges.split(",") if a.judges else JUDGES
    jobs = {}
    for j in judges:
        for line in gzip.open(HERE / "inputs" / f"readout_jobs{SFX[j]}.jsonl.gz", "rt"):
            x = json.loads(line)
            if x["judge"] == j and x["item_id"] in items:
                jobs[j, x["item_id"]] = x
    print(f"{len(items)} eligible items; {len(jobs)} (judge, item) jobs", flush=True)
    if a.summarize:
        return summarize(jobs)
    cache = JsonlCache(V / "data" / (f"jury_repeat_{a.tag}.jsonl" if a.tag else "jury_repeat.jsonl"))
    seen = all_rows()
    chats = make_chats([POOL_BY_KEY[j] for j in judges], "off", False)
    for j, c in chats.items():
        print(f"  {j}: renderer {c.renderer_name}", flush=True)
    sem = asyncio.Semaphore(a.concurrency)
    stop = False

    total = [sum(r["cost"] for r in seen.values())]

    async def one(j, iid, k, n):
        nonlocal stop
        key = f"{j}|{iid}|{k}"
        if key in cache or key in seen:
            return
        async with sem:
            if stop or total[0] > a.cap:
                if not stop:
                    print(f"cap ${a.cap} reached; stopping", flush=True)
                stop = True
                return
            r = await asyncio.wait_for(chats[j].chat(jobs[j, iid]["messages"], max_tokens=MAX_TOKENS,
                                                     temperature=0.7, n=n), TIMEOUT)
        cost = call_cost(POOL_BY_KEY[j], r["n_in"], r["n_out"])
        total[0] += cost
        cache.put(dict(cache_key=key, judge=j, item=iid, draw=k, texts=[o["text"] for o in r["outputs"]],
                       clean=[o["clean"] for o in r["outputs"]], n_out=[o["n_out"] for o in r["outputs"]],
                       votes=[vote(jobs[j, iid], o["text"]) for o in r["outputs"]], n_in=r["n_in"], cost=cost))

    async def run(coros, label):
        errs = 0
        res = await asyncio.gather(*coros, return_exceptions=True)
        for e in res:
            if isinstance(e, Exception):
                errs += 1
                print(f"[error] {type(e).__name__}: {str(e)[:200]}", flush=True)
        print(f"{label}: done ({errs} errors); spent ${total[0]:.2f}", flush=True)

    await run([one(j, i, "main", 2) for (j, i) in jobs], "main draws")
    for k in ("retry1", "retry2"):  # redraw unparseable votes, one draw per missing vote
        got, rows = collections.Counter(), {**all_rows(), **cache.rows}
        for r in rows.values():
            got[r["judge"], r["item"]] += sum(v is not None for v in r["votes"])
        need = {(j, i): max(0, 2 - got[j, i]) for (j, i) in jobs if f"{j}|{i}|main" in rows}
        await run([one(j, i, k, n) for (j, i), n in need.items() if n], k)



def summarize(jobs):
    """Parsed votes + check of the parser against the paper's original verdicts (all caches)."""
    rows = all_rows()
    reps = collections.defaultdict(list)
    for r in sorted(rows.values(), key=lambda r: r["draw"]):
        reps[r["judge"], r["item"]] += [v for v in r["votes"] if v is not None]
    orig = {}
    for _, od, sfx in P.FAM:
        for r in P.load(od, sfx):
            orig[r["judge"], r["item"]] = r
    agree, n = 0, 0
    for (j, i), x in jobs.items():
        v0, r = vote(x, x["transcript"]), orig[j, i]
        if v0 is None:
            continue
        paper = (r["y"] if r["ok"] == 0 else 1 - r["y"]) if x["pairwise"] else r["y"]
        agree, n = agree + (v0 == paper), n + 1
    cost = collections.Counter()
    for r in rows.values():
        cost[r["judge"]] += r["cost"]
    out = dict(judges=JUDGES, max_tokens=MAX_TOKENS, temperature=0.7, spent=sum(cost.values()),
               spent_by_judge=dict(cost), calls=len(rows), parser_vs_paper_original=dict(agree=agree, n=n),
               cut_off=sum(not c for r in rows.values() for c in r["clean"]),
               votes={f"{j}|{i}": reps[j, i][:2] for (j, i) in jobs})
    (V / "jury_repeat_votes.json").write_text(json.dumps(out) + "\n")
    short = collections.Counter(k.split("|")[0] for k, v in out["votes"].items() if len(v) < 2)
    print(f"parser on original transcripts agrees with the paper's verdict {agree}/{n}; outputs not ended cleanly "
          f"{out['cut_off']}; (judge, item) with < 2 parsed repeats: {dict(short)}; spent ${out['spent']:.2f} "
          f"{ {k: round(v, 2) for k, v in cost.items()} }")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=float, default=70.0)
    ap.add_argument("--concurrency", type=int, default=48)
    ap.add_argument("--limit", type=int, default=None, help="pilot: only the first N eligible items")
    ap.add_argument("--judges", default="", help="comma list (default: all six)")
    ap.add_argument("--tag", default="", help="this process's cache suffix (parallel runs)")
    ap.add_argument("--summarize", action="store_true", help="no calls: write the votes file from all caches")
    a = ap.parse_args()
    if a.limit:
        _el = eligible
        eligible = lambda: _el()[: a.limit]  # noqa: E731
    asyncio.run(main_async(a))
