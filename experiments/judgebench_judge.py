#!/usr/bin/env python3
"""
ScalerLab/JudgeBench (arXiv:2410.12784) as a pairwise judge task for our Choice-based backends
(Jev, Laya, jeff). Fully algorithmic gold labels (MMLU-Pro/LiveBench/LiveCodeBench verifiers) --
NOT human-annotated. Read results here as capability/algorithmic-agreement, not human-preference.

Usage (repo root):
  uv run python experiments/judgebench_judge.py --backend jev --limit 40   # pilot
  uv run python experiments/judgebench_judge.py --backend jev             # full (620 pairs)
  uv run python experiments/judgebench_judge.py --backend laya
  uv run python experiments/judgebench_judge.py --mock
"""
import argparse
import json
import random
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "tinker_pool"))
sys.path.insert(0, str(HERE / "common"))
from data import load_judgebench  # noqa: E402
from backends import Backend, get_choice_probs  # noqa: E402

INSTR = ("Compare the two responses to the same question. Which is better -- more correct, more "
         "complete, more rigorous? Judge substance, not style or length.")
CRITERIA = {"a": "Response A is better.", "b": "Response B is better."}


class JudgeBenchJudge:
    def __init__(self, backend, model, clm_url):
        self.b = Backend(backend, model, clm_url)

    def __call__(self, item):
        state = {"question": item["question"], "response_a": item["response_a"], "response_b": item["response_b"]}
        q = {"better": self.b.Choice(instructions=INSTR, criteria=CRITERIA)}
        t0 = time.time()
        res, meta = self.b.ask(state, q)
        probs = get_choice_probs(res, "better")
        p_a = probs.get("a", probs.get("A"))
        return dict(p_a=p_a, latency=time.time() - t0, in_tok=meta["in_tok"], backend_model=meta["backend_model"])


class MockJudge:
    def __init__(self, seed=0):
        self.rng = random.Random(seed)

    def __call__(self, item):
        base = item["gold"] * 0.7 + (1 - item["gold"]) * 0.3
        p = min(max(base + self.rng.gauss(0, 0.2), 0.0), 1.0)
        return dict(p_a=p, latency=self.rng.uniform(0.05, 0.3), in_tok=len(item["question"]) // 4, backend_model="mock")


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
    meta = pd.DataFrame(items)
    df = df.merge(meta, on="id")
    df.to_csv(out / "items.csv", index=False)
    y, p = df["gold"].tolist(), df["p_a"].tolist()
    yh = [int(x >= 0.5) for x in p]
    acc = sum(a == b for a, b in zip(y, yh)) / len(y)
    k = kappa(y, yh)
    L = ["# JudgeBench: pairwise judge results", "",
         f"n={len(df)} (fully algorithmic gold -- NOT human-annotated). "
         f"Backend: {', '.join(sorted(df['backend_model'].unique()))}.", "",
         f"Accuracy: {fmt(acc)}  Cohen's κ: {fmt(k)}", "",
         "## By split", "", "| Split | n | Accuracy |", "|---|---|---|"]
    for s, g in df.groupby("split"):
        yg, pg = g["gold"].tolist(), g["p_a"].tolist()
        yhg = [int(x >= 0.5) for x in pg]
        L.append(f"| {s} | {len(g)} | {fmt(sum(a==b for a,b in zip(yg,yhg))/len(yg))} |")
    L.append("")
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
    ap.add_argument("--mock", action="store_true")
    a = ap.parse_args()

    out = Path(a.out or HERE / f"judgebench_{a.backend}_results")
    out.mkdir(parents=True, exist_ok=True)
    items = load_judgebench()
    if a.limit:
        random.Random(a.seed).shuffle(items)
        items = items[: a.limit]
    print(f"{len(items)} judgebench pairs", file=sys.stderr)

    judge = MockJudge(a.seed) if a.mock else JudgeBenchJudge(a.backend, a.model, a.clm_url)
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
                if r["p_a"] is None:
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
