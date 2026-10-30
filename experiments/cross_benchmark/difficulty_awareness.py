"""Do weaker judges sense how hard an item is, and how hard it will be for the expert (best) judge? (no new calls)

Outcome throughout: the best judge is wrong in at least one order (all pairs, stored run). A weaker judge's
"doubt" = its low stated confidence (confidence run, mean of both orders). AUROC 0.5 = chance.

  T1  hard for me vs hard for the expert: AUROC of a weak judge's doubt for the best judge's errors, separately
      on pairs the weak judge got right and on pairs it got wrong (its own correctness held fixed). Also a
      within-benchmark logistic fit: best wrong ~ weak judge wrong + weak judge doubt (standardised).
  T2  expert vs peers: AUROC of a weak judge's doubt for the best judge's errors vs for each other weak judge's
      errors (excluding itself and the best judge).
  T4  within model families (Qwen 4B/9B/35B, gpt-oss 20B/120B, Nemotron Nano/Super): accuracy vs T1.
  T5  independent difficulty: doubt vs (a) leave-two-out difficulty = share of the other 6 judges wrong,
      (b) human vote split (AlpacaFarm, MT-Bench human), (c) BFF solve labels (the best judge / the weak judge
      could not answer the question), (d) controlled BFF pairs: confidence on identical / corrupted / padded vs
      real pairs.
Usage: python difficulty_awareness.py -> results/flips/difficulty_awareness.{json,md}
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from conf_analysis import per_pair, read  # noqa: E402
from flip_analysis import load  # noqa: E402
from order_consistency import POOL, SHORT, auroc, pair_table  # noqa: E402

BENCHES = ["bffpair", "judgebench", "alpacafarm", "mtbhuman"]
FAMILY = {"qwen3.5-4b": "Qwen", "qwen3.5-9b": "Qwen", "qwen3.6-35b-a3b": "Qwen", "gpt-oss-20b": "gpt-oss",
          "gpt-oss-120b": "gpt-oss", "nemotron3-nano-30b": "Nemotron", "nemotron3-super-120b": "Nemotron",
          "deepseek-v3.1": "DeepSeek"}
OUT = HERE / "results" / "flips"


def tables(b):
    """Pairs x judges: wrong (either order, stored), doubt (low confidence, confidence run)."""
    w = pair_table(b, "none")
    wrong = (w.pivot_table(index="pair_id", columns="judge", values="err") > 0).astype(float)
    J = [j for j in POOL if j in wrong.columns]
    wrong = wrong[J].dropna()
    conf = per_pair(read("confidence", b)).pivot_table(index="pair_id", columns="judge", values="stated")
    conf = conf.reindex(wrong.index)[J]
    acc = w.groupby("judge").apply(lambda x: 1 - x.err.sum() / (2 * len(x)))
    return wrong, -conf, acc, J


def logit_fit(y, X):
    """Plain logistic regression (Newton); returns coefficients and Wald p-values."""
    X = np.c_[np.ones(len(y)), X]
    beta = np.zeros(X.shape[1])
    for _ in range(50):
        p = 1 / (1 + np.exp(-X @ beta))
        W = p * (1 - p)
        H = X.T @ (X * W[:, None]) + 1e-8 * np.eye(X.shape[1])
        step = np.linalg.solve(H, X.T @ (y - p))
        beta += step
        if np.abs(step).max() < 1e-8:
            break
    se = np.sqrt(np.diag(np.linalg.inv(H)))
    return beta[1:], 2 * stats.norm.sf(np.abs(beta[1:] / se[1:]))


def solve_labels(index):
    G = pd.DataFrame([json.loads(l) for l in open(HERE.parent / "tinker_pool/bff_results/grades.jsonl")])
    S = G.pivot_table(index=["model", "item", "turn"], columns="grader", values="correct")
    solved = (S.min(1) == 1).astype(float).where(S.min(1).eq(S.max(1)))      # NaN when the two graders disagree
    it = pd.read_pickle(HERE / "data" / "bffpair_items.pkl").drop_duplicates("pair_id").set_index("pair_id")
    qk = it.question_key.reindex(index).str.rsplit("-t", n=1, expand=True)
    return pd.DataFrame({j: [solved.get((j, u, int(t)), np.nan) for u, t in zip(qk[0], qk[1])] for j in POOL},
                        index=index)


def human_split(b, index):
    it = pd.read_pickle(HERE / "data" / f"{b}_items.pkl").drop_duplicates("pair_id").set_index("pair_id")
    def split(v):
        if not isinstance(v, (list, np.ndarray)) or len(v) < 2:
            return np.nan
        k = sum(x == "first" for x in v)
        return float(min(k, len(v) - k) > 0)                      # 1 = annotators did not all agree
    return it.votes.reindex(index).map(split)


def main():
    T1, T2, T5, LOG = [], [], [], []
    for b in BENCHES:
        df, best, _ = load(b)
        wrong, doubt, acc, J = tables(b)
        yb = wrong[best]
        weak = [j for j in J if j != best]
        sol = solve_labels(wrong.index) if b == "bffpair" else None
        hs = human_split(b, wrong.index) if b in ("alpacafarm", "mtbhuman") else None
        for j in weak:
            m = doubt[j].notna()
            r = m & (wrong[j] == 0)
            wj = m & (wrong[j] == 1)
            row = dict(bench=b, judge=j, short=SHORT[j], family=FAMILY[j], acc=float(acc[j]),
                       auc_all=auroc(yb[m].values, doubt[j][m].values),
                       auc_when_right=auroc(yb[r].values, doubt[j][r].values),
                       auc_when_wrong=auroc(yb[wj].values, doubt[j][wj].values),
                       n_right=int(r.sum()), best_err_when_right=float(yb[r].mean()),
                       n_wrong=int(wj.sum()), best_err_when_wrong=float(yb[wj].mean()),
                       p_when_right=float(stats.mannwhitneyu(doubt[j][r & (yb == 1)], doubt[j][r & (yb == 0)],
                                                             alternative="greater").pvalue))
            T1.append(row)
            # T2: errors of each other weak judge
            peers = [k for k in weak if k != j]
            pa = [auroc(wrong[k][m].values, doubt[j][m].values) for k in peers]
            T2.append(dict(bench=b, judge=j, short=SHORT[j], acc=float(acc[j]), auc_best=row["auc_all"],
                           auc_peers=float(np.mean(pa)), auc_peers_min=float(np.min(pa)), auc_peers_max=float(np.max(pa)),
                           auc_stronger_peers=float(np.mean([a for k, a in zip(peers, pa) if acc[k] > acc[j]] or [np.nan])),
                           auc_weaker_peers=float(np.mean([a for k, a in zip(peers, pa) if acc[k] <= acc[j]] or [np.nan]))))
            # T5: independent difficulty
            rest = [k for k in J if k not in (j, best)]
            diff = wrong.loc[m, rest].mean(1)
            t5 = dict(bench=b, judge=j, short=SHORT[j],
                      rho_leave2out=float(stats.spearmanr(doubt[j][m], diff)[0]))
            if hs is not None:
                mh = m & hs.notna()
                t5["auc_human_split"] = auroc(hs[mh].values.astype(int), doubt[j][mh].values)
                t5["n_human_votes"] = int(mh.sum())
            if sol is not None:
                ms = m & sol[best].notna()
                t5["auc_best_unsolved"] = auroc((1 - sol[best][ms]).values.astype(int), doubt[j][ms].values)
                mj = m & sol[j].notna()
                t5["auc_own_unsolved"] = auroc((1 - sol[j][mj]).values.astype(int), doubt[j][mj].values)
            T5.append(t5)
        # within-benchmark logistic: best wrong ~ weak wrong + weak doubt, per weak judge
        for j in weak:
            m = doubt[j].notna()
            z = (doubt[j][m] - doubt[j][m].mean()) / doubt[j][m].std()
            coef, p = logit_fit(yb[m].values, np.c_[wrong[j][m].values, z.values])
            LOG.append(dict(bench=b, judge=j, short=SHORT[j], coef_own_wrong=float(coef[0]), p_own_wrong=float(p[0]),
                            coef_doubt=float(coef[1]), p_doubt=float(p[1])))
    T1, T2, T5, LOG = map(pd.DataFrame, (T1, T2, T5, LOG))

    # T5d: controlled pairs (confidence run), mean confidence per judge and condition, vs real BFF pairs
    items = {o["id"]: o for o in json.load(open(HERE / "data" / "bffctrl_items.json"))}
    t = read("confidence", "bffctrl") if False else pd.DataFrame(
        [json.loads(l) for l in open(HERE / "results" / "confidence" / "bffctrl" / "judgments.jsonl")])
    t["condition"] = t.item_id.map(lambda i: items[i]["condition"])
    real = pd.DataFrame([json.loads(l) for l in open(HERE / "results" / "confidence" / "bffpair" / "judgments.jsonl")])
    ctrl = t.groupby(["judge", "condition"]).conf.mean().unstack()
    ctrl["real"] = real.groupby("judge").conf.mean()
    ctrl.index = ctrl.index.map(SHORT)

    # pooled summaries
    s = {}
    s["T1_mean_auc_all"] = float(T1.auc_all.mean())
    s["T1_mean_auc_when_right"] = float(T1.auc_when_right.mean())
    s["T1_mean_auc_when_wrong"] = float(T1.auc_when_wrong.mean())
    s["T1_points_right_above_0_6"] = int((T1.auc_when_right > 0.6).sum())
    s["T1_points_right_p05"] = int((T1.p_when_right < 0.05).sum())
    s["T1_n_points"] = int(len(T1))
    s["T1_sign_test_right_gt_0_5_p"] = float(stats.binomtest(int((T1.auc_when_right > 0.5).sum()), len(T1), 0.5,
                                                             alternative="greater").pvalue)
    s["LOG_doubt_positive_p05"] = int(((LOG.coef_doubt > 0) & (LOG.p_doubt < 0.05)).sum())
    s["LOG_median_coef_doubt"] = float(LOG.coef_doubt.median())
    d = T2.auc_best - T2.auc_peers
    s["T2_mean_best_minus_peers"] = float(d.mean())
    s["T2_wilcoxon_p"] = float(stats.wilcoxon(d).pvalue)
    s["T2_share_best_higher"] = float((d > 0).mean())
    s["T5_mean_rho_leave2out"] = float(T5.rho_leave2out.mean())
    for c in ["auc_human_split", "auc_best_unsolved", "auc_own_unsolved"]:
        if c in T5:
            s[f"T5_mean_{c}"] = float(T5[c].mean())
    # T4: within families, rank correlation of accuracy and auc_when_right per benchmark (families with >= 2)
    fam = []
    for (b, f), g in T1.groupby(["bench", "family"]):
        if len(g) >= 2:
            g = g.sort_values("acc")
            fam.append(dict(bench=b, family=f, judges=" < ".join(g.short), acc=" < ".join(f"{100 * a:.0f}" for a in g.acc),
                            auc_all=" → ".join(f"{a:.2f}" for a in g.auc_all),
                            auc_when_right=" → ".join(f"{a:.2f}" for a in g.auc_when_right),
                            increasing=bool(np.all(np.diff(g.auc_all.values) > 0))))
    T4 = pd.DataFrame(fam)
    s["T4_increasing_share"] = float(T4.increasing.mean())

    res = dict(summary=s, T1=T1.to_dict(orient="records"), T2=T2.to_dict(orient="records"), T4=T4.to_dict(orient="records"),
               T5=T5.to_dict(orient="records"), LOG=LOG.to_dict(orient="records"), T5_ctrl=ctrl.round(2).to_dict())
    (OUT / "difficulty_awareness.json").write_text(json.dumps(res, indent=1, default=float))
    r3 = lambda x: x.round(3)
    L = ["# Do weaker judges sense how hard an item is for the expert? (no new calls)", "",
         "Outcome: the best judge is wrong in at least one order (all pairs). Doubt = a weaker judge's low stated "
         "confidence. AUROC 0.5 = chance. 28 judge-benchmark points (7 weaker judges x 4 benchmarks).", "",
         "## Summary", "", "\n".join(f"- {k}: {v:.3f}" if isinstance(v, float) else f"- {k}: {v}" for k, v in s.items()), "",
         "## T1. Hard for me vs hard for the expert", "",
         r3(T1.drop(columns=["judge", "family"])).to_markdown(index=False), "",
         "Logistic, within benchmark: best wrong ~ weak judge wrong + weak judge doubt (z-scored)", "",
         r3(LOG.drop(columns=["judge"])).to_markdown(index=False), "",
         "## T2. Expert vs peers", "", r3(T2.drop(columns=["judge"])).to_markdown(index=False), "",
         "## T4. Within model families (sorted by accuracy)", "", T4.to_markdown(index=False), "",
         "## T5. Independent difficulty measures", "", r3(T5.drop(columns=["judge"])).to_markdown(index=False), "",
         "Controlled BFF pairs: mean stated confidence by condition (real = real BFF pairs)", "",
         ctrl.round(1).to_markdown(), ""]
    (OUT / "difficulty_awareness.md").write_text("\n".join(L))
    print("\n".join(L[:8]))


if __name__ == "__main__":
    main()
