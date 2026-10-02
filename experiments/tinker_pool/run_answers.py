#!/usr/bin/env python3
"""
Phase 1 (ANSWER): every pool model answers every question itself.

Why: (1) gives each model's "can it solve this?" label, the certificate idea from No Free Labels;
(2) on benchmarks without candidate responses (BBEH Mini) these answers ARE the candidates for Phase 2.

  --bench bff   BFF-Bench, two turns, No Free Labels protocol: turn 2 is asked with the model's OWN
                turn-1 answer in context. Not graded here -> run grade_bff_answers.py next (Jev + expert ref).
  --bench bbeh  BBEH Mini, graded automatically with the official BBEH matcher.

Outputs in experiments/tinker_pool/<bench>_results/:
  answers.jsonl   raw cache (git-ignored), one row per (model, item, turn); reruns resume
  answers_summary.md   tokens, cost, truncation rate (+ accuracy / headroom for bbeh)

Examples:
  uv run python experiments/tinker_pool/run_answers.py --bench bff --mock --limit 5     # offline dry run
  uv run python experiments/tinker_pool/run_answers.py --bench bff --limit 10          # ~$0.10 pilot
  uv run python experiments/tinker_pool/run_answers.py --bench bff                     # all 80 x 2 turns
  uv run python experiments/tinker_pool/run_answers.py --bench bbeh --models routing   # 460 x 6 models
"""
import argparse, asyncio, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import JsonlCache, make_chats, run_jobs, select_models, call_cost, POOL_BY_KEY  # noqa: E402
from data import BBEH_SUFFIX, bbeh_correct, load_bbeh_mini, load_bff  # noqa: E402
from analyze import cost_table, headroom  # noqa: E402

HERE = Path(__file__).resolve().parent


def out_dir(bench, mock=False):
    d = HERE / (f"mock_{bench}_results" if mock else f"{bench}_results")
    d.mkdir(parents=True, exist_ok=True)
    return d


async def answer_bff(chat, row, cache, a):
    m = chat.spec["key"]
    k1, k2 = f"{m}|{row['uid']}|1", f"{m}|{row['uid']}|2"
    msgs = [{"role": "user", "content": row["turns"][0]}]
    if k1 not in cache:
        r = await chat.chat(msgs, max_tokens=a.max_tokens, temperature=a.temperature, n=a.samples)
        cache.put(dict(cache_key=k1, model=m, item=row["uid"], turn=1, messages=msgs,
                       answer=r["outputs"][0]["text"], outputs=r["outputs"], n_in=r["n_in"], n_out=r["n_out"],
                       renderer=r["renderer"], temperature=a.temperature))
    a1 = cache.get(k1)["answer"]
    if len(row["turns"]) > 1 and k2 not in cache:
        msgs2 = msgs + [{"role": "assistant", "content": a1}, {"role": "user", "content": row["turns"][1]}]
        r = await chat.chat(msgs2, max_tokens=a.max_tokens, temperature=a.temperature, n=a.samples)
        cache.put(dict(cache_key=k2, model=m, item=row["uid"], turn=2, messages=msgs2,
                       answer=r["outputs"][0]["text"], outputs=r["outputs"], n_in=r["n_in"], n_out=r["n_out"],
                       renderer=r["renderer"], temperature=a.temperature))


async def answer_bbeh(chat, ex, cache, a):
    m = chat.spec["key"]
    k = f"{m}|{ex['id']}|1"
    if k in cache:
        return
    msgs = [{"role": "user", "content": ex["input"] + BBEH_SUFFIX}]
    r = await chat.chat(msgs, max_tokens=a.max_tokens, temperature=a.temperature, n=a.samples)
    corr = [int(bbeh_correct(o["text"], ex["target"])) for o in r["outputs"]]
    cache.put(dict(cache_key=k, model=m, item=ex["id"], task=ex["task"], turn=1, messages=msgs,
                   answer=r["outputs"][0]["text"], outputs=r["outputs"], correct=corr[0], correct_all=corr,
                   target=ex["target"], n_in=r["n_in"], n_out=r["n_out"], renderer=r["renderer"],
                   temperature=a.temperature))


def summarize(bench, cache, models, out):
    rows = [r for r in cache.rows.values() if r["model"] in {m["key"] for m in models}]
    L = [f"# Phase 1 answers: {bench}", "",
         f"Rows: {len(rows)} | models: {', '.join(m['key'] for m in models)}", ""]
    cl, _ = cost_table(rows)
    L += cl
    trunc = {}
    for r in rows:
        trunc.setdefault(r["model"], []).append(0 if all(o.get("clean", True) for o in r["outputs"]) else 1)
    L += ["## Truncated / malformed outputs (hit max tokens or no clean stop)", "", "| Model | Share |", "|---|---|"]
    for mk, v in sorted(trunc.items()):
        L.append(f"| {mk} | {sum(v) / len(v):.3f} |")
    L.append("")
    if bench == "bbeh":
        matrix = {}
        for r in rows:
            matrix.setdefault(r["item"], {})[r["model"]] = r["correct"]
        hl, _ = headroom(matrix, [m["key"] for m in models], "Accuracy and routing headroom (auto-graded)")
        L += hl
        # per-task view: the 'which judge per task type' question
        by_task = {}
        for r in rows:
            by_task.setdefault(r["task"], {}).setdefault(r["model"], []).append(r["correct"])
        keys = [m["key"] for m in models]
        L += ["## Accuracy by BBEH task", "", "| Task | " + " | ".join(keys) + " |",
              "|---|" + "---|" * len(keys)]
        for t, d in sorted(by_task.items()):
            L.append(f"| {t} | " + " | ".join(
                f"{sum(d[k]) / len(d[k]):.2f}" if d.get(k) else "–" for k in keys) + " |")
        L.append("")
    else:
        L += ["BFF answers are not graded here: run `grade_bff_answers.py` next.", ""]
    (out / "answers_summary.md").write_text("\n".join(L))
    print("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", choices=["bff", "bbeh"], required=True)
    ap.add_argument("--models", default="all", help="all | routing | strong | comma-separated keys")
    ap.add_argument("--limit", type=int, default=None, help="first N items (pilot)")
    ap.add_argument("--temperature", type=float, default=0.7, help="No Free Labels used 0.7")
    ap.add_argument("--max-tokens", type=int, default=None, help="default 2048 (bff), 4096 (bbeh)")
    ap.add_argument("--samples", type=int, default=1, help="samples per prompt (one request; prefill paid once)")
    ap.add_argument("--thinking", choices=["off", "on"], default="off",
                    help="off: no-thinking renderers where the family has one (GPT-OSS always reasons)")
    ap.add_argument("--concurrency", type=int, default=32)
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--bff-path"), ap.add_argument("--bbeh-path")
    a = ap.parse_args()
    a.max_tokens = a.max_tokens or (2048 if a.bench == "bff" else 4096)

    models = select_models(a.models)
    out = out_dir(a.bench, a.mock)
    cache = JsonlCache(out / ("answers_mock.jsonl" if a.mock else "answers.jsonl"))
    data = load_bff(a.bff_path) if a.bench == "bff" else load_bbeh_mini(a.bbeh_path)
    if a.limit:
        data = data[: a.limit]
    chats = make_chats(models, a.thinking, a.mock)
    fn = answer_bff if a.bench == "bff" else answer_bbeh
    jobs = [(lambda c=c, x=x: fn(c, x, cache, a)) for c in chats.values() for x in data]
    print(f"{len(data)} items x {len(models)} models = {len(jobs)} jobs "
          f"({sum(1 for r in cache.rows.values() if r['model'] in chats)} rows already cached)", flush=True)
    for k, c in chats.items():
        print(f"  {k}: renderer={c.renderer_name}", flush=True)
    asyncio.run(run_jobs(jobs, a.concurrency, "answers"))
    summarize(a.bench, cache, models, out)


if __name__ == "__main__":
    main()
