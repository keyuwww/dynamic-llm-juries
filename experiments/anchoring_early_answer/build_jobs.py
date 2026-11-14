"""Build the input files for the early-answering anchoring experiment (no API calls).

Question: when a judge approves a WRONG answer that matches its OWN wrong answer, was it already
leaning CORRECT before it reasoned (position A), or did the approval build up during reasoning?

Judges: the three Qwen models of the Tinker pool. Benchmarks: RewardBench 2 Math, JudgeBench (coding pairs
dropped: no short final answer to match) and BFF-Bench (finance, expert-labelled VERDICTS responses) -- the main
set -- plus BBEH Mini as a "beyond the judge's ability" contrast.

BFF own answers: the judge answers exactly the conversation the candidate answered (turn 1: the question;
turn 2: question 1, the candidate model's own turn-1 answer, question 2), so qid is per question for turn 1 and
per item for turn 2.

Writes inputs/ (read by tinker_jobs.py on Modal):
  solve_jobs.jsonl      each Qwen answers each RB2-Math / JudgeBench question once (BBEH answers
                        already exist in tinker_pool/bbeh_results/answers.jsonl)
  readout_jobs.jsonl.gz one row per pool judgment by a Qwen judge: the exact judge prompt, the judge's
                        own transcript from the pool run, and the gold label

  python3 experiments/anchoring_early_answer/build_jobs.py
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
POOL = HERE.parent / "tinker_pool"
sys.path.insert(0, str(POOL))
import run_judges  # noqa: E402
from data import load_judgebench, load_rb2_domain  # noqa: E402

QWENS = ["qwen3.5-4b", "qwen3.5-9b", "qwen3.6-35b-a3b"]
RB2_SOLVE_SUFFIX = "\n\nSolve the problem. End with your final answer in \\boxed{}."
OUT = HERE / "inputs"


def pool_judgments(bench, keep):
    rows = {}
    for line in open(POOL / f"{bench}_results" / "judgments.jsonl"):
        r = json.loads(line)
        if r["judge"] in QWENS and r["condition"] == "none" and keep(r["item_id"]):
            rows[(r["judge"], r["item_id"])] = r
    return rows


def main():
    OUT.mkdir(exist_ok=True)
    solve, readout = [], []

    # ---- BBEH: judge prompts already rebuilt exactly (llama_bbeh/build_prompts.py asserts the match)
    bbeh_prompts = {p["id"]: p for p in map(json.loads, open(HERE.parent / "llama_bbeh" / "prompts.jsonl"))
                    if p["kind"] == "judge"}
    for (judge, iid), r in pool_judgments("bbeh", lambda i: True).items():
        p = bbeh_prompts[iid]
        readout.append(dict(bench="bbeh", judge=judge, item_id=iid, gold=int(r["gold"]), messages=p["messages"],
                            transcript=(r["raw"] or [""])[0] or "", pool_n_in=r["n_in"], pairwise=False,
                            candidates=[], qid=iid.split("|")[0], question=""))

    # ---- RewardBench 2, Math domain
    rb2 = {it["id"]: it for it in load_rb2_domain("Math")}
    for (judge, iid), r in pool_judgments("rb2", lambda i: i.startswith("rb2math-")).items():
        it = rb2[iid]
        prompt = run_judges.build_prompt("rb2", it, "none", None)
        readout.append(dict(bench="rb2math", judge=judge, item_id=iid, gold=int(r["gold"]),
                            messages=[{"role": "user", "content": prompt}],
                            transcript=(r["raw"] or [""])[0] or "", pool_n_in=r["n_in"], pairwise=False,
                            candidates=[it["response"]], qid=iid.rsplit("-", 1)[0], question=it["prompt"]))
    for q in sorted({it["prompt"] for it in rb2.values()}):
        qid = next(i.rsplit("-", 1)[0] for i, it in rb2.items() if it["prompt"] == q)  # rb2math-<id>
        for m in QWENS:
            solve.append(dict(bench="rb2math", model=m, qid=qid,
                              messages=[{"role": "user", "content": q + RB2_SOLVE_SUFFIX}]))

    # ---- JudgeBench (pairwise), no coding pairs
    jb = {it["id"]: it for it in load_judgebench() if not it["source"].startswith("livecodebench")}
    for (judge, iid), r in pool_judgments("judgebench", lambda i: i in jb).items():
        it = jb[iid]
        prompt = run_judges.build_prompt("judgebench", it, "none", None)
        readout.append(dict(bench="judgebench", judge=judge, item_id=iid, gold=int(r["gold"]),
                            messages=[{"role": "user", "content": prompt}],
                            transcript=(r["raw"] or [""])[0] or "", pool_n_in=r["n_in"], pairwise=True,
                            candidates=[it["response_a"], it["response_b"]], qid=None, question=it["question"]))
    seen = {}
    for iid, it in sorted(jb.items()):
        seen.setdefault(it["question"], iid)
    for r in readout:
        if r["bench"] == "judgebench":
            r["qid"] = "jbq-" + seen[r["question"]]
    for q, iid in seen.items():
        for m in QWENS:  # JudgeBench questions already say how to format the final answer
            solve.append(dict(bench="judgebench", model=m, qid="jbq-" + iid,
                              messages=[{"role": "user", "content": q}]))

    # ---- BFF-Bench (VERDICTS responses with unanimous expert labels), single answer, two turns
    items = {it["id"]: it for it in run_judges.bff_items(argparse.Namespace(verdicts_path=None, bff_path=None,
                                                                             consensus="unanimous"))}
    bff_solve = {}
    for (judge, iid), r in pool_judgments("bff", lambda i: True).items():
        it = items[iid]
        ctx = [dict(role=m["role"], content=m["content"]) for m in it["conv"][:-1]]
        qid = f"bff-{it['uid']}-t1" if int(it["turn"]) == 1 else f"bff-{iid}"
        bff_solve[qid] = ctx
        readout.append(dict(bench="bff", judge=judge, item_id=iid, gold=int(r["gold"]),
                            messages=[{"role": "user", "content": run_judges.build_prompt("bff", it, "none", None)}],
                            transcript=(r["raw"] or [""])[0] or "", pool_n_in=r["n_in"], pairwise=False,
                            candidates=[it["conv"][-1]["content"]], qid=qid, uid=it["uid"],
                            question=run_judges.render_conv(ctx)))
    for qid, ctx in sorted(bff_solve.items()):
        for m in QWENS:
            solve.append(dict(bench="bff", model=m, qid=qid, messages=ctx))

    with open(OUT / "solve_jobs.jsonl", "w") as f:
        for s in solve:
            f.write(json.dumps(s) + "\n")
    with gzip.open(OUT / "readout_jobs.jsonl.gz", "wt") as f:
        for r in readout:
            f.write(json.dumps(r) + "\n")
    by = {}
    for r in readout:
        by[(r["bench"], r["judge"])] = by.get((r["bench"], r["judge"]), 0) + 1
    print(f"solve jobs: {len(solve)}  readout jobs: {len(readout)}")
    for k, v in sorted(by.items()):
        print(f"  {k[0]:11s} {k[1]:16s} {v}")
    # map JudgeBench pair -> question key, so the analysis can find each judge's own answer
    (OUT / "judgebench_qkey.json").write_text(json.dumps({iid: "jbq-" + seen[it["question"]] for iid, it in jb.items()}))


if __name__ == "__main__":
    main()
