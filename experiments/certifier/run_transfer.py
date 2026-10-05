#!/usr/bin/env python3
"""
Cross-benchmark transfer: does a reliability predictor fit on BFF-Bench transfer to the Safety
subset (or vice versa), or is judge reliability task-specific? Fits the same logistic-regression
reliability model as run_certifier.py on one benchmark's full data, applies it (same feature
scaling) to the other benchmark's items, and compares the resulting top-K certifier kappa to
(a) the in-domain certifier (trained and evaluated on the same benchmark) and (b) an unweighted
majority baseline.

Usage (repo root): uv run python experiments/certifier/run_transfer.py
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
    rows_X, rows_y = [], []
    judge_to_col = {j: i for i, j in enumerate(judge_names)}
    for i in range(len(items)):
        g = gold[i]
        for j in judge_names:
            p = pmat[j][i]
            conf = abs(p - 0.5) * 2
            onehot = [0.0] * len(judge_names)
            onehot[judge_to_col[j]] = 1.0
            rows_X.append([np.log1p(tokmat[j][i]), conf] + onehot)
            rows_y.append(1.0 if int(g) == int(p >= 0.5) else 0.0)
    return np.array(rows_X), np.array(rows_y)


def vote_with_model(items, judge_names, pmat, tokmat, w, mu, sd, K):
    n_items = len(items)
    reliab = {j: np.zeros(n_items) for j in judge_names}
    for j in judge_names:
        feats = []
        for i in range(n_items):
            conf = abs(pmat[j][i] - 0.5) * 2
            onehot = [0.0] * len(judge_names)
            onehot[judge_names.index(j)] = 1.0
            feats.append([np.log1p(tokmat[j][i]), conf] + onehot)
        Xn = (np.array(feats) - mu) / sd
        reliab[j] = logistic_predict(w, Xn)
    yhat = np.zeros(n_items, dtype=int)
    for i in range(n_items):
        ranked = sorted(judge_names, key=lambda j: -reliab[j][i])[:K]
        ps = np.array([pmat[j][i] for j in ranked])
        wts = np.array([reliab[j][i] for j in ranked])
        wts = wts / wts.sum() if wts.sum() > 0 else np.ones(len(ranked)) / len(ranked)
        yhat[i] = int((wts * ps).sum() >= 0.5)
    return yhat


def fit_on(df, judge_names):
    items, gold, pmat, tokmat = wide_pool(df, judge_names)
    X, y = build_features(items, judge_names, pmat, tokmat, gold)
    mu, sd = X.mean(0), X.std(0) + 1e-9
    w = logistic_fit((X - mu) / sd, y)
    return w, mu, sd


def main():
    sources = {
        "BFF noref": bff_long("noref"),
        "BFF ref": bff_long("ref"),
        "Safety": safety_long(),
    }
    K = 3
    L = ["# Cross-benchmark transfer: does judge reliability generalize across tasks?", "",
         f"Reliability model (logistic regression, same features as the certifier) fit on one "
         f"benchmark's full data, applied as-is to another's. Top-{K} weighted vote, kappa vs. gold.", "",
         "| Trained on | Evaluated on | Kappa (transferred) | Kappa (in-domain, from run_certifier.py) |",
         "|---|---|---|---|"]
    in_domain = {}
    for name, df in sources.items():
        res_path = HERE / f"{ {'BFF noref':'bff_noref','BFF ref':'bff_ref','Safety':'safety'}[name] }_results.csv"
        if res_path.exists():
            res = pd.read_csv(res_path)
            row = res[res.strategy == f"certifier top-{K}"]
            in_domain[name] = float(row.kappa.iloc[0]) if len(row) else float("nan")
        else:
            in_domain[name] = float("nan")

    for train_name, train_df in sources.items():
        w, mu, sd = fit_on(train_df, ALL_JUDGES)
        for test_name, test_df in sources.items():
            if test_name == train_name:
                continue
            items, gold, pmat, tokmat = wide_pool(test_df, ALL_JUDGES)
            yhat = vote_with_model(items, ALL_JUDGES, pmat, tokmat, w, mu, sd, K)
            k = kappa(gold, yhat)
            L.append(f"| {train_name} | {test_name} | {k:.3f} | {in_domain[test_name]:.3f} |")

    (HERE / "transfer_summary.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
