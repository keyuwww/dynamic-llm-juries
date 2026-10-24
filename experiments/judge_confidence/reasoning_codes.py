#!/usr/bin/env python3
"""
Step 1.4: what does a judge's reasoning look like when it is confidently wrong?

Sample: every confident error on real BFF answers without the reference (all 5 samples agree, majority verdict
disagrees with the unanimous expert label), and for each judge an equal-size random set of confident CORRECT
verdicts on the same kind of answer (same expert label), as a control. The first sample's reasoning is coded by
Nemotron-3 Super 120B (not one of the judges), which does not see the expert label or whether the judge was right.

Codes: recomputed (did the grader redo at least one calculation itself), checked_inputs (did it check numbers
against the question), named_issue (did it name a specific flaw), hedged (did it express doubt), focus
(final_answer / method / numbers / definitions / completeness), plus reasoning length in tokens.

Raw (git-ignored): results/raw/reasoning_codes.jsonl. Summary: results/reasoning_summary.md

  python experiments/judge_confidence/reasoning_codes.py
"""
import asyncio, collections, json, random, re

from jc_common import HERE, RAW, JsonlCache, call_cost, make_chats, run_jobs, select_models

CODER = "nemotron3-super-120b"
PROMPT = """Below is an AI grader's reasoning about whether an assistant's answer to a finance question is correct. Describe HOW the grader reasoned. Do not judge whether the grader was right.

[QUESTION (shortened)]
{question}

[GRADER'S REASONING]
{reasoning}

Reply with ONLY a JSON object:
{{"recomputed": "yes|no",            // did the grader redo at least one calculation itself (not just restate the answer's numbers)?
 "checked_inputs": "yes|no",        // did it compare numbers or facts in the answer against the question?
 "named_issue": "yes|no",           // did it name a specific flaw in the answer?
 "hedged": "yes|no",                // did it express doubt or uncertainty?
 "focus": "final_answer|method|numbers|definitions|completeness"}}"""


def sample(seed=0):
    rows = [json.loads(l) for l in open(RAW / "judgments_real.jsonl")]
    rows = [r for r in rows if r["condition"] == "none" and r["gold_unanimous"] in (0, 1) and r["vote_share"] in (0.0, 1.0)]
    rng = random.Random(seed)
    out = []
    for j in sorted({r["judge"] for r in rows}):
        for gold in (0, 1):
            rs = [r for r in rows if r["judge"] == j and r["gold_unanimous"] == gold]
            wrong = [r for r in rs if (r["vote_share"] == 1.0) != (gold == 1)]
            right = [r for r in rs if (r["vote_share"] == 1.0) == (gold == 1)]
            out += [(r, "confident_error") for r in wrong]
            out += [(r, "confident_correct") for r in rng.sample(right, min(len(wrong), len(right)))]
    return out


def run():
    todo = sample()
    cache = JsonlCache(RAW / "reasoning_codes.jsonl")
    chat = make_chats(select_models(CODER))[CODER]
    print(f"{len(todo)} verdicts to code", flush=True)

    async def one(r, group):
        ck = f"{r['judge']}|{r['item_id']}"
        if ck in cache:
            return
        q = r["prompt"].split("[USER]")[-1].split("[ASSISTANT]")[0].strip()[:1500]
        reasoning = r["samples"][0]["text"][-5000:]
        prompt = PROMPT.format(question=q, reasoning=reasoning)
        out = await chat.chat([{"role": "user", "content": prompt}], max_tokens=1024, temperature=0.0)
        raw = out["outputs"][0]["text"]
        m = re.search(r"\{.*\}", raw or "", re.S)
        try:
            p = json.loads(re.sub(r"//[^\n]*", "", m.group(0))) if m else {}
        except json.JSONDecodeError:
            p = {}
        cache.put(dict(cache_key=ck, judge=r["judge"], item_id=r["item_id"], examinee=r["examinee"], group=group,
                       gold=r["gold_unanimous"], verdict=int(r["vote_share"] == 1.0), n_out=r["samples"][0]["n_out"],
                       coder=CODER, prompt=prompt, raw=raw, **{k: p.get(k) for k in
                                                                ("recomputed", "checked_inputs", "named_issue", "hedged", "focus")},
                       cost=call_cost(chat.spec, out["n_in"], out["n_out"])))

    asyncio.run(run_jobs([lambda r=r, g=g: one(r, g) for r, g in todo], 8, "reasoning"))


def summarize():
    rows = [json.loads(l) for l in open(RAW / "reasoning_codes.jsonl")]
    L = ["# How judges reason when they are confidently wrong (real BFF, no reference)", "",
         "Coder: Nemotron-3 Super 120B, blind to the label and to whether the judge was right. Control = an equal number "
         "of confident correct verdicts per judge and expert label. Rows split by what the judge said.", ""]
    for verdict, name in ((1, "Judge said CORRECT (missed errors vs correct accepts)"),
                          (0, "Judge said INCORRECT (false rejections vs correct rejections)")):
        L += [f"## {name}", "", "| Group | n | Recomputed | Checked inputs | Named an issue | Hedged | Median tokens |",
              "|---|---|---|---|---|---|---|"]
        for g in ("confident_error", "confident_correct"):
            rs = [r for r in rows if r["group"] == g and r["verdict"] == verdict]
            if not rs:
                continue
            f = lambda k: f"{sum(r.get(k) == 'yes' for r in rs) / len(rs):.0%}"
            med = sorted(r["n_out"] for r in rs)[len(rs) // 2]
            L.append(f"| {g.replace('_', ' ')} | {len(rs)} | {f('recomputed')} | {f('checked_inputs')} | "
                     f"{f('named_issue')} | {f('hedged')} | {med} |")
        L += ["", "Focus of the reasoning:", ""]
        for g in ("confident_error", "confident_correct"):
            rs = [r for r in rows if r["group"] == g and r["verdict"] == verdict]
            c = collections.Counter(r.get("focus") for r in rs)
            L.append(f"- {g.replace('_', ' ')}: " + ", ".join(f"{k} {v}" for k, v in c.most_common()))
        L.append("")
    L.append(f"Coder cost ${sum(r['cost'] for r in rows):.2f}.")
    (HERE / "results" / "reasoning_summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    run()
    summarize()
