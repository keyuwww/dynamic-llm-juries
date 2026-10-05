#!/usr/bin/env python3
"""
Certifier / per-item judge router, trained on already-collected judge verdicts only (no new
API calls). Generalizes B5's lite reliability-weighted voting from 4 pseudo-judges (Jev/CLM x
noref/ref) to the full 11-judge mixed pool: Jev, Laya, jeff (HTTP System One backends) plus the
8 Tinker-hosted open-weight models.

For each item, predict out-of-fold (5-fold CV, grouped by item so no leakage) each judge's
probability of being correct from structural features (log input tokens, the judge's own
confidence, judge identity). Take the top-K most-reliable judges per item and vote, weighted by
predicted reliability. Compare against: unweighted majority, best fixed single judge, each
individual judge, and the oracle (any judge in the pool correct).

NOTE: this 11-judge mixed pool is deliberately different from (and larger than) the dashboard's
oracle metric, which is restricted to the 8-model Tinker pool only, per an earlier explicit
decision. Do not compare these oracle numbers directly to the dashboard's.

Usage (repo root): uv run python experiments/certifier/run_certifier.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from loaders import bff_long, safety_long, wide_pool, kappa, ALL_JUDGES


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


def build_features(items, judge_names, pmat, tokmat, gold):
    """Long per-(item, judge) rows: [log1p(tok), confidence, judge one-hot...], target=agrees."""
    n_items = len(items)
    rows_X, rows_y, rows_item = [], [], []
    judge_to_col = {j: i for i, j in enumerate(judge_names)}
    for i in range(n_items):
        g = gold[i]
        for j in judge_names:
            p = pmat[j][i]
            conf = abs(p - 0.5) * 2
            onehot = [0.0] * len(judge_names)
            onehot[judge_to_col[j]] = 1.0
            rows_X.append([np.log1p(tokmat[j][i]), conf] + onehot)
            rows_y.append(1.0 if int(g) == int(p >= 0.5) else 0.0)
            rows_item.append(i)
    return np.array(rows_X), np.array(rows_y), np.array(rows_item)


def run_pool(df, judge_names, label, out_prefix):
    items, gold, pmat, tokmat = wide_pool(df, judge_names)
    n_items = len(items)
    print(f"{label}: {n_items} items common to all {len(judge_names)} judges", flush=True)

    X, y, item_idx = build_features(items, judge_names, pmat, tokmat, gold)
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Xn = (X - mu) / sd

    rng = np.random.RandomState(0)
    order = rng.permutation(n_items)
    folds = np.array_split(order, 5)
    item_fold = np.zeros(n_items, dtype=int)
    for k, idx in enumerate(folds):
        item_fold[idx] = k
    row_fold = item_fold[item_idx]

    oof = np.zeros(len(y))
    for k in range(5):
        test_mask = row_fold == k
        train_mask = ~test_mask
        w = logistic_fit(Xn[train_mask], y[train_mask])
        oof[test_mask] = logistic_predict(w, Xn[test_mask])

    reliab = {j: np.zeros(n_items) for j in judge_names}
    row = 0
    for i in range(n_items):
        for j in judge_names:
            reliab[j][i] = oof[row]
            row += 1

    def vote(topk_lists, weighted):
        yhat = np.zeros(n_items, dtype=int)
        for i in range(n_items):
            names_i = topk_lists[i]
            ps = np.array([pmat[j][i] for j in names_i])
            if weighted:
                w = np.array([reliab[j][i] for j in names_i])
                w = w / w.sum() if w.sum() > 0 else np.ones(len(names_i)) / len(names_i)
            else:
                w = np.ones(len(names_i)) / len(names_i)
            yhat[i] = int((w * ps).sum() >= 0.5)
        return yhat

    results = []
    for K in range(1, len(judge_names) + 1):
        topk = [sorted(judge_names, key=lambda j: -reliab[j][i])[:K] for i in range(n_items)]
        yhat = vote(topk, weighted=True)
        results.append(dict(K=K, strategy=f"certifier top-{K}", kappa=kappa(gold, yhat),
                             accuracy=float((yhat == gold).mean())))

    yhat_majority = vote([judge_names] * n_items, weighted=False)
    results.append(dict(K=len(judge_names), strategy="unweighted majority (all)",
                         kappa=kappa(gold, yhat_majority), accuracy=float((yhat_majority == gold).mean())))

    for j in judge_names:
        yhat_single = (pmat[j] >= 0.5).astype(int)
        results.append(dict(K=1, strategy=f"single judge: {j}", kappa=kappa(gold, yhat_single),
                             accuracy=float((yhat_single == gold).mean())))

    any_correct = np.zeros(n_items, dtype=bool)
    for j in judge_names:
        any_correct |= ((pmat[j] >= 0.5).astype(int) == gold)
    oracle_yhat = np.where(any_correct, gold, 1 - gold)
    results.append(dict(K=len(judge_names), strategy="oracle (any of 11 judges correct)",
                         kappa=kappa(gold, oracle_yhat), accuracy=float((oracle_yhat == gold).mean())))

    res = pd.DataFrame(results).sort_values("kappa", ascending=False)
    res.to_csv(HERE / f"{out_prefix}_results.csv", index=False)
    return res, n_items


def main():
    benches = [
        ("BFF noref", bff_long("noref"), "bff_noref"),
        ("BFF ref", bff_long("ref"), "bff_ref"),
        ("Safety", safety_long(), "safety"),
    ]
    L = ["# Certifier: per-item judge router (11-judge mixed pool: Jev/Laya/jeff + 8 Tinker models)", "",
         "Trained on already-collected judge verdicts only -- no new API calls. Out-of-fold "
         "(5-fold, grouped by item) logistic-regression reliability predictor over structural "
         "features (log input tokens, the judge's own confidence, judge identity); top-K most "
         "reliable judges per item vote, weighted by predicted reliability.", "",
         "**Note:** this 11-judge mixed pool is a different, larger pool than the dashboard's "
         "oracle metric, which is restricted to the 8-model Tinker pool only per an earlier "
         "explicit decision. Do not compare these oracle numbers directly to the dashboard's.", ""]
    for label, df, prefix in benches:
        res, n = run_pool(df, ALL_JUDGES, label, prefix)
        L.append(f"## {label} (n={n})\n")
        L.append("| Strategy | Cohen's kappa | Accuracy |")
        L.append("|---|---|---|")
        for _, r in res.iterrows():
            L.append(f"| {r.strategy} | {r.kappa:.3f} | {r.accuracy:.3f} |")
        L.append("")
    (HERE / "summary.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
