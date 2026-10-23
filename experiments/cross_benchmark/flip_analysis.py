"""Stage A of docs/order_flip_difficulty_plan.md: do other judges' order flips flag the best judge's confident errors,
and why? Stored verdicts only (no new calls).

Unit: one answer pair, judged by 8 judges in both orders. Target: the benchmark's best judge (highest accuracy over
both orders). Outcome: the target's confident error (wrong in both orders), on pairs where the target is consistent.

  features  pair controls from stored text (similarity, length, formatting, numbers, hedging, item aspects, votes)
  A1        controls vs controls + others' flip count (grouped CV logistic, bootstrap CI on the AUROC gain)
  A2        matched comparison: error rate for 0-1 vs >=2 flips within control strata (Mantel-Haenszel)
  A3        flips vs consistent disagreement vs a pooled-agreement score (Hamidieh-style), and their sum
  A5        same-pair vs sibling-pair flips (BFF pairwise, MT-Bench human: several pairs per question)
  A6        flips and solvability (BFF pairwise; solve labels from tinker_pool/bff_results/grades.jsonl)
  A7        flips as label-free difficulty: leave-one-judge-out, and prediction of human vote splits
  A9        checker sets chosen on training folds vs pooled flips vs disagreement, at matched flag rates
  floor     share of the target's confident errors that no other judge flags

Usage (from experiments/cross_benchmark): python flip_analysis.py
Writes results/flips/{features_<bench>.csv, stage_a.json, stage_a.md}
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from order_consistency import POOL, auroc, pair_table  # noqa: E402

BENCHES = ["bffpair", "judgebench", "alpacafarm", "mtbhuman"]
OUT = HERE / "results" / "flips"
RNG = np.random.default_rng(0)
HEDGE = re.compile(r"\b(might|may|perhaps|possibly|likely|unclear|approximately|roughly|assume|i think|it depends)\b", re.I)
CONF = re.compile(r"\b(clearly|definitely|certainly|exactly|always|must|undoubtedly)\b", re.I)
NUM = re.compile(r"-?\d[\d,]*\.?\d*%?")


# ----------------------------------------------------------------------------- data
def load(bench):
    """Per pair: others' states, target outcome, controls. Returns (df, target, judges)."""
    w = pair_table(bench, "none")
    acc = w.groupby("judge").apply(lambda x: 1 - x.err.sum() / (2 * len(x)))
    target = acc.idxmax()
    piv = {c: w.pivot_table(index="pair_id", columns="judge", values=c) for c in ["flip", "cons_wrong", "cons_right"]}
    J = [j for j in POOL if j in piv["flip"].columns]
    ok = piv["flip"][J].dropna().index
    fl, cw, cr = (piv[c].loc[ok, J] for c in ["flip", "cons_wrong", "cons_right"])
    others = [j for j in J if j != target]
    # a consistent judge "disagrees" with the target when it is consistent and on the other side of gold
    t_right = cr[target] == 1
    dis = pd.DataFrame({j: ((fl[j] == 0) & ((cr[j] == 1) != t_right)).astype(int) for j in others})
    df = pd.DataFrame({"t_flip": fl[target], "t_conf_err": cw[target], "n_flip": fl[others].sum(1),
                       "n_dis": dis.sum(1)}, index=ok)
    # pooled agreement score (Hamidieh-style epistemic proxy): 1 - mean P(other picks target's answer), per order
    df["eu"] = (df.n_dis + 0.5 * df.n_flip) / len(others)
    for j in others:
        df[f"flip_{j}"] = fl[j]
        df[f"dis_{j}"] = dis[j]
        df[f"err_{j}"] = (cw[j] + 0.5 * fl[j])        # 1 = wrong both orders, .5 = flip, 0 = right
    return df, target, J


def features(bench, idx):
    it = pd.read_pickle(HERE / "data" / f"{bench}_items.pkl")
    it = it[it.order == 0].drop_duplicates("pair_id").set_index("pair_id").loc[idx]
    dec = pd.read_pickle(HERE / "data" / f"{bench}_decisions.pkl")
    asp = dec.drop_duplicates("pair_id").set_index("pair_id")
    a, b = it.resp_a.fillna("").astype(str), it.resp_b.fillna("").astype(str)
    v = TfidfVectorizer(min_df=2, sublinear_tf=True).fit(pd.concat([a, b]))
    sim = np.asarray(v.transform(a).multiply(v.transform(b)).sum(1)).ravel()
    la, lb = a.str.len(), b.str.len()

    def cnt(s, pat):
        return s.str.count(pat)
    f = pd.DataFrame(index=idx)
    f["sim"] = sim
    f["len_gap"] = np.abs(np.log1p(la) - np.log1p(lb)).values
    f["len_total"] = np.log1p(la + lb).values
    gold_first = it.gold.values == 1
    f["longer_is_better"] = np.where(la.values >= lb.values, gold_first, ~gold_first).astype(int)
    for name, pat in [("headers", r"(?m)^#+ "), ("bullets", r"(?m)^\s*[-*•] "), ("tables", r"\|"),
                      ("code", r"```")]:
        f[f"{name}_gap"] = np.abs(cnt(a, pat) - cnt(b, pat)).values
    na, nb = a.apply(lambda s: len(NUM.findall(s))), b.apply(lambda s: len(NUM.findall(s)))
    f["nums_gap"] = np.abs(np.log1p(na) - np.log1p(nb)).values
    f["hedge_gap"] = (a.apply(lambda s: len(HEDGE.findall(s))) - b.apply(lambda s: len(HEDGE.findall(s)))).abs().values
    f["conf_gap"] = (a.apply(lambda s: len(CONF.findall(s))) - b.apply(lambda s: len(CONF.findall(s)))).abs().values
    # final number agreement (last number in each answer)
    last = lambda s: (NUM.findall(s) or [None])[-1]
    f["same_final_number"] = [int(x is not None and x == y) for x, y in zip(a.map(last), b.map(last))]
    f["q_len"] = np.log1p(it.question.fillna("").astype(str).str.len()).values
    for c in ["knowledge", "reasoning", "constraints", "open_endedness", "context_load", "risk"]:
        if c in asp.columns:
            f[c] = pd.to_numeric(asp.loc[idx, c], errors="coerce").values
    votes = it.votes
    if votes.notna().any() and votes.dropna().map(len).max() > 1:
        def margin(v):
            if not isinstance(v, (list, np.ndarray)) or len(v) < 2:
                return np.nan
            k = sum(x == "first" for x in v)
            return abs(2 * k - len(v)) / len(v)
        f["human_margin"] = votes.map(margin).values
    f["group"] = it.group.astype(str).values
    f["category"] = it.category.astype(str).values
    f = f.fillna(f.median(numeric_only=True))
    return f


# ----------------------------------------------------------------------------- helpers
def cv_pred(X, y, g, seeds=5):
    """Out-of-fold probabilities averaged over seeds (5x grouped 5-fold)."""
    P = np.zeros(len(y))
    ug = np.unique(g)
    for s in range(seeds):
        perm = dict(zip(np.random.default_rng(s).permutation(ug), np.arange(len(ug)) % 5))
        fold = np.array([perm[x] for x in g])
        p = np.zeros(len(y))
        for k in range(5):
            tr, te = fold != k, fold == k
            if y[tr].sum() < 3:
                p[te] = y[tr].mean()
                continue
            m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=0.5)).fit(X[tr], y[tr])
            p[te] = m.predict_proba(X[te])[:, 1]
        P += p / seeds
    return P


def boot_gain(y, p0, p1, g, n=2000):
    """Bootstrap over question groups: AUROC(p1) - AUROC(p0)."""
    ug = np.unique(g)
    idx = {u: np.where(g == u)[0] for u in ug}
    d = []
    for _ in range(n):
        s = np.concatenate([idx[u] for u in RNG.choice(ug, len(ug))])
        if y[s].sum() and (1 - y[s]).sum():
            d.append(auroc(y[s], p1[s]) - auroc(y[s], p0[s]))
    return float(auroc(y, p1) - auroc(y, p0)), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def boot_auc(y, p, g, n=2000):
    ug = np.unique(g)
    idx = {u: np.where(g == u)[0] for u in ug}
    d = []
    for _ in range(n):
        s = np.concatenate([idx[u] for u in RNG.choice(ug, len(ug))])
        if y[s].sum() and (1 - y[s]).sum():
            d.append(auroc(y[s], p[s]))
    return float(auroc(y, p)), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def catch_at_rate(score, y, rate):
    """Share of positives in the top `rate` fraction by score (ties broken at random)."""
    s = score + RNG.uniform(0, 1e-6, len(score))
    k = max(1, int(round(rate * len(s))))
    top = np.argsort(-s)[:k]
    return float(y[top].sum() / max(y.sum(), 1))


# ----------------------------------------------------------------------------- analyses
def run(bench):
    df, target, J = load(bench)
    others = [j for j in J if j != target]
    F = features(bench, df.index)
    F.to_csv(OUT / f"features_{bench}.csv")
    cons = df.t_flip == 0
    d, f = df[cons], F[cons]
    y = d.t_conf_err.values.astype(int)
    g = f.group.values
    ctrl_cols = [c for c in f.columns if c not in ("group", "category")]
    Xc = pd.get_dummies(f[ctrl_cols + ["category"]], columns=["category"], drop_first=True).values.astype(float)
    res = dict(bench=bench, target=target, n_pairs=int(len(df)), n_consistent=int(cons.sum()),
               n_conf_err=int(y.sum()), conf_err_rate=float(y.mean()))

    # A1 controls vs controls + flips
    p_c = cv_pred(Xc, y, g)
    p_cf = cv_pred(np.c_[Xc, d.n_flip.values], y, g)
    p_f = d.n_flip.values.astype(float)            # single counts are scored directly (no model needed)
    res["A1"] = dict(controls=boot_auc(y, p_c, g), flips=boot_auc(y, p_f, g), controls_plus_flips=boot_auc(y, p_cf, g),
                     gain=boot_gain(y, p_c, p_cf, g))
    # univariate control AUROCs (sign-free) for the write-up
    uni = {}
    for c in ctrl_cols:
        a = auroc(y, f[c].values)
        uni[c] = float(max(a, 1 - a)) if not np.isnan(a) else np.nan
    res["A1"]["control_univariate"] = dict(sorted(uni.items(), key=lambda kv: -np.nan_to_num(kv[1]))[:6])
    res["A1"]["flip_vs_controls_corr"] = {c: float(np.corrcoef(d.n_flip, f[c])[0, 1]) for c in
                                          ["sim", "len_gap", "same_final_number", "human_margin"] if c in f}

    # A2 matched (strata: len_gap tercile x sim tercile x category), Mantel-Haenszel risk difference
    st = (pd.qcut(f.len_gap.rank(method="first"), 3, labels=False).astype(str) + "|" +
          pd.qcut(f.sim.rank(method="first"), 3, labels=False).astype(str) + "|" + f.category)
    hi = (d.n_flip >= 2).astype(int)
    num = den = 0.0
    rows = []
    for s, idx in d.groupby(st).groups.items():
        h, yy = hi.loc[idx].values, d.loc[idx, "t_conf_err"].values
        n1, n0 = h.sum(), (1 - h).sum()
        if n1 == 0 or n0 == 0:
            continue
        w = n1 * n0 / (n1 + n0)
        num += w * (yy[h == 1].mean() - yy[h == 0].mean())
        den += w
        rows.append((n1, n0))
    res["A2"] = dict(mh_risk_diff=float(num / den) if den else np.nan, strata_used=len(rows),
                     raw_low=float(d.t_conf_err[hi == 0].mean()), raw_high=float(d.t_conf_err[hi == 1].mean()),
                     share_high=float(hi.mean()))

    # A3 flips vs consistent disagreement vs pooled agreement
    p_dis = d.n_dis.values.astype(float)
    p_both = cv_pred(d[["n_dis", "n_flip"]].values.astype(float), y, g)
    p_eu = d.eu.values
    p_all = cv_pred(np.c_[Xc, d.n_dis.values, d.n_flip.values], y, g)
    p_cd = cv_pred(np.c_[Xc, d.n_dis.values], y, g)
    res["A3"] = dict(disagree=boot_auc(y, p_dis, g), flips=res["A1"]["flips"], pooled_agreement=boot_auc(y, p_eu, g),
                     disagree_plus_flips=boot_auc(y, p_both, g), gain_flips_over_disagree=boot_gain(y, p_dis, p_both, g),
                     controls_disagree=boot_auc(y, p_cd, g), controls_disagree_flips=boot_auc(y, p_all, g),
                     gain_flips_over_controls_disagree=boot_gain(y, p_cd, p_all, g),
                     corr_flip_dis=float(np.corrcoef(d.n_flip, d.n_dis)[0, 1]))
    for rate in (0.10, 0.18, 0.30):
        res["A3"][f"catch@{int(rate * 100)}"] = dict(flips=catch_at_rate(d.n_flip.values.astype(float), y, rate),
                                                     disagree=catch_at_rate(d.n_dis.values.astype(float), y, rate),
                                                     both=catch_at_rate(p_both, y, rate),
                                                     controls_all=catch_at_rate(p_all, y, rate))

    # A5 sibling pairs
    if f.group.value_counts().max() > 1:
        allf = F.copy()
        allf["n_flip"] = df.n_flip
        sib = allf.groupby("group").n_flip.transform(lambda s: (s.sum() - s) / max(len(s) - 1, 1))
        has = allf.groupby("group").n_flip.transform("size") > 1
        m = cons & has
        yy = df.t_conf_err[m].values.astype(int)
        gg = F.group[m].values
        res["A5"] = dict(n=int(m.sum()), same_pair=boot_auc(yy, df.n_flip[m].values.astype(float), gg),
                         sibling_pairs=boot_auc(yy, sib[m].values, gg),
                         both=boot_auc(yy, cv_pred(np.c_[df.n_flip[m].values, sib[m].values], yy, gg), gg))

    # A6 solvability (BFF pairwise only)
    if bench == "bffpair":
        G = pd.DataFrame([json.loads(l) for l in open(HERE.parent / "tinker_pool/bff_results/grades.jsonl")])
        S = G.pivot_table(index=["model", "item", "turn"], columns="grader", values="correct")
        solved = ((S.min(1) == 1).astype(float).where(S.min(1).eq(S.max(1))))   # NaN when graders disagree
        it = pd.read_pickle(HERE / "data" / "bffpair_items.pkl").drop_duplicates("pair_id").set_index("pair_id")
        qk = it.question_key.loc[df.index].str.rsplit("-t", n=1, expand=True)
        uid, turn = qk[0].values, qk[1].astype(int).values
        sol = pd.DataFrame({j: [solved.get((j, u, t), np.nan) for u, t in zip(uid, turn)] for j in J}, index=df.index)
        rows = []
        w = pair_table(bench, "none")
        flp = w.pivot_table(index="pair_id", columns="judge", values="flip").loc[df.index]
        for j in J:
            m = sol[j].notna()
            rows.append(dict(judge=j, solved_share=float(sol[j][m].mean()),
                             flip_if_solved=float(flp[j][m & (sol[j] == 1)].mean()),
                             flip_if_unsolved=float(flp[j][m & (sol[j] == 0)].mean())))
        n_solved = sol[J].sum(1, min_count=1)
        tgt_solved = sol[target]
        m = cons & tgt_solved.notna()
        res["A6"] = dict(per_judge=rows,
                         target_err_if_target_solved=float(df.t_conf_err[m & (tgt_solved == 1)].mean()),
                         target_err_if_target_unsolved=float(df.t_conf_err[m & (tgt_solved == 0)].mean()),
                         n_target_solved=int((m & (tgt_solved == 1)).sum()), n_target_unsolved=int((m & (tgt_solved == 0)).sum()),
                         corr_flips_vs_n_solved=float(pd.concat([df.n_flip, n_solved], axis=1).dropna().corr().iloc[0, 1]))

    # A7 leave-one-judge-out difficulty; human split prediction
    w = pair_table(bench, "none")
    flp = w.pivot_table(index="pair_id", columns="judge", values="flip").loc[df.index, J]
    cwj = w.pivot_table(index="pair_id", columns="judge", values="cons_wrong").loc[df.index, J]
    errj = w.pivot_table(index="pair_id", columns="judge", values="err").loc[df.index, J]
    lo = []
    for h in J:
        rest = [j for j in J if j != h]
        m = flp[h] == 0
        yy = cwj[h][m].values.astype(int)
        if yy.sum() < 5:
            continue
        lo.append(dict(judge=h, flips_of_others=auroc(yy, flp.loc[m, rest].sum(1).values),
                       errors_of_others_labelled=auroc(yy, errj.loc[m, rest].sum(1).values)))
    res["A7"] = dict(leave_one_out=lo,
                     mean_flips=float(np.mean([r["flips_of_others"] for r in lo])),
                     mean_labelled=float(np.mean([r["errors_of_others_labelled"] for r in lo])))
    if "human_margin" in F and F.human_margin.nunique() > 1:
        split = (F.human_margin < 1).astype(int).values      # not unanimous
        res["A7"]["human_split"] = dict(share_split=float(split.mean()),
                                        flips_all8=auroc(split, flp.sum(1).values),
                                        errors_all8_labelled=auroc(split, errj.sum(1).values))

    # A9 checker sets chosen on training folds (any selected checker flips or disagrees -> flag)
    ug = np.unique(g)
    perm = dict(zip(np.random.default_rng(1).permutation(ug), np.arange(len(ug)) % 5))
    fold = np.array([perm[x] for x in g])
    flagmat = {j: ((d[f"flip_{j}"] == 1) | (d[f"dis_{j}"] == 1)).astype(int).values for j in others}
    sel_log, tp = [], []
    res["A9"] = {}
    for size in (1, 2, 3):
        caught = flagged = 0
        chosen_sets = []
        for k in range(5):
            tr, te = fold != k, fold == k
            S, best_set = [], None
            for _ in range(size):
                best, bs = None, -1
                for j in others:
                    if j in S:
                        continue
                    fl_ = np.max([flagmat[x][tr] for x in S + [j]], axis=0)
                    yt = y[tr]
                    tpr, fpr = fl_[yt == 1].mean(), fl_[yt == 0].mean()
                    sc = tpr - fpr                                     # Youden: catches minus false alarms
                    if sc > bs:
                        best, bs = j, sc
                S.append(best)
            fl_te = np.max([flagmat[x][te] for x in S], axis=0)
            caught += fl_te[y[te] == 1].sum()
            flagged += fl_te.sum()
            chosen_sets.append(S)
        rate = flagged / len(y)
        res["A9"][f"{size}_checkers"] = dict(flag_rate=float(rate), caught=float(caught / max(y.sum(), 1)),
                                             pooled_flips_same_rate=catch_at_rate(d.n_flip.values.astype(float), y, rate),
                                             disagree_count_same_rate=catch_at_rate(d.n_dis.values.astype(float), y, rate),
                                             random_same_rate=float(rate),
                                             chosen=[list(s) for s in chosen_sets])

    # floor: confident errors that no other judge flags (no flip, no disagreement)
    unflag = (d.n_flip == 0) & (d.n_dis == 0)
    res["floor"] = dict(share_of_conf_errors_unflagged=float(unflag[d.t_conf_err == 1].mean()),
                        share_of_all_errors=float(d.t_conf_err[unflag].sum() / max(d.t_conf_err.sum(), 1)),
                        n=int((unflag & (d.t_conf_err == 1)).sum()))
    return res


def fmt_ci(t):
    return f"{t[0]:.2f} [{t[1]:.2f}, {t[2]:.2f}]"


def report(R):
    L = ["# Stage A results: order flips and the best judge's confident errors", "",
         "Stored verdicts, no new calls. Target = best judge per benchmark; outcome = its confident error (wrong in both "
         "orders) on pairs where it is consistent. AUROC with 95% bootstrap CI over question groups; models are "
         "out-of-fold (5x grouped 5-fold).", ""]
    for r in R:
        L += [f"## {r['bench']} (best judge {r['target']}; {r['n_consistent']} consistent pairs, "
              f"{r['n_conf_err']} confident errors = {100 * r['conf_err_rate']:.1f}%)", ""]
        a1, a3 = r["A1"], r["A3"]
        L += ["| Signal | AUROC |", "|---|---|",
              f"| Controls only | {fmt_ci(a1['controls'])} |", f"| Others' flip count | {fmt_ci(a1['flips'])} |",
              f"| Controls + flips | {fmt_ci(a1['controls_plus_flips'])} |",
              f"| Others' consistent disagreement | {fmt_ci(a3['disagree'])} |",
              f"| Pooled agreement score | {fmt_ci(a3['pooled_agreement'])} |",
              f"| Disagreement + flips | {fmt_ci(a3['disagree_plus_flips'])} |",
              f"| Controls + disagreement + flips | {fmt_ci(a3['controls_disagree_flips'])} |", "",
              f"- A1 gain from flips over controls: {fmt_ci(a1['gain'])}. Top single controls: " +
              ", ".join(f"{k} {v:.2f}" for k, v in a1["control_univariate"].items()) + ".",
              f"- A3 gain from flips over disagreement: {fmt_ci(a3['gain_flips_over_disagree'])}; over controls + "
              f"disagreement: {fmt_ci(a3['gain_flips_over_controls_disagree'])}. corr(flips, disagreement) = "
              f"{a3['corr_flip_dis']:+.2f}.",
              f"- A2 matched: error rate {100 * r['A2']['raw_low']:.1f}% with 0–1 flips vs {100 * r['A2']['raw_high']:.1f}% "
              f"with ≥ 2 flips; within strata the difference is {100 * r['A2']['mh_risk_diff']:+.1f} pts "
              f"({r['A2']['strata_used']} strata).",
              "- Errors caught at a fixed flag rate (flips / disagreement / both / controls + both): " +
              "; ".join(f"{k.split('@')[1]}% → {100 * v['flips']:.0f} / {100 * v['disagree']:.0f} / "
                        f"{100 * v['both']:.0f} / {100 * v['controls_all']:.0f}%"
                        for k, v in a3.items() if k.startswith("catch@")) + "."]
        if "A5" in r:
            L.append(f"- A5 same pair vs sibling pairs of the same question: {fmt_ci(r['A5']['same_pair'])} vs "
                     f"{fmt_ci(r['A5']['sibling_pairs'])}; both {fmt_ci(r['A5']['both'])} (n = {r['A5']['n']}).")
        if "A6" in r:
            a6 = r["A6"]
            fl = "; ".join(f"{x['judge']} {100 * x['flip_if_solved']:.0f}% vs {100 * x['flip_if_unsolved']:.0f}%"
                           for x in a6["per_judge"])
            L.append(f"- A6 flip rate when the judge solved vs did not solve the question: {fl}. Target's confident-error "
                     f"rate: {100 * a6['target_err_if_target_solved']:.1f}% when it solved the question "
                     f"(n={a6['n_target_solved']}) vs {100 * a6['target_err_if_target_unsolved']:.1f}% when it did not "
                     f"(n={a6['n_target_unsolved']}). corr(others' flips, judges that solved) = {a6['corr_flips_vs_n_solved']:+.2f}.")
        a7 = r["A7"]
        L.append(f"- A7 leave-one-judge-out, mean AUROC for a held-out judge's confident errors: others' flips "
                 f"{a7['mean_flips']:.2f} vs others' labelled errors {a7['mean_labelled']:.2f}.")
        if "human_split" in a7:
            h = a7["human_split"]
            L.append(f"- A7 human split ({100 * h['share_split']:.0f}% of pairs): AUROC flips {h['flips_all8']:.2f}, "
                     f"labelled errors {h['errors_all8_labelled']:.2f}.")
        L.append("- A9 checkers chosen on training folds (flag if a checker flips or disagrees): " + "; ".join(
            f"{k.split('_')[0]} → flag {100 * v['flag_rate']:.0f}%, catch {100 * v['caught']:.0f}% "
            f"(pooled flips {100 * v['pooled_flips_same_rate']:.0f}%, disagreement {100 * v['disagree_count_same_rate']:.0f}%, "
            f"random {100 * v['random_same_rate']:.0f}%)" for k, v in r["A9"].items()) + ".")
        L += [f"- Floor: {100 * r['floor']['share_of_conf_errors_unflagged']:.0f}% of the confident errors "
              f"(n = {r['floor']['n']}) have no other judge flipping or disagreeing.", ""]
    return "\n".join(L)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    R = [run(b) for b in (sys.argv[1:] or BENCHES)]
    (OUT / "stage_a.json").write_text(json.dumps(R, indent=1, default=float))
    txt = report(R)
    (OUT / "stage_a.md").write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
