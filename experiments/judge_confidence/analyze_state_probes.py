#!/usr/bin/env python3
"""
Study B analysis (docs/confident_errors_plan.md, B3-B5) on the activations from probe_states_modal.py.

Per model, per pair: the forced verdict in each order (P(A) vs P(B)) gives outcome R / W / F and a confidence
(mean probability of the picked answer); level = within-model thirds per benchmark (snapped, ties kept together).
Activations = mean over the two orders, at q_end (question read, no answers), b_end (both answers read) and verdict.

B3 probes   W vs R within each confidence level. Pipeline: standardise -> PCA(64) -> L2 logistic. Nested grouped CV
            by question: outer 5 folds report AUROC, the layer is chosen on the training folds only (inner 3 folds,
            every 3rd layer). Baseline: text features (similarity, lengths, final numbers, aspects) + benchmark.
            Two label sources: 'own' = the model's forced verdict; 'tinker' = the same model's reasoning verdicts
            from the confidence run (only for judges in that run) - can activations before any reasoning predict
            the reasoned outcome?
B4 geometry Cross-fitted direction from low-confidence wrong (LW) to high-confidence right (HR) at the verdict
            position; position of each cell on it (0 = like LW, 1 = like HR). HW split by how many other judges
            (Tinker, confidence run) are also wrong in both orders.
B5 transfer The model's own W-vs-R probe (all levels) applied to other judges' errors on the same items.
Outputs: experiments/cross_benchmark/results/confident_errors/probes/<model>.json and probes_summary.md
Usage: python experiments/judge_confidence/analyze_state_probes.py [--models qwen3.5-4b,...]
"""
import argparse, json, sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
XB = HERE.parent / "cross_benchmark"
sys.path.insert(0, str(XB))
RAW = HERE / "results" / "raw" / "activations_states"
OUT = XB / "results" / "confident_errors" / "probes"
BENCHES = ["bffpair", "judgebench", "alpacafarm", "mtbhuman"]
LEVELS = ["low", "mid", "high"]
POSITIONS = ["q_end", "b_end", "verdict"]
TINKER = {"qwen3.5-4b": "qwen3.5-4b", "qwen3.5-9b": "qwen3.5-9b", "gpt-oss-20b": "gpt-oss-20b",
          "gpt-oss-120b": "gpt-oss-120b"}


def auc(y, s):
    y = np.asarray(y)
    return float(roc_auc_score(y, s)) if 0 < y.sum() < len(y) else np.nan


def load(model):
    rows, X = [], {p: [] for p in POSITIONS}
    for b in BENCHES:
        d = RAW / model / b
        if not (d / "index.jsonl").exists():
            continue
        idx = pd.DataFrame([json.loads(l) for l in open(d / "index.jsonl")])
        for pid, g in idx.groupby("pair_id"):
            if set(g.order) != {"ab", "ba"} or len(g) != 2:
                continue
            g = g.set_index("order")
            # float16 storage: gpt-oss-120b has a few residual dimensions beyond the float16 range (stored as inf)
            arrs = {o: np.nan_to_num(np.load(d / g.loc[o, "file"]).astype(np.float32), nan=0.0, posinf=65504.0,
                                     neginf=-65504.0) for o in ("ab", "ba")}
            ok = all(set(POSITIONS) <= set(g.loc[o, "positions"]) for o in ("ab", "ba"))
            if not ok:
                continue
            for p in POSITIONS:
                X[p].append(np.mean([arrs[o][list(g.loc[o, "positions"]).index(p)] for o in ("ab", "ba")], 0))
            # pick of the 'ab'-first answer in each order; gold is per order (1 = first shown better)
            pa_ab, pa_ba = g.loc["ab", "p_a"], g.loc["ba", "p_a"]
            right_ab = (pa_ab > .5) == (g.loc["ab", "gold"] == 1)
            right_ba = (pa_ba > .5) == (g.loc["ba", "gold"] == 1)
            conf = np.mean([max(pa_ab, 1 - pa_ab), max(pa_ba, 1 - pa_ba)])
            rows.append(dict(bench=b, pair_id=pid, right=int(right_ab) + int(right_ba), conf=conf,
                             flip=int((pa_ab > .5) == (pa_ba > .5))))
    S = pd.DataFrame(rows)
    X = {p: np.stack(v).astype(np.float32) for p, v in X.items()}       # (n, layers+1, hidden)
    S["outcome"] = np.select([S.right == 2, S.right == 0], ["R", "W"], "F")

    def third(c):
        lo, hi = c.quantile(1 / 3), c.quantile(2 / 3)
        return pd.Series(np.where(c >= hi, "high", np.where(c < lo, "low", "mid")), index=c.index)
    S["level"] = S.groupby("bench", group_keys=False).conf.apply(third)
    its = {b: pd.read_pickle(XB / "data" / f"{b}_items.pkl").drop_duplicates("pair_id").set_index("pair_id")
           for b in S.bench.unique()}
    S["group"] = [b + "|" + str(its[b].group.get(p, p)) for b, p in zip(S.bench, S.pair_id)]
    return S, X


def tinker_states(model):
    st = pd.read_csv(XB / "results" / "confident_errors" / "states.csv")
    other = st[st.judge != TINKER.get(model, "")]
    n_other_w = other.assign(w=(other.outcome == "W").astype(int)).groupby(["bench", "pair_id"]).w.sum()
    own = st[st.judge == TINKER.get(model, "")].set_index(["bench", "pair_id"])
    return st, own, n_other_w


def text_feats(S):
    from flip_analysis import features
    F = []
    for b, g in S.groupby("bench"):
        f = features(b, pd.Index(g.pair_id))
        f = f.drop(columns=[c for c in ("group", "category") if c in f.columns]).apply(pd.to_numeric, errors="coerce")
        f = f.fillna(f.median()).fillna(0)
        f.index = g.index
        F.append(f)
    F = pd.concat(F).reindex(S.index).fillna(0)
    return np.c_[F.values, pd.get_dummies(S.bench).values.astype(float)]


def folds(groups, k, seed):
    ug = np.unique(groups)
    m = dict(zip(np.random.default_rng(seed).permutation(ug), np.arange(len(ug)) % k))
    return np.array([m[g] for g in groups])


def probe(n_comp):
    return make_pipeline(StandardScaler(), PCA(n_components=n_comp, random_state=0),
                         LogisticRegression(C=0.05, max_iter=3000))


def nested_auc(Xl, y, groups, layers, seed=0):
    """Outer 5-fold AUROC; layer picked on inner folds of each training split. Xl: (n, L, h)."""
    y = np.asarray(y)
    fo = folds(groups, 5, seed)
    scores, chosen = np.full(len(y), np.nan), []
    for k in range(5):
        tr, te = fo != k, fo == k
        if y[tr].sum() < 8 or y[te].sum() == 0:
            continue
        fi = folds(groups[tr], 3, seed + 1)
        best, best_a = layers[0], -1
        for l in layers:
            s = np.full(tr.sum(), np.nan)
            for j in range(3):
                a, b_ = fi != j, fi == j
                if y[tr][a].sum() < 5:
                    continue
                m = probe(min(64, a.sum() - 1)).fit(Xl[tr][a][:, l], y[tr][a])
                s[b_] = m.predict_proba(Xl[tr][b_][:, l])[:, 1]
            ok = ~np.isnan(s)
            a_ = auc(y[tr][ok], s[ok])
            if a_ > best_a:
                best, best_a = l, a_
        chosen.append(int(best))
        m = probe(min(64, tr.sum() - 1)).fit(Xl[tr][:, best], y[tr])
        scores[te] = m.predict_proba(Xl[te][:, best])[:, 1]
    ok = ~np.isnan(scores)
    return auc(y[ok], scores[ok]), chosen, scores


def baseline_auc(F, y, groups, seed=0):
    y = np.asarray(y)
    fo = folds(groups, 5, seed)
    s = np.full(len(y), np.nan)
    for k in range(5):
        tr, te = fo != k, fo == k
        if y[tr].sum() < 3 or y[te].sum() == 0:
            continue
        m = make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=3000)).fit(F[tr], y[tr])
        s[te] = m.predict_proba(F[te])[:, 1]
    ok = ~np.isnan(s)
    return auc(y[ok], s[ok])


def boot_ci(y, s, groups, n=500):
    y, s, groups = np.asarray(y), np.asarray(s), np.asarray(groups)
    ok = ~np.isnan(s)
    y, s, groups = y[ok], s[ok], groups[ok]
    ug = np.unique(groups)
    ix = {g: np.where(groups == g)[0] for g in ug}
    rng = np.random.default_rng(0)
    out = []
    for _ in range(n):
        i = np.concatenate([ix[g] for g in rng.choice(ug, len(ug))])
        if 0 < y[i].sum() < len(i):
            out.append(roc_auc_score(y[i], s[i]))
    return (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))) if out else (np.nan, np.nan)


def run_model(model):
    S, X = load(model)
    nL = X["verdict"].shape[1]
    layers = list(range(2, nL, 3))
    F = text_feats(S)
    st, own_t, n_other_w = tinker_states(model)
    G = S.group.values
    res = dict(model=model, n_pairs=len(S), layers=nL,
               cells=S.groupby(["level", "outcome"]).size().unstack(fill_value=0).reindex(LEVELS).to_dict())

    # ---------- B3 within-level W vs R, two label sources
    label_sets = {"own": S[["level", "outcome"]]}
    if model in TINKER:
        j = own_t.reindex(pd.MultiIndex.from_arrays([S.bench, S.pair_id]))
        if j.third.notna().sum() > 100:
            label_sets["tinker"] = pd.DataFrame({"level": j.third.values, "outcome": j.outcome.values}, index=S.index)
    B3 = []
    for src, lab in label_sets.items():
        for L in LEVELS + ["all"]:
            m = (lab.outcome.isin(["R", "W"]) & ((lab.level == L) if L != "all" else True)).values
            y = (lab.outcome[m] == "W").astype(int).values
            if y.sum() < 15 or (1 - y).sum() < 15:
                B3.append(dict(labels=src, level=L, n_w=int(y.sum()), n=int(m.sum()), note="too few"))
                continue
            row = dict(labels=src, level=L, n_w=int(y.sum()), n=int(m.sum()),
                       baseline=baseline_auc(F[m], y, G[m]))
            for p in POSITIONS:
                a, ch, s = nested_auc(X[p][m], y, G[m], layers)
                lo, hi = boot_ci(y, s, G[m])
                row.update({f"{p}": a, f"{p}_lo": lo, f"{p}_hi": hi, f"{p}_layers": ch})
            B3.append(row)
            print(model, src, L, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items()
                                  if not k.endswith("layers")}, flush=True)
    res["B3"] = B3

    # ---------- B4 geometry at the verdict position, layer = most chosen in the own 'all' probe
    all_row = next((r for r in B3 if r["labels"] == "own" and r["level"] == "all" and "verdict_layers" in r), None)
    lay = int(pd.Series(all_row["verdict_layers"]).mode()[0]) if all_row else layers[len(layers) // 2]
    Xv = X["verdict"][:, lay]
    cell = (S.level.str[0].str.upper() + S.outcome).values
    fo = folds(G, 5, 0)
    t = np.full(len(S), np.nan)
    for k in range(5):
        tr, te = fo != k, fo == k
        sc = StandardScaler().fit(Xv[tr])
        Z = sc.transform(Xv)
        mu_hr, mu_lw = Z[tr & (cell == "HR")].mean(0), Z[tr & (cell == "LW")].mean(0)
        d = mu_hr - mu_lw
        t[te] = (Z[te] - mu_lw) @ d / (d @ d)
    S["t"] = t
    geo = S.assign(cell=cell).groupby("cell").t.agg(["mean", "count"])
    hw = S.assign(cell=cell)[cell == "HW"].copy()
    hw["shared"] = [n_other_w.get((b, p), np.nan) for b, p in zip(hw.bench, hw.pair_id)]
    hw["share_lvl"] = pd.cut(hw.shared, [-1, 1, 3, 8], labels=["0-1", "2-3", "4+"])
    res["B4"] = dict(layer=lay, cells=geo.round(3).reset_index().to_dict(orient="records"),
                     hw_by_sharing=hw.groupby("share_lvl", observed=False).t.agg(["mean", "count"]).round(3)
                     .reset_index().astype({"share_lvl": str}).to_dict(orient="records"))
    print(model, "B4 layer", lay, geo.round(2).to_dict(), flush=True)

    # ---------- B5 transfer: own W-vs-R probe (verdict position, layer lay) -> other judges' W vs R
    m = S.outcome.isin(["R", "W"]).values
    y_own = (S.outcome == "W").astype(int).values
    s = np.full(len(S), np.nan)
    for k in range(5):
        tr, te = (fo != k) & m, fo == k
        mdl = probe(64).fit(Xv[tr], y_own[tr])
        s[te] = mdl.predict_proba(Xv[te])[:, 1]
    B5 = [dict(target="own", auc=auc(y_own[m], s[m]), n_w=int(y_own[m].sum()))]
    for jj, g in st.groupby("judge"):
        if jj == TINKER.get(model):
            label = "same model, reasoning run"
        else:
            label = jj
        gi = g.set_index(["bench", "pair_id"]).reindex(pd.MultiIndex.from_arrays([S.bench, S.pair_id]))
        mm = gi.outcome.isin(["R", "W"]).values
        yy = (gi.outcome == "W").astype(int).values
        B5.append(dict(target=label, auc=auc(yy[mm], s[mm]), n_w=int(yy[mm].sum())))
    res["B5"] = B5
    print(model, "B5", [(r["target"], round(r["auc"], 3)) for r in B5], flush=True)
    S.drop(columns=["t"]).to_csv(OUT / f"{model}_states.csv", index=False)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="qwen3.5-4b,qwen3.5-9b,gpt-oss-20b,gpt-oss-120b")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for model in a.models.split(","):
        if not (RAW / model).exists():
            print("skip", model, "(no activations)")
            continue
        r = run_model(model)
        (OUT / f"{model}.json").write_text(json.dumps(r, indent=1, default=float))


if __name__ == "__main__":
    main()
