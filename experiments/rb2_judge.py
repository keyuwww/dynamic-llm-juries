#!/usr/bin/env python3
"""
RewardBench 2, non-Safety domains (Factuality, Focus, Math, Precise IF, Ties) as a judge task for
our Noul-based backends (Jev, Laya, jeff). Mirrors safety_judge.py's design (one Noul yes/no
question per response, scored against gold: chosen=1, rejected=0) but across the other five domains.

IMPORTANT: only RewardBench 2's Safety domain is human-annotated (per the paper's own Table 2).
These five domains use LLM-judged or algorithmic gold labels -- read results here as
capability/algorithmic-agreement, not human-preference agreement. Use safety_judge.py for the one
genuinely human-labeled domain.

Usage (repo root):
  uv run python experiments/rb2_judge.py --backend jev --domain Math --limit 40   # pilot
  uv run python experiments/rb2_judge.py --backend jev                             # all 5 domains, full
  uv run python experiments/rb2_judge.py --backend laya --domain Factuality
  uv run python experiments/rb2_judge.py --mock
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
from data import RB2_DOMAINS, load_rb2_all  # noqa: E402
from backends import Backend, get_noul  # noqa: E402

DOMAIN_HINTS = {
    "Factuality": "Focus on whether the factual claims in the response are accurate.",
    "Focus": "Focus on whether the response actually addresses what the user asked, without padding or going off-topic.",
    "Math": "Focus on whether the mathematical reasoning and final answer are correct.",
    "Precise IF": "Focus on whether the response precisely follows every explicit instruction/constraint in the request.",
    "Ties": "This category pairs two similarly-good responses; focus on whichever substantive difference actually matters.",
}
NON_SAFETY_DOMAINS = [d for d in RB2_DOMAINS if d != "Safety"]


class RB2Judge:
    def __init__(self, backend, model, clm_url):
        self.b = Backend(backend, model, clm_url)

    def __call__(self, item):
        instr = (f"You are grading an AI assistant's response in the \"{item['domain']}\" category of "
                 f"RewardBench 2. {DOMAIN_HINTS.get(item['domain'], '')} Is this a good, correct response "
                 "to the request? Judge substance, not style or length.")
        criteria = {"true": "The response is good/correct for this request.",
                    "false": "The response has a substantive flaw for this request."}
        state = {"user_request": item["prompt"], "assistant_response": item["response"]}
        q = {"is_good": self.b.Noul(instructions=instr, criteria=criteria)}
        t0 = time.time()
        res, meta = self.b.ask(state, q)
        return dict(p=get_noul(res, "is_good"), latency=time.time() - t0,
                    in_tok=meta["in_tok"], backend_model=meta["backend_model"])


class MockJudge:
    def __init__(self, seed=0):
        self.rng = random.Random(seed)

    def __call__(self, item):
        base = item["human"] * 0.7 + (1 - item["human"]) * 0.3
        p = min(max(base + self.rng.gauss(0, 0.2), 0.0), 1.0)
        return dict(p=p, latency=self.rng.uniform(0.05, 0.3), in_tok=len(item["prompt"]) // 4, backend_model="mock")


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
    y, p = df["human"].tolist(), df["p"].tolist()
    yh = [int(x >= 0.5) for x in p]
    acc = sum(a == b for a, b in zip(y, yh)) / len(y)
    k = kappa(y, yh)
    L = ["# RewardBench 2 (non-Safety domains): judge results", "",
         f"n={len(df)} (NOT human-annotated -- LLM-judged/algorithmic gold; read as capability, not "
         f"human-preference agreement). Backend: {', '.join(sorted(df['backend_model'].unique()))}.",
         "", f"Overall -- Accuracy: {fmt(acc)}  Cohen's κ: {fmt(k)}", ""]
    L += ["## By domain", "", "| Domain | n | Accuracy | Cohen's κ |", "|---|---|---|---|"]
    for d, g in df.groupby("domain"):
        yd, pd_ = g["human"].tolist(), g["p"].tolist()
        yhd = [int(x >= 0.5) for x in pd_]
        L.append(f"| {d} | {len(g)} | {fmt(sum(a==b for a,b in zip(yd,yhd))/len(yd))} | {fmt(kappa(yd, yhd))} |")
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
    ap.add_argument("--domain", choices=NON_SAFETY_DOMAINS + ["all"], default="all")
    ap.add_argument("--out", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--rb2-path")
    a = ap.parse_args()

    out = Path(a.out or HERE / f"rb2_{a.backend}_results")
    out.mkdir(parents=True, exist_ok=True)
    items = [it for it in load_rb2_all(a.rb2_path) if it["domain"] != "Safety"]
    if a.domain != "all":
        items = [it for it in items if it["domain"] == a.domain]
    if a.limit:
        random.Random(a.seed).shuffle(items)
        items = items[: a.limit]
    print(f"{len(items)} rb2 (non-safety) items", file=sys.stderr)

    judge = MockJudge(a.seed) if a.mock else RB2Judge(a.backend, a.model, a.clm_url)
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
            if i % 200 == 0:
                print(f"  {i}/{len(todo)}", file=sys.stderr)
    if errors:
        print(f"{errors} calls failed; rerun the same command to retry them.", file=sys.stderr)
    ids = {it["id"] for it in items}
    preds = [r for i, r in done.items() if i in ids]
    summarize(preds, items, out)


if __name__ == "__main__":
    main()
