#!/usr/bin/env python3
"""
BBEH Mini (Phase 2: judging) for our Noul-based HTTP backends (Jev, Laya, jeff). Candidates =
the 8 Tinker-pool models' own Phase 1 answers (experiments/tinker_pool/bbeh_results/answers.jsonl),
balanced correct/incorrect per question, same selection logic as run_judges.py's bbeh_items().
Gold = BBEH's own official auto-grader (fully algorithmic, not human-annotated).

Usage (repo root):
  uv run python experiments/bbeh_judge.py --backend jev --limit 40   # pilot
  uv run python experiments/bbeh_judge.py --backend jev              # full
  uv run python experiments/bbeh_judge.py --backend laya
  uv run python experiments/bbeh_judge.py --backend jeff --workers 1
"""
import argparse
import json
import random
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "tinker_pool"))
sys.path.insert(0, str(HERE / "common"))
from common import JsonlCache  # noqa: E402
from data import BBEH_SUFFIX  # noqa: E402
from run_judges import bbeh_items  # noqa: E402
from backends import Backend, get_noul  # noqa: E402

INSTR = ("Is the assistant's final answer to this reasoning question correct? Only the final "
         "answer matters, not the style of the reasoning.")
CRITERIA = {"true": "The final answer is correct.", "false": "The final answer is wrong."}


class BBEHJudge:
    def __init__(self, backend, model, clm_url, max_answer_chars=None):
        self.b = Backend(backend, model, clm_url)
        self.max_answer_chars = max_answer_chars

    def __call__(self, item):
        answer = item["answer"]
        if self.max_answer_chars and len(answer) > self.max_answer_chars:
            # Some backends (Laya, jeff) reject oversized payloads outright (413/422) -- BBEH's
            # reasoning traces run to tens of thousands of characters. Keep the END of the answer:
            # that's where "The answer is: ..." lives (see BBEH_SUFFIX), not the start.
            answer = "...[truncated]...\n" + answer[-self.max_answer_chars:]
        state = {"question": item["question"].replace(BBEH_SUFFIX, ""), "assistant_answer": answer}
        q = {"is_correct": self.b.Noul(instructions=INSTR, criteria=CRITERIA)}
        t0 = time.time()
        res, meta = self.b.ask(state, q)
        return dict(p=get_noul(res, "is_correct"), latency=time.time() - t0,
                    in_tok=meta["in_tok"], backend_model=meta["backend_model"])


class MockJudge:
    def __init__(self, seed=0):
        self.rng = random.Random(seed)

    def __call__(self, item):
        base = item["gold"] * 0.7 + (1 - item["gold"]) * 0.3
        p = min(max(base + self.rng.gauss(0, 0.2), 0.0), 1.0)
        return dict(p=p, latency=self.rng.uniform(0.05, 0.3), in_tok=len(item["question"]) // 4, backend_model="mock")


def kappa(y, yhat):
    n = len(y)
    if n == 0:
        return float("nan")
    po = sum(a == b for a, b in zip(y, yhat)) / n
    p1, q1 = sum(y) / n, sum(yhat) / n
    pe = p1 * q1 + (1 - p1) * (1 - q1)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def fmt(x, nd=3):
    return "n/a" if x != x else f"{x:.{nd}f}"


def summarize(preds, items, out):
    df = pd.DataFrame(preds)
    meta = pd.DataFrame(items)[["id", "gold", "examinee", "task"]]
    df = df.merge(meta, on="id")
    df.to_csv(out / "items.csv", index=False)
    y, p = df["gold"].tolist(), df["p"].tolist()
    yh = [int(x >= 0.5) for x in p]
    acc = sum(a == b for a, b in zip(y, yh)) / len(y)
    k = kappa(y, yh)
    L = ["# BBEH Mini (Phase 2 judging): judge results", "",
         f"n={len(df)} (candidates = the 8 Tinker models' own Phase 1 answers, balanced correct/incorrect; "
         f"gold = BBEH's own auto-grader -- fully algorithmic, not human-annotated). "
         f"Backend: {', '.join(sorted(df['backend_model'].unique()))}.", "",
         f"Accuracy: {fmt(acc)}  Cohen's κ: {fmt(k)}", ""]
    lat = df["latency"].tolist()
    tok = df["in_tok"].fillna(0).sum()
    L += ["## Cost & latency", "",
          f"- Calls: {len(df)}; input tokens: {int(tok):,}",
          f"- Latency p50 {statistics.median(lat):.3f}s, p95 {sorted(lat)[int(0.95*(len(lat)-1))]:.3f}s"]
    (out / "summary.md").write_text("\n".join(L))
    print("\n".join(L))
    (out / "metrics.json").write_text(json.dumps(dict(n=len(df), acc=acc, kappa=k), indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["jev", "clm", "laya", "jeff"], default="jev")
    ap.add_argument("--clm-url", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--per-item", type=int, default=2)
    ap.add_argument("--max-answer-chars", type=int, default=None,
                     help="truncate the candidate answer to its last N chars (keeps the end, where "
                          "BBEH's 'The answer is: ...' line lives) -- Laya/jeff reject oversized "
                          "payloads outright (413/422), unlike Jev which handles full-length fine")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--bbeh-path")
    a = ap.parse_args()

    out = Path(a.out or HERE / f"bbeh_{a.backend}_results")
    out.mkdir(parents=True, exist_ok=True)
    answers = JsonlCache(HERE / "tinker_pool" / "bbeh_results" / "answers.jsonl")
    if not answers.rows:
        sys.exit("No Phase 1 BBEH answers found at experiments/tinker_pool/bbeh_results/answers.jsonl")
    item_args = SimpleNamespace(bbeh_path=a.bbeh_path, per_item=a.per_item, seed=a.seed)
    items = bbeh_items(item_args, answers)
    if a.limit:
        random.Random(a.seed).shuffle(items)
        items = items[: a.limit]
    print(f"{len(items)} bbeh judge items", file=sys.stderr)

    judge = MockJudge(a.seed) if a.mock else BBEHJudge(a.backend, a.model, a.clm_url, a.max_answer_chars)
    cache_f = out / ("predictions_mock.jsonl" if a.mock else "predictions.jsonl")
    done = {}
    if cache_f.exists():
        for line in cache_f.read_text().splitlines():
            r = json.loads(line)
            done[r["id"]] = r
    todo = [it for it in items if it["id"] not in done]
    print(f"{len(done)} cached, {len(todo)} to run", file=sys.stderr)

    errors = 0
    with open(cache_f, "a") as fh, ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(judge, it): it for it in todo}
        for i, f in enumerate(as_completed(futs), 1):
            it = futs[f]
            try:
                r = dict(id=it["id"], **f.result())
                if r["p"] is None:
                    raise ValueError("empty/null prediction")
                done[it["id"]] = r
                fh.write(json.dumps(r) + "\n")
                fh.flush()
            except Exception as e:
                errors += 1
                print(f"[error] {it['id']}: {type(e).__name__}: {str(e)[:200]}", file=sys.stderr)
            if i % 100 == 0:
                print(f"  {i}/{len(todo)}", file=sys.stderr)
    if errors:
        print(f"{errors} calls failed; rerun the same command to retry them.", file=sys.stderr)
    ids = {it["id"] for it in items}
    preds = [r for i, r in done.items() if i in ids]
    summarize(preds, items, out)


if __name__ == "__main__":
    main()
