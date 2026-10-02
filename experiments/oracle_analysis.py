#!/usr/bin/env python3
"""
Oracle kappa across the whole judge pool: per item, trust whichever judge happened to get it
right (if any did); kappa of that assembled series vs. the real human/gold labels. This is the
upper bound the pool could reach if you had a perfect per-item judge-selector.

Usage (repo root): uv run python experiments/oracle_analysis.py
"""
import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent


def kappa(y, yhat):
    n = len(y)
    if n == 0:
        return float("nan")
    po = sum(a == b for a, b in zip(y, yhat)) / n
    p1, q1 = sum(y) / n, sum(yhat) / n
    pe = p1 * q1 + (1 - p1) * (1 - q1)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def bff_matrix(cond):
    """item_id -> {gold, judge: yhat (0/1)}"""
    m = {}
    backends = {"jev": "jev_bff_results", "clm": "clm_bff_results", "laya": "laya_bff_results", "jeff": "jeff_bff_results"}
    for name, folder in backends.items():
        f = REPO / "experiments/jev_bff" / folder / "items.csv"
        if not f.exists():
            continue
        df = pd.read_csv(f)
        df = df[df.cond == cond]
        for _, r in df.iterrows():
            m.setdefault(r["id"], {"gold": int(r["human"])})
            m[r["id"]][name] = int(r["p"] >= 0.5)
    jf = REPO / "experiments/tinker_pool/bff_results/judgments.jsonl"
    cond_tag = "none" if cond == "noref" else "human"
    if jf.exists():
        for line in jf.read_text().splitlines():
            r = json.loads(line)
            if r["condition"] != cond_tag:
                continue
            m.setdefault(r["item_id"], {"gold": int(r["gold"])})
            vs = r["vote_share"]
            m[r["item_id"]][r["judge"]] = int((vs or 0) > 0.5)
    return m


def safety_matrix():
    m = {}
    backends = {"jev": "safety_jev_results", "laya": "safety_laya_results",
                "jeff": "safety_jeff_results", "clm": "safety_clm_results"}
    for name, folder in backends.items():
        f = REPO / "experiments" / folder / "items.csv"
        if not f.exists():
            continue
        df = pd.read_csv(f)
        for _, r in df.iterrows():
            m.setdefault(r["id"], {"gold": int(r["human"])})
            m[r["id"]][name] = int(r["p"] >= 0.5)
    jf = REPO / "experiments/tinker_pool/safety_results/judgments.jsonl"
    if jf.exists():
        for line in jf.read_text().splitlines():
            r = json.loads(line)
            m.setdefault(r["item_id"], {"gold": int(r["gold"])})
            vs = r["vote_share"]
            m[r["item_id"]][r["judge"]] = int((vs or 0) > 0.5)
    return m


TINKER_POOL = {"qwen3.5-4b", "gpt-oss-20b", "nemotron3-nano-30b", "qwen3.5-9b",
               "qwen3.6-35b-a3b", "nemotron3-super-120b", "gpt-oss-120b", "deepseek-v3.1"}


def oracle_kappa(matrix, judge_filter=None):
    y, yhat, judges_seen = [], [], set()
    n_any_judge = 0
    for item_id, row in matrix.items():
        gold = row["gold"]
        preds = {k: v for k, v in row.items() if k != "gold" and (judge_filter is None or k in judge_filter)}
        if not preds:
            continue
        n_any_judge += 1
        judges_seen |= set(preds)
        any_correct = any(v == gold for v in preds.values())
        y.append(gold)
        yhat.append(gold if any_correct else 1 - gold)
    return dict(n=n_any_judge, judges=sorted(judges_seen), oracle_kappa=kappa(y, yhat),
                oracle_acc=sum(a == b for a, b in zip(y, yhat)) / len(y) if y else float("nan"))


def main():
    for label, cond in [("BFF noref", "noref"), ("BFF ref", "ref")]:
        m = bff_matrix(cond)
        res = oracle_kappa(m, judge_filter=TINKER_POOL)
        print(f"{label} (8-model Tinker pool only): n={res['n']}  judges={res['judges']}  oracle_kappa={res['oracle_kappa']:.3f}  oracle_acc={res['oracle_acc']:.3f}")
    m = safety_matrix()
    res = oracle_kappa(m, judge_filter=TINKER_POOL)
    print(f"Safety (8-model Tinker pool only): n={res['n']}  judges={res['judges']}  oracle_kappa={res['oracle_kappa']:.3f}  oracle_acc={res['oracle_acc']:.3f}")


if __name__ == "__main__":
    main()
