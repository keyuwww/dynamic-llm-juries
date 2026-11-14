#!/usr/bin/env python3
"""
Overnight deep-dive, step 2: per-layer linear-probe accuracy curves + Jacobian-norm curves for the
three comparison models, from the scaled (up to 200-item) probe_jacobian captures.

5-fold cross-validated logistic regression (closed-form-free; plain gradient descent, no sklearn
dependency assumed) per layer, predicting gold correctness from the layer's hidden state.
"""
import argparse
import json
from pathlib import Path

import numpy as np


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def logreg_cv_acc(X, y, n_folds=5, l2=1.0, lr=0.1, n_iter=300, seed=0):
    n, d = X.shape
    rng = np.random.RandomState(seed)
    idx = rng.permutation(n)
    folds = np.array_split(idx, n_folds)
    correct = 0
    for i, test_idx in enumerate(folds):
        train_idx = np.concatenate([folds[j] for j in range(n_folds) if j != i])
        Xtr, ytr = X[train_idx], y[train_idx]
        mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-6
        Xtr_n = (Xtr - mu) / sd
        w = np.zeros(d)
        b = 0.0
        for _ in range(n_iter):
            z = Xtr_n @ w + b
            p = sigmoid(z)
            grad_w = Xtr_n.T @ (p - ytr) / len(ytr) + l2 * w / len(ytr)
            grad_b = np.mean(p - ytr)
            w -= lr * grad_w
            b -= lr * grad_b
        Xte_n = (X[test_idx] - mu) / sd
        pred = (sigmoid(Xte_n @ w + b) > 0.5).astype(int)
        correct += np.sum(pred == y[test_idx])
    return correct / n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe-jsonl", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--max-layers", type=int, default=None, help="cap for speed; None = all layers")
    a = ap.parse_args()

    rows = [json.loads(l) for l in Path(a.probe_jsonl).read_text().splitlines() if l.strip()]
    n_layers = len(rows[0]["hidden"])
    gold = np.array([int(r["gold"]) for r in rows])
    layers = range(n_layers) if a.max_layers is None else range(0, n_layers, max(1, n_layers // a.max_layers))

    probe_acc = {}
    jac_mean = {}
    for l in layers:
        X = np.array([r["hidden"][l] for r in rows], dtype=np.float64)
        acc = logreg_cv_acc(X, gold)
        probe_acc[l] = acc
        jnorms = [r["jacobian_norm"][l] for r in rows if r["jacobian_norm"][l] is not None]
        jac_mean[l] = float(np.mean(jnorms)) if jnorms else None
        print(f"layer {l:3d}/{n_layers}: probe_acc={acc:.3f}  jacobian_norm_mean={jac_mean[l]}", flush=True)

    out = dict(label=a.label, probe_jsonl=a.probe_jsonl, n_items=len(rows), n_layers=n_layers,
               probe_acc=probe_acc, jacobian_norm_mean=jac_mean,
               baseline_majority_class_acc=float(max(gold.mean(), 1 - gold.mean())))
    out_path = Path(a.probe_jsonl).parent.parent / f"probe_curve_{a.label or Path(a.probe_jsonl).stem}.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
