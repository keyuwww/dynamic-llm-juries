"""Minimal pairs for belief bias: same question, same response text, only the answer letter changes.

JudgeBench multiple-choice questions (MMLU-Pro style A-J, AMC style A-E). For every question, every option letter X becomes
one judging item whose response is the fixed answer-only template below. Correctness of X is known (the letter of the
better JudgeBench candidate), and the judge's belief in X is the share of its own 7 solves (s1..s7, T = 0.7, thinking
off) that end in X. So within a question, among WRONG letters, the only thing that varies is how often the judge itself
would give that answer: a clean test of belief bias, and a clean contrast for finding the belief direction.

Writes
  cannon_belief/pair_jobs.jsonl.gz   capture.py jobs: one checkpoint "A" (after "VERDICT:"), options CORRECT / INCORRECT
  out/minimal_pairs_meta.jsonl       one row per (judge, question, letter): correct, k (of n votes), n votes, belief

  python3 experiments/anchoring_early_answer/minimal_pairs_prep.py
"""
import collections
import gzip
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
JUDGES = ["qwen3.5-9b", "qwen3.5-4b"]
PROMPT = ("You are grading an AI assistant's response to a multiple-choice question.\n"
          "Focus on whether the final answer is correct.\n\n"
          "[USER REQUEST]\n{q}\n\n[ASSISTANT'S RESPONSE]\nThe answer is ({x}).\n\n{x5}\n\n"
          "Is this a good, correct response to the request? Judge substance, not style or length.\n"
          "Reason briefly, then end with exactly one line: \"VERDICT: CORRECT\" or \"VERDICT: INCORRECT\".")


def letter(t):
    """Final answer letter of a solve or candidate: a trailing run like 'FFFFF', 'C C C C C', 'I'."""
    m = re.search(r"(?<![A-Za-z])([A-J])(?:[\s*]*\1)*[\s*.]*$", t.strip())
    return m.group(1) if m else None


def options(q):
    return sorted(set(re.findall(r"\(([A-J])\)", q)))


def main():
    jobs = [json.loads(l) for l in gzip.open(HERE / "inputs" / "readout_jobs.jsonl.gz", "rt")]
    qs = {}
    for j in jobs:
        if j["bench"] == "judgebench":
            qs.setdefault(j["qid"], j)
    solves = collections.defaultdict(list)
    for s in map(json.loads, open(HERE / "out" / "solves_k.jsonl")):
        if s["bench"] == "judgebench" and s["sample"] >= 1:
            solves[(s["model"], s["qid"])].append(letter(s["answer"]))
    out_jobs, meta, skipped = [], [], collections.Counter()
    for qid, j in sorted(qs.items()):
        O = options(j["question"])
        if len(O) < 4:
            skipped["not multiple choice"] += 1
            continue
        L = [letter(c) for c in j["candidates"]]
        if None in L or L[0] == L[1]:
            skipped["candidate letters unclear"] += 1
            continue
        gold = L[0] if j["gold"] == 1 else L[1]  # gold = 1: response A is the better (correct) one
        for judge in JUDGES:
            v = [x for x in solves[(judge, qid)] if x]
            if len(v) < 5:
                skipped[f"{judge}: < 5 readable solves"] += 1
                continue
            c = collections.Counter(v)
            for x in O:
                item = f"{qid}|{x}"
                msg = PROMPT.format(q=j["question"], x=x, x5=x * 5)
                out_jobs.append(dict(judge=judge, item_id=item, bench="jb_pairs", messages=[dict(role="user", content=msg)],
                                     ckpts=[["A", "VERDICT:", [" CORRECT", " INCORRECT"]]]))
                meta.append(dict(judge=judge, item=item, qid=qid, letter=x, correct=int(x == gold), k=c[x], n=len(v),
                                 belief=c[x] / len(v), n_options=len(O)))
    with gzip.open(HERE / "cannon_belief" / "pair_jobs.jsonl.gz", "wt") as f:
        f.write("".join(json.dumps(r) + "\n" for r in out_jobs))
    with open(HERE / "out" / "minimal_pairs_meta.jsonl", "w") as f:
        f.write("".join(json.dumps(r) + "\n" for r in meta))
    print(f"{len(out_jobs)} items; skipped questions: {dict(skipped)}")
    for judge in JUDGES:
        M = [m for m in meta if m["judge"] == judge]
        w = [m for m in M if not m["correct"]]
        print(f"{judge}: {len({m['qid'] for m in M})} questions, {len(M)} letters; wrong letters by belief: "
              f"0/7 {sum(m['k'] == 0 for m in w)}, 1-3 {sum(1 <= m['k'] <= 3 for m in w)}, "
              f">=4 {sum(m['belief'] >= 4 / 7 for m in w)}; correct letters believed >=4/7: "
              f"{sum(m['belief'] >= 4 / 7 for m in M if m['correct'])}")


if __name__ == "__main__":
    main()
