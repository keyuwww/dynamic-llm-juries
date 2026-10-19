#!/usr/bin/env python3
"""
What makes an item hard to judge, and which judges are better at what, across benchmarks.

For every benchmark (condition without a reference, the 8 Tinker judges):

  hardness   item difficulty = share of the 8 judges that disagree with the gold label. Univariate breakdowns
             (gold direction, split human votes, aspect levels, category, length) and one multivariable
             linear model with standardised predictors; 95% CIs resample whole groups (conversation / prompt).
  judges     relative agreement = a judge's agreement minus the mean of all judges on the same item (item
             difficulty cancels). Per judge: mean relative agreement by feature level; per judge type
             (reasoning gpt-oss vs thinking-off judges; large vs small): the gap regressed on features.
  leniency   per judge: false-positive rate (accepts bad / prefers the worse) vs false-negative rate.
  answerers  for benchmarks where the gold label is the answer model's own correctness (BFF, (C)MT-Bench,
             BBEH): relative correctness of each answer model by aspect level and category.

  uv run python experiments/cross_benchmark/xb_factors.py --work <work folder>
Writes results/factors.json.
"""
import argparse, json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ASPECTS = ["knowledge", "reasoning", "constraints", "open_endedness", "context_load", "risk"]
TINKER = ["gpt-oss-120b", "gpt-oss-20b", "deepseek-v3.1", "qwen3.6-35b-a3b", "qwen3.5-9b", "qwen3.5-4b",
          "nemotron3-super-120b", "nemotron3-nano-30b"]
REASONING = {"gpt-oss-120b", "gpt-oss-20b"}           # always reason; the rest run with thinking off
LARGE = {"gpt-oss-120b", "deepseek-v3.1", "nemotron3-super-120b", "qwen3.6-35b-a3b"}
FAMILY = {"gpt-oss-120b": "gpt-oss", "gpt-oss-20b": "gpt-oss", "deepseek-v3.1": "deepseek", "qwen3.6-35b-a3b": "qwen",
          "qwen3.5-9b": "qwen", "qwen3.5-4b": "qwen", "nemotron3-super-120b": "nemotron", "nemotron3-nano-30b": "nemotron"}
BENCHES = ["bff", "mtb", "bffpair", "safety", "bbeh", "judgebench", "rb2", "alpacafarm", "mtbhuman"]


def item_table(d):
    """One row per item with the pool's verdicts, difficulty and features."""
    t = d[(d.condition == "none") & d.judge.isin(TINKER)]
    cov = t.groupby("judge").key.nunique()
    pool = [j for j in TINKER if j in cov and cov[j] >= 0.95 * cov.median()]
    t = t[t.judge.isin(pool)]
    A = t.pivot_table(index="key", columns="judge", values="agree")[pool].dropna()
    V = t.pivot_table(index="key", columns="judge", values="verdict")[pool].loc[A.index]
    info = t.drop_duplicates("key").set_index("key").loc[A.index]
    it = pd.DataFrame(index=A.index)
    for c in ["group", "category", "gold", "fmt", "examinee", "question_key", "question", "len_a", "len_b", "votes",
              "order"] + [a for a in ASPECTS if a in info]:
        if c in info:
            it[c] = info[c]
    for a in ASPECTS:  # a few questions have no aspect codes (unparsed annotation, BFF question 18)
        if a in it:
            it[a] = it[a].astype(float).fillna(it[a].median())
    it["wrong"] = 1 - A.mean(1)
    it["all_right"] = (A.min(1) == 1).astype(int)
    it["most_wrong"] = (A.mean(1) <= 0.5).astype(int)
    if it.fmt.iat[0] == "pair":
        la, lb = it.len_a.astype(float), it.len_b.astype(float)
        it["log_len"] = np.log1p((la + lb) / 2)
        it["len_gap"] = np.abs(np.log((la + 1) / (lb + 1)))
        it["better_is_longer"] = (((la > lb) & (it.gold == 1)) | ((lb > la) & (it.gold == 0))).astype(int)
    else:
        it["log_len"] = np.log1p(it.len_a.astype(float))
    if it["votes"].notna().any():
        def split(v):
            if not isinstance(v, (list, np.ndarray)) or len(v) == 0:
                return np.nan
            s = [x for x in v if x not in ("tie", "not sure")]
            return float(len(set(s)) > 1 or len(s) < len(v))
        it["split_votes"] = it["votes"].apply(split)
    return it, A, V, pool


def group_boot(fn, groups, n=500, seed=0):
    rng = np.random.default_rng(seed)
    ug = np.unique(groups)
    idx = {g: np.where(groups == g)[0] for g in ug}
    out = []
    for _ in range(n):
        s = np.concatenate([idx[g] for g in rng.choice(ug, len(ug))])
        try:
            out.append(fn(s))
        except Exception:
            continue
    return np.array(out)


def ols(X, y):
    X1 = np.c_[np.ones(len(X)), X]
    beta, *_ = np.linalg.lstsq(X1, y, rcond=None)
    return beta[1:]


def hardness(it):
    """Univariate tables + a standardised multivariable model of item difficulty."""
    out = dict(n=len(it), mean_wrong=float(it.wrong.mean()), all_right=float(it.all_right.mean()),
               most_wrong=float(it.most_wrong.mean()))
    uni = {}
    if it.fmt.iat[0] == "single":
        uni["gold"] = {("good answer" if k == 1 else "bad answer"): dict(n=int(len(g)), wrong=float(g.wrong.mean()))
                       for k, g in it.groupby("gold")}
    else:
        uni["better_is_longer"] = {("better one is longer" if k == 1 else "better one is shorter"): dict(n=int(len(g)), wrong=float(g.wrong.mean()))
                                   for k, g in it.groupby("better_is_longer")}
    if "split_votes" in it and it.split_votes.notna().any():
        uni["split_votes"] = {("humans split" if k == 1 else "humans unanimous"): dict(n=int(len(g)), wrong=float(g.wrong.mean()))
                              for k, g in it.groupby("split_votes")}
    for a in ASPECTS:
        if a in it and it[a].notna().any():
            uni[a] = {int(k): dict(n=int(len(g)), wrong=float(g.wrong.mean())) for k, g in it.groupby(it[a].astype(int))}
    q = pd.qcut(it.log_len.rank(method="first"), 3, labels=["short", "medium", "long"])
    uni["length"] = {str(k): dict(n=int(len(g)), wrong=float(g.wrong.mean())) for k, g in it.groupby(q, observed=True)}
    cats = it.groupby("category").wrong.agg(["mean", "size"]).sort_values("mean", ascending=False)
    uni["category"] = {str(k): dict(n=int(r["size"]), wrong=float(r["mean"])) for k, r in cats.iterrows() if r["size"] >= 10}
    out["univariate"] = uni

    # multivariable model
    feats = [a for a in ASPECTS if a in it and it[a].notna().all() and it[a].std() > 0] + ["log_len"]
    if it.fmt.iat[0] == "single":
        it = it.assign(bad_answer=1 - it.gold.astype(int))
        feats.append("bad_answer")
    else:
        it = it.assign(shorter_is_better=1 - it.better_is_longer)
        feats += ["shorter_is_better", "len_gap"]
    if "split_votes" in it and it.split_votes.notna().all() and it.split_votes.std() > 0:
        feats.append("split_votes")
    X = it[feats].astype(float).values
    sd = X.std(0)
    keep = sd > 0
    X, feats = (X[:, keep] - X[:, keep].mean(0)) / sd[keep], [f for f, k in zip(feats, keep) if k]
    y = it.wrong.values
    beta = ols(X, y)
    bs = group_boot(lambda s: ols(X[s], y[s]), it.group.astype(str).values)
    out["model"] = [dict(feature=f, beta=float(b), ci=[float(np.percentile(bs[:, i], 2.5)), float(np.percentile(bs[:, i], 97.5))])
                    for i, (f, b) in enumerate(zip(feats, beta))]
    return out


def judge_strengths(it, A, V, pool):
    """Relative agreement by feature, per judge and per judge type."""
    rel = A.sub(A.mean(1), axis=0)
    res = {}
    # leniency
    single = it.fmt.iat[0] == "single"
    len_ = {}
    for j in pool:
        g = it.gold.astype(int)
        v = V[j]
        len_[j] = dict(acc=float(A[j].mean()),
                       fpr=float(((v == 1) & (g == 0)).sum() / max((g == 0).sum(), 1)),
                       fnr=float(((v == 0) & (g == 1)).sum() / max((g == 1).sum(), 1)),
                       positive=float(v.mean()))
    res["leniency"] = len_
    # per judge, mean relative agreement by feature level
    tables = {}
    feats = [a for a in ASPECTS if a in it and it[a].notna().any()]
    for f in feats + (["gold"] if single else ["better_is_longer"]) + (["split_votes"] if "split_votes" in it else []):
        lv = it[f]
        if f in ASPECTS:
            lv = lv.astype(int).clip(upper=3)
        rows = {}
        for k in sorted(lv.dropna().unique()):
            m = (lv == k).values
            if m.sum() < 15:
                continue
            rows[str(int(k))] = dict(n=int(m.sum()), rel={j: float(rel[j].values[m].mean()) for j in pool},
                                     acc={j: float(A[j].values[m].mean()) for j in pool})
        if len(rows) >= 2:
            tables[f] = rows
    # category (top categories)
    cats = it.category.value_counts()
    cats = cats[cats >= 15].index[:12]
    tables["category"] = {str(c): dict(n=int((it.category == c).sum()),
                                       rel={j: float(rel[j][it.category == c].mean()) for j in pool},
                                       acc={j: float(A[j][it.category == c].mean()) for j in pool}) for c in cats}
    res["tables"] = tables
    # judge-type gaps regressed on features
    gaps = {}
    groups = it.group.astype(str).values
    mfeats = [a for a in ASPECTS if a in it and it[a].notna().all() and it[a].std() > 0] + ["log_len"]
    if single:
        it = it.assign(bad_answer=1 - it.gold.astype(int))
        mfeats.append("bad_answer")
    else:
        it = it.assign(shorter_is_better=1 - it.better_is_longer)
        mfeats.append("shorter_is_better")
    X = it[mfeats].astype(float).values
    X = (X - X.mean(0)) / (X.std(0) + 1e-9)
    for name, a_set, b_set in [("reasoning_vs_thinking_off", REASONING, set(pool) - REASONING),
                               ("large_vs_small", LARGE, set(pool) - LARGE)]:
        a_set, b_set = [j for j in pool if j in a_set], [j for j in pool if j in b_set]
        if not a_set or not b_set:
            continue
        gap = (A[a_set].mean(1) - A[b_set].mean(1)).values
        beta = ols(X, gap)
        bs = group_boot(lambda s: ols(X[s], gap[s]), groups)
        gaps[name] = dict(a=a_set, b=b_set, mean=float(gap.mean()),
                          ci_mean=[float(np.percentile(group_boot(lambda s: gap[s].mean(), groups), q)) for q in (2.5, 97.5)],
                          model=[dict(feature=f, beta=float(b), ci=[float(np.percentile(bs[:, i], 2.5)), float(np.percentile(bs[:, i], 97.5))])
                                 for i, (f, b) in enumerate(zip(mfeats, beta))])
    res["type_gaps"] = gaps
    return res


def answerers(items):
    it = items[items.gold.notna()].copy()
    it["gold"] = it.gold.astype(int)
    W = it.pivot_table(index="question_key", columns="examinee", values="gold")
    W = W[[m for m in W.columns if W[m].notna().sum() >= 0.95 * W.notna().sum().max()]].dropna()
    if W.shape[1] < 3:
        return None
    rel = W.sub(W.mean(1), axis=0)
    q = it.drop_duplicates("question_key").set_index("question_key").loc[W.index].copy()
    for a in ASPECTS:  # a few questions have no aspect codes (unparsed annotation)
        if a in q:
            q[a] = q[a].astype(float).fillna(q[a].median())
    out = dict(acc={m: float(W[m].mean()) for m in W.columns}, tables={})
    for f in [a for a in ASPECTS if a in q and q[a].notna().any()] + ["category"]:
        lv = q[f].astype(int).clip(upper=3) if f in ASPECTS else q[f]
        rows = {}
        for k in (sorted(lv.dropna().unique()) if f in ASPECTS else lv.value_counts().index[:10]):
            m = (lv == k).values
            if m.sum() < 8:
                continue
            rows[str(int(k)) if f in ASPECTS else str(k)] = dict(n=int(m.sum()), acc={c: float(W[c].values[m].mean()) for c in W.columns},
                                                                 rel={c: float(rel[c].values[m].mean()) for c in W.columns})
        if len(rows) >= 2:
            out["tables"][f] = rows
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    a = ap.parse_args()
    base = Path(a.work) / "cross_benchmark"
    out = {}
    for b in BENCHES:
        p = base / "data" / f"{b}_decisions.pkl"
        if not p.exists():
            continue
        d = pd.read_pickle(p)
        asp = base / "data" / f"{'bff' if b == 'bffpair' else b}_aspects.pkl"
        if "knowledge" not in d and asp.exists():
            d = d.merge(pd.read_pickle(asp), on="question_key", how="left")
        it, A, V, pool = item_table(d)
        items = pd.read_pickle(base / "data" / f"{b}_items.pkl")
        if asp.exists():
            items = items.merge(pd.read_pickle(asp), on="question_key", how="left")
        r = dict(pool=pool, hardness=hardness(it), judges=judge_strengths(it, A, V, pool),
                 answerers=answerers(items) if b in ("bff", "mtb", "bbeh") else None)
        out[b] = r
        it.drop(columns=["question", "votes"], errors="ignore").to_pickle(base / "data" / f"{b}_itemhard.pkl")
        h = r["hardness"]
        print(f"{b}: n={h['n']} mean wrong {h['mean_wrong']:.3f}; model:",
              ", ".join(f"{m['feature']} {m['beta']:+.3f}{'*' if m['ci'][0] > 0 or m['ci'][1] < 0 else ''}" for m in h["model"]))
        g = r["judges"]["type_gaps"].get("reasoning_vs_thinking_off")
        if g:
            print(f"   reasoning − off: {g['mean']:+.3f} {g['ci_mean']}; ",
                  ", ".join(f"{m['feature']} {m['beta']:+.3f}{'*' if m['ci'][0] > 0 or m['ci'][1] < 0 else ''}" for m in g["model"]))
    (base / "results" / "factors.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
