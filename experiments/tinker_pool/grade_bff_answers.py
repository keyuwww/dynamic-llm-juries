#!/usr/bin/env python3
"""
Grade the pool's Phase 1 BFF-Bench answers -> each model's "did it solve this question?" label.

New answers have no expert labels, so we use Jev WITH the expert reference as the grader
(same prompt as Exp 1's 'ref' condition, which reached kappa = 0.856 vs the human labels).
Treat these as noisy labels: good enough to pick the pool and estimate headroom, but report them
as proxy labels in the paper. Optional cross-check: --second-grader <pool key> also grades every
answer with a Tinker model + reference, and the summary reports grader agreement.

Outputs in experiments/tinker_pool/bff_results/:
  grades.jsonl          cache (git-ignored)
  grades_summary.md     per-model accuracy by turn, routing headroom, grading cost

  uv run python experiments/tinker_pool/grade_bff_answers.py --mock
  uv run python experiments/tinker_pool/grade_bff_answers.py
  uv run python experiments/tinker_pool/grade_bff_answers.py --second-grader gpt-oss-120b
"""
import argparse, asyncio, random, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "common"))
sys.path.insert(0, str(HERE.parent / "jev_bff"))
from common import JsonlCache, kappa, load_env, make_chats, parse_verdict, run_jobs, select_models, fmt  # noqa: E402
from data import load_bff  # noqa: E402
from analyze import headroom  # noqa: E402

JEV_PRICE_PER_M_INPUT = 0.042

GRADER_PROMPT = """You are grading an AI assistant's answer to a finance/accounting question, using an expert reference answer as ground truth.

{conversation}

Expert reference answer for the final question:
{ref}

Is the assistant's FINAL response substantively correct? The key facts, calculations, numbers and conclusions must match the reference; minor wording or formatting differences do not matter, but a wrong number, wrong method or wrong conclusion makes it incorrect.
Explain briefly, then end with exactly one line: "VERDICT: CORRECT" or "VERDICT: INCORRECT"."""


def render_conv(conv):
    return "\n\n".join(f"[{m['role'].upper()}]\n{m['content']}" for m in conv)


def build_jobs(answers, bff, models):
    refs = {r["uid"]: r["refs"] for r in bff}
    out = []
    for r in answers.rows.values():
        if r["model"] not in models:
            continue
        rl = refs.get(r["item"], [])
        ref = rl[r["turn"] - 1] if 0 < r["turn"] <= len(rl) else None
        if ref is None:
            continue
        conv = [dict(x) for x in r["messages"]] + [{"role": "assistant", "content": r["answer"]}]
        out.append(dict(key=r["cache_key"], model=r["model"], item=r["item"], turn=r["turn"], conv=conv, ref=ref))
    return out


def grade_with_jev(jobs, cache, workers, mock, jev_model):
    from run_jev_bff import INSTR_REF, CRITERIA
    todo = [j for j in jobs if f"jev|{j['key']}" not in cache]
    if not todo:
        return
    if mock:
        rng = random.Random(0)
        call = lambda j: dict(p=rng.random(), in_tok=len(str(j["conv"])) // 4)  # noqa: E731
    else:
        load_env()
        from backends import Backend, get_noul
        b = Backend("jev", jev_model)

        def call(j):
            q = {"is_correct": b.Noul(instructions=INSTR_REF, criteria=CRITERIA)}
            res, meta = b.ask({"conversation": j["conv"], "reference_answer_for_final_question": j["ref"]}, q)
            return dict(p=get_noul(res, "is_correct"), in_tok=meta["in_tok"])
    errors = 0
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(call, j): j for j in todo}
        for i, f in enumerate(as_completed(futs), 1):
            j = futs[f]
            try:
                r = f.result()
                cache.put(dict(cache_key=f"jev|{j['key']}", grader="jev", model=j["model"], item=j["item"],
                               turn=j["turn"], p=r["p"], correct=int(r["p"] >= 0.5), in_tok=r["in_tok"]))
            except Exception as e:  # noqa: BLE001
                errors += 1
                print(f"[error] {j['key']}: {type(e).__name__}: {str(e)[:200]}")
            if i % 100 == 0:
                print(f"  jev grades: {i}/{len(todo)}", flush=True)
    if errors:
        print(f"{errors} Jev calls failed; rerun to retry.")


async def grade_with_tinker(jobs, cache, grader_key, mock, concurrency):
    chat = make_chats(select_models(grader_key), "off", mock)[grader_key]

    async def one(j):
        k = f"{grader_key}|{j['key']}"
        if k in cache:
            return
        prompt = GRADER_PROMPT.format(conversation=render_conv(j["conv"]), ref=j["ref"])
        r = await chat.chat([{"role": "user", "content": prompt}], max_tokens=1024, temperature=0.0)
        v = parse_verdict(r["outputs"][0]["text"])
        cache.put(dict(cache_key=k, grader=grader_key, model=j["model"], item=j["item"], turn=j["turn"],
                       correct=v, n_in=r["n_in"], n_out=r["n_out"]))

    await run_jobs([(lambda j=j: one(j)) for j in jobs], concurrency, f"{grader_key} grades")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="all")
    ap.add_argument("--second-grader", default=None, help="pool key, e.g. gpt-oss-120b or deepseek-v3.1")
    ap.add_argument("--jev-model", default="jev-1.13.0", help="pin the version used in Exp 1")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--concurrency", type=int, default=32)
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--bff-path")
    a = ap.parse_args()

    out = HERE / ("mock_bff_results" if a.mock else "bff_results")
    answers = JsonlCache(out / ("answers_mock.jsonl" if a.mock else "answers.jsonl"))
    if not answers.rows:
        sys.exit("No Phase 1 answers yet: run run_answers.py --bench bff first.")
    cache = JsonlCache(out / ("grades_mock.jsonl" if a.mock else "grades.jsonl"))
    models = [m["key"] for m in select_models(a.models)]
    jobs = build_jobs(answers, load_bff(a.bff_path), set(models))
    print(f"{len(jobs)} answers to grade", flush=True)
    grade_with_jev(jobs, cache, a.workers, a.mock, a.jev_model)
    if a.second_grader:
        asyncio.run(grade_with_tinker(jobs, cache, a.second_grader, a.mock, a.concurrency))

    # ---- summary
    present = sorted({r["model"] for r in answers.rows.values()} & set(models))
    L = ["# Phase 1 grades: BFF-Bench (grader = Jev + expert reference; proxy labels)", ""]
    for turn in (1, 2, None):
        matrix = {}
        for r in cache.rows.values():
            if r["grader"] != "jev" or (turn and r["turn"] != turn):
                continue
            matrix.setdefault(f"{r['item']}|{r['turn']}", {})[r["model"]] = r["correct"]
        hl, _ = headroom(matrix, present, f"Turn {turn}" if turn else "Both turns")
        L += hl
    if a.second_grader:
        pairs = []
        for r in cache.rows.values():
            if r["grader"] == a.second_grader and r["correct"] is not None:
                j = cache.get("jev|" + r["cache_key"].split("|", 1)[1])
                if j:
                    pairs.append((j["correct"], r["correct"]))
        if pairs:
            agree = sum(x == y for x, y in pairs) / len(pairs)
            L += [f"## Grader agreement: Jev vs {a.second_grader}", "",
                  f"n={len(pairs)}, raw agreement {fmt(agree)}, Cohen's kappa {fmt(kappa([p[0] for p in pairs], [p[1] for p in pairs]))}",
                  "Low agreement means the solve labels are too noisy to trust without human spot checks.", ""]
    jev_tok = sum(r.get("in_tok") or 0 for r in cache.rows.values() if r["grader"] == "jev")
    L += [f"Jev grading cost: ~${jev_tok / 1e6 * JEV_PRICE_PER_M_INPUT:.3f} ({jev_tok:,} input tokens).", ""]
    (out / "grades_summary.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
