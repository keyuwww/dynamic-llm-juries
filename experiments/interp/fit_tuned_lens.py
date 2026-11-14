#!/usr/bin/env python3
"""
Overnight deep-dive, step 1 (scoped): task-targeted affine "tuned lens" approximation for
gpt-oss-120b's BFF-standard cell (layer 10/36, depth 27.8% -- the genuinely early-layer winning
cell on file).

What this IS: a ridge-regression affine map h_l -> final_margin (final layer's own
logit_CORRECT - logit_INCORRECT), fit with 5-fold cross-validation so every item's "tuned"
prediction is out-of-fold (never fit on its own label). This targets the model's OWN final
decision, same spirit as Belrose et al.'s Tuned Lens objective (train toward final output, not
toward ground truth) -- the correction asks "if I de-noise this layer's representation using only
information about where the network ultimately ends up, does the resulting readout still diverge
from the final answer?"

What this is NOT: full Tuned Lens. Belrose et al. fit a full d x d affine map by SGD, minimizing KL
to the full-vocabulary final-layer distribution, trained on many millions of generic-LM-corpus
(layer, token) pairs. Here: (a) only ~200 task-specific items are available, far too few to fit an
unregularized d x d map without catastrophic overfitting, so we restrict the target to the 2-class
decision subspace (the only thing this task's forced-choice setup actually reads out) and use
ridge-regularized regression instead of SGD; (b) training data is task-specific (this benchmark's
items), not generic LM text. This is a legitimate, documented simplification for a task-targeted
question ("does the gap survive a lens trained toward final output"), not a replacement for a
general-purpose Tuned Lens.

Held-out gap recomputation: same methodology as held_out_significance.py -- kappa(tuned-lens
prediction, held-out half) - kappa(final verbalized answer, held-out half), 200 random 50/50
splits, bootstrap 95% CI, sign-permutation p-value -- but using the out-of-fold tuned prediction in
place of raw logit-lens pcn.
"""
import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def kappa(y1, y2):
    y1, y2 = np.array(y1), np.array(y2)
    n = len(y1)
    po = np.mean(y1 == y2)
    p1_1, p2_1 = np.mean(y1), np.mean(y2)
    pe = p1_1 * p2_1 + (1 - p1_1) * (1 - p2_1)
    if pe >= 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


def ridge_cv_predict(X, y, n_folds=5, alpha=50.0, seed=0):
    """Out-of-fold ridge regression predictions (closed-form, no sklearn dependency assumed)."""
    n = len(y)
    rng = np.random.RandomState(seed)
    idx = rng.permutation(n)
    folds = np.array_split(idx, n_folds)
    preds = np.zeros(n)
    Xc_mean = X.mean(axis=0)
    for i, test_idx in enumerate(folds):
        train_idx = np.concatenate([folds[j] for j in range(n_folds) if j != i])
        Xtr, ytr = X[train_idx], y[train_idx]
        mu = Xtr.mean(axis=0)
        Xtr_c = Xtr - mu
        y_mu = ytr.mean()
        ytr_c = ytr - y_mu
        d = Xtr_c.shape[1]
        A = Xtr_c.T @ Xtr_c + alpha * np.eye(d)
        b = Xtr_c.T @ ytr_c
        w = np.linalg.solve(A, b)
        Xte_c = X[test_idx] - mu
        preds[test_idx] = Xte_c @ w + y_mu
    return preds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe-jsonl", required=True, help="overnight_deepdive/probe_data/<model>_<rubric>.jsonl")
    ap.add_argument("--layer", type=int, required=True)
    ap.add_argument("--raw-gap", type=float, default=None, help="the raw-logit-lens gap on file, for comparison")
    ap.add_argument("--n-splits", type=int, default=200)
    ap.add_argument("--alpha", type=float, default=50.0)
    ap.add_argument("--label", default="")
    a = ap.parse_args()

    rows = [json.loads(l) for l in Path(a.probe_jsonl).read_text().splitlines() if l.strip()]
    print(f"{len(rows)} items loaded from {a.probe_jsonl}", flush=True)

    X = np.array([r["hidden"][a.layer] for r in rows], dtype=np.float64)
    gold = np.array([int(r["gold"]) for r in rows])
    final_pred = np.array([1 if r["pred_standard"] == "CORRECT" else 0 for r in rows])

    # final margin target: reconstruct from pred_standard as a proxy (+1/-1) since the raw logit
    # margin itself wasn't persisted by probe_jacobian.py -- document this substitution plainly.
    # (If a true margin field is present, use it instead for a sharper regression target.)
    if "final_margin" in rows[0]:
        y = np.array([r["final_margin"] for r in rows], dtype=np.float64)
        target_note = "true final logit margin"
    else:
        y = np.where(final_pred == 1, 1.0, -1.0)
        target_note = "proxy +-1 target from pred_standard (no true margin field in capture)"
    print(f"Regression target: {target_note}", flush=True)

    oof_margin = ridge_cv_predict(X, y, n_folds=5, alpha=a.alpha)
    tuned_pred = (oof_margin > 0).astype(int)

    n = len(rows)
    rng = random.Random(0)
    gaps = []
    for _ in range(a.n_splits):
        idx = list(range(n))
        rng.shuffle(idx)
        half = idx[: n // 2]
        k_tuned = kappa(tuned_pred[half], gold[half])
        k_final = kappa(final_pred[half], gold[half])
        gaps.append(k_tuned - k_final)
    gaps = np.array(gaps)
    mean_gap = float(gaps.mean())
    ci_lo, ci_hi = np.percentile(gaps, [2.5, 97.5])
    p = float(np.mean(np.sign(gaps) != np.sign(mean_gap))) if mean_gap != 0 else 1.0

    # whole-sample agreement, for sanity (not the held-out stat, just a sniff test)
    agree_tuned = float(np.mean(tuned_pred == gold))
    agree_final = float(np.mean(final_pred == gold))

    result = dict(
        label=a.label, probe_jsonl=a.probe_jsonl, layer=a.layer, n_items=n,
        method="ridge_cv_affine_margin_proxy (5-fold out-of-fold, alpha=%s)" % a.alpha,
        target_note=target_note,
        agree_tuned_full_sample=agree_tuned, agree_final_full_sample=agree_final,
        tuned_held_out_gap_mean=mean_gap, tuned_held_out_gap_ci95=[float(ci_lo), float(ci_hi)],
        tuned_held_out_gap_p=p, n_splits=a.n_splits,
        raw_logit_lens_gap_on_file=a.raw_gap,
    )
    print(json.dumps(result, indent=2))

    out = Path(a.probe_jsonl).parent.parent / f"tuned_lens_{a.label or 'result'}.json"
    out.write_text(json.dumps(result, indent=2))
    print(f"Wrote {out}", flush=True)


if __name__ == "__main__":
    main()
