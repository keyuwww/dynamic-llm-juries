"""Build the controlled-edit pairs (PROTOCOL.md): Kimi-K3.1-Pro introduces one wrong step into a right Qwen3.5-4B MATH
answer; GLM-5.3-Flash confirms the new final answer is wrong; surface and similarity filters keep the pair otherwise
matched. Every model call is cached (re-running resumes and pays nothing twice).

  .venv/bin/python experiments/beyond_capability/edit_test/edit_build.py --set design   # first 40 problems
  .venv/bin/python experiments/beyond_capability/edit_test/edit_build.py --set test
-> edit_test/edits_raw.jsonl (cache), grades.jsonl (cache), pairs_<set>.jsonl (passing pairs), log_<set>.json
"""
import argparse
import os
import asyncio
import difflib
import gzip
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BC = HERE.parent
sys.path.insert(0, str(BC))
import bc_jobs as B  # noqa: E402
import paper_surface as PS  # noqa: E402
from common import JsonlCache, load_env  # noqa: E402

SEED, N_DESIGN, MAX_CHARS, ATTEMPTS = 20261121, 40, 8000, 2

EDIT_PROMPT = """Below is a math problem and a correct solution to it. We are building a test of whether automatic graders can detect a single reasoning error, so we need a minimally edited copy of this solution that is wrong.

Rewrite the solution with EXACTLY ONE error:
- Change one intermediate calculation or algebraic step so that its result is wrong (for example a wrong product, sum, sign, exponent, or a wrong value substituted).
- Carry the wrong value consistently through every later step, so the solution stays internally coherent and ends with a different, wrong final answer.
- Change nothing else: keep every other word, symbol, line break, markdown and LaTeX command exactly as it is. Do not add or remove sentences, steps, or lines.
- Do not add anything that hints at the error (no "wait", "actually", corrections, hedging or comments). The edited solution must read exactly as confidently as the original.
- Keep the final line in the same form: "The answer is: <answer>".

[PROBLEM]
{problem}

[CORRECT SOLUTION]
{solution}

Output the complete edited solution between the tags <edited> and </edited>. After the closing tag, write one line: "CHANGED: <one sentence saying which step you changed and how>"."""


async def with_timeout(coro, t=600):
    """unlike asyncio.wait_for, does not wait for a stalled call to acknowledge cancellation."""
    task = asyncio.ensure_future(coro)
    done, _ = await asyncio.wait({task}, timeout=t)
    if task in done:
        return task.result()
    task.cancel()
    raise asyncio.TimeoutError


def answer_text(row):
    return PS.answer_text(row).strip("\n")


def load_sources():
    rows = [json.loads(l) for l in gzip.open(BC / "inputs" / "math_full_items.jsonl.gz", "rt")]
    by_q = {}
    for r in sorted(rows, key=lambda r: r["aid"]):
        if r["src"] == "qwen3.5-4b" and r["gold"] == 1 and r["qid"] not in by_q and len(answer_text(r)) <= MAX_CHARS:
            by_q[r["qid"]] = r
    qs = sorted(by_q)
    random.Random(SEED).shuffle(qs)
    return [by_q[q] for q in qs]


def problem_text(row):
    t = row["messages"][-1]["content"]
    i, j = t.find("[PROBLEM]"), t.find("[ASSISTANT'S ANSWER]")
    return t[i + len("[PROBLEM]"): j].strip()


def parse_edit(text):
    m = re.search(r"<edited>\n?(.*?)\n?</edited>", text or "", re.S)
    ch = re.search(r"CHANGED:\s*(.+)", text or "")
    return (m.group(1) if m else None), (ch.group(1).strip() if ch else None)


def match_whitespace(orig, ed):
    """design-set finding: the editor sometimes adds trailing spaces (e.g. after the final answer). Where the line counts
    agree, give every edited line the original line's trailing whitespace; strip leading/trailing blank space overall."""
    o, e = orig.split("\n"), ed.strip("\n").split("\n")
    if len(o) != len(e):
        return ed.strip("\n")
    return "\n".join(le.rstrip() + lo[len(lo.rstrip()):] for lo, le in zip(o, e))


def surface_ok(orig, ed):
    fo, fe = PS.feats(orig), PS.feats(ed)
    names = PS.NAMES
    bad = [n for n, a, b in zip(names, fo, fe) if n not in ("log_chars",) and a != b]
    ratio = len(ed) / len(orig)
    sim = difflib.SequenceMatcher(None, orig, ed, autojunk=False).ratio()
    return dict(feature_mismatch=bad, len_ratio=ratio, sim=sim, ok=not bad and abs(ratio - 1) <= 0.05 and sim >= 0.85)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=("design", "test"), required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--conc", type=int, default=24)
    a = ap.parse_args()
    load_env()
    import tinker
    service = tinker.ServiceClient()
    kimi, glm = B.Chat("kimi-k3.1-pro", service), B.Chat("glm", service)
    edits, grades = JsonlCache(HERE / "edits_raw.jsonl"), JsonlCache(HERE / "grades.jsonl")
    src = load_sources()
    rows = src[:N_DESIGN] if a.set == "design" else src[N_DESIGN:]
    rows = rows[: a.limit or None]
    gold = {q["id"]: q for q in map(json.loads, open(BC / "inputs" / "solveq_math.jsonl"))}
    tokens = dict(kimi_in=0, kimi_out=0, glm_in=0, glm_out=0)
    out, log = {}, {}

    async def one(r):
        orig = answer_text(r)
        prob = problem_text(r)
        rec = dict(qid=r["qid"], aid=r["aid"], attempts=[])
        for k in range(ATTEMPTS):
            ck = f"{r['aid']}|{k}"
            if ck not in edits:
                try:  # a call that has not returned after 10 minutes counts as a failed attempt (stalled calls)
                    res = await with_timeout(kimi.sample([{"role": "user", "content": EDIT_PROMPT.format(problem=prob, solution=orig)}],
                                                             n=1, temperature=0.7, max_tokens=24000, retries=1))
                    s = res["samples"][0]
                    edits.put(dict(cache_key=ck, text=s["text"], n_in=res["n_in"], n_out=s["n_out"], clean=s["clean"]))
                except asyncio.TimeoutError:
                    edits.put(dict(cache_key=ck, text="", n_in=0, n_out=0, clean=False, timeout=True))
            e = edits.get(ck)
            tokens["kimi_in"] += e["n_in"]
            tokens["kimi_out"] += e["n_out"]
            ed, changed = parse_edit(e["text"])
            att = dict(k=k, parsed=ed is not None, changed=changed)
            rec["attempts"].append(att)
            if ed is None:
                continue
            ed = match_whitespace(orig, ed)
            cand = B.math_final(ed)
            att["final"] = cand
            if cand is None:
                continue
            q = gold[r["qid"]]
            if B._canon(cand) == B._canon(q["gold"]):
                att["wrong"] = False
                continue
            gk = f"{ck}|grade"
            if gk not in grades:
                msg = B.MATH_EQ_PROMPT.format(problem=q["prompt"].split("\n\nThink step by step")[0][-4000:], gold=q["gold"],
                                              cand=cand[-2000:])
                try:
                    g = await with_timeout(glm.sample([{"role": "user", "content": msg}], n=1, temperature=0.0, retries=1))
                    t = g["samples"][0]["text"].strip().upper()
                    last = re.findall(r"\b(SAME|DIFFERENT)\b", t)
                    grades.put(dict(cache_key=gk, verdict=None if not last else last[-1], n_in=g["n_in"], n_out=g["samples"][0]["n_out"]))
                except asyncio.TimeoutError:
                    grades.put(dict(cache_key=gk, verdict=None, n_in=0, n_out=0, timeout=True))
            gr = grades.get(gk)
            tokens["glm_in"] += gr["n_in"]
            tokens["glm_out"] += gr["n_out"]
            att["wrong"] = gr["verdict"] == "DIFFERENT"
            if not att["wrong"]:
                continue
            att |= surface_ok(orig, ed)
            if att["ok"]:
                out[r["qid"]] = dict(qid=r["qid"], aid=r["aid"], attempt=k, original=orig, edited=ed, changed=changed,
                                     final_original=B.math_final(orig), final_edited=cand, reference=q["gold"],
                                     len_ratio=att["len_ratio"], sim=att["sim"])
                break
        log[r["qid"]] = rec

    await B.run_all([one(r) for r in rows], a.conc, f"edit {a.set}")
    with open(HERE / f"pairs_{a.set}.jsonl", "w") as fh:
        for q in sorted(out):
            fh.write(json.dumps(out[q]) + "\n")
    fails = {"unparsed": 0, "no_final": 0, "not_wrong": 0, "surface": 0}
    for rec in log.values():
        if rec["qid"] in out:
            continue
        last = rec["attempts"][-1] if rec["attempts"] else {}
        key = ("unparsed" if not last.get("parsed") else "no_final" if last.get("final") is None else
               "not_wrong" if not last.get("wrong") else "surface")
        fails[key] += 1
    summ = dict(set=a.set, problems=len(rows), passed=len(out), fails_by_last_attempt=fails, tokens=tokens,
                feature_mismatch=sorted({n for rec in log.values() for att in rec["attempts"] for n in att.get("feature_mismatch", [])}))
    json.dump(dict(summary=summ, log=log), open(HERE / f"log_{a.set}.json", "w"), indent=1)
    print(json.dumps(summ, indent=1), flush=True)
    os._exit(0)


if __name__ == "__main__":
    import os
    asyncio.run(main())
    os._exit(0)  # stalled API calls can keep the event loop's shutdown waiting
