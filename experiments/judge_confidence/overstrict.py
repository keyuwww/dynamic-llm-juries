#!/usr/bin/env python3
"""
Over-strictness study: correct answers (all experts said correct) that a judge rejects with all 5 samples even when
it has the expert reference.

1. --code     A coder outside the judge trio (Nemotron-3 Super 120B) reads the question, the reference, the answer and
              the judge's reasoning, and labels WHY the judge rejected it and whether the objection holds.
              Raw: results/raw/overstrict_codes.jsonl (one row per (judge, item); prompt and raw output kept).
2. --analyze  Reason counts, plus whether cheap signals would flag these false rejections:
              - vote share (not unanimous)          -> by construction never fires on these cases; reported for all
                                                      rejections of correct answers instead
              - a second judge disagrees            -> catch rate vs escalation rate, per judge pair
              - the same judge without the reference disagrees
              Summary: results/overstrict_summary.md

  python experiments/judge_confidence/overstrict.py --code
  python experiments/judge_confidence/overstrict.py --analyze
"""
import argparse, asyncio, collections, json, re

from jc_common import HERE, RAW, JsonlCache, call_cost, make_chats, run_jobs, select_models

CODER = "nemotron3-super-120b"
REASONS = {
    "ROUNDING": "the judge objects to a numeric difference that is only rounding/precision",
    "OMISSION": "the judge objects that the answer leaves out a point, step or caveat that the reference includes",
    "ALT_METHOD": "the answer uses a different but defensible method, assumption or convention than the reference",
    "JUDGE_MISREAD": "the judge misread the answer, the question or the reference",
    "JUDGE_CALC_ERROR": "the judge made its own calculation or reasoning error",
    "ANSWER_FLAW": "the answer really has a substantive error or wrong conclusion that the experts overlooked",
    "FORMAT_OR_EXTRA": "the judge objects to presentation, extra content, or how the final answer is stated",
    "OTHER": "none of the above",
}

PROMPT = """Three finance experts all marked the ASSISTANT'S ANSWER below as correct. An AI grader, which was given the same expert reference answer, marked it INCORRECT. Your job is to explain the disagreement.

[CONVERSATION (user turns)]
{question}

[EXPERT REFERENCE ANSWER]
{ref}

[ASSISTANT'S ANSWER]
{answer}

[AI GRADER'S REASONING]
{judge}

Choose the ONE main reason the grader rejected the answer:
{reasons}

Then judge whether the grader's objection is valid: "valid" (the answer really is wrong on a point that matters), "partly" (a real but minor issue that should not make it incorrect), or "invalid" (no real issue).

Reply with ONLY a JSON object:
{{"reason": "<one label>", "objection": "valid|partly|invalid", "explanation": "<one or two sentences naming the specific point>"}}"""


BLIND = """Below is a finance question, an expert's reference answer, and an assistant's answer. Check the assistant's answer carefully.

[CONVERSATION (user turns)]
{question}

[EXPERT REFERENCE ANSWER]
{ref}

[ASSISTANT'S ANSWER]
{answer}

Answer two questions:
1. Does the assistant's final conclusion / final answer match the reference? "yes", "partly", or "no".
2. Does the assistant's answer contain a substantive error anywhere (a wrong number, wrong formula, wrong definition, wrong fact, or a wrong reasoning step), even if the final conclusion is right? Ignore style, length and minor rounding. "yes" or "no"; if yes, name the error.

Reply with ONLY a JSON object:
{{"conclusion_matches": "yes|partly|no", "substantive_error": "yes|no", "error": "<the error, or empty>"}}"""


def split_prompt(p):
    """Recover the pieces from the stored judge prompt (render_conv + REF_BLOCK format)."""
    ref = p.split("[REFERENCE ANSWER (written by an expert)]")[-1].split("Is the assistant's FINAL")[0].strip()
    body = p.split("[REFERENCE ANSWER")[0]
    turns = re.split(r"\n\n(?=\[(?:USER|ASSISTANT)\]\n)", body.split("\n\n", 1)[1])
    answer = turns[-1].split("\n", 1)[1].strip() if turns[-1].startswith("[ASSISTANT]") else ""
    question = "\n\n".join(turns[:-1]).strip()
    return question, ref, answer


def cases():
    rows = [json.loads(l) for l in open(RAW / "judgments_real.jsonl")]
    return [r for r in rows if r["condition"] == "human" and r["gold_unanimous"] == 1 and r["vote_share"] == 0], rows


def code(a):
    cs, _ = cases()
    cache = JsonlCache(RAW / "overstrict_codes.jsonl")
    chat = make_chats(select_models(CODER))[CODER]
    reasons = "\n".join(f"- {k}: {v}" for k, v in REASONS.items())
    print(f"{len(cs)} confident rejections of correct answers; coder {CODER}", flush=True)

    async def one(r):
        ck = f"{r['judge']}|{r['item_id']}"
        if ck in cache:
            return
        q, ref, ans = split_prompt(r["prompt"])
        judge_text = r["samples"][0]["text"]
        prompt = PROMPT.format(question=q[-6000:], ref=ref[:6000], answer=ans[:8000], judge=judge_text[-4000:],
                               reasons=reasons)
        out = await chat.chat([{"role": "user", "content": prompt}], max_tokens=2048, temperature=0.0)
        raw = out["outputs"][0]["text"]
        m = re.search(r"\{.*\}", raw or "", re.S)
        try:
            parsed = json.loads(m.group(0)) if m else {}
        except json.JSONDecodeError:
            parsed = {}
        cache.put(dict(cache_key=ck, judge=r["judge"], item_id=r["item_id"], examinee=r["examinee"], coder=CODER,
                       prompt=prompt, raw=raw, reason=parsed.get("reason"), objection=parsed.get("objection"),
                       explanation=parsed.get("explanation"), n_in=out["n_in"], n_out=out["n_out"],
                       cost=call_cost(chat.spec, out["n_in"], out["n_out"])))

    asyncio.run(run_jobs([lambda r=r: one(r) for r in cs], a.concurrency, "code"))


def blind_sets():
    """Answers for the blind check: every correct answer some judge confidently rejected ('rejected'), and a control
    set of the same size of correct answers ALL three judges accepted with the reference ('accepted')."""
    import random
    cs, rows = cases()
    rej = sorted({r["item_id"] for r in cs})
    acc = collections.defaultdict(list)
    for r in rows:
        if r["condition"] == "human" and r["gold_unanimous"] == 1 and r["vote_share"] is not None:
            acc[r["item_id"]].append(r["vote_share"] >= 0.5)
    ok = sorted(i for i, v in acc.items() if len(v) == 3 and all(v) and i not in rej)
    ctrl = random.Random(0).sample(ok, min(len(rej), len(ok)))
    prompts = {}
    for r in rows:
        if r["condition"] == "human" and r["item_id"] in set(rej) | set(ctrl) and r["item_id"] not in prompts:
            prompts[r["item_id"]] = r["prompt"]
    return [(i, "rejected", prompts[i]) for i in rej] + [(i, "accepted", prompts[i]) for i in ctrl]


def blind(a):
    cache = JsonlCache(RAW / "overstrict_blind.jsonl")
    chat = make_chats(select_models(CODER))[CODER]
    todo = blind_sets()
    print(f"blind check: {len(todo)} answers ({sum(g == 'rejected' for _, g, _ in todo)} rejected, "
          f"{sum(g == 'accepted' for _, g, _ in todo)} accepted control)", flush=True)

    async def one(item_id, group, p):
        if item_id in cache:
            return
        q, ref, ans = split_prompt(p)
        prompt = BLIND.format(question=q[-6000:], ref=ref[:6000], answer=ans[:8000])
        out = await chat.chat([{"role": "user", "content": prompt}], max_tokens=2048, temperature=0.0)
        raw = out["outputs"][0]["text"]
        m = re.search(r"\{.*\}", raw or "", re.S)
        try:
            parsed = json.loads(m.group(0)) if m else {}
        except json.JSONDecodeError:
            parsed = {}
        cache.put(dict(cache_key=item_id, item_id=item_id, group=group, coder=CODER, prompt=prompt, raw=raw,
                       conclusion_matches=parsed.get("conclusion_matches"),
                       substantive_error=parsed.get("substantive_error"), error=parsed.get("error"),
                       n_in=out["n_in"], n_out=out["n_out"], cost=call_cost(chat.spec, out["n_in"], out["n_out"])))

    asyncio.run(run_jobs([lambda t=t: one(*t) for t in todo], a.concurrency, "blind"))


def analyze():
    cs, rows = cases()
    R = {(r["judge"], r["item_id"], r["condition"]): r for r in rows}
    judges = sorted({r["judge"] for r in rows})
    codes = {}
    if (RAW / "overstrict_codes.jsonl").exists():
        for l in open(RAW / "overstrict_codes.jsonl"):
            c = json.loads(l)
            codes[(c["judge"], c["item_id"])] = c
    n_by_item = collections.Counter(r["item_id"] for r in cs)
    L = ["# Over-strict judges: correct answers rejected with all 5 samples, even with the reference", "",
         f"{len(cs)} cases (judge × answer) on {len(n_by_item)} answers that all experts marked correct. "
         f"Rejected by 1/2/3 judges: {dict(sorted(collections.Counter(n_by_item.values()).items()))}.", ""]

    # 1. reasons
    L += ["## Why the judge rejected it (coded by Nemotron-3 Super 120B)", "",
          "| Reason | Cases | Objection valid | Partly | Invalid |", "|---|---|---|---|---|"]
    by = collections.defaultdict(list)
    for r in cs:
        c = codes.get((r["judge"], r["item_id"]))
        if c:
            by[c.get("reason") or "unparsed"].append(c)
    for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
        o = collections.Counter(c.get("objection") for c in v)
        L.append(f"| {k} | {len(v)} | {o['valid']} | {o['partly']} | {o['invalid']} |")
    shared = {i for i, n in n_by_item.items() if n == 3}
    o3 = collections.Counter(codes[(r['judge'], r['item_id'])].get("objection") for r in cs
                             if r["item_id"] in shared and (r["judge"], r["item_id"]) in codes)
    L += ["", f"Answers rejected by all three judges ({len(shared)}): coder says objection valid {o3['valid']}, "
          f"partly {o3['partly']}, invalid {o3['invalid']} (over judge × answer cases).", ""]

    # 2. cheap flags
    L += ["## Would a cheap signal flag these false rejections?", ""]
    for c in ("human",):
        corr = [r for r in rows if r["condition"] == c and r["gold_unanimous"] == 1 and r["vote_share"] is not None]
        rej = [r for r in corr if r["vote_share"] < 0.5]
        L.append(f"- **Vote share:** of {len(rej)} majority rejections of correct answers (all judges), "
                 f"{sum(r['vote_share'] == 0 for r in rej)} ({sum(r['vote_share'] == 0 for r in rej) / len(rej):.0%}) "
                 "are unanimous, so a 'samples disagree' trigger can catch at most "
                 f"{1 - sum(r['vote_share'] == 0 for r in rej) / len(rej):.0%} of them.")
    nr = [R.get((r["judge"], r["item_id"], "none")) for r in cs]
    L.append(f"- **Same judge without the reference:** accepts (vote ≥ 0.5) in "
             f"{sum(1 for x in nr if x and x['vote_share'] is not None and x['vote_share'] >= 0.5)} of {len(cs)} cases, "
             "so the strictness is not caused by the reference.")
    L += ["", "**Second judge disagrees (with the reference).** Catch = share of judge A's confident false rejections "
          "where judge B says CORRECT (majority). Escalated = share of ALL unanimous-label answers where A and B "
          "disagree. Lost = share of A's correct rejections of wrong answers where B says CORRECT (would be escalated "
          "too, so these cost a review but are not lost if a human resolves them).", "",
          "| Judge A | Judge B | A's false rejections | Caught by B | Escalated (all answers) |",
          "|---|---|---|---|---|"]
    for ja in judges:
        mine = [r for r in cs if r["judge"] == ja]
        for jb in judges:
            if jb == ja or not mine:
                continue
            caught = sum(1 for r in mine if (R.get((jb, r["item_id"], "human")) or {}).get("vote_share", 0) is not None
                         and (R.get((jb, r["item_id"], "human")) or {}).get("vote_share", 0) >= 0.5)
            allr = [r for r in rows if r["judge"] == ja and r["condition"] == "human" and r["gold_unanimous"] in (0, 1)
                    and r["vote_share"] is not None]
            dis = sum(1 for r in allr if (R.get((jb, r["item_id"], "human")) or {}).get("vote_share") is not None
                      and (r["vote_share"] >= 0.5) != (R[(jb, r["item_id"], "human")]["vote_share"] >= 0.5))
            L.append(f"| {ja} | {jb} | {len(mine)} | {caught} ({caught / len(mine):.0%}) | {dis / len(allr):.0%} |")
    if (RAW / "overstrict_blind.jsonl").exists():
        bl = [json.loads(l) for l in open(RAW / "overstrict_blind.jsonl")]
        n3 = {i for i, n in n_by_item.items() if n == 3}
        L += ["", "## Blind check (coder does not see the judge's reasoning)", "",
              "Same coder, shown only the question, the reference and the answer. Control = correct answers all three "
              "judges accepted.", "",
              "| Group | Answers | Conclusion matches reference | Partly | No | Substantive error found |",
              "|---|---|---|---|---|---|"]
        groups = [("rejected by ≥1 judge", lambda b: b["group"] == "rejected"),
                  ("rejected by all 3 judges", lambda b: b["item_id"] in n3),
                  ("accepted by all 3 (control)", lambda b: b["group"] == "accepted")]
        for name, f in groups:
            g = [b for b in bl if f(b)]
            if not g:
                continue
            cm = collections.Counter(b.get("conclusion_matches") for b in g)
            se = sum(b.get("substantive_error") == "yes" for b in g)
            L.append(f"| {name} | {len(g)} | {cm['yes']} | {cm['partly']} | {cm['no']} | {se} ({se / len(g):.0%}) |")
    L += ["", "## Examples (coder's explanation)", ""]
    for c in list(codes.values())[:12]:
        L.append(f"- **{c['judge']} / {c['item_id']} ({c['examinee']})**: {c.get('reason')}, objection "
                 f"{c.get('objection')}. {c.get('explanation')}")
    (HERE / "results" / "overstrict_summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", action="store_true")
    ap.add_argument("--blind", action="store_true")
    ap.add_argument("--concurrency", type=int, default=8)
    a = ap.parse_args()
    if a.code:
        code(a)
    if a.blind:
        blind(a)
    analyze()


if __name__ == "__main__":
    main()
