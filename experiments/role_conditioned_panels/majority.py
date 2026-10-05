"""Majority-vote-consistent role construction + serving (no eta-hat table anywhere).

Gain of a change to a panel = change in majority-vote ACCURACY on construction-validation. Serving uses the
same majority vote, so the panel is selected and scored under one rule.

Parity: a 2-judge majority can never beat its best member, so single-judge greedy growth stalls at size 1.
The global panel therefore starts with the single best judge (gain vs. the constant fit-prior prediction) and
then grows by the best *pair* of judges, keeping |S| odd (no ties at the global stage). Specialists are added
to a slice one at a time, exactly as in the spec; ties in the active set are broken by the best fit-accuracy
judge in that set (Ingrid's convention). The Cm match matrix is never used; accuracy is computed from (Z, Y).
"""
import itertools

import numpy as np
import pandas as pd

from audit import baseline_predictions, oracle_verdicts
from evaluate import _metrics
from slices import fit_slice_thresholds, slice_masks, usable_slices


def mv_verdict(Z, cols, tie_col):
    """Strict majority of 1s over `cols`; an exact tie takes judge `tie_col`'s verdict. Empty panel -> None."""
    share = Z[:, cols].mean(1)
    v = (share > 0.5).astype(int)
    tie = np.isclose(share, 0.5)
    v[tie] = Z[tie, tie_col]
    return v


def _tie_col(cols, fit_acc):
    return max(cols, key=lambda c: fit_acc[c])


def mv_acc(Z, Y, rows, cols, fit_acc, prior_pred):
    if len(rows) == 0:
        return 0.0
    if not cols:
        return float((Y[rows] == prior_pred).mean())
    return float((mv_verdict(Z[rows], cols, _tie_col(cols, fit_acc)) == Y[rows]).mean())


def construct_panel_mv(names, Z, Y, cost_vec, masks, slices, fit, val, tau_P=0.005, tau_f=0.005, lam=0.0, step="pair"):
    col = {j: k for k, j in enumerate(names)}
    fit_acc = (Z[fit] == Y[fit][:, None]).mean(0)
    prior_pred = int(Y[fit].mean() >= 0.5)
    acc = lambda cols, rows=val: mv_acc(Z, Y, rows, list(cols), fit_acc, prior_pred)
    S, specialists, copies = [], {f: [] for f in slices}, []
    unassigned = list(names)

    while unassigned:
        base = acc([col[s] for s in S])
        if not S:
            cands = [((j,), acc([col[j]]) - base - lam * cost_vec[col[j]]) for j in unassigned]
        elif step == "pair":
            cands = [((j, k), acc([col[s] for s in S] + [col[j], col[k]]) - base - lam * (cost_vec[col[j]] + cost_vec[col[k]]))
                     for j, k in itertools.combinations(unassigned, 2)]
        else:   # 'single': one judge at a time (stalls on parity; kept to show that it does)
            cands = [((j,), acc([col[s] for s in S] + [col[j]]) - base - lam * cost_vec[col[j]]) for j in unassigned]
        if cands:
            best, val_ = max(cands, key=lambda t: t[1])
            if val_ > tau_P:
                S += list(best)
                for j in best:
                    unassigned.remove(j)
                continue
        for j in list(unassigned):          # slice pass: accuracy delta on the slice rows, same tie rule
            sc = []
            for f in slices:
                rows = val[masks[f][val]]
                cols = [col[s] for s in S]
                sc.append((f, acc(cols + [col[j]], rows) - acc(cols, rows) - lam * cost_vec[col[j]]))
            f_best, sval = max(sc, key=lambda t: t[1]) if sc else (None, float("-inf"))
            if sval > tau_f:
                specialists[f_best].append(j)
            else:
                copies.append(j)
            unassigned.remove(j)
    return S, specialists, copies


def serve_mv(S, specialists, masks, Z, cost_vec, test, col, sel_acc, prior_pred):
    spec_slices = [f for f, js in specialists.items() if js]
    verdict, paid = np.zeros(len(test), int), np.zeros(len(test))
    for n, i in enumerate(test):
        cols = [col[j] for j in S]
        for f in spec_slices:
            if masks[f][i]:
                cols += [col[j] for j in specialists[f] if col[j] not in cols]
        verdict[n] = prior_pred if not cols else mv_verdict(Z[i:i + 1], cols, _tie_col(cols, sel_acc))[0]
        paid[n] = cost_vec[cols].sum()
    return verdict, paid


def run_all_repeats_mv(data, splits, tau_P=0.005, tau_f=0.005, lam=0.0, step="pair", shuffle_labels=False,
                       shuffle_seed=123, verbose=True, mask_fn=None, **_ignored):
    Z, Y, names = data.Z, data.Y, data.judge_names
    cost_vec = np.array([data.cost[j] for j in names]); col = {j: k for k, j in enumerate(names)}
    rng = np.random.default_rng(shuffle_seed)
    rows, roles, slice_log, pooled, pooled_cost = [], [], [], {}, {}
    for r, (fit, val, test) in enumerate(splits):
        Yw = Y.copy()
        if shuffle_labels:
            Yw[fit] = rng.permutation(Y[fit]); Yw[val] = rng.permutation(Y[val])
        if mask_fn is not None:
            masks = mask_fn(data, fit)
        else:
            thr = fit_slice_thresholds(data.prompt[fit], data.response[fit])
            masks = slice_masks(data.prompt, data.response, thr)
        keep, dropped = usable_slices(masks, fit, val)
        for f, m in masks.items():
            slice_log.append(dict(repeat=r, slice=f, prevalence_fit=float(m[fit].mean()), n_fit=int(m[fit].sum()),
                                  n_val=int(m[val].sum()), kept=f in keep, reason=dropped.get(f, "")))
        S, spec, copies = construct_panel_mv(names, Z, Yw, cost_vec, masks, keep, fit, val, tau_P, tau_f, lam, step)
        roles += [dict(repeat=r, judge=j, role="Complement") for j in S]
        for f, js in spec.items():
            roles += [dict(repeat=r, judge=j, role=f"Specialist:{f}") for j in js]
        roles += [dict(repeat=r, judge=j, role="Copy") for j in copies]

        sel = np.concatenate([fit, val])
        sel_acc = (Z[sel] == Yw[sel][:, None]).mean(0)
        v, c = serve_mv(S, spec, masks, Z, cost_vec, test, col, sel_acc, int(Yw[sel].mean() >= 0.5))
        ytest = Y[test]
        strat = {"path_a_panel": (v, c)}
        for name, (bv, bc, cols) in baseline_predictions(Z, Yw, sel, test, cost_vec).items():
            strat[name] = (bv, bc)
            if name in ("static_top3", "full_jury"):   # calibrated vote count: ONE parameter tuned on fit U val
                cnt = Z[:, cols].sum(1)
                k = max(range(len(cols) + 2), key=lambda k: ((cnt[sel] >= k).astype(int) == Yw[sel]).mean())
                strat["tuned_vote_" + ("top3" if name == "static_top3" else "all8")] = ((cnt[test] >= k).astype(int), bc)
        strat["oracle"] = (oracle_verdicts(Z, Y, test), np.full(len(test), np.nan))
        for name, (sv, sc) in strat.items():
            d = _metrics(sv, ytest, sc)
            if name == "path_a_panel":
                d.update(panel_size=len(S), n_specialists=sum(len(js) for js in spec.values()), n_copies=len(copies))
            rows.append(dict(repeat=r, strategy=name, n_test=len(test), **d))
            pooled.setdefault(name, []).append((test, (sv == ytest).astype(int)))
            pooled_cost.setdefault(name, []).append((test, np.asarray(sc, float)))
        if verbose:
            print(f"[repeat {r:2d}] S={S} spec={ {f: js for f, js in spec.items() if js} } copies={len(copies)} "
                  f"| acc={rows[-len(strat)]['acc']:.3f}")
    return dict(results=pd.DataFrame(rows), roles=pd.DataFrame(roles), slice_log=pd.DataFrame(slice_log), pooled=pooled, pooled_cost=pooled_cost)
