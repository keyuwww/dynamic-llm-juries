"""Serving, per-split baselines, repeats, pooled bootstrap and the copy stress test.

Serving scores with the SAME eta-hat tables used for construction (no separate majority vote):
once (S, specialists) are frozen, eta-hat is refit on construction-fit U construction-validation and
the verdict is 1[eta-hat(Z_active) >= 0.5]. The match indicator is never used here.
"""
import itertools

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

from audit import baseline_predictions, oracle_verdicts          # functions on (Z, Y); no match indicator exposed
from construct import construct_panel
from oracle_risk import conditional_gain, fit_eta_table, slice_gain
from slices import fit_slice_thresholds, slice_masks, usable_slices


def kappa(v, y):
    k = cohen_kappa_score(y, v) if len(set(v)) > 1 and len(set(y)) > 1 else 0.0
    return 0.0 if np.isnan(k) else float(k)


def _profile(spec_slices, masks, rows):
    """Per row: frozenset of specialist-bearing slices that fire."""
    return [frozenset(f for f in spec_slices if masks[f][i]) for i in rows]


def _active_cols(S, specialists, firing, col):
    cols = [col[j] for j in S]
    for f in sorted(firing):
        cols += [col[j] for j in specialists[f] if col[j] not in cols]
    return cols


def fit_serving_tables(S, specialists, Z, Y, serve_idx, masks, col, mode="all", m=2.0):
    """One eta-hat table per possible firing-profile of the specialist-bearing slices, refit on serve_idx
    (= fit U val). mode='all': fit on every serve row; mode='matched': only rows with the same profile."""
    spec_slices = [f for f, js in specialists.items() if js]
    prof = _profile(spec_slices, masks, serve_idx)
    tables = {}
    for r in range(len(spec_slices) + 1):
        for combo in itertools.combinations(spec_slices, r):
            key = frozenset(combo)
            cols = _active_cols(S, specialists, key, col)
            rows = serve_idx
            if mode == "matched":
                sel = np.array([p == key for p in prof], dtype=bool)
                if sel.sum() >= 10:
                    rows = serve_idx[sel]
            tables[key] = (cols, fit_eta_table(Z[np.ix_(rows, cols)], Y[rows], m))
    return tables, spec_slices


def serve(S, specialists, eta_tables, item_features, Z, cost_vec, test_idx, spec_slices=None):
    """item_features: {slice: bool mask over all rows}. Returns verdicts and $ paid for each test item."""
    spec_slices = spec_slices if spec_slices is not None else [f for f, js in specialists.items() if js]
    verdict = np.zeros(len(test_idx), dtype=int)
    paid = np.zeros(len(test_idx))
    for n, i in enumerate(test_idx):
        key = frozenset(f for f in spec_slices if item_features[f][i])
        cols, tab = eta_tables[key]
        verdict[n] = int(tab.predict(Z[i:i + 1][:, cols])[0] >= 0.5)
        paid[n] = cost_vec[cols].sum()
    return verdict, paid


def construct_for_split(Z, Yw, names, cost_vec, masks, keep, fit, val, tau_P, tau_f, lam):
    col = {j: k for k, j in enumerate(names)}
    cost = {j: cost_vec[col[j]] for j in names}
    gain_fn = lambda j, S: conditional_gain(col[j], [col[s] for s in S], Z, Yw, fit, val)
    slice_gain_fn = lambda j, S, f: slice_gain(col[j], [col[s] for s in S], f, Z, Yw, fit, val, masks[f])
    return construct_panel(names, gain_fn, slice_gain_fn, cost, keep, tau_P, tau_f, lam)


def _metrics(v, y, c):
    return dict(acc=float((v == y).mean()), kappa=kappa(v, y), cost=float(np.mean(c)))


def run_all_repeats(data, splits, tau_P=0.005, tau_f=0.005, lam=0.0, serving_fit="all",
                    shuffle_labels=False, shuffle_seed=123, verbose=True, mask_fn=None):
    """mask_fn(data, fit_idx) -> {slice: bool mask over all rows} overrides the hand-crafted slices.
    Returns dict(results: per repeat x strategy DataFrame, roles, slice_log, pooled).
    pooled[strategy] = list of (test item indices, correct-indicator) over repeats, for the question bootstrap."""
    Z, Y, names = data.Z, data.Y, data.judge_names
    cost_vec = np.array([data.cost[j] for j in names])
    col = {j: k for k, j in enumerate(names)}
    rng = np.random.default_rng(shuffle_seed)
    rows, roles, slice_log, pooled, pooled_cost = [], [], [], {}, {}

    for r, (fit, val, test) in enumerate(splits):
        Yw = Y.copy()
        if shuffle_labels:       # permute Y within construction-fit and construction-validation independently
            Yw[fit] = rng.permutation(Y[fit])
            Yw[val] = rng.permutation(Y[val])
        if mask_fn is not None:
            masks = mask_fn(data, fit)
        else:
            thr = fit_slice_thresholds(data.prompt[fit], data.response[fit])
            masks = slice_masks(data.prompt, data.response, thr)
        keep, dropped = usable_slices(masks, fit, val)
        for f, m in masks.items():
            slice_log.append(dict(repeat=r, slice=f, prevalence_fit=float(m[fit].mean()), n_fit=int(m[fit].sum()),
                                  n_val=int(m[val].sum()), kept=f in keep, reason=dropped.get(f, "")))

        S, spec, copies = construct_for_split(Z, Yw, names, cost_vec, masks, keep, fit, val, tau_P, tau_f, lam)
        for j in S:
            roles.append(dict(repeat=r, judge=j, role="Complement"))
        for f, js in spec.items():
            roles += [dict(repeat=r, judge=j, role=f"Specialist:{f}") for j in js]
        roles += [dict(repeat=r, judge=j, role="Copy") for j in copies]

        sel = np.concatenate([fit, val])
        tables, spec_slices = fit_serving_tables(S, spec, Z, Yw, sel, masks, col, serving_fit)
        verdict, paid = serve(S, spec, tables, masks, Z, cost_vec, test, spec_slices)

        ytest = Y[test]
        strat = {"path_a_panel": (verdict, paid)}
        for name, (v, c, cols) in baseline_predictions(Z, Yw, sel, test, cost_vec).items():
            strat[name] = (v, c)
            if name in ("static_top3", "full_jury"):   # extra control: same eta-hat serving rule, no panel selection
                tab = fit_eta_table(Z[np.ix_(sel, cols)], Yw[sel])
                strat["stacked_" + name.replace("static_", "").replace("full_jury", "full")] = (
                    (tab.predict(Z[np.ix_(test, cols)]) >= 0.5).astype(int), c)
        strat["oracle"] = (oracle_verdicts(Z, Y, test), np.full(len(test), np.nan))
        for name, (v, c) in strat.items():
            d = _metrics(v, ytest, c)
            if name == "path_a_panel":
                d.update(panel_size=len(S), n_specialists=sum(len(js) for js in spec.values()), n_copies=len(copies))
            rows.append(dict(repeat=r, strategy=name, n_test=len(test), **d))
            pooled.setdefault(name, []).append((test, (v == ytest).astype(int)))
            pooled_cost.setdefault(name, []).append((test, np.asarray(c, float)))
        if verbose:
            print(f"[repeat {r:2d}] S={S} spec={ {f: js for f, js in spec.items() if js} } copies={len(copies)} "
                  f"slices kept={keep} | path_a acc={rows[-len(strat)]['acc']:.3f}")
    return dict(results=pd.DataFrame(rows), roles=pd.DataFrame(roles), slice_log=pd.DataFrame(slice_log), pooled=pooled, pooled_cost=pooled_cost)


def pooled_bootstrap(pooled, groups, a, b, n_boot=5000, seed=0):
    """Paired cluster bootstrap over questions on predictions pooled across repeats. Each question contributes
    its (correct, count) totals for both strategies; one draw resamples the questions with replacement."""
    G = groups.max() + 1
    def tot(name):
        c, n = np.zeros(G), np.zeros(G)
        for idx, corr in pooled[name]:
            np.add.at(c, groups[idx], corr)
            np.add.at(n, groups[idx], 1)
        return c, n
    ca, na = tot(a); cb, nb = tot(b)
    ok = na > 0
    ca, na, cb, nb = ca[ok], na[ok], cb[ok], nb[ok]
    rng = np.random.default_rng(seed)
    q = len(ca)
    d = np.empty(n_boot)
    for t in range(n_boot):
        s = rng.integers(0, q, q)
        d[t] = ca[s].sum() / na[s].sum() - cb[s].sum() / nb[s].sum()
    point = ca.sum() / na.sum() - cb.sum() / nb.sum()
    return dict(diff=float(point), lo=float(np.percentile(d, 2.5)), hi=float(np.percentile(d, 97.5)), n_questions=int(q))


def copy_stress_test(data, splits, tau_P=0.005, tau_f=0.005, lam=0.0, n_dup=2):
    """Duplicate the first n_dup Complement judges' verdict columns under fake names, rebuild the panel,
    and check (i) every duplicate lands in `copies` and (ii) every real judge keeps its role."""
    Z, Y, names = data.Z, data.Y, data.judge_names
    cost_vec = np.array([data.cost[j] for j in names])
    out = []
    for r, (fit, val, test) in enumerate(splits):
        thr = fit_slice_thresholds(data.prompt[fit], data.response[fit])
        masks = slice_masks(data.prompt, data.response, thr)
        keep, _ = usable_slices(masks, fit, val)
        S, spec, copies = construct_for_split(Z, Y, names, cost_vec, masks, keep, fit, val, tau_P, tau_f, lam)
        dup = S[:n_dup]
        if not dup:
            continue
        dcols = [names.index(j) for j in dup]
        Z2 = np.hstack([Z, Z[:, dcols]])
        names2 = names + [f"{j}__copy" for j in dup]
        cost2 = np.concatenate([cost_vec, cost_vec[dcols]])
        S2, spec2, copies2 = construct_for_split(Z2, Y, names2, cost2, masks, keep, fit, val, tau_P, tau_f, lam)
        fake = [f"{j}__copy" for j in dup]
        real = lambda xs: sorted(x for x in xs if not x.endswith("__copy"))
        same = (real(S2) == sorted(S) and real(copies2) == sorted(copies)
                and all(real(spec2[f]) == sorted(spec[f]) for f in spec))
        out.append(dict(repeat=r, duplicated=",".join(dup), all_dups_are_copies=all(f in copies2 for f in fake),
                        real_roles_unchanged=same))
    return pd.DataFrame(out)
