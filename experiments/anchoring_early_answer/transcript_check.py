"""Transcript check (Nov 16): when a judge approves a wrong answer it believes, does it work the problem out itself
and land on the same wrong answer ("re-solve and agree"), or does it only read the answer and go along with it?

GLM-5.3-Flash reads each judging transcript (thinking off, the pool transcript or its from-scratch rerun) with the
question and the graded answer, and labels:
  RESOLVE  YES / NO     did the grader independently work out its own result?
  OWN      SAME / DIFFERENT / NONE   is that result the graded answer's final answer?
  STYLE    RESOLVE / STEPS / SURFACE   re-solves then compares / checks the given steps / no real check
Single-answer benchmarks only (RB2 Math, BFF); judges that show the belief rise: three Qwens and Nemotron-3-Super.
Rows come from the belief tables (belief_rows_clean.json), so every transcript has a belief score and a verdict.

  python3 experiments/anchoring_early_answer/transcript_check.py --prep     -> inputs/ask_transcripts.jsonl.gz
  (modal_app.py::run --phase ask --pairs transcripts)                     -> out/ask_glm5.3-flash_transcripts.jsonl
  python3 experiments/anchoring_early_answer/transcript_check.py            -> out/transcript_check.md
  --think   the three Qwens WITH THINKING ON (out/think_gen.jsonl + its from-scratch reruns, Experiment 5): the reasoning
            is written out, so re-solving cannot stay hidden. Verdict = the spoken verdict after </think>; GLM sees
            the first and last 30,000 characters of the thinking + the answer. -> ask_transcripts_think / *_think.md
"""
import collections
import gzip
import json
import re
import sys
from pathlib import Path

import numpy as np

THINK = "--think" in sys.argv
TAGT = "_think" if THINK else ""
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tinker_pool"))
from common import parse_verdict  # noqa: E402

HERE = Path(__file__).resolve().parent
SETS = {"": ["qwen3.5-4b", "qwen3.5-9b", "qwen3.6-35b-a3b"], "_nemotron": ["nemotron3-super-120b"]}
if THINK:
    SETS = {"": ["qwen3.5-4b", "qwen3.5-9b", "qwen3.6-35b-a3b"]}


def think_transcripts():
    """(judge, item) -> (text for GLM, spoken verdict 1/0) for finished thinking-on judgments."""
    rows = {}
    for f in ("think_gen.jsonl", "think_gen_rerun.jsonl"):
        p = HERE / "out" / f
        if not p.exists():
            continue
        for line in open(p):
            r = json.loads(line)
            kind, bench, iid = r["key"].split("|", 2)
            if kind != "judge" or bench not in BENCHES or "</think>" not in r["text"]:
                continue
            think, after = r["text"].split("</think>", 1)
            v = parse_verdict(after)
            if v is None:
                continue
            t = think if len(think) <= 60000 else think[:30000] + "\n[... middle of the reasoning omitted ...]\n" + think[-30000:]
            rows[(r["judge"], iid)] = ("<reasoning>\n" + t + "\n</reasoning>\n" + after.strip(), int(v))
    return rows
BENCHES = ("rb2math", "bff")
PROMPT = """You are analysing how an AI grader checked another AI's answer. Do not judge the answer yourself; describe only what the grader did.

QUESTION:
{question}

ANSWER BEING GRADED:
{cand}

THE GRADER'S EVALUATION:
{transcript}

Q1 RESOLVE: Did the grader independently work out its own result for the question (computing or reasoning to a final answer itself), rather than only reading or checking the given answer's steps? Restating the given answer's numbers does not count.
Q2 OWN: If Q1 is YES, is the final result the grader worked out the SAME as the graded answer's final answer, or DIFFERENT? If Q1 is NO, NONE.
Q3 STYLE: RESOLVE = solves it on its own, then compares; STEPS = goes through the given answer's steps and checks them; SURFACE = only comments on plausibility, clarity or format, without a real check.

End with exactly three lines:
RESOLVE: YES or NO
OWN: SAME or DIFFERENT or NONE
STYLE: RESOLVE or STEPS or SURFACE"""


def binof(b):
    k = round(b * 7)
    return "0/7" if k == 0 else "1-3" if k <= 3 else "4-6" if k <= 6 else "7/7"


def items():
    """(set, judge, item) -> dict(question, cand, transcript, bench, gold, belief, accepted)."""
    out = {}
    tt = think_transcripts() if THINK else None
    for sfx, judges in SETS.items():
        d = HERE / f"out{sfx}"
        with gzip.open(HERE / "inputs" / f"readout_jobs{sfx}.jsonl.gz", "rt") as f:
            jobs = {(j["judge"], j["item_id"]): j for j in map(json.loads, f) if j["bench"] in BENCHES}
        ext = {}
        for p in d.glob("extended_judge*.jsonl"):
            for r in map(json.loads, open(p)):
                ext[r["cache_key"]] = r["text"]
        for r in json.load(open(d / "belief_rows_clean.json")):
            if r["bench"] not in BENCHES or r["judge"] not in judges or r.get("acc_C") is None:
                continue
            j = jobs[(r["judge"], r["item"])]
            t, acc = ext.get(f"judge|{r['judge']}|{r['item']}", j["transcript"]), r["acc_C"]
            if THINK:
                if (r["judge"], r["item"]) not in tt:
                    continue
                t, acc = tt[(r["judge"], r["item"])]
            out[(r["judge"], r["item"])] = dict(question=j["question"], cand=j["candidates"][0], transcript=t,
                                                bench=r["bench"], gold=r["target_ok"], belief=r["belief"],
                                                accepted=acc)
    return out


def prep():
    X = items()
    with gzip.open(HERE / "inputs" / f"ask_transcripts{TAGT}.jsonl.gz", "wt") as f:
        for (judge, iid), x in X.items():
            prompt = PROMPT.format(question=x["question"][-6000:], cand=x["cand"][-6000:],
                                   transcript=x["transcript"] if THINK else x["transcript"][-12000:])
            f.write(json.dumps(dict(cache_key=f"tc{TAGT}|{judge}|{iid}", prompt=prompt)) + "\n")
    print(len(X), "transcripts", collections.Counter((k[0], v["bench"], v["gold"]) for k, v in X.items()))


def parse(text):
    g = lambda k, opts: (re.findall(rf"{k}:\s*\**\s*({opts})", text or "") or [None])[-1]
    return g("RESOLVE", "YES|NO"), g("OWN", "SAME|DIFFERENT|NONE"), g("STYLE", "RESOLVE|STEPS|SURFACE")


def analyze():
    X = items()
    lab = {}
    for r in map(json.loads, open(HERE / "out" / f"ask_glm5.3-flash_transcripts{TAGT}.jsonl")):
        _, judge, iid = r["cache_key"].split("|", 2)
        lab[(judge, iid)] = parse(r["text"])
    L = ["# Transcript check: how judges approve the wrong answers they believe" + (" (THINKING ON)" if THINK else "") + "\n",
         f"GLM-5.3-Flash read each judging transcript ({'thinking ON: the written reasoning plus the answer' if THINK else 'thinking off'}; RB2 Math + BFF; clean labels). "
         "*Re-solves* = the grader works out its own result; *lands on it* = that result equals the graded answer. "
         f"Labelled: {sum(all(v) for v in lab.values())} of {len(X)}.\n"]

    def table(title, keyf):
        L.append(f"## {title}\n")
        L.append("| group | n | re-solves | re-solves and lands on the graded answer | step check | surface only |")
        L.append("|---|---|---|---|---|---|")
        groups = collections.defaultdict(list)
        for k, x in X.items():
            if k in lab and all(lab[k]):
                g = keyf(k, x)
                if g:
                    groups[g].append(lab[k])
        for g in sorted(groups):
            v = groups[g]
            pct = lambda f: f"{100 * np.mean([f(t) for t in v]):.0f}%"
            L.append(f"| {g} | {len(v)} | {pct(lambda t: t[0] == 'YES')} | {pct(lambda t: t[0] == 'YES' and t[1] == 'SAME')} | "
                     f"{pct(lambda t: t[2] == 'STEPS')} | {pct(lambda t: t[2] == 'SURFACE')} |")
        L.append("")

    fam = lambda k: "Nemotron" if k[0].startswith("nemotron") else "Qwen"
    table("Wrong answers, by belief and verdict",
          lambda k, x: None if x["gold"] else f"{fam(k)} · belief {binof(x['belief'])} · {'approved' if x['accepted'] else 'rejected'}")
    table("Correct answers, by belief and verdict (control)",
          lambda k, x: None if not x["gold"] else f"{fam(k)} · belief {binof(x['belief'])} · {'approved' if x['accepted'] else 'rejected'}")
    table("Wrong answers, by judge (all beliefs)",
          lambda k, x: None if x["gold"] else f"{k[0]} · {'approved' if x['accepted'] else 'rejected'}")
    out = HERE / "out" / f"transcript_check{TAGT}.md"
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    prep() if "--prep" in sys.argv else analyze()  # add --think for the thinking-on transcripts
