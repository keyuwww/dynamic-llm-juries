#!/usr/bin/env python3
"""
Per-benchmark analysis for the cross-benchmark report. For one benchmark it joins items, judge verdicts and
aspect codes into a decisions table and computes, for the 8 Tinker judges without a reference:

  judges      agreement, κ, parse rate, positive / first-pick rate, order consistency (pairs), cost
  labels      vote patterns and κ under unanimous vs majority gold (benchmarks with several human votes)
  errors      pairwise error phi, everyone-right / many-wrong vs independence, the best judge's error profile
  aspects     agreement by aspect level, judge x aspect interaction (permutation by group, BH-corrected)
  candidates  answer-model accuracy by category, oracle vs best, rescue and error phi (answer-labelled sets)
  length      verdicts against response length, given the gold label; position bias for pairs
  juries      top-k vs threshold juries on an out-of-fold reliability predictor (see JURY below)

  uv run python experiments/cross_benchmark/analyze_xb.py --bench mtb --work <folder with tinker_pool/ and cross_benchmark/>
Writes results/<bench>/analysis.json and data/<bench>_decisions.pkl.
"""
import argparse, json, sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
TINKER = ["gpt-oss-120b", "gpt-oss-20b", "deepseek-v3.1", "qwen3.6-35b-a3b", "qwen3.5-9b", "qwen3.5-4b",
          "nemotron3-super-120b", "nemotron3-nano-30b"]
ASPECTS = ["knowledge", "reasoning", "constraints", "open_endedness", "context_load", "risk"]

JUDGMENTS = {  # relative to the work folder
    "bff": ["tinker_pool/bff_results_max4096_majority/judgments.jsonl"],
    "mtb": ["tinker_pool/mtb_results_max4096_majority/judgments.jsonl"],
    "bffpair": ["tinker_pool/bffpair_results_max4096/judgments.jsonl"],
    "safety": ["tinker_pool/safety_results/judgments.jsonl"],
    "bbeh": ["tinker_pool/bbeh_results/judgments.jsonl"],
}
SYSTEM_ONE = {"bff": "jev_bff/{j}_bff_results/items.csv", "safety": "safety_{j}_results/items.csv"}


# ----------------------------------------------------------------------------- helpers
def kappa(y, v):
    y, v = np.asarray(y, float), np.asarray(v, float)
    if len(y) == 0:
        return None
    pe = y.mean() * v.mean() + (1 - y.mean()) * (1 - v.mean())
    return float(((y == v).mean() - pe) / (1 - pe)) if pe < 1 else None


def auroc(y, s):
    y, s = np.asarray(y), np.asarray(s, float)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return None
    r = pd.Series(np.concatenate([pos, neg])).rank().values
    return float((r[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def boot_ci(diff, groups, n=2000, seed=0):
    """95% CI of mean(diff) resampling whole groups."""
    g = pd.Series(diff).groupby(np.asarray(groups))
    sums, cnts = g.sum().values, g.count().values
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(sums), (n, len(sums)))
    m = sums[idx].sum(1) / cnts[idx].sum(1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def bh(p):
    p = np.asarray(p, float)
    o = np.argsort(p)
    q = np.empty_like(p)
    run = 1.0
    for rank, i in reversed(list(enumerate(o, 1))):
        run = min(run, p[i] * len(p) / rank)
        q[i] = run
    return q


def logit(p):
    p = np.clip(p, 1e-3, 1 - 1e-3)
    return np.log(p / (1 - p))


# ----------------------------------------------------------------------------- decisions
def load_judgments(bench, work):
    paths = JUDGMENTS.get(bench, [f"cross_benchmark/results/{bench}/judgments.jsonl"])
    rows = []
    for p in paths:
        p = Path(work) / p
        if not p.exists():
            continue
        for line in open(p):
            r = json.loads(line)
            key = f"{r['item_id']}|{r['examinee']}" if bench in ("bff", "mtb") else r["item_id"]
            share = r.get("vote_share")
            rows.append(dict(key=key, judge=r["judge"], condition=r["condition"],
                             verdict=int((share or 0) > 0.5), parsed=int(r.get("n_parsed", 0) > 0),
                             cost=r.get("cost"), n_out=r.get("n_out"),
                             raw=(r.get("raw") or [""])[0][-1500:] if r.get("raw") else ""))
    d = pd.DataFrame(rows)
    if len(d):
        d = d.drop_duplicates(["key", "judge", "condition"], keep="last")
    return d


def load_system_one(bench, exp):
    out = []
    if bench not in SYSTEM_ONE:
        return pd.DataFrame()
    for j in ["jev", "jeff", "laya", "clm"]:
        f = Path(exp) / SYSTEM_ONE[bench].format(j=j)
        if not f.exists():
            continue
        d = pd.read_csv(f)
        if "cond" not in d:
            d["cond"] = "noref"
        d = d.drop_duplicates(["id", "cond"])
        key = (d.id + "|" + d.examinee) if bench == "bff" else d.id
        out.append(pd.DataFrame(dict(key=key, judge=j, condition=d.cond.map({"noref": "none", "ref": "human"}),
                                     verdict=(d.p >= 0.5).astype(int), parsed=1, cost=np.nan, n_out=np.nan, raw="",
                                     score=d.p)))
    return pd.concat(out) if out else pd.DataFrame()


def decisions(bench, work, exp):
    items = pd.read_pickle(Path(work) / "cross_benchmark/data" / f"{bench}_items.pkl")
    j = load_judgments(bench, work)
    s1 = load_system_one(bench, exp)
    if len(s1):
        j = pd.concat([j, s1], ignore_index=True)
    asp_path = Path(work) / "cross_benchmark/data" / f"{'bff' if bench == 'bffpair' else bench}_aspects.pkl"
    if asp_path.exists():
        asp = pd.read_pickle(asp_path)
        items = items.merge(asp, on="question_key", how="left")
    d = j.merge(items, on="key", how="inner")
    d = d[d.gold.notna()].copy()
    d["gold"] = d.gold.astype(int)
    d["agree"] = (d.verdict == d.gold).astype(int)
    return items, d


# ----------------------------------------------------------------------------- analyses
def judges_table(d):
    out = []
    for j, g in d.groupby("judge"):
        row = dict(judge=j, n=len(g), acc=float(g.agree.mean()), kappa=kappa(g.gold, g.verdict),
                   parse=float(g.parsed.mean()), positive=float(g.verdict.mean()),
                   cost=float(g.cost.mean()) if g.cost.notna().any() else None,
                   tinker=j in TINKER)
        if "score" in g and g.score.notna().any():
            row["auroc"] = auroc(g.gold, g.score)
        if g.fmt.iat[0] == "pair":
            w = g.pivot_table(index="pair_id", columns="order", values="verdict")
            if w.shape[1] == 2:
                # consistent = picks the same response in both orders: verdict o0 = 1 - verdict o1
                row["consistent"] = float((w[0] + w[1] == 1).mean())
                row["first_pick"] = float(g.verdict.mean())
        out.append(row)
    return sorted(out, key=lambda r: -r["acc"])


def wide(d, col="agree", judges=None):
    w = d.pivot_table(index="key", columns="judge", values=col)
    judges = [j for j in (judges or TINKER) if j in w.columns]
    return w[judges].dropna()


def error_structure(d, items_info):
    A = wide(d)
    if A.shape[1] < 3:
        return None
    E = 1 - A
    phi = E.corr()
    tri = phi.values[np.triu_indices(phi.shape[0], 1)]
    k = E.sum(1)
    p = E.mean().values
    rng = np.random.default_rng(0)
    sim = np.concatenate([(rng.random((len(E), len(p))) < p).sum(1) for _ in range(200)])
    best = A.mean().idxmax()
    info = items_info.set_index("key").loc[A.index]
    err = A[best] == 0
    gold = info.gold.astype(int)
    verdict = np.where(err, 1 - gold, gold)
    by_cat = []
    for c, g in info.assign(err=err.values).groupby("category"):
        by_cat.append(dict(category=str(c), n=len(g), errors=int(g.err.sum()), rate=float(g.err.mean())))
    others = E.loc[err, [c for c in E.columns if c != best]].sum(1).value_counts().sort_index()
    qerr = info.assign(err=err.values).groupby("question_key").err.sum()
    by_ex = []
    if info.examinee.nunique() <= 12:
        for c, g in info.assign(err=err.values).groupby("examinee"):
            by_ex.append(dict(examinee=str(c), n=len(g), rate=float(g.err.mean())))
    return dict(judges=list(A.columns), phi=[[None if np.isnan(x) else float(x) for x in r] for r in phi.values],
                phi_mean=float(np.nanmean(tri)), phi_min=float(np.nanmin(tri)), phi_max=float(np.nanmax(tri)),
                n=len(A), all_right_obs=float((k == 0).mean()), all_right_ind=float((sim == 0).mean()),
                many_wrong_obs=float((k >= 6).mean()), many_wrong_ind=float((sim >= 6).mean()),
                hist={int(a): int(b) for a, b in k.value_counts().sort_index().items()},
                best=best, best_errors=int(err.sum()),
                fp=int(((gold == 0) & (verdict == 1)).sum()), fn=int(((gold == 1) & (verdict == 0)).sum()),
                fpr=float(((gold == 0) & (verdict == 1)).sum() / max((gold == 0).sum(), 1)),
                fnr=float(((gold == 1) & (verdict == 0)).sum() / max((gold == 1).sum(), 1)),
                by_category=sorted(by_cat, key=lambda r: -r["n"]), by_examinee=by_ex,
                others_wrong={int(a): int(b) for a, b in others.items()},
                q_with_2plus=int((qerr >= 2).sum()), errors_in_2plus=int(qerr[qerr >= 2].sum()),
                n_questions=int(len(qerr)))


def label_audit(d, items):
    """Benchmarks with several human votes: vote patterns and κ per judge under unanimous vs majority gold."""
    it = items[items.votes.notna()].copy()
    if not len(it):
        return None
    it["pattern"] = it.votes.apply(lambda v: " / ".join(f"{n} {x}" for x, n in sorted(pd.Series(v).value_counts().items())))
    it["n_votes"] = it.votes.apply(len)
    if d.bench.iat[0] in ("bff", "mtb"):
        def unanimous(v):
            return len(set(v)) == 1 and v[0] in ("correct", "incorrect")
    else:
        def unanimous(v):
            s = [x for x in v if x != "tie"]
            return len(v) >= 2 and len(s) == len(v) and len(set(s)) == 1
    it["unanimous"] = it.votes.apply(unanimous)
    keyset = it.drop_duplicates("pair_id" if it.fmt.iat[0] == "pair" else "key")
    pat = keyset.pattern.value_counts()
    nv = keyset.n_votes.value_counts().sort_index()
    rows = []
    dd = d.merge(it[["key", "unanimous"]], on="key")
    for j, g in dd.groupby("judge"):
        u, s = g[g.unanimous], g[~g.unanimous]
        rows.append(dict(judge=j, k_all=kappa(g.gold, g.verdict), n_all=len(g), k_unan=kappa(u.gold, u.verdict),
                         n_unan=len(u), k_split=kappa(s.gold, s.verdict) if len(s) else None, n_split=len(s)))
    return dict(patterns=[dict(pattern=k, n=int(v)) for k, v in pat.items()][:10],
                n_units=int(len(keyset)), no_majority=int(keyset.gold.isna().sum()),
                unanimous_units=int(keyset.unanimous.sum()), votes_per_unit={int(a): int(b) for a, b in nv.items()},
                judges=sorted(rows, key=lambda r: -(r["k_all"] or -9)))


def aspect_analysis(d, n_perm=2000):
    """Judge x aspect-level interaction. Statistic: sum over (judge, level) of n * mean(relative agreement)^2,
    where relative agreement = judge's agreement minus all judges' mean agreement on the same item (difficulty
    cancels). Null: permute aspect levels across questions (all items of a question move together)."""
    if "knowledge" not in d or d.knowledge.isna().all():
        return None
    t = d[d.judge.isin(TINKER) & d.knowledge.notna()].copy()
    if not len(t):
        return None
    t["rel"] = t.agree - t.groupby("key").agree.transform("mean")
    judges = [j for j in TINKER if j in set(t.judge)]
    ji = t.judge.map({j: i for i, j in enumerate(judges)}).values
    qkeys = t.question_key.astype(str).values
    uq, qi = np.unique(qkeys, return_inverse=True)
    rel = t.rel.values
    rng = np.random.default_rng(0)
    out, pvals = [], []
    for a in ASPECTS:
        lv_item = t[a].astype(int).values
        levels = sorted(np.unique(lv_item))
        if len(levels) < 2:
            continue
        qlev = pd.Series(lv_item).groupby(qi).first().reindex(range(len(uq))).values
        nl = 4

        def stat(lev):
            idx = ji * nl + lev
            s = np.bincount(idx, weights=rel, minlength=len(judges) * nl)
            c = np.bincount(idx, minlength=len(judges) * nl)
            return float((s[c > 0] ** 2 / c[c > 0]).sum())
        obs = stat(lv_item)
        null = np.array([stat(qlev[rng.permutation(len(qlev))][qi]) for _ in range(n_perm)])
        p = (np.sum(null >= obs) + 1) / (n_perm + 1)
        cells = {j: {int(l): dict(n=int(((ji == n) & (lv_item == l)).sum()),
                                  acc=float(t.agree.values[(ji == n) & (lv_item == l)].mean()) if ((ji == n) & (lv_item == l)).any() else None)
                     for l in levels} for n, j in enumerate(judges)}
        base = {int(l): int((qlev == l).sum()) for l in levels}
        pvals.append(p)
        out.append(dict(aspect=a, levels=[int(l) for l in levels], items_per_level=base, cells=cells, stat=obs, p=float(p)))
    q = bh(pvals) if pvals else []
    for r, qq in zip(out, q):
        r["q"] = float(qq)
    dist = {a: {int(k): int(v) for k, v in d.drop_duplicates("question_key")[a].dropna().astype(int).value_counts().sort_index().items()}
            for a in ASPECTS if a in d}
    return dict(tests=out, distribution=dist)


def candidates(items, bench):
    """Answer-model outcomes when the gold label is the candidate's own correctness."""
    if bench not in ("bff", "mtb", "bbeh"):
        return None
    it = items[items.gold.notna()].copy()
    it["gold"] = it.gold.astype(int)
    W = it.pivot_table(index="question_key", columns="examinee", values="gold")
    W = W[[m for m in W.columns if W[m].notna().sum() >= 0.95 * W.notna().sum().max()]].dropna()
    if W.shape[1] < 2:
        return None
    acc = W.mean().sort_values(ascending=False)
    best = acc.index[0]
    rescue = []
    for m in W.columns:
        if m == best:
            continue
        miss = W[best] == 0
        rescue.append(dict(model=m, rescues=int(W.loc[miss, m].sum()), of=int(miss.sum())))
    E = 1 - W
    phi = E.corr()
    tri = phi.values[np.triu_indices(phi.shape[0], 1)]
    cat = it.drop_duplicates("question_key").set_index("question_key").category
    by_cat = []
    for c in sorted(cat.loc[W.index].unique()):
        sub = W[cat.loc[W.index] == c]
        by_cat.append(dict(category=str(c), n=len(sub), acc={m: float(sub[m].mean()) for m in W.columns}))
    return dict(n_questions=len(W), acc={m: float(v) for m, v in acc.items()}, best=best,
                oracle=float(W.max(1).mean()), rescue=sorted(rescue, key=lambda r: -r["rescues"]),
                phi_mean=float(np.nanmean(tri)), by_category=by_cat)


def length_analysis(d):
    t = d[d.judge.isin(TINKER)].copy()
    if not len(t) or t.resp_len.isna().all():
        return None
    if t.fmt.iat[0] == "pair":
        t = t[(t.len_a.notna()) & (t.len_b.notna())]
        t["ratio"] = np.log((t.len_a + 1) / (t.len_b + 1))
        t = t[t.ratio.abs() > np.log(1.2)]
        t["longer_first"] = (t.ratio > 0).astype(int)
        t["pick_longer"] = (t.verdict == t.longer_first).astype(int)
        t["gold_longer"] = (t.gold == t.longer_first).astype(int)
        rows = []
        for j, g in t.groupby("judge"):
            rows.append(dict(judge=j, n=len(g), pick_longer=float(g.pick_longer.mean()),
                             human_longer=float(g.gold_longer.mean()),
                             acc_when_longer_better=float(g[g.gold_longer == 1].agree.mean()) if (g.gold_longer == 1).any() else None,
                             acc_when_shorter_better=float(g[g.gold_longer == 0].agree.mean()) if (g.gold_longer == 0).any() else None))
        return dict(kind="pair", rows=sorted(rows, key=lambda r: -r["pick_longer"]))
    t["tercile"] = pd.qcut(t.resp_len.rank(method="first"), 3, labels=["short", "medium", "long"])
    rows = []
    for j, g in t.groupby("judge"):
        r = dict(judge=j)
        for gold, name in [(1, "good"), (0, "bad")]:
            sub = g[g.gold == gold]
            r[name] = {str(k): float(v) for k, v in sub.groupby("tercile", observed=True).verdict.mean().items()}
        rows.append(r)
    return dict(kind="single", rows=rows,
                base={str(k): float(v) for k, v in t.drop_duplicates("key").groupby("tercile", observed=True).gold.mean().items()})


# ----------------------------------------------------------------------------- juries: top-k vs threshold
def features(info):
    """Pre-call features for the reliability predictor: aspect codes, category, response length (pairs: length
    of both and their log ratio), and a 20-dim TF-IDF/SVD summary of the question."""
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    X = []
    if "knowledge" in info and info.knowledge.notna().any():
        X.append(info[ASPECTS].fillna(info[ASPECTS].median()).values)
    cats = pd.get_dummies(info.category.astype(str)).values.astype(float)
    if cats.shape[1] <= 40:
        X.append(cats)
    la = np.log1p(info.len_a.fillna(0).values.astype(float))
    X.append(la[:, None])
    if info.fmt.iat[0] == "pair":
        lb = np.log1p(info.len_b.fillna(0).values.astype(float))
        X.append(np.c_[lb, la - lb])
    txt = info.question.fillna("").astype(str).values
    if len(set(txt)) > 25:
        tf = TfidfVectorizer(min_df=2, max_features=5000, sublinear_tf=True).fit_transform(txt)
        k = min(20, tf.shape[1] - 1)
        if k >= 2:
            X.append(TruncatedSVD(k, random_state=0).fit_transform(tf))
    X = np.hstack(X)
    return (X - X.mean(0)) / (X.std(0) + 1e-9)


TAUS = [0.6, 0.7, 0.8, 0.85, 0.9, 0.95]


def jury_rules(V, P, acc_tr):
    """V: verdicts (n x J), P: predicted P(judge agrees with human) (n x J), acc_tr: train accuracy per judge.
    Returns dict rule -> (verdicts, jury sizes). Votes weighted by logit(p) (Jury-on-Demand style)."""
    n, J = V.shape
    sign = 2 * V - 1
    w = logit(P)
    order = np.argsort(-P, axis=1)
    out = {}
    best = int(np.argmax(acc_tr))
    out["best_single"] = (V[:, best], np.ones(n))
    out["majority_all"] = ((V.mean(1) > 0.5).astype(int), np.full(n, J))
    for k in (1, 3, 5):
        m = np.zeros_like(P, bool)
        np.put_along_axis(m, order[:, :k], True, axis=1)
        out[f"top{k}"] = (((w * sign * m).sum(1) > 0).astype(int), m.sum(1))
    for tau in TAUS:
        m = P >= tau
        empty = ~m.any(1)
        m[empty, order[empty, 0]] = True              # fallback: the single most reliable judge
        out[f"thr{tau}"] = (((w * sign * m).sum(1) > 0).astype(int), m.sum(1), empty)
        # same threshold, capped at 3 members
        mc = m & (np.argsort(order, axis=1) < 3)
        mc[empty, order[empty, 0]] = True
        out[f"thr{tau}_cap3"] = (((w * sign * mc).sum(1) > 0).astype(int), mc.sum(1), empty)
    return out


def jury_experiment(d, items, repeats=5, folds=5, C=0.5):
    from sklearn.linear_model import LogisticRegression
    t = d[d.judge.isin(TINKER)]
    V = wide(t, "verdict")
    if V.shape[1] < 5 or len(V) < 60:
        return None
    A = wide(t, "agree").loc[V.index, V.columns]
    info = items.drop_duplicates("key").set_index("key").loc[V.index].reset_index()
    X = features(info)
    y = info.gold.astype(int).values
    Vm, Am = V.values.astype(int), A.values.astype(int)
    groups = info.group.astype(str).values
    ug = np.unique(groups)
    J = Vm.shape[1]
    res = {}
    P_all = np.zeros((repeats, len(y), J))
    sizes = {}
    for rep in range(repeats):
        rng = np.random.default_rng(rep)
        fold_of = dict(zip(rng.permutation(ug), np.arange(len(ug)) % folds))
        f = np.array([fold_of[g] for g in groups])
        preds = {}
        for k in range(folds):
            tr, te = np.where(f != k)[0], np.where(f == k)[0]
            P = np.zeros((len(te), J))
            for jj in range(J):
                ya = Am[tr, jj]
                if ya.min() == ya.max():
                    P[:, jj] = ya[0]
                    continue
                m = LogisticRegression(C=C, max_iter=2000).fit(X[tr], ya)
                P[:, jj] = m.predict_proba(X[te])[:, 1]
            P_all[rep, te] = P
            rules = jury_rules(Vm[te], P, Am[tr].mean(0))
            for name, val in rules.items():
                v, s = val[0], val[1]
                preds.setdefault(name, (np.zeros(len(y), int), np.zeros(len(y)), np.zeros(len(y), bool)))
                preds[name][0][te] = v
                preds[name][1][te] = s
                if len(val) > 2:
                    preds[name][2][te] = val[2]
        for name, (v, s, e) in preds.items():
            r = res.setdefault(name, dict(acc=[], kap=[], hit=np.zeros(len(y)), size=[], fallback=[]))
            hit = (v == y).astype(float)
            r["acc"].append(hit.mean())
            r["kap"].append(kappa(y, v))
            r["hit"] += hit / repeats
            r["size"].append(s.mean())
            r["fallback"].append(e.mean())
    base = res["best_single"]["hit"]
    rows = []
    for name, r in res.items():
        diff = r["hit"] - base
        rows.append(dict(rule=name, acc=float(np.mean(r["acc"])), kappa=float(np.mean([x for x in r["kap"] if x is not None])),
                         size=float(np.mean(r["size"])), fallback=float(np.mean(r["fallback"])),
                         diff=float(diff.mean()), ci=boot_ci(diff, groups)))
    Pm = P_all.mean(0)
    pred_q = []
    for jj, j in enumerate(V.columns):
        p, a = Pm[:, jj], Am[:, jj]
        bins = np.clip((p * 10).astype(int), 0, 9)
        ece = float(sum(abs(p[bins == b].mean() - a[bins == b].mean()) * (bins == b).mean() for b in range(10) if (bins == b).any()))
        pred_q.append(dict(judge=j, auroc=auroc(a, p), ece=ece, mean_p=float(p.mean()), acc=float(a.mean()),
                           share_above={str(tau): float((p >= tau).mean()) for tau in TAUS}))
    # oracle-informed upper bound: the true agreement used as p (shows what a perfect predictor would allow)
    orc = ((Am * (2 * Vm - 1)).sum(1) > 0) | ((Am.sum(1) == 0) & False)
    oracle_any = float((Am.max(1) == 1).mean())
    return dict(n=len(y), n_groups=len(ug), judges=list(V.columns), rules=rows, predictor=pred_q,
                oracle=oracle_any, features=int(X.shape[1]))


def human_condition(d_all):
    h = d_all[(d_all.condition == "human") & d_all.judge.isin(TINKER)]
    if not len(h):
        return None
    return sorted([dict(judge=j, n=len(g), acc=float(g.agree.mean()), kappa=kappa(g.gold, g.verdict))
                   for j, g in h.groupby("judge")], key=lambda r: -r["acc"])


def examples_of_errors(d, best, n=4):
    """A few of the best judge's errors with its reasoning tail, for the report."""
    e = d[(d.judge == best) & (d.agree == 0)].copy()
    if not len(e):
        return []
    e = e.sample(min(n, len(e)), random_state=0)
    return [dict(category=str(r.category), gold=int(r.gold), verdict=int(r.verdict),
                 question=" ".join(str(r.question).split())[:420], reasoning=" ".join(str(r.raw).split())[-420:])
            for r in e.itertuples()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--exp", default=str(HERE.parent), help="repo experiments/ folder (System One result CSVs)")
    a = ap.parse_args()
    items, d_all = decisions(a.bench, a.work, a.exp)
    out_dir = Path(a.work) / "cross_benchmark/results" / a.bench
    out_dir.mkdir(parents=True, exist_ok=True)
    d_all.to_pickle(Path(a.work) / "cross_benchmark/data" / f"{a.bench}_decisions.pkl")
    d = d_all[d_all.condition == "none"]
    # routing pool = Tinker judges that graded (nearly) every item; a judge missing >5% (e.g. DeepSeek-V3.1 when
    # Tinker timed out) is still listed but left out of every combination, so tables are not cut to its subset
    global TINKER
    cov = d[d.judge.isin(TINKER)].groupby("judge").key.nunique()
    dropped = [j for j in TINKER if j in cov and cov[j] < 0.95 * cov.median()]
    TINKER = [j for j in TINKER if j in cov and j not in dropped]
    # score every judge on the items the whole pool graded (a judge with extra items, e.g. from an earlier
    # run that picked different BBEH answers, would otherwise be scored on a different set)
    common = set.intersection(*[set(d[d.judge == j].key) for j in TINKER])
    d = d[d.key.isin(common)]
    d_all = d_all[d_all.key.isin(common) | (d_all.condition != "none")]
    jt = judges_table(d)
    for r in jt:
        if r["judge"] in dropped:
            r["partial"] = int(cov[r["judge"]])
    es = error_structure(d, items)
    res = dict(bench=a.bench, fmt=str(items.fmt.iat[0]), n_items=int(d.key.nunique()), n_items_all=int(len(items)),
               n_groups=int(d.group.nunique()), base_rate=float(d.drop_duplicates("key").gold.mean()),
               categories={str(k): int(v) for k, v in d.drop_duplicates("key").category.value_counts().items()},
               judges=jt, human_condition=human_condition(d_all), labels=label_audit(d, items), errors=es,
               error_examples=examples_of_errors(d, es["best"]) if es else [],
               aspects=aspect_analysis(d), candidates=candidates(items, a.bench), length=length_analysis(d),
               juries=jury_experiment(d, items), cost=float(d_all.cost.fillna(0).sum()),
               pool=TINKER, dropped_judges={j: int(cov[j]) for j in dropped})
    (out_dir / "analysis.json").write_text(json.dumps(res, indent=1, default=lambda x: None if x is None else float(x)))
    print(json.dumps({k: res[k] for k in ["bench", "n_items", "n_groups", "base_rate"]}))
    for r in jt[:10]:
        print(f"  {r['judge']:22s} acc {r['acc']:.3f}  κ {r['kappa'] if r['kappa'] is None else round(r['kappa'], 3)}  parse {r['parse']:.2f}")
    if res["juries"]:
        for r in res["juries"]["rules"]:
            print(f"  {r['rule']:16s} acc {r['acc']:.3f} size {r['size']:.2f} Δ {r['diff']:+.3f} {r['ci']}")


if __name__ == "__main__":
    main()
