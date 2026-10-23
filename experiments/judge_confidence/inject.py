#!/usr/bin/env python3
"""
Step 2.1/2.2: inject one numeric error (or a control edit) into BFF answers all experts marked correct.

DeepSeek-V3.1 proposes exact text edits as JSON; this script applies them and checks them. Nothing is dropped
silently: every proposal is stored with its check results, and later steps use only rows with ok=True.

Variant types (docs/judge_confidence_and_error_injection_plan.md):
  V1      final stated result wrong, working left intact (the answer contradicts itself)
  V2-10   one intermediate number off by ~10%, all later numbers recomputed consistently
  V2-1    same, ~1%
  V2-x10  same, x10
  V2-lead same as V2 but only the LEADING digit of the target number changes
  C1      harmless rounding of one stated number (answer stays correct)
  C2      paraphrase of one sentence, no number changed (answer stays correct)

Raw outputs (git-ignored, kept for reuse):
  results/raw/generator_calls.jsonl   every DeepSeek call: prompt, raw output, tokens, cost
  results/raw/variants.jsonl          one row per (item, variant): original/new answer, edits, checks, ok

  python experiments/judge_confidence/inject.py --limit 30          # pilot
  python experiments/judge_confidence/inject.py --report            # pass rates + examples for hand-checking
"""
import argparse, asyncio, json, random, re

from jc_common import (RAW, JsonlCache, call_cost, load_bff_correct, make_chats, mask_numbers, numbers, run_jobs,
                       select_models, to_float)

VARIANTS = ["V1", "V2-10", "V2-1", "V2-x10", "V2-lead", "C1", "C2"]
GEN_MODEL = "deepseek-v3.1"

TASK = {
    "V1": "Change ONLY the final stated result of the answer (the number given as the conclusion / final answer to "
          "the user's last question) to a wrong value, about 10-30% off. Leave every calculation step and every "
          "intermediate number unchanged, so the conclusion no longer follows from the working shown. If the "
          "final result is stated several times in the concluding part, change each of those statements; do not "
          "touch the calculation lines.",
    "V2-10": "Pick ONE intermediate number in the working (an input value copied from the question or an early "
             "computed value; not the final result) and change it by about 10% (between 5% and 20%). Then "
             "recompute EVERY later number that depends on it -- in text, tables, code output and the conclusion "
             "-- so the answer is internally consistent but wrong. If the conclusion (e.g. which option is better) "
             "would flip, update it too.",
    "V2-1": "Same as a consistent intermediate error, but the change to the chosen intermediate number must be "
            "small: about 1% (between 0.5% and 2%). Recompute EVERY later number that depends on it so the answer "
            "is internally consistent but wrong.",
    "V2-x10": "Pick ONE intermediate number in the working (not the final result) and multiply it by 10 or divide "
              "it by 10 (a decimal-place error). Recompute EVERY later number that depends on it so the answer is "
              "internally consistent but wrong.",
    "V2-lead": "Pick ONE intermediate number in the working with at least 2 significant digits (not the final "
               "result) and change ONLY its first (leading) digit, keeping all other digits and the number of "
               "digits the same (e.g. 4,520 -> 5,520 or 0.0734 -> 0.0834). Recompute EVERY later number that "
               "depends on it so the answer is internally consistent but wrong.",
    "C1": "Round ONE stated number that has at least 2 decimal places to one fewer decimal place, in a way any "
          "grader would still accept as correct (e.g. 0.9375 -> 0.938, 12.47% -> 12.5%). Change nothing else. "
          "Do not round the inputs copied from the question.",
    "C2": "Rephrase ONE explanatory sentence that contains no numbers, keeping its meaning. Change nothing else; "
          "do not touch any number, formula, table or code.",
}

GEN_PROMPT = """You are helping build a controlled test set for AI graders. Below is a finance question and an assistant's answer that experts verified as fully correct. Make the following edit to the answer.

EDIT TO MAKE ({vtype}):
{task}

Rules:
- Return edits as exact find/replace pairs on the ANSWER text. Each "old" string must be copied exactly from the answer (same spacing, symbols and line breaks) and must occur exactly ONCE in the answer; include a few surrounding words if needed to make it unique.
- Keep each edit as short as possible. Change only what the task requires.
- Do not add any comment, marker or hint about the change inside the answer.
- If this edit is impossible for this answer (e.g. there is no suitable number), set "applicable" to false.

[QUESTION]
{question}

[ANSWER]
{answer}

Reply with ONLY a JSON object, no other text:
{{"applicable": true, "target_old": "<the number you changed first, as written>", "target_new": "<its new value>", "edits": [{{"old": "...", "new": "..."}}], "explanation": "<one sentence>"}}"""


FEEDBACK = """An automatic checker rejected these edits. Failed checks: {failed}
Meaning: "problems" = an "old" string was not found exactly once (copy it exactly, add context to make it unique); "only_numbers_changed" = you changed words, not just numbers; "propagated" = a consistent error must also change at least one later number that depends on the changed one; "target_size_ok" = the size of the change is outside the requested range; "one_rounding" = exactly one number with 2+ decimals must lose one decimal place; "target_in_edits" = target_old/target_new must appear in the edits.
Try again with the same task. Reply with ONLY the JSON object."""


def question_text(conv):
    return "\n\n".join(f"[{m['role'].upper()}]\n{m['content']}" for m in conv[:-1])


def parse_json(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def apply_edits(answer, edits):
    """Exact match first; if the 'old' string is not found exactly (typically \\r\\n or table spacing copied
    differently), match it with any run of whitespace standing for any run of whitespace. Must match once."""
    new, problems = answer, []
    for e in edits:
        old, rep = e.get("old", ""), e.get("new", "")
        if not old:
            problems.append("empty 'old'")
            continue
        c = new.count(old)
        if c == 1:
            new = new.replace(old, rep, 1)
            continue
        if c == 0:
            pat = re.compile(r"\s+".join(re.escape(w) for w in old.split()))
            ms = list(pat.finditer(new))
            if len(ms) == 1:
                new = new[:ms[0].start()] + rep + new[ms[0].end():]
                continue
            c = len(ms)
        problems.append(f"'old' occurs {c} times: {old[:60]!r}")
    return new, problems


def rel_change(a, b):
    a, b = to_float(a or ""), to_float(b or "")
    if a is None or b is None or a == 0:
        return None
    return abs(b - a) / abs(a)


def check(vtype, answer, new, prop, problems):
    """Automatic checks. Returns dict of named checks plus ok."""
    c = dict(applied=not problems and new != answer, problems=problems)
    same_frame = mask_numbers(answer) == mask_numbers(new)
    na, nb = numbers(answer), numbers(new)
    changed = [(x, y) for x, y in zip(na, nb) if x != y] if len(na) == len(nb) else None
    c["n_numbers_changed"] = len(changed) if changed is not None else None
    if vtype == "C2":
        c["numbers_unchanged"] = na == nb
        c["text_changed"] = answer != new
        c["ok"] = c["applied"] and c["numbers_unchanged"]
        return c
    c["only_numbers_changed"] = same_frame
    t_old, t_new = str(prop.get("target_old", "")), str(prop.get("target_new", ""))
    r = rel_change(t_old, t_new)
    c["target_rel_change"] = r
    if vtype == "C1":
        dec = lambda s: len(s.split(".")[1]) if "." in s else 0
        ok_round = (bool(changed) and len(changed) == 1 and (rel_change(*changed[0]) or 1) < 0.01
                    and dec(changed[0][0]) >= 2 and dec(changed[0][1]) < dec(changed[0][0]))
        c["one_rounding"] = ok_round
        c["ok"] = c["applied"] and same_frame and ok_round
        return c
    if vtype == "V1":
        size_ok = r is not None and 0.03 <= r <= 0.6
    elif vtype == "V2-10":
        size_ok = r is not None and 0.04 <= r <= 0.25
    elif vtype == "V2-1":
        size_ok = r is not None and 0.003 <= r <= 0.025
    elif vtype == "V2-x10":
        size_ok = r is not None and (abs(r - 9) < 0.5 or abs(r - 0.9) < 0.05)
    else:  # V2-lead: same digit count, only the first digit differs
        da, db = re.sub(r"\D", "", t_old), re.sub(r"\D", "", t_new)
        da, db = da.lstrip("0"), db.lstrip("0")
        size_ok = len(da) == len(db) >= 2 and da[0] != db[0] and da[1:] == db[1:]
    c["target_size_ok"] = size_ok
    c["target_in_edits"] = any(t_old in e.get("old", "") and t_new in e.get("new", "") for e in prop.get("edits", []))
    if vtype.startswith("V2"):
        # at least one changed number that is not just another copy of the target (a downstream recomputation)
        tv = to_float(t_old)
        c["propagated"] = changed is not None and any(to_float(x) != tv for x, _ in changed)
    c["ok"] = bool(c["applied"] and same_frame and size_ok and c["target_in_edits"] and c.get("propagated", True))
    return c


def run(a):
    RAW.mkdir(parents=True, exist_ok=True)
    items = load_bff_correct()
    rng = random.Random(0)
    order = items[:]
    rng.shuffle(order)  # fixed order, so the pilot's 30 are the first 30 of the full run
    if a.limit:
        order = order[: a.limit]
    calls = JsonlCache(RAW / "generator_calls.jsonl")
    var = JsonlCache(RAW / "variants.jsonl")
    chat = make_chats(select_models(GEN_MODEL))[GEN_MODEL]
    print(f"{len(items)} unanimous-correct answers; generating for {len(order)} x {len(VARIANTS)} variants", flush=True)

    async def one(it, vtype):
        ck = f"{it['id']}|{it['examinee']}|{vtype}"
        prev = var.get(ck)
        if prev and (prev["ok"] or not prev.get("applicable") or prev.get("attempt", 1) >= a.max_attempts):
            return
        answer = it["conv"][-1]["content"]
        prompt = GEN_PROMPT.format(vtype=vtype, task=TASK[vtype], question=question_text(it["conv"]), answer=answer)
        messages = [{"role": "user", "content": prompt}]
        attempt = 1
        if prev:  # retry once, telling the generator what the checker found
            attempt = prev.get("attempt", 1) + 1
            failed = {k: v for k, v in prev["checks"].items() if v is False or (k == "problems" and v)}
            messages += [{"role": "assistant", "content": json.dumps(prev["proposal"])},
                         {"role": "user", "content": FEEDBACK.format(failed=json.dumps(failed))}]
        r = await chat.chat(messages, max_tokens=4096, temperature=0.3)
        raw = r["outputs"][0]["text"]
        calls.put(dict(cache_key=f"{ck}|a{attempt}", model=GEN_MODEL, messages=messages, raw=raw, n_in=r["n_in"],
                       n_out=r["n_out"], cost=call_cost(chat.spec, r["n_in"], r["n_out"]),
                       clean=r["outputs"][0]["clean"]))
        prop = parse_json(raw) or {}
        if not prop.get("applicable", False):
            var.put(dict(cache_key=ck, item_id=it["id"], examinee=it["examinee"], vtype=vtype, applicable=False,
                         parsed=bool(prop), ok=False, original=answer, new=None, proposal=prop, attempt=attempt))
            return
        new, problems = apply_edits(answer, prop.get("edits", []))
        c = check(vtype, answer, new, prop, problems)
        var.put(dict(cache_key=ck, item_id=it["id"], examinee=it["examinee"], qid=it["qid"], turn=it["turn"],
                     vtype=vtype, applicable=True, parsed=True, original=answer, new=new, proposal=prop,
                     checks=c, ok=c["ok"], attempt=attempt))

    asyncio.run(run_jobs([lambda it=it, v=v: one(it, v) for it in order for v in VARIANTS], a.concurrency, "inject"))
    report()


def recheck():
    """Recompute apply + checks for every stored proposal (no API calls) and rewrite variants.jsonl.
    The previous file is kept as variants.jsonl.bak."""
    path = RAW / "variants.jsonl"
    rows = {}
    for l in open(path):
        r = json.loads(l)
        rows[r["cache_key"]] = r  # last write wins
    out = []
    for r in rows.values():
        if r.get("applicable") and r.get("proposal"):
            new, problems = apply_edits(r["original"], r["proposal"].get("edits", []))
            r["new"], r["checks"] = new, check(r["vtype"], r["original"], new, r["proposal"], problems)
            r["ok"] = r["checks"]["ok"]
        out.append(r)
    path.rename(path.with_suffix(".jsonl.bak"))
    with open(path, "w") as fh:
        for r in out:
            fh.write(json.dumps(r) + "\n")


def report():
    import collections
    rows = [json.loads(l) for l in open(RAW / "variants.jsonl")]
    by = collections.defaultdict(list)
    for r in rows:
        by[r["vtype"]].append(r)
    cost = sum(json.loads(l)["cost"] for l in open(RAW / "generator_calls.jsonl"))
    print(f"\nvariants: {len(rows)} rows, generator cost ${cost:.2f}")
    print(f"{'type':8} {'n':>4} {'applicable':>10} {'ok':>5}  failing checks")
    for v in VARIANTS:
        rs = by.get(v, [])
        fails = collections.Counter()
        for r in rs:
            if r.get("applicable") and not r["ok"]:
                for k, val in r["checks"].items():
                    if val is False or (k == "problems" and val):
                        fails[k] += 1
        print(f"{v:8} {len(rs):4d} {sum(r.get('applicable', False) for r in rs):10d} {sum(r['ok'] for r in rs):5d}  "
              f"{dict(fails)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--max-attempts", type=int, default=2)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--recheck", action="store_true", help="re-apply stored proposals with the current checks")
    a = ap.parse_args()
    if a.recheck:
        recheck()
        report()
    else:
        report() if a.report else run(a)


if __name__ == "__main__":
    main()
