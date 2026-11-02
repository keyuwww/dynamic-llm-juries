"""Study A of docs/confident_errors_plan.md: confidence level x outcome, and how errors are shared across judges.

Per judge x pair (confidence run; verdict and confidence from the same calls, both orders):
  outcome  R = right in both orders, W = wrong in both, F = flip (right in one order)
  level    low / mid / high confidence. Three schemes:
             third  within judge x benchmark, cuts at the 33rd / 67th percentile values, ties kept together (primary)
             risk   cross-fitted isotonic map confidence -> P(not right in both orders), grouped 5-fold by question;
                    expected error < 15% high, 15-35% mid, > 35% low (same meaning across judges)
             fixed  >= 90 high, < 70 low
Steps
  A0  cell counts; error rate and flip share by level
  A1  overlap: lift = P(other judge also errs | focal judge W at level L) / P(other judge errs), judge x judge,
      same vs different family; "errs" = not right in both orders. Bootstrap CI over question groups.
  A2  sharing: for each focal W verdict, how many of the other 7 judges also err, vs an independence
      (Poisson-binomial) null from each other judge's error rate on that benchmark
  A3  item features, W vs R within each level and W across levels (standardised within benchmark)
  A4  hidden doubt: within each level, AUROC of low verdict-token probability and of lower stated confidence for W vs R
  A5  cross-judge catch: within each level, AUROC of others' doubt and others' disagreement for W vs R,
      W split by how many other judges also err (0-1 / 2-3 / 4+)
Usage: python confident_errors.py -> results/confident_errors/{summary.md, *.csv, summary.json}
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from conf_analysis import read  # noqa: E402
from difficulty_awareness import FAMILY, human_split, solve_labels  # noqa: E402
from flip_analysis import features  # noqa: E402
from order_consistency import SHORT, auroc  # noqa: E402

BENCHES = ["bffpair", "judgebench", "alpacafarm", "mtbhuman"]
LEVELS = ["low", "mid", "high"]
OUT = HERE / "results" / "confident_errors"
FEATS = ["sim", "len_gap", "longer_is_better", "same_final_number", "q_len", "knowledge", "reasoning",
         "constraints", "open_endedness", "human_split", "solved_by_judge"]


def groups(b):
    it = pd.read_pickle(HERE / "data" / f"{b}_items.pkl")
    return it.drop_duplicates("pair_id").set_index("pair_id").group.astype(str)


def states(b):
    """One row per judge x pair: outcome, conf, token prob, pick of answer A in each order."""
    t = read("confidence", b)
    t["right"] = (t.verdict == t.gold).astype(float)
    t["pick_a"] = np.where(t.order == "ab", t.verdict, 1 - t.verdict)      # 1 = picks the 'ab'-first answer
    t["tok"] = t.p_verdict.astype(float)
    g = t.groupby(["judge", "pair_id"]).agg(n=("order", "nunique"), right=("right", "sum"), conf=("conf", "mean"),
                                            tok=("tok", "mean"), pick=("pick_a", "mean")).reset_index()
    g = g[(g.n == 2) & g.conf.notna()].copy()
    g["outcome"] = np.select([g.right == 2, g.right == 0], ["R", "W"], "F")
    g["bench"] = b
    g["group"] = g.pair_id.map(groups(b)).fillna("na")
    return g


def add_levels(g):
    def third(c):
        lo, hi = c.quantile(1 / 3), c.quantile(2 / 3)
        return pd.Series(np.where(c >= hi, "high", np.where(c < lo, "low", "mid")), index=c.index)

    def risk(x):
        ug = x.group.unique()
        fold = x.group.map(dict(zip(np.random.default_rng(0).permutation(ug), np.arange(len(ug)) % 5)))
        p = pd.Series(np.nan, index=x.index)
        y = (x.outcome != "R").astype(float)
        for k in range(5):
            tr, te = fold != k, fold == k
            iso = IsotonicRegression(increasing=False, out_of_bounds="clip").fit(x.conf[tr], y[tr])
            p[te] = iso.predict(x.conf[te])
        return pd.Series(np.where(p < .15, "high", np.where(p > .35, "low", "mid")), index=x.index)

    g["third"] = g.groupby(["judge", "bench"], group_keys=False).conf.apply(third)
    g["risk"] = g.groupby(["judge", "bench"], group_keys=False).apply(risk)
    g["fixed"] = np.where(g.conf >= 90, "high", np.where(g.conf < 70, "low", "mid"))
    return g


def boot_mean(v, grp, n=1000, seed=0):
    """Mean and 95% CI, bootstrap over question groups."""
    v, grp = np.asarray(v, float), np.asarray(grp)
    ok = ~np.isnan(v)
    v, grp = v[ok], grp[ok]
    if len(v) < 5:
        return np.nan, np.nan, np.nan
    idx = pd.Series(np.arange(len(v))).groupby(grp).apply(list).tolist()
    rng = np.random.default_rng(seed)
    bs = [v[np.concatenate([idx[i] for i in rng.integers(0, len(idx), len(idx))])].mean() for _ in range(n)]
    return float(v.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def run(g, scheme):
    res = {}
    # ---------------- A0
    a0 = g.pivot_table(index=["bench", "judge", scheme], columns="outcome", values="pair_id", aggfunc="count",
                       fill_value=0).reset_index()
    pooled = g.groupby(scheme).outcome.value_counts().unstack(fill_value=0).reindex(LEVELS)
    pooled["err_rate_consistent"] = pooled.W / (pooled.W + pooled.R)
    pooled["flip_share"] = pooled.F / pooled[["R", "W", "F"]].sum(1)
    res["A0"] = pooled
    res["A0_cells"] = a0

    # wide helpers per bench
    rows1, rows2, rows5 = [], [], []
    for b, x in g.groupby("bench"):
        err = x.pivot_table(index="pair_id", columns="judge", values="outcome", aggfunc="first").ne("R").astype(float)
        out = x.pivot_table(index="pair_id", columns="judge", values="outcome", aggfunc="first")
        lev = x.pivot_table(index="pair_id", columns="judge", values=scheme, aggfunc="first")
        pick = x.pivot_table(index="pair_id", columns="judge", values="pick", aggfunc="first")
        doubt = 1 - x.pivot_table(index="pair_id", columns="judge", values="conf", aggfunc="first").rank(pct=True)
        grp = x.drop_duplicates("pair_id").set_index("pair_id").group
        J = list(out.columns)
        rate = err.mean()
        for j in J:
            others = [k for k in J if k != j]
            n_others_err = err[others].sum(1)
            wrongW = (out == "W").astype(float)
            n_others_W = wrongW[others].sum(1)
            psW = wrongW.mean()[others].values
            # null: Poisson-binomial mean and P(>=4) from the other judges' marginal error rates
            ps = rate[others].values
            dist = np.array([1.0])
            for p in ps:
                dist = np.convolve(dist, [1 - p, p])
            for L in LEVELS:
                foc = (out[j] == "W") & (lev[j] == L)
                for k in others:
                    if foc.sum() >= 3:
                        rows1.append(dict(bench=b, level=L, judge=j, other=k, n=int(foc.sum()),
                                          lift=float(err[k][foc].mean() / max(rate[k], 1e-9)),
                                          same_family=FAMILY[j] == FAMILY[k]))
                for p_id in out.index[foc]:
                    rows2.append(dict(bench=b, level=L, judge=j, pair_id=p_id, group=grp[p_id],
                                      n_others_err=int(n_others_err[p_id]), n_others_W=int(n_others_W[p_id]),
                                      null_W_mean=float(psW.sum()),
                                      null_mean=float(ps.sum()), null_ge4=float(dist[4:].sum())))
                # A5: within level, W vs R
                inl = (lev[j] == L) & out[j].isin(["R", "W"])
                if inl.sum() < 10:
                    continue
                y = (out[j][inl] == "W").astype(int).values
                od = doubt[others][inl].mean(1).values
                # disagreement: share of other judges whose mean pick differs from j's pick (consistent verdicts)
                dis = (pick[others][inl].sub(pick[j][inl], axis=0).abs()).mean(1).values
                share_lvl = pd.cut(n_others_err[inl], [-1, 1, 3, 7], labels=["0-1", "2-3", "4+"]).values
                for name, s in [("others_doubt", od), ("others_disagree", dis)]:
                    rows5.append(dict(bench=b, level=L, judge=j, signal=name, split="all W", n_w=int(y.sum()),
                                      auc=auroc(y, s) if 0 < y.sum() < len(y) else np.nan))
                    for sl in ["0-1", "2-3", "4+"]:
                        m = (y == 0) | (share_lvl == sl)
                        yy = y[m]
                        if yy.sum() >= 3:
                            rows5.append(dict(bench=b, level=L, judge=j, signal=name, split=f"W shared {sl}",
                                              n_w=int(yy.sum()), auc=auroc(yy, s[m])))
    A1, A2, A5 = pd.DataFrame(rows1), pd.DataFrame(rows2), pd.DataFrame(rows5)
    res["A1_pairs"] = A1
    res["A1"] = A1.groupby("level").apply(lambda d: pd.Series(dict(
        lift_all=d.lift.mean(), lift_same_family=d.lift[d.same_family].mean(),
        lift_diff_family=d.lift[~d.same_family].mean(), n_judge_pairs=len(d)))).reindex(LEVELS)
    # bootstrap CI of the mean number of other judges erring, per level (over question groups)
    a2 = []
    for L in LEVELS:
        d = A2[A2.level == L]
        m, lo, hi = boot_mean(d.n_others_err, d.group)
        mw, lw, hw = boot_mean(d.n_others_W, d.group)
        a2.append(dict(level=L, n_W=len(d), others_err_mean=m, ci_lo=lo, ci_hi=hi, null_mean=d.null_mean.mean(),
                       share_ge4=(d.n_others_err >= 4).mean(), null_share_ge4=d.null_ge4.mean(),
                       others_W_mean=mw, W_ci_lo=lw, W_ci_hi=hw, null_W_mean=d.null_W_mean.mean(),
                       share_none_W=(d.n_others_W == 0).mean()))
    res["A2"] = pd.DataFrame(a2).set_index("level")
    res["A2_rows"] = A2
    res["A5"] = A5.groupby(["signal", "split", "level"]).auc.agg(["mean", "count"]).unstack("level")
    res["A5_rows"] = A5

    # ---------------- A4: hidden doubt within level
    a4 = []
    for (b, j, L), x in g[g.outcome.isin(["R", "W"])].groupby(["bench", "judge", scheme]):
        y = (x.outcome == "W").astype(int).values
        if y.sum() < 3 or y.sum() > len(y) - 3:
            continue
        a4.append(dict(bench=b, judge=j, level=L, n_w=int(y.sum()), n=len(y),
                       auc_token=auroc(y, -x.tok.fillna(x.tok.median()).values), auc_stated=auroc(y, -x.conf.values),
                       tok_saturated=float((x.tok >= 0.999).mean())))
    A4 = pd.DataFrame(a4)
    res["A4_rows"] = A4
    res["A4"] = A4.groupby("level")[["auc_token", "auc_stated", "tok_saturated"]].mean().reindex(LEVELS)
    return res


def a3_features(g, scheme):
    """Standardised (within benchmark) feature means by cell; W-R gap within level and HW-LW gap."""
    F = []
    for b in BENCHES:
        x = g[g.bench == b]
        idx = pd.Index(x.pair_id.unique())
        f = features(b, idx)
        if b in ("alpacafarm", "mtbhuman"):
            f["human_split"] = human_split(b, idx)
        f = f[[c for c in FEATS if c in f.columns]]
        z = (f - f.mean()) / f.std(ddof=0).replace(0, np.nan)
        m = x.merge(z, left_on="pair_id", right_index=True, how="left")
        if b == "bffpair":
            sol = solve_labels(idx)
            m["solved_by_judge"] = [sol[j].get(p, np.nan) if j in sol else np.nan for j, p in zip(m.judge, m.pair_id)]
            s = m.solved_by_judge
            m["solved_by_judge"] = (s - s.mean()) / s.std(ddof=0)
        F.append(m)
    M = pd.concat(F)
    rows = []
    for c in FEATS:
        if c not in M.columns:
            continue
        for L in LEVELS:
            for o in ["R", "W", "F"]:
                d = M[(M[scheme] == L) & (M.outcome == o)]
                mean, lo, hi = boot_mean(d[c], d.group.astype(str) + d.bench, n=500)
                rows.append(dict(feature=c, level=L, outcome=o, mean_z=mean, ci_lo=lo, ci_hi=hi, n=int(d[c].notna().sum())))
    T = pd.DataFrame(rows)
    M["unit"] = M.bench + "|" + M.group.astype(str)
    units = M.unit.unique()
    rng = np.random.default_rng(0)
    contrasts = [(f"W-R {L}", (L, "W"), (L, "R")) for L in LEVELS] + [("HW-LW", ("high", "W"), ("low", "W"))]
    by_unit = {u: d for u, d in M.groupby("unit")}
    boots = []
    for _ in range(300):
        Mb = pd.concat([by_unit[u] for u in rng.choice(units, len(units))])
        boots.append(Mb.groupby([scheme, "outcome"])[[c for c in FEATS if c in M.columns]].mean())
    rows = []
    for c in [c for c in FEATS if c in M.columns]:
        full = M.groupby([scheme, "outcome"])[c].mean()
        for name, a, b_ in contrasts:
            d = full.get(a, np.nan) - full.get(b_, np.nan)
            bs = np.array([bt[c].get(a, np.nan) - bt[c].get(b_, np.nan) for bt in boots])
            rows.append(dict(feature=c, contrast=name, gap=d, ci_lo=np.nanpercentile(bs, 2.5),
                             ci_hi=np.nanpercentile(bs, 97.5)))
    G = pd.DataFrame(rows)
    gaps = G.assign(cell=G.apply(lambda r: f"{r.gap:+.2f} [{r.ci_lo:+.2f}, {r.ci_hi:+.2f}]" +
                                 ("*" if r.ci_lo > 0 or r.ci_hi < 0 else ""), axis=1)
                    ).pivot(index="feature", columns="contrast", values="cell")[[x[0] for x in contrasts]]
    G.to_csv(OUT / "A3_gaps.csv", index=False)
    return T, gaps


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    g = add_levels(pd.concat([states(b) for b in BENCHES], ignore_index=True))
    g.to_csv(OUT / "states.csv", index=False)
    R = {s: run(g, s) for s in ["third", "risk", "fixed"]}
    T3, gaps = a3_features(g, "third")
    T3.to_csv(OUT / "A3_features_by_cell.csv", index=False)
    p = R["third"]
    for k in ["A0_cells", "A1_pairs", "A2_rows", "A4_rows", "A5_rows"]:
        p[k].to_csv(OUT / f"{k}.csv", index=False)

    # robustness: key numbers per scheme
    rob = []
    for s, r in R.items():
        for L in LEVELS:
            a5 = r["A5"]
            rob.append(dict(scheme=s, level=L,
                            err_rate=r["A0"].loc[L, "err_rate_consistent"], n_W=int(r["A0"].loc[L, "W"]),
                            lift=r["A1"].loc[L, "lift_all"], others_err=r["A2"].loc[L, "others_err_mean"],
                            share_ge4=r["A2"].loc[L, "share_ge4"],
                            auc_token=r["A4"].loc[L, "auc_token"],
                            others_doubt=a5.loc[("others_doubt", "all W"), ("mean", L)],
                            others_disagree=a5.loc[("others_disagree", "all W"), ("mean", L)]))
    Rob = pd.DataFrame(rob)
    Rob.to_csv(OUT / "robustness.csv", index=False)

    md = lambda d: d.round(3).to_markdown()  # noqa: E731
    L = ["# Study A: confidence level x outcome (primary scheme: within-judge thirds)", "",
         "R = right in both orders, W = wrong in both, F = flip. 'Errs' for other judges = not right in both orders.",
         "", "## A0 Cells (pooled)", "", md(p["A0"]), "",
         "## A1 Overlap: lift of other judges' error rate when the focal judge is W at this level", "", md(p["A1"]), "",
         "## A2 How many of the other 7 judges also err (observed vs independence null)", "", md(p["A2"]), "",
         "## A3 Item features (z within benchmark): W minus R within each level; HW minus LW. 95% CI over question groups; * = excludes 0", "", gaps.to_markdown(), "",
         "## A4 Hidden doubt within level: AUROC for W vs R (mean over judge x benchmark)", "", md(p["A4"]), "",
         "## A5 Cross-judge catch within level: AUROC for W vs R (mean over judge x benchmark; count = cells)", "",
         md(p["A5"]), "",
         "## Robustness across level schemes", "", Rob.round(3).to_markdown(index=False), ""]
    (OUT / "summary.md").write_text("\n".join(L))
    json.dump({s: {k: (v.round(4).reset_index().to_dict(orient="records") if hasattr(v, "reset_index") else v)
                   for k, v in r.items() if k in ("A0", "A1", "A2", "A4")} for s, r in R.items()} |
              {"A3_gaps": gaps.reset_index().to_dict(orient="records")},
              open(OUT / "summary.json", "w"), indent=1, default=str)
    print("\n".join(L))


if __name__ == "__main__":
    main()
