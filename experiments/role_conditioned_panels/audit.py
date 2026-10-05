"""Audit-only module: the match indicator Cm and the descriptive / baseline computations built on it.

Cm[i, j] = 1[Z[i, j] == Y[i]] is already defined using Y, so it must never be a predictor input.
Nothing in oracle_risk.py / construct.py / evaluate.py may use Cm; evaluate.py only imports the
baseline *functions* below, which take (Z, Y) and return verdicts.
"""
import numpy as np


def match_matrix(Z, Y):
    return (Z == Y[:, None]).astype(np.int8)


def judge_accuracy(Z, Y, idx):
    return match_matrix(Z[idx], Y[idx]).mean(0)


def e0_audit(Z, Y, judge_names, cost):
    """Ingrid's E0: per-judge accuracy, oracle accuracy, headroom, mean off-diagonal error correlation."""
    Cm = match_matrix(Z, Y)
    acc = Cm.mean(0)
    err = 1 - Cm
    ec = np.corrcoef(err.T)
    off = ec[~np.eye(len(judge_names), dtype=bool)].mean()
    return dict(accuracy=dict(zip(judge_names, acc.round(3))), best=judge_names[int(acc.argmax())],
                best_acc=acc.max(), oracle_acc=Cm.max(1).mean(), mean_err_corr=off,
                nobody_right=(Cm.sum(1) == 0).mean())


def oracle_verdicts(Z, Y, idx):
    """Upper bound: the verdict is right whenever any judge is right."""
    anyc = match_matrix(Z[idx], Y[idx]).max(1)
    return np.where(anyc == 1, Y[idx], 1 - Y[idx])


def _majority(Zs, tie_break_col):
    """Strict majority of 1s; an exact tie takes the tie_break judge's verdict (Ingrid: best global judge)."""
    share = Zs.mean(1)
    v = (share > 0.5).astype(int)
    tie = np.isclose(share, 0.5)
    v[tie] = Zs[tie, tie_break_col]
    return v


def baseline_predictions(Z, Y, sel_idx, test_idx, cost_vec, k_top=3):
    """Best single / static top-k / full jury, chosen on `sel_idx` (fit U val), scored on `test_idx`.
    Returns {strategy: (verdicts, per-item cost, judge column set)}."""
    acc = judge_accuracy(Z, Y, sel_idx)
    order = np.argsort(-acc, kind="stable")
    J = Z.shape[1]
    out = {}
    b = order[0]
    out["best_single"] = (Z[test_idx, b], np.full(len(test_idx), cost_vec[b]), [int(b)])
    top = [int(j) for j in order[:k_top]]
    out[f"static_top{k_top}"] = (_majority(Z[np.ix_(test_idx, top)], int(np.argmax(acc[top]))),
                                 np.full(len(test_idx), cost_vec[top].sum()), top)
    out["full_jury"] = (_majority(Z[test_idx], int(b)), np.full(len(test_idx), cost_vec.sum()), list(range(J)))
    return out
