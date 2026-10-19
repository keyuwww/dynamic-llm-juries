#!/usr/bin/env python3
"""
Content coding of judge-hard vs judge-easy items: what kind of task each item is, what a judge has to do to
verify it, and what (if anything) makes it tricky.

Sample per benchmark: up to --n items that most judges got wrong (share wrong ≥ 0.5) and the same number that
every judge got right. The coder (DeepSeek-V3.1) sees the question, the response(s) and the gold label but is
NOT told whether judges found the item hard, so the hard / easy comparison is not driven by the coder.

  uv run python experiments/cross_benchmark/code_content.py --bench bff --work <work folder>
Reads data/<bench>_itemhard.pkl (xb_factors.py) and data/<bench>_items.pkl; writes results/<bench>/content_codes.jsonl.
"""
import argparse, asyncio, json, re, sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
from common import JsonlCache, call_cost, make_chats, run_jobs, select_models  # noqa: E402

TASK = ["calculation", "factual_knowledge", "rule_or_standard", "logic_puzzle", "code", "instruction_following",
        "open_writing", "advice_or_explanation", "safety_sensitive", "underspecified_request", "other"]
VERIFY = ["recompute_numbers", "recall_facts", "check_rule_application", "trace_reasoning", "run_or_read_code",
          "check_constraints", "compare_quality", "judge_harm_or_refusal", "judge_whether_answerable"]
DRIVER = ["subtle_numeric_error", "partially_correct", "convention_or_assumption_dependent", "ambiguous_question",
          "subjective_quality", "near_identical_responses", "long_or_dense_input", "plausible_but_wrong_reasoning",
          "unusual_request_type", "gold_debatable", "none_obvious"]

PROMPT = """You are characterising a benchmark item that an LLM judge had to grade.

[FORMAT]
{fmt}

[QUESTION / REQUEST]
{question}

{responses}

[GOLD LABEL]
{gold}

Classify the item. Use only these keys.
- task (one): {task}
- verify (one or two): what a grader must actually do to reach the gold label: {verify}
- driver (one or two): what could make grading this item tricky: {driver}
- skill: up to 6 words naming the main skill or knowledge the question demands (e.g. "deferred tax under IAS 12", "modular arithmetic", "refusing a phishing request").

Answer with ONLY a JSON object, e.g.
{{"task": "calculation", "verify": ["recompute_numbers"], "driver": ["subtle_numeric_error"], "skill": "bond yield to maturity"}}"""


def cut(s, n):
    s = str(s or "")
    return s if len(s) <= n else s[:n] + " [...]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--coder", default="deepseek-v3.1")
    a = ap.parse_args()
    base = Path(a.work) / "cross_benchmark"
    ih = pd.read_pickle(base / "data" / f"{a.bench}_itemhard.pkl")
    items = pd.read_pickle(base / "data" / f"{a.bench}_items.pkl").set_index("key")
    if ih.fmt.iat[0] == "pair":       # one presentation per pair (order 0), so a pair is not coded twice
        ih = ih[ih.index.map(lambda k: str(items.loc[k, "order"]) == "0")]
    hard = ih[ih.wrong >= 0.5]
    easy = ih[ih.wrong == 0]
    pick = pd.concat([hard.sample(min(a.n, len(hard)), random_state=0).assign(set="hard"),
                      easy.sample(min(a.n, len(easy)), random_state=0).assign(set="easy")])
    cache = JsonlCache(base / "results" / a.bench / "content_codes.jsonl")
    chat = make_chats(select_models(a.coder))[a.coder]

    async def code(key, row):
        if key in cache:
            return
        it = items.loc[key]
        if it.fmt == "pair":
            fmt = "Pairwise: which of two responses is better."
            resp = f"[RESPONSE A]\n{cut(it.resp_a, 1800)}\n\n[RESPONSE B]\n{cut(it.resp_b, 1800)}"
            gold = "Response A is better" if it.gold == 1 else "Response B is better"
        else:
            fmt = "Single grading: is this response good / correct?"
            resp = f"[RESPONSE]\n{cut(it.response, 2500)}"
            gold = "good / correct" if it.gold == 1 else "bad / incorrect"
        r = await chat.chat([{"role": "user", "content": PROMPT.format(
            fmt=fmt, question=cut(it.question, 2500), responses=resp, gold=gold, task=", ".join(TASK),
            verify=", ".join(VERIFY), driver=", ".join(DRIVER))}], max_tokens=300, temperature=0.0)
        t = r["outputs"][0]["text"]
        j = {}
        for s in reversed(re.findall(r"\{[^{}]*\}", t, re.S)):
            try:
                j = json.loads(s)
                break
            except json.JSONDecodeError:
                continue
        lst = lambda v, allowed: [x for x in (v if isinstance(v, list) else [v]) if x in allowed][:2]
        cache.put(dict(cache_key=key, key=key, set=row["set"], wrong=float(row["wrong"]), category=str(it.category),
                       task=j.get("task") if j.get("task") in TASK else "other", verify=lst(j.get("verify"), VERIFY),
                       driver=lst(j.get("driver"), DRIVER), skill=str(j.get("skill", ""))[:80],
                       cost=call_cost(chat.spec, r["n_in"], r["n_out"])))

    asyncio.run(run_jobs([lambda k=k, r=r: code(k, r) for k, r in pick.iterrows()], 16, "content"))
    df = pd.DataFrame(cache.rows.values())
    print(a.bench, df.groupby("set").task.value_counts().unstack(0).fillna(0).astype(int).to_dict())


if __name__ == "__main__":
    main()
