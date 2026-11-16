"""Causal tests of the re-solve account (Nov 16). Three Qwens, thinking off, RB2 Math + BFF, every candidate (right and
wrong); belief scores come from the existing 7-answer runs (belief_rows_clean.json).

  pull        The candidate is shown, but the model is asked to SOLVE the question itself (not to judge). How often
              does its own answer become the candidate's answer, by belief? At belief 0/7 the model never reaches that
              answer alone, so any landing there is the candidate pulling the solve.
  solvefirst  The model's own first answer (out/solves.jsonl, generated without the candidate, and not one of the 7
              belief answers) sits in the conversation before the usual judge prompt. Does approving never-reached
              wrong answers drop once the judge has committed to its own answer first?

  python3 experiments/anchoring_early_answer/causal_prep.py --prep   -> inputs/gen_pull.jsonl.gz, gen_solvefirst.jsonl.gz
  (modal_app.py::run --phase gen --pairs pull / solvefirst; then --phase pairs --pairs pull for GLM matching)
  python3 experiments/anchoring_early_answer/causal_prep.py --pairs  -> inputs/pairs_pull.jsonl.gz (after gen pull)
  python3 experiments/anchoring_early_answer/causal_prep.py          -> out/causal.md
"""
import collections
import gzip
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
from common import parse_verdict  # noqa: E402

QWENS = ["qwen3.5-4b", "qwen3.5-9b", "qwen3.6-35b-a3b"]
BENCHES = ("rb2math", "bff")
PULL = ("\n\nFor reference, here is another AI assistant's answer to this question:\n[OTHER ANSWER]\n{cand}\n[END OF OTHER ANSWER]\n\n"
        "That answer may be right or wrong. Work out the answer yourself.")
FIRST = "Now grade another AI assistant's answer to the same question.\n\n"


def load():
    with gzip.open(HERE / "inputs" / "readout_jobs.jsonl.gz", "rt") as f:
        jobs = {(j["judge"], j["item_id"]): j for j in map(json.loads, f) if j["bench"] in BENCHES and j["judge"] in QWENS}
    solve_msgs = {(j["model"], j["qid"]): j["messages"] for j in map(json.loads, open(HERE / "inputs" / "solve_jobs.jsonl"))}
    own = {r["cache_key"]: r for r in map(json.loads, open(HERE / "out" / "solves.jsonl"))}
    rows = {(r["judge"], r["item"]): r for r in json.load(open(HERE / "out" / "belief_rows_clean.json"))
            if r["bench"] in BENCHES and r["judge"] in QWENS}
    return jobs, solve_msgs, own, rows


def prep():
    jobs, solve_msgs, own, rows = load()
    pull, first = [], []
    for (judge, iid), r in rows.items():
        j = jobs[(judge, iid)]
        msgs = solve_msgs[(judge, j["qid"])]
        last = dict(msgs[-1])
        last["content"] = last["content"] + PULL.format(cand=j["candidates"][0])
        pull.append(dict(cache_key=f"pull|{judge}|{iid}", model=judge, messages=msgs[:-1] + [last]))
        o = own.get(f"{judge}|{j['qid']}")
        if o and o["clean"]:
            first.append(dict(cache_key=f"solvefirst|{judge}|{iid}", model=judge, messages=msgs + [
                {"role": "assistant", "content": o["answer"]},
                {"role": "user", "content": FIRST + j["messages"][0]["content"]}]))
    for name, L in (("pull", pull), ("solvefirst", first)):
        with gzip.open(HERE / "inputs" / f"gen_{name}.jsonl.gz", "wt") as f:
            f.write("".join(json.dumps(x) + "\n" for x in L))
        print(name, len(L), collections.Counter(x["model"] for x in L))


def pairs():
    jobs, _, _, rows = load()
    gen = {r["cache_key"]: r for r in map(json.loads, open(HERE / "out" / "gen_pull.jsonl"))}
    out = []
    for (judge, iid) in rows:
        g = gen.get(f"pull|{judge}|{iid}")
        if g and g["clean"]:
            j = jobs[(judge, iid)]
            out.append(dict(cache_key=f"pull|{judge}|{iid}", question=j["question"], a=g["text"], b=j["candidates"][0]))
    with gzip.open(HERE / "inputs" / "pairs_pull.jsonl.gz", "wt") as f:
        f.write("".join(json.dumps(x) + "\n" for x in out))
    print(len(out), "pairs")


def binof(b):
    k = round(b * 7)
    return "0/7" if k == 0 else "1-3" if k <= 3 else "4-6" if k <= 6 else "7/7"


def analyze():
    jobs, _, _, rows = load()
    L = ["# Causal tests of the re-solve account (Qwens, thinking off, RB2 Math + BFF, clean labels)\n"]
    pm = {r["cache_key"]: r["verdict"] for r in map(json.loads, open(HERE / "out" / "matches_glm5.3-flash_pull.jsonl"))}
    L += ["## Pull: shown the candidate, asked to SOLVE. Share of solves that land on the candidate's answer\n",
          "Belief = share of the model's 7 own answers (candidate NOT shown) that reach the candidate's answer. "
          "Without the candidate, the share landing on it would be about the belief itself (0 at 0/7).\n",
          "| candidate | 0/7 | 1-3 | 4-6 | 7/7 |", "|---|---|---|---|---|"]
    for ok, name in ((0, "wrong"), (1, "right")):
        cells = []
        for b in ("0/7", "1-3", "4-6", "7/7"):
            v = [pm[f"pull|{k[0]}|{k[1]}"] == "SAME" for k, r in rows.items() if r["target_ok"] == ok and binof(r["belief"]) == b
                 and pm.get(f"pull|{k[0]}|{k[1]}") in ("SAME", "DIFFERENT")]
            cells.append(f"{100 * np.mean(v):.0f}% (n={len(v)})" if v else "–")
        L.append(f"| {name} | " + " | ".join(cells) + " |")
    gen = {r["cache_key"]: r for r in map(json.loads, open(HERE / "out" / "gen_solvefirst.jsonl"))}
    L += ["", "## Solve first, then judge: wrong answers approved\n",
          "| condition | 0/7 | 1-3 | 4-6 | 7/7 |", "|---|---|---|---|---|"]
    for cond in ("usual judge prompt (pool, spoken verdict)", "own answer first"):
        cells = []
        for b in ("0/7", "1-3", "4-6", "7/7"):
            v = []
            for k, r in rows.items():
                if r["target_ok"] or binof(r["belief"]) != b:
                    continue
                if cond.startswith("usual"):
                    if r.get("spoken") is not None:
                        v.append(r["acc_S"] if r.get("acc_S") is not None else r["spoken"])
                else:
                    g = gen.get(f"solvefirst|{k[0]}|{k[1]}")
                    vv = parse_verdict(g["text"]) if g else None
                    if vv is not None:
                        v.append(int(vv))
            cells.append(f"{100 * np.mean(v):.0f}% (n={len(v)})" if v else "–")
        L.append(f"| {cond} | " + " | ".join(cells) + " |")
    out = HERE / "out" / "causal.md"
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    prep() if "--prep" in sys.argv else pairs() if "--pairs" in sys.argv else analyze()
