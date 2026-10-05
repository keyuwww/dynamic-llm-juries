"""Exp 1: brute-force best subset (all 255 panels) vs top-3.   Exp 2: logistic regression over the 8 raw verdicts.
Same 20 question-grouped fit/val/test splits as run.py. Everything uses (Z, Y) only; no match matrix."""
import argparse
import itertools
import os
import sys
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit import baseline_predictions, oracle_verdicts                 # noqa: E402
from data import load_judgments                                          # noqa: E402
from evaluate import _metrics, pooled_bootstrap                          # noqa: E402
from majority import mv_verdict                                          # noqa: E402
from splits import make_3way_splits                                      # noqa: E402



def subset_acc(Z, Y, rows, cols, fit_acc):
    return float((mv_verdict(Z[rows], cols, max(cols, key=lambda c: fit_acc[c])) == Y[rows]).mean())


def run(d, a):
    Z, Y, names = d.Z, d.Y, d.judge_names
    J = Z.shape[1]
    SUBSETS = [list(c) for r in range(1, J + 1) for c in itertools.combinations(range(J), r)]   # every non-empty panel
    cost = np.array([d.cost[j] for j in names])
    splits = make_3way_splits(d.groups, a.seed, a.n_repeats)
    rec, pooled, chosen = [], {}, {k: [] for k in ("subset_val", "subset_fitval", "subset_fitval_odd")}
    coefs = []
    full_fit_acc = (Z == Y[:, None]).mean(0)
    for r, (fit, val, test) in enumerate(splits):
        sel = np.concatenate([fit, val]); ytest = Y[test]
        fit_acc = (Z[fit] == Y[fit][:, None]).mean(0); sel_acc = (Z[sel] == Y[sel][:, None]).mean(0)
        strat = {}
        for name, (v, c, cols) in baseline_predictions(Z, Y, sel, test, cost).items():
            strat[name] = (v, c)
            if name == "static_top3":
                top3 = cols
        strat["oracle"] = (oracle_verdicts(Z, Y, test), np.full(len(test), np.nan))

        # ---- Exp 1: every subset, majority vote, chosen on validation / fit U val
        def pick(rows, acc_vec, odd_only=False):
            best = None
            for cols in SUBSETS:
                if odd_only and len(cols) % 2 == 0:
                    continue
                acc = subset_acc(Z, Y, rows, cols, acc_vec)
                key = (acc, -len(cols), -cost[cols].sum())      # ties: fewer judges, then cheaper
                if best is None or key > best[0]:
                    best = (key, cols)
            return best[1]
        for tag, rows, av, odd in [("subset_val", val, fit_acc, False), ("subset_fitval", sel, sel_acc, False),
                                   ("subset_fitval_odd", sel, sel_acc, True)]:
            cols = pick(rows, av, odd)
            chosen[tag].append(tuple(sorted(cols)))
            strat[tag] = (mv_verdict(Z[test], cols, max(cols, key=lambda c: sel_acc[c])), np.full(len(test), cost[cols].sum()))
        # selection ceiling (optimistic): best subset picked ON the test rows themselves
        best_t = max(SUBSETS, key=lambda cols: subset_acc(Z, Y, test, cols, sel_acc))
        strat["subset_test_oracle(optimistic)"] = (mv_verdict(Z[test], best_t, max(best_t, key=lambda c: sel_acc[c])),
                                                    np.full(len(test), cost[best_t].sum()))

        # ---- Exp 2: logistic regression over the raw verdicts (intercept + one weight per judge)
        def fit_lr(cols, penalty):
            best = None
            for C in a.c_grid:
                m = LogisticRegression(C=C, penalty=penalty, solver="liblinear" if penalty == "l1" else "lbfgs", max_iter=2000)
                m.fit(Z[np.ix_(fit, cols)], Y[fit])
                ll = log_loss(Y[val], m.predict_proba(Z[np.ix_(val, cols)])[:, 1], labels=[0, 1])
                if best is None or ll < best[0]:
                    best = (ll, C)
            m = LogisticRegression(C=best[1], penalty=penalty, solver="liblinear" if penalty == "l1" else "lbfgs", max_iter=2000)
            return m.fit(Z[np.ix_(sel, cols)], Y[sel]), best[1]
        allc = list(range(J))
        m, C = fit_lr(allc, "l2")
        strat["lr_all8_l2"] = ((m.predict_proba(Z[test][:, allc])[:, 1] >= 0.5).astype(int), np.full(len(test), cost.sum()))
        coefs.append(dict(repeat=r, C=C, **dict(zip(names, m.coef_[0])), intercept=m.intercept_[0]))
        m1, _ = fit_lr(allc, "l1")
        used = [c for c in allc if abs(m1.coef_[0][c]) > 1e-8]
        strat["lr_all8_l1"] = ((m1.predict_proba(Z[test][:, allc])[:, 1] >= 0.5).astype(int), np.full(len(test), cost[used].sum()))
        m3, _ = fit_lr(top3, "l2")
        strat["lr_top3_l2"] = ((m3.predict_proba(Z[test][:, top3])[:, 1] >= 0.5).astype(int), np.full(len(test), cost[top3].sum()))
        # calibrated vote count (1 parameter) for reference
        cnt = Z.sum(1); k = max(range(J + 2), key=lambda k: ((cnt[sel] >= k).astype(int) == Y[sel]).mean())
        strat["tuned_vote_all8"] = ((cnt[test] >= k).astype(int), np.full(len(test), cost.sum()))

        for name, (v, c) in strat.items():
            rec.append(dict(repeat=r, strategy=name, **_metrics(v, ytest, c)))
            pooled.setdefault(name, []).append((test, (v == ytest).astype(int)))

    res = pd.DataFrame(rec)
    T = res.groupby("strategy").agg(acc=("acc", "mean"), acc_sd=("acc", "std"), kappa=("kappa", "mean"), cost=("cost", "mean"))
    order = ["best_single", "static_top3", "full_jury", "tuned_vote_all8", "subset_val", "subset_fitval", "subset_fitval_odd",
             "subset_test_oracle(optimistic)", "lr_top3_l2", "lr_all8_l2", "lr_all8_l1", "oracle"]
    print("\n=== %s: final-test, mean over %d repeats ===" % (a.bench, a.n_repeats)); print(T.reindex(order).round(4).to_string())

    print("\nPaired question-bootstrap on pooled test predictions (strategy minus static top-3):")
    for s in order:
        if s in ("static_top3", "oracle", "subset_test_oracle(optimistic)"):
            continue
        b = pooled_bootstrap(pooled, d.groups, s, "static_top3")
        print(f"  {s:20s} {b['diff']:+.4f}  95% CI [{b['lo']:+.4f}, {b['hi']:+.4f}]  {'(excludes 0)' if b['lo'] > 0 or b['hi'] < 0 else ''}")

    print("\nSubsets chosen by brute force (share of repeats):")
    for tag, lst in chosen.items():
        cnt_ = Counter(lst).most_common(5)
        t3 = sum(1 for s in lst if len(s) == 3 and set(s) == set(np.argsort(-full_fit_acc)[:3]))
        print(f"  {tag}: " + "; ".join(f"{[names[i] for i in s]} x{n}" for s, n in cnt_) + f"  | sizes {dict(Counter(len(s) for s in lst))}")
    # in-sample ceiling on all items (optimistic: selected and scored on the same rows)
    allrows = np.arange(len(Y))
    accs = sorted(((subset_acc(Z, Y, allrows, c, full_fit_acc), c) for c in SUBSETS), key=lambda t: -t[0])
    top3_set = sorted(np.argsort(-full_fit_acc)[:3].tolist())
    rank = [i for i, (_, c) in enumerate(accs) if sorted(c) == top3_set][0] + 1
    print(f"\nIn-sample (all {len(Y)} items, optimistic): best of {len(SUBSETS)} subsets = {accs[0][0]:.4f} "
          f"{[names[i] for i in accs[0][1]]}; top-3-by-accuracy {[names[i] for i in top3_set]} = "
          f"{[x for x, c in accs if sorted(c) == top3_set][0]:.4f}, rank {rank}/{len(SUBSETS)}")
    print("  top 8 subsets in-sample:")
    for x, c in accs[:8]:
        print(f"    {x:.4f}  size {len(c)}  {[names[i] for i in c]}")
    cf = pd.DataFrame(coefs)
    print("\nLogistic regression (all 8, L2) mean coefficient over repeats (+- sd), chosen C counts", dict(Counter(cf.C))); 
    print(pd.DataFrame({"mean": cf[names + ["intercept"]].mean(), "sd": cf[names + ["intercept"]].std()}).round(3).to_string())
    os.makedirs(a.out, exist_ok=True)
    res.to_csv(os.path.join(a.out, f"explore_12_{a.bench}{a.tag}.csv"), index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True); ap.add_argument("--bench", default="bff")
    ap.add_argument("--verdicts-path"); ap.add_argument("--rb2-path")
    ap.add_argument("--n-repeats", type=int, default=20); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--c-grid", type=float, nargs="+", default=[0.03, 0.1, 0.3, 1, 3, 10])
    ap.add_argument("--out", default="results/explore_12")
    ap.add_argument("--exclude", nargs="*", default=[]); ap.add_argument("--tag", default=""); ap.add_argument("--condition", default="none")
    a = ap.parse_args()
    from data import drop_judges
    d0 = load_judgments(a.data, a.bench, condition=a.condition, verdicts_path=a.verdicts_path, rb2_path=a.rb2_path)
    run(drop_judges(d0, a.exclude) if a.exclude else d0, a)
