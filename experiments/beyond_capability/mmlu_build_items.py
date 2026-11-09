"""MMLU-Redux judging items for the stretching study (no API calls). Candidates = answers from Qwen3.5-4B, Qwen3.6-35B
and Nemotron-3-Super (Tinker, thinking off, one each) that state a final letter; gold = the expert-verified key.
Each item is a judge-role row in the dir_capture.py format (thinking off, read at "VERDICT:").
Also prints each judge's solve rate (Qwen-9B: majority of 3 on Tinker; Llama-8B: 1 on the cluster, if present).

  python3 experiments/beyond_capability/mmlu_build_items.py
"""
import collections
import gzip
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bc_load import OUT, jl  # noqa: E402

CANDIDATE_MODELS = ["qwen3.5-4b", "qwen3.6-35b-a3b", "nemotron3-super-120b"]
MC_JUDGE = """You are grading an AI assistant's answer to a multiple-choice question.

[QUESTION]
{question}

[ASSISTANT'S ANSWER]
{answer}

Is the assistant's final answer correct? Only the final answer matters, not the style of the reasoning.
Reason briefly, then end with exactly one line: "VERDICT: CORRECT" or "VERDICT: INCORRECT"."""


MATH_JUDGE = """You are grading an AI assistant's answer to a math problem.

[PROBLEM]
{question}

[ASSISTANT'S ANSWER]
{answer}

Is the assistant's final answer correct? Only the final answer matters, not the style of the reasoning.
Reason briefly, then end with exactly one line: "VERDICT: CORRECT" or "VERDICT: INCORRECT"."""


def math_final(text):
    if not text or "answer is" not in text.lower():
        return None
    i = text.lower().rfind("answer is")
    return text[i + len("answer is"):].lstrip(": ").strip().split("\n")[0].strip().rstrip(".").strip("$ ") or None


def letter(text):
    m = re.findall(r"answer is:?\s*\**\s*\(?([A-J])\)?\b", text or "", re.I)
    return m[-1].upper() if m else None


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--stem", default="mmlu_full", help="question file inputs/<stem>.jsonl")
    ap.add_argument("--mixed-only", action="store_true", help="keep only questions with a right AND a wrong answer")
    a = ap.parse_args()
    qs = {q["id"]: q for q in jl(HERE / "inputs" / f"{a.stem}.jsonl")}
    is_math = a.stem.startswith("math")
    grades = {r["cache_key"]: r["verdict"] for r in jl(OUT / f"egrades_{a.stem}.jsonl")} if is_math else {}
    rows, by = [], collections.Counter()
    for m in CANDIDATE_MODELS:
        for r in jl(OUT / f"esolves_{a.stem}_{m}.jsonl"):
            seen = set()
            for k, s in enumerate(r["samples"]):  # every attempt is a candidate; one per (model, final answer)
                L = math_final(s["text"]) if is_math else letter(s["text"])
                if L is None or not s["clean"] or L in seen:
                    continue
                q = qs[r["qid"]]
                if is_math:
                    g = grades.get(f"esolves_{a.stem}_{m}|{r['qid']}|{k}")
                    if g is None:
                        continue
                    gold = int(g)
                else:
                    gold = int(L == q["gold"])
                seen.add(L)
                by[(m, gold)] += 1
                qtext = q["prompt"].split("\n\nThink step by step")[0].replace("Answer the following multiple-choice question.\n\n", "")
                tmpl = MATH_JUDGE if is_math else MC_JUDGE
                rows.append(dict(bench="math" if is_math else "mmlu", qid=q["id"], aid=f"{q['id']}|{m}|{k}", gold=gold, src=m,
                                 mode="J", messages=[{"role": "user", "content": tmpl.format(question=qtext, answer=s["text"])}],
                                 suffix="VERDICT:", letter=L))
    if a.mixed_only:
        mix = collections.defaultdict(set)
        for r in rows:
            mix[r["qid"]].add(r["gold"])
        rows = [r for r in rows if len(mix[r["qid"]]) == 2]
    with gzip.open(HERE / "inputs" / f"{a.stem}_items.jsonl.gz", "wt") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    per_q = collections.defaultdict(set)
    for r in rows:
        per_q[r["qid"]].add(r["gold"])
    print(f"{len(rows)} items on {len(per_q)} questions; {sum(len(v) == 2 for v in per_q.values())} questions have both a right and a wrong answer")
    for m in CANDIDATE_MODELS:
        print(f"  {m:22s} right {by[(m, 1)]:4d}  wrong {by[(m, 0)]:4d}")
    # solve rates of the two judges
    s9 = {}
    for r in jl(OUT / f"esolves_{a.stem}_qwen3.5-9b.jsonl"):
        if is_math:
            oks = [grades.get(f"esolves_{a.stem}_qwen3.5-9b|{r['qid']}|{i}") for i in range(len(r["samples"]))]
            if None in oks:
                continue
        else:
            oks = [int(letter(x["text"]) == qs[r["qid"]]["gold"]) for x in r["samples"]]
        s9[r["qid"]] = int(sum(oks) * 2 > len(oks))
    if s9:
        print(f"Qwen-9B solves {sum(s9.values()) / len(s9):.2f} of {len(s9)} questions (majority of 3)")
    ll = HERE / "out_dirs" / "llama3.1-8b" / f"esolves_{a.stem}_llama3.1-8b.jsonl"
    if ll.exists():
        sl = {} if is_math else {r["qid"]: int(letter(r["text"]) == qs[r["qid"]]["gold"]) for r in jl(ll)}
        print(f"Llama-8B solves {sum(sl.values()) / len(sl):.2f} of {len(sl)} questions")


if __name__ == "__main__":
    main()
