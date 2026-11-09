"""Calibration metrics exactly as defined in the paper (Section 3, Evaluation metrics).
Kuiper: sort by score, C_k = (1/n) sum_{j<=k} (R_j - S_j) W_j, Kuiper = max_k C_k - min_k C_k (k = 0..n, C_0 = 0), weights W_j = S_j.
ECE: 10 equal-width bins of [0,1], sum_m |B_m|/n * |acc(B_m) - conf(B_m)|."""
import numpy as np
from sklearn.metrics import roc_auc_score


def kuiper(S, R, weighted=True):
    S, R = np.asarray(S, float), np.asarray(R, float); o = np.argsort(S, kind="stable"); S, R = S[o], R[o]
    W = S if weighted else np.ones_like(S)
    C = np.concatenate([[0.0], np.cumsum((R - S) * W) / len(S)])
    return float(C.max() - C.min())


def bin_stats(S, R, bins=10):
    S, R = np.asarray(S, float), np.asarray(R, float); b = np.minimum((S * bins).astype(int), bins - 1)
    return [(m, int((b == m).sum()), float(S[b == m].mean()) if (b == m).any() else np.nan, float(R[b == m].mean()) if (b == m).any() else np.nan) for m in range(bins)]


def ece(S, R, bins=10):
    n = len(S); return float(sum(c / n * abs(a - f) for _, c, f, a in bin_stats(S, R, bins) if c))


def auroc(S, R):
    return float(roc_auc_score(R, S)) if len(set(np.asarray(R))) == 2 else float("nan")


def brier(S, R):
    return float(np.mean((np.asarray(S, float) - np.asarray(R, float)) ** 2))


def accuracy_at_thresholds(S, R, thresholds):
    S, R = np.asarray(S, float), np.asarray(R, float)
    return [(t, float((S >= t).mean()), float(R[S >= t].mean()) if (S >= t).any() else float("nan")) for t in thresholds]   # (threshold, share of items kept, accuracy of kept)
