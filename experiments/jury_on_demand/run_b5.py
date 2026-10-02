#!/usr/bin/env python3
"""
B5: Jury-on-Demand, reproduced from data we already collected (no new API calls).

Li et al. 2025: per-judge XGBoost predicts "will this judge agree with humans?" from text
features (token distributions, embeddings, structural features); top-K judges by predicted
reliability vote, weighted by that reliability.

Substitutions, documented rather than hidden:
  - No XGBoost or embeddings available offline in this environment -> a from-scratch
    (numpy-only) logistic regression reliability predictor over STRUCTURAL features only
    (no token-distribution or embedding features). This is a lite reproduction, not a
    faithful one -- treat results as a lower bound on what a real implementation could do.
  - "Judges": we only have two real judge backends (Jev, CLM), but each was run in two
    conditions (noref/ref) on the SAME items in Exp 1 -- so the jury pool is 4 pseudo-judges:
    jev_noref, jev_ref, clm_noref, clm_ref. A real deployment would use K genuinely different
    judge MODELS; here two of the four "judges" share a backend, which likely correlates their
    errors more than independent models would (weakens the vote's ensemble benefit).

Reliability target per (judge, item): did this judge's own yes/no verdict match the human
label? Predicted out-of-fold via 5-fold CV (no leakage) from: log(input tokens), turn,
annotator count, examinee model (one-hot), and the judge's own p / confidence.

Per item: take the top-K pseudo-judges by predicted reliability, vote weighted by that
reliability; sweep K over {1,2,3,4} and compare against unweighted-majority-of-4 and the
single best judge (jev_ref).

Usage (repo root):
  uv run python experiments/jury_on_demand/run_b5.py
Reads experiments/jev_bff/{jev,clm}_bff_results/items.csv
Writes experiments/jury_on_demand/summary.md and metrics.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
EXAMINEES = ["gemma-2-2b", "gpt-4o", "llama-3.3-70b", "phi-4", "qwen2.5-7b", "yi1.5-34b-16k"]


def kappa(y, yhat):
    n = len(y)
    if n == 0:
        return float("nan")
    y, yhat = np.asarray(y), np.asarray(yhat)
    po = (y == yhat).mean()
    p1, q1 = y.mean(), yhat.mean()
    pe = p1 * q1 + (1 - p1) * (1 - q1)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def auroc(y, s):
    y, s = np.asarray(y), np.asarray(s)
    pos, neg = s[y == 1], s[y == 0]
    if not len(pos) or not len(neg):
        return float("nan")
    wins = sum((p > neg).sum() + 0.5 * (p == neg).sum() for p in pos)
    return wins / (len(pos) * len(neg))


def features(df):
    X = [np.log1p(df["in_tok"].fillna(0).values), df["turn"].values.astype(float),
         df["n_annot"].values.astype(float), df["p"].values, (df["p"] - 0.5).abs().values * 2]
    for m in EXAMINEES:
        X.append((df["examinee"] == m).values.astype(float))
    X = np.stack(X, axis=1)
    mu, sd = X.mean(0), X.std(0) + 1e-9
    return (X - mu) / sd


def logistic_fit(X, y, iters=500, lr=0.3, l2=1e-2):
    n, d = X.shape
    Xb = np.hstack([np.ones((n, 1)), X])
    w = np.zeros(d + 1)
    for _ in range(iters):
        p = 1 / (1 + np.exp(-Xb @ w))
        grad = Xb.T @ (p - y) / n + l2 * np.r_[0, w[1:]]
        w -= lr * grad
    return w


def logistic_predict(w, X):
    n = X.shape[0]
    Xb = np.hstack([np.ones((n, 1)), X])
    return 1 / (1 + np.exp(-Xb @ w))


def oof_reliability(df, seed=0, folds=5):
    """5-fold CV, out-of-fold predicted P(this judge's verdict agrees with the human label)."""
    X = features(df)
    y = (df["human"] == (df["p"] >= 0.5).astype(int)).astype(float).values
    idx = np.arange(len(df))
    rng = np.random.RandomState(seed)
    rng.shuffle(idx)
    fold_id = np.array_split(idx, folds)
    oof = np.zeros(len(df))
    for k in range(folds):
        test_idx = fold_id[k]
        train_idx = np.concatenate([fold_id[j] for j in range(folds) if j != k])
        w = logistic_fit(X[train_idx], y[train_idx])
        oof[test_idx] = logistic_predict(w, X[test_idx])
    return oof, y


def load_judge(path, cond, tag):
    df = pd.read_csv(path)
    df = df[df.cond == cond].copy()
    df["judge"] = tag
    # `id` (cid-t{turn}) is unique per response -- unlike qid+turn, which six examinees share
    return df.set_index("id")


def main():
    out = HERE
    jev_path = REPO / "experiments/jev_bff/jev_bff_results/items.csv"
    clm_path = REPO / "experiments/jev_bff/clm_bff_results/items.csv"
    judges = {
        "jev_noref": load_judge(jev_path, "noref", "jev_noref"),
        "jev_ref": load_judge(jev_path, "ref", "jev_ref"),
        "clm_noref": load_judge(clm_path, "noref", "clm_noref"),
        "clm_ref": load_judge(clm_path, "ref", "clm_ref"),
    }
    common = None
    for d in judges.values():
        common = d.index if common is None else common.intersection(d.index)
    judges = {k: v.loc[common] for k, v in judges.items()}
    n = len(common)
    print(f"{n} items common to all 4 pseudo-judges", flush=True)

    reliab, y_correct = {}, {}
    for name, d in judges.items():
        oof, y = oof_reliability(d)
        reliab[name] = oof
        y_correct[name] = y
        r_auroc = auroc(y, oof)
        print(f"  {name}: reliability predictor AUROC (predicting its own correctness) = {r_auroc:.3f}", flush=True)

    human = judges["jev_noref"]["human"].values
    P = {name: judges[name]["p"].values for name in judges}
    R = {name: reliab[name] for name in judges}
    names = list(judges.keys())

    def vote(topk_names_per_item, weighted):
        yhat = []
        for i in range(n):
            names_i = topk_names_per_item[i]
            if weighted:
                w = np.array([R[nm][i] for nm in names_i])
                w = w / w.sum() if w.sum() > 0 else np.ones(len(names_i)) / len(names_i)
            else:
                w = np.ones(len(names_i)) / len(names_i)
            p = sum(wi * P[nm][i] for wi, nm in zip(w, names_i))
            yhat.append(int(p >= 0.5))
        return np.array(yhat)

    rows = []
    for K in [1, 2, 3, 4]:
        topk_per_item = []
        for i in range(n):
            ranked = sorted(names, key=lambda nm: -R[nm][i])
            topk_per_item.append(ranked[:K])
        yhat = vote(topk_per_item, weighted=True)
        rows.append(dict(K=K, strategy=f"top-{K} reliability-weighted", accuracy=(yhat == human).mean(),
                          kappa=kappa(human, yhat)))

    # baselines
    yhat_majority4 = vote([names] * n, weighted=False)
    rows.append(dict(K=4, strategy="unweighted majority (all 4)", accuracy=(yhat_majority4 == human).mean(),
                      kappa=kappa(human, yhat_majority4)))
    for nm in names:
        yhat_single = (P[nm] >= 0.5).astype(int)
        rows.append(dict(K=1, strategy=f"single judge: {nm}", accuracy=(yhat_single == human).mean(),
                          kappa=kappa(human, yhat_single)))

    res = pd.DataFrame(rows)
    res.to_csv(out / "b5_results.csv", index=False)

    L = ["# B5 Jury-on-Demand (lite reproduction): reliability-weighted top-K judge voting", "",
         f"Pool of 4 pseudo-judges (2 backends x 2 conditions) on {n} items common to all four. "
         "Reliability predicted out-of-fold (5-fold CV) by a from-scratch logistic regression over "
         "structural features (log input tokens, turn, annotator count, examinee model, the judge's "
         "own p/confidence) -- substituting for the paper's XGBoost + token-distribution/embedding "
         "features, which need infra not available offline here.", "",
         "| Strategy | Accuracy | Cohen's kappa |", "|---|---|---|"]
    for _, r in res.sort_values("kappa", ascending=False).iterrows():
        L.append(f"| {r.strategy} | {r.accuracy:.3f} | {r.kappa:.3f} |")
    L += ["", "## Per-judge reliability predictor quality",
          "(AUROC of the out-of-fold predictor for 'will THIS judge be correct on this item', from structural features alone)", "",
          "| Judge | Reliability-predictor AUROC |", "|---|---|"]
    for name in names:
        L.append(f"| {name} | {auroc(y_correct[name], reliab[name]):.3f} |")
    (out / "summary.md").write_text("\n".join(L))
    print("\n".join(L))
    (out / "metrics.json").write_text(json.dumps(dict(
        n=n, results=res.to_dict(orient="records"),
        reliability_auroc={name: auroc(y_correct[name], reliab[name]) for name in names},
    ), indent=2))


if __name__ == "__main__":
    main()
