"""
Shared data loaders for the certifier/diversity/transfer/calibration experiments.
Reads only already-collected judge output (no new API calls).
"""
import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent.parent

HTTP_BFF = {"jev": "jev_bff_results", "laya": "laya_bff_results", "jeff": "jeff_bff_results"}
HTTP_SAFETY = {"jev": "safety_jev_results", "laya": "safety_laya_results", "jeff": "safety_jeff_results"}
TINKER_POOL = ["qwen3.5-4b", "qwen3.5-9b", "qwen3.6-35b-a3b", "gpt-oss-20b", "gpt-oss-120b",
               "nemotron3-nano-30b", "nemotron3-super-120b", "deepseek-v3.1"]
ALL_JUDGES = list(HTTP_BFF.keys()) + TINKER_POOL  # jev, laya, jeff + 8 tinker = 11


def _http_bff(cond):
    rows = []
    for name, folder in HTTP_BFF.items():
        f = REPO / "experiments/jev_bff" / folder / "items.csv"
        df = pd.read_csv(f)
        df = df[df.cond == cond]
        for _, r in df.iterrows():
            rows.append(dict(item_id=r["id"], judge=name, p=float(r["p"]), gold=int(r["human"]),
                              in_tok=float(r["in_tok"]), cond=cond))
    return rows


def _tinker_bff(cond):
    cond_tag = "none" if cond == "noref" else "human"
    f = REPO / "experiments/tinker_pool/bff_results/judgments.jsonl"
    rows = []
    for line in f.read_text().splitlines():
        r = json.loads(line)
        if r["condition"] != cond_tag:
            continue
        rows.append(dict(item_id=r["item_id"], judge=r["judge"], p=float(r["vote_share"] or 0.0),
                          gold=int(r["gold"]), in_tok=float(r["n_in"]), cond=cond))
    return rows


def bff_long(cond):
    """Long-format df: one row per (item_id, judge). cond in {'noref', 'ref'}."""
    return pd.DataFrame(_http_bff(cond) + _tinker_bff(cond))


def _http_safety():
    rows = []
    for name, folder in HTTP_SAFETY.items():
        f = REPO / "experiments" / folder / "items.csv"
        df = pd.read_csv(f)
        for _, r in df.iterrows():
            rows.append(dict(item_id=r["id"], judge=name, p=float(r["p"]), gold=int(r["human"]),
                              in_tok=float(r["in_tok"]), cond="safety"))
    return rows


def _tinker_safety():
    f = REPO / "experiments/tinker_pool/safety_results/judgments.jsonl"
    rows = []
    for line in f.read_text().splitlines():
        r = json.loads(line)
        rows.append(dict(item_id=r["item_id"], judge=r["judge"], p=float(r["vote_share"] or 0.0),
                          gold=int(r["gold"]), in_tok=float(r["n_in"]), cond="safety"))
    return rows


def safety_long():
    """Long-format df: one row per (item_id, judge). cond == 'safety'."""
    return pd.DataFrame(_http_safety() + _tinker_safety())


def wide_pool(df, judge_names):
    """Pivot a long df to item x judge matrices (p, in_tok), restricted to items where ALL
    judge_names are present. Returns (items, gold, pmat, tokmat) where pmat/tokmat are dicts
    judge -> np.ndarray aligned to items."""
    import numpy as np
    sub = df[df.judge.isin(judge_names)]
    wide = sub.pivot_table(index="item_id", columns="judge", values="p", aggfunc="first")
    wide = wide.dropna(subset=judge_names)
    items = wide.index.to_numpy()
    gold = sub.drop_duplicates("item_id").set_index("item_id")["gold"].loc[items].astype(int).to_numpy()
    tok_wide = sub.pivot_table(index="item_id", columns="judge", values="in_tok", aggfunc="first").loc[items]
    pmat = {j: wide[j].to_numpy() for j in judge_names}
    tokmat = {j: tok_wide[j].to_numpy() if j in tok_wide.columns else np.zeros(len(items)) for j in judge_names}
    return items, gold, pmat, tokmat


def kappa(y, yhat):
    import numpy as np
    y, yhat = np.asarray(y), np.asarray(yhat)
    n = len(y)
    if n == 0:
        return float("nan")
    po = (y == yhat).mean()
    p1, q1 = y.mean(), yhat.mean()
    pe = p1 * q1 + (1 - p1) * (1 - q1)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def auroc(y, s):
    import numpy as np
    y, s = np.asarray(y), np.asarray(s)
    pos, neg = s[y == 1], s[y == 0]
    if not len(pos) or not len(neg):
        return float("nan")
    wins = sum((p > neg).sum() + 0.5 * (p == neg).sum() for p in pos)
    return wins / (len(pos) * len(neg))
