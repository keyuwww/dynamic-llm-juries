#!/usr/bin/env python3
"""
Multi-judge debate pilot: Jev (decision-only, no reasoning) vs gpt-oss-120b (Tinker-hosted
reasoning judge), on BFF-noref items where their independent (round-1) verdicts disagree.

Literature context: ChatEval (ICLR 2024) and D3 (arXiv:2410.04663) show debate can beat
independent majority-vote, but "Beyond Consensus: Downward Bias and Role Asymmetry in
Multi-Agent LLM Judges" (arXiv:2608.30373) shows debate can introduce order-dependent bias --
whichever judge moves SECOND may get disproportionately pulled toward the first judge's
verdict, right or wrong. This pilot explicitly tests for that: every disagreement item is
debated in BOTH orders so order effects are visible rather than averaged away.

Round 1 (already collected, zero new calls): Jev's noref verdict, gpt-oss-120b's noref verdict
+ reasoning -- loaded from experiments/jev_bff/jev_bff_results and
experiments/tinker_pool/bff_results/judgments.jsonl.

Round 2 (new calls, this script), only on round-1 DISAGREEMENT items:
  Order A (jev_first):   Jev revises after seeing gpt-oss's round-1 reasoning+verdict.
                          Then gpt-oss revises after seeing Jev's REVISED verdict (last word).
  Order B (gptoss_first): gpt-oss revises after seeing Jev's round-1 verdict+confidence.
                          Then Jev revises after seeing gpt-oss's REVISED reasoning (last word).

Needs TYPESAFE_API_KEY (Jev) and TINKER_API_KEY + tinker/tinker-cookbook (gpt-oss-120b) --
run via experiments/tinker_pool_modal.py::run_debate, same as the rest of the Tinker-pool
experiments (local PyPI access to tinker is blocked here; Modal's build environment isn't).

Usage (inside the Modal image): uv run python experiments/debate/run_debate_pilot.py --limit 40
"""
import argparse
import asyncio
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
sys.path.insert(0, str(HERE.parent / "jev_bff"))
sys.path.insert(0, str(HERE.parent / "tinker_pool"))

from backends import Backend, get_noul  # noqa: E402
import run_jev_bff as rjb  # noqa: E402
from common import POOL_BY_KEY, load_env, make_chats, parse_verdict  # noqa: E402

GPTOSS_KEY = "gpt-oss-120b"

DEBATE_INSTR = (
    "Evaluate the assistant's FINAL response in this finance/accounting conversation. "
    "Answer yes only if it correctly answers the user's final question: the key facts, "
    "calculations, numbers and conclusions must be correct. Minor wording or formatting "
    "issues do not matter; a wrong number, wrong method or wrong conclusion makes it incorrect.\n\n"
    "Another AI judge independently reviewed this same response and reached a DIFFERENT "
    "conclusion: it said the response is {other_verdict}. {other_reasoning_block}"
    "Reconsider the response given this. You may keep your original view or change it -- "
    "decide based on what is actually correct, not on deferring to the other judge."
)
CRITERIA = {"true": "The final response is substantively correct.",
            "false": "The final response contains a substantive error or reaches a wrong answer."}

BFF_JUDGE_DEBATE = """You are grading an AI assistant's answer in a finance/accounting conversation.

{conversation}
{reference}
Is the assistant's FINAL response a correct answer to the user's final question? The key facts, calculations, numbers and conclusions must be correct; minor wording or formatting issues do not matter, but a wrong number, wrong method or wrong conclusion makes it incorrect.

Another AI judge independently reviewed this same response and reached a verdict of {other_verdict} ({other_conf_note}). Reconsider given this -- you may keep your original view or change it, based on what is actually correct.

Reason briefly, then end with exactly one line: "VERDICT: CORRECT" or "VERDICT: INCORRECT"."""


def render_conv(conv):
    return "\n\n".join(f"[{m['role'].upper()}]\n{m['content']}" for m in conv)


def load_round1(repo):
    import pandas as pd
    jev = pd.read_csv(repo / "experiments/jev_bff/jev_bff_results/items.csv")
    jev = jev[jev.cond == "noref"][["id", "p", "human"]]
    gptoss = {}
    for line in (repo / "experiments/tinker_pool/bff_results/judgments.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r["judge"] == GPTOSS_KEY and r["condition"] == "none":
            gptoss[r["item_id"]] = r
    rows = []
    for _, row in jev.iterrows():
        g = gptoss.get(row["id"])
        if not g:
            continue
        rows.append(dict(id=row["id"], human=int(row["human"]), jev_p=float(row["p"]),
                          jev_verdict=int(row["p"] >= 0.5),
                          gptoss_vote_share=g["vote_share"], gptoss_verdict=int((g["vote_share"] or 0) > 0.5),
                          gptoss_reasoning=g["raw"][0] if g["raw"] else ""))
    return rows


def summarize(rows, out):
    n = len(rows)
    if n == 0:
        print("no rows", flush=True)
        return

    def acc(key):
        return sum(1 for r in rows if r[key] == r["gold"]) / n

    def flip_rate(subset, final_key):
        if not subset:
            return float("nan")
        return sum(1 for r in subset if r[final_key] != r["gold"]) / len(subset)

    r1_jev_acc, r1_gptoss_acc = acc("jev_r1"), acc("gptoss_r1")
    a_acc, b_acc = acc("final_orderA"), acc("final_orderB")
    jev_right_gptoss_wrong = [r for r in rows if r["jev_r1"] == r["gold"] and r["gptoss_r1"] != r["gold"]]
    gptoss_right_jev_wrong = [r for r in rows if r["gptoss_r1"] == r["gold"] and r["jev_r1"] != r["gold"]]

    L = ["# Multi-judge debate pilot: Jev vs gpt-oss-120b, BFF-noref disagreement items", "",
         f"n={n} items where round-1 (independent) verdicts disagreed. Reconsidering arXiv:2608.30373's "
         "order-asymmetry finding -- every item debated in both orders.", "",
         "## Round-1 accuracy on this (hard, disagreement-only) subset", "",
         f"- Jev alone: {r1_jev_acc:.3f}", f"- gpt-oss-120b alone: {r1_gptoss_acc:.3f}", "",
         "## Round-2 (post-debate) final-verdict accuracy, by order", "",
         f"- Order A (Jev revises first, gpt-oss has last word): {a_acc:.3f}",
         f"- Order B (gpt-oss revises first, Jev has last word): {b_acc:.3f}", "",
         "## Order-asymmetry / groupthink check", "",
         f"- Of {len(jev_right_gptoss_wrong)} items where Jev was right and gpt-oss was wrong (round 1): "
         f"debate ends up wrong {100*flip_rate(jev_right_gptoss_wrong,'final_orderA'):.0f}% of the time under "
         f"Order A, {100*flip_rate(jev_right_gptoss_wrong,'final_orderB'):.0f}% under Order B.",
         f"- Of {len(gptoss_right_jev_wrong)} items where gpt-oss was right and Jev was wrong (round 1): "
         f"debate ends up wrong {100*flip_rate(gptoss_right_jev_wrong,'final_orderA'):.0f}% of the time under "
         f"Order A, {100*flip_rate(gptoss_right_jev_wrong,'final_orderB'):.0f}% under Order B.", ""]
    (out / "summary.md").write_text("\n".join(L))
    print("\n".join(L), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None)
    ap.add_argument("--verdicts-path"); ap.add_argument("--bff-path")
    a = ap.parse_args()
    repo = HERE.parent.parent
    out = Path(a.out or HERE / "debate_pilot_results")
    out.mkdir(parents=True, exist_ok=True)

    round1 = load_round1(repo)
    disagree = [r for r in round1 if r["jev_verdict"] != r["gptoss_verdict"]]
    print(f"{len(round1)} items with both round-1 verdicts; {len(disagree)} disagreements", flush=True)
    random.Random(a.seed).shuffle(disagree)
    pilot = disagree[: a.limit]
    print(f"piloting on {len(pilot)} disagreement items", flush=True)

    v, b = rjb.load_data(a.verdicts_path, a.bff_path)
    items, _ = rjb.build_items(v, b, consensus="unanimous")
    by_id = {it["id"]: it for it in items}

    jev = Backend("jev")
    load_env()
    chats = make_chats([POOL_BY_KEY[GPTOSS_KEY]], thinking="off")
    gptoss_chat = chats[GPTOSS_KEY]

    cache_f = out / "debate_predictions.jsonl"
    done = {}
    if cache_f.exists():
        for line in cache_f.read_text().splitlines():
            r = json.loads(line)
            done[r["id"]] = r

    def jev_call(conv, ref, other_verdict_word, other_reasoning):
        state = {"conversation": conv}
        if ref:
            state["reference_answer_for_final_question"] = ref
        reasoning_block = f'Its stated reasoning: "{other_reasoning[:600]}"\n\n' if other_reasoning else ""
        instr = DEBATE_INSTR.format(other_verdict=other_verdict_word, other_reasoning_block=reasoning_block)
        q = {"is_correct": jev.Noul(instructions=instr, criteria=CRITERIA)}
        res, meta = jev.ask(state, q)
        p = get_noul(res, "is_correct")
        return dict(verdict=int(round(p)) if p is not None else 0, p=p)

    async def gptoss_call(conv, ref, other_verdict_word, other_conf_note):
        prompt = BFF_JUDGE_DEBATE.format(
            conversation=render_conv(conv), reference=("\n[REFERENCE ANSWER]\n" + ref + "\n" if ref else ""),
            other_verdict=other_verdict_word, other_conf_note=other_conf_note)
        r = await gptoss_chat.chat([{"role": "user", "content": prompt}], max_tokens=1024, temperature=0.7, n=1)
        v = parse_verdict(r["outputs"][0]["text"])
        return dict(verdict=v if v is not None else 0, raw=r["outputs"][0]["text"])

    async def run_item(r1):
        iid = r1["id"]
        if iid in done:
            return
        it = by_id.get(iid)
        if it is None:
            print(f"[skip] {iid}: no conv/ref found", file=sys.stderr, flush=True)
            return
        conv, ref, gold = it["conv"], it["ref"], r1["human"]
        jev_word = "CORRECT" if r1["jev_verdict"] else "INCORRECT"
        gptoss_word = "CORRECT" if r1["gptoss_verdict"] else "INCORRECT"

        # Order A: jev_first
        jev_r2 = jev_call(conv, ref, gptoss_word, r1["gptoss_reasoning"])
        gptoss_r2a = await gptoss_call(conv, ref, "CORRECT" if jev_r2["verdict"] else "INCORRECT",
                                        "its revised verdict after seeing your reasoning")

        # Order B: gptoss_first
        gptoss_r2b = await gptoss_call(conv, ref, jev_word, f"confidence {abs(r1['jev_p']-0.5)*2:.2f}")
        jev_r2b = jev_call(conv, ref, "CORRECT" if gptoss_r2b["verdict"] else "INCORRECT", gptoss_r2b["raw"])

        row = dict(id=iid, gold=gold, jev_r1=r1["jev_verdict"], gptoss_r1=r1["gptoss_verdict"],
                   jev_r2_orderA=jev_r2["verdict"], final_orderA=gptoss_r2a["verdict"],
                   gptoss_r2_orderB=gptoss_r2b["verdict"], final_orderB=jev_r2b["verdict"])
        done[iid] = row
        with open(cache_f, "a") as fh:
            fh.write(json.dumps(row) + "\n")
        if len(done) % 5 == 0:
            print(f"  {len(done)}/{len(pilot)}", flush=True)

    async def run_all():
        for r1 in pilot:
            await run_item(r1)

    asyncio.run(run_all())
    rows = [done[r["id"]] for r in pilot if r["id"] in done]
    summarize(rows, out)


if __name__ == "__main__":
    main()
