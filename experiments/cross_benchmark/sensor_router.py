"""Sensor-skill router: pick, per item, the judge whose verdict to trust, using how good each judge is at spotting
the others' errors.

Per item and judge, score = share of the two presentation orders the judge gets right (1, 0.5 = flip, 0). A judge is
"wrong" on an item if score < 1. Doubt = 1 - the judge's stated confidence (confidence run, mean of both orders),
turned into a percentile against the training fold, so no test item affects another's score.

Routers (5 x grouped 5-fold CV by question; everything is fitted on the training fold):
  best        the single most accurate judge on the training fold
  vote        majority of all judges, per order (ties count 0.5)
  self_conf   the judge with the lowest own doubt (classic "trust the most confident judge")
  skill       the user's idea. Skill M[s,t] = AUROC of s's doubt for t's errors. Risk of t on an item =
              skill-weighted mean of the sensors' doubts, weights max(0, M[s,t] - 0.5); a one-variable logistic per t
              turns risk into P(t wrong). Route to the judge with the lowest P(wrong). Two versions: sensors = others
              only (skill_others) and others + the judge itself (skill_all).
  full        the same choice, but P(t wrong) from a logistic on all judges' doubts (learned weights, no skill
              structure); tells us whether the skill matrix adds anything beyond a plain fit
  oracle      any judge right
Every router except best reads all judges' confidence, so it costs about as much as a full jury.
Usage: python sensor_router.py -> results/flips/sensor_router.{json,md}
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from conf_analysis import per_pair, read  # noqa: E402
from order_consistency import SHORT, auroc, pair_table  # noqa: E402

BENCHES = ["bffpair", "judgebench", "alpacafarm", "mtbhuman"]
OUT = HERE / "results" / "flips"


def load(b):
    w = pair_table(b, "none")
    w["score"] = (w.right0 + w.right1) / 2
    S = w.pivot_table(index="pair_id", columns="judge", values="score")
    R0 = w.pivot_table(index="pair_id", columns="judge", values="right0")
    R1 = w.pivot_table(index="pair_id", columns="judge", values="right1")
    t = read("confidence", b)
    C = per_pair(t).pivot_table(index="pair_id", columns="judge", values="stated")
    cost = t.groupby("judge").cost.sum() / t.pair_id.nunique()          # $ per pair, both orders
    J = [j for j in S.columns if j in C.columns]
    idx = S[J].dropna().index.intersection(C[J].dropna().index)
    it = pd.read_pickle(HERE / "data" / f"{b}_items.pkl")
    g = it[it.order == 0].drop_duplicates("pair_id").set_index("pair_id").group.astype(str)
    return S.loc[idx, J], R0.loc[idx, J], R1.loc[idx, J], C.loc[idx, J], g.reindex(idx).fillna("na").values, cost


def doubt(C, tr):
    """1 - percentile of confidence against the training fold, per judge."""
    D = pd.DataFrame(index=C.index, columns=C.columns, dtype=float)
    for j in C.columns:
        ref = np.sort(C[j].values[tr])
        D[j] = 1 - (np.searchsorted(ref, C[j].values, side="left") + np.searchsorted(ref, C[j].values, side="right")) / (2 * len(ref))
    return D


def fit_p(x, y, xt):
    if y.sum() < 3 or y.sum() > len(y) - 3:
        return np.full(len(xt), y.mean())
    x = np.asarray(x).reshape(len(x), -1)
    m = LogisticRegression(max_iter=2000, C=1.0).fit(x, y)
    return m.predict_proba(np.asarray(xt).reshape(len(xt), -1))[:, 1]


def run(b, seeds=5):
    S, R0, R1, C, g, cost = load(b)
    J = list(S.columns)
    W = (S < 1).astype(int)
    n = len(S)
    acc = {k: np.zeros(n) for k in ["best", "vote", "self_conf", "skill_others", "skill_all", "full"]}
    pick = {k: [] for k in ["skill_others", "skill_all", "full", "self_conf"]}
    Ms = []
    vote = ((R0.sum(1) > len(J) / 2) + 0.5 * (R0.sum(1) == len(J) / 2) +
            (R1.sum(1) > len(J) / 2) + 0.5 * (R1.sum(1) == len(J) / 2)).values / 2
    ug = np.unique(g)
    for s in range(seeds):
        perm = dict(zip(np.random.default_rng(s).permutation(ug), np.arange(len(ug)) % 5))
        fold = np.array([perm[x] for x in g])
        for k in range(5):
            tr, te = fold != k, fold == k
            D = doubt(C, tr)
            best = S[tr].mean().idxmax()
            acc["best"][te] += S[best].values[te] / seeds
            acc["vote"][te] += vote[te] / seeds
            ch = D.values[te].argmin(1)
            acc["self_conf"][te] += S.values[te][np.arange(te.sum()), ch] / seeds
            pick["self_conf"] += [J[c] for c in ch]
            M = pd.DataFrame({t: {s_: auroc(W[t].values[tr], D[s_].values[tr]) for s_ in J} for t in J})  # rows s, cols t
            Ms.append(M)
            for name, own in [("skill_others", False), ("skill_all", True)]:
                P = np.zeros((te.sum(), len(J)))
                for i, t in enumerate(J):
                    wts = (M[t] - 0.5).clip(lower=0)
                    if not own:
                        wts[t] = 0
                    risk = (D[J].values @ wts.values) / max(wts.sum(), 1e-9)
                    P[:, i] = fit_p(risk[tr], W[t].values[tr], risk[te])
                ch = P.argmin(1)
                acc[name][te] += S.values[te][np.arange(te.sum()), ch] / seeds
                pick[name] += [J[c] for c in ch]
            P = np.zeros((te.sum(), len(J)))
            for i, t in enumerate(J):
                P[:, i] = fit_p(D.values[tr], W[t].values[tr], D.values[te])
            ch = P.argmin(1)
            acc["full"][te] += S.values[te][np.arange(te.sum()), ch] / seeds
            pick["full"] += [J[c] for c in ch]
    M = sum(Ms) / len(Ms)
    res = {k: float(v.mean()) for k, v in acc.items()}
    res["oracle"] = float((S.max(1)).mean())
    res["n"] = n
    # paired bootstrap over question groups: skill_others - best
    rng = np.random.default_rng(0)
    gi = pd.Series(np.arange(n)).groupby(g).apply(list).tolist()
    diffs = {}
    for k in ["skill_others", "skill_all", "full", "vote", "self_conf"]:
        d = acc[k] - acc["best"]
        bs = [d[np.concatenate([gi[i] for i in rng.integers(0, len(gi), len(gi))])].mean() for _ in range(2000)]
        diffs[k] = (float(d.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)))
    share = {k: pd.Series(v).map(SHORT).value_counts(normalize=True).round(3).to_dict() for k, v in pick.items()}
    return dict(bench=b, acc=res, gain_vs_best=diffs, pick_share=share,
                skill=M.rename(index=SHORT, columns=SHORT).round(3).to_dict(),
                cost_per_pair={SHORT[j]: float(cost.get(j, np.nan)) for j in J})


def main():
    R = [run(b) for b in BENCHES]
    (OUT / "sensor_router.json").write_text(json.dumps(R, indent=1))
    L = ["# Sensor-skill router", "",
         "Accuracy = share of presentation orders judged correctly (5x grouped 5-fold CV by question). "
         "Gain = router minus best single judge, 95% CI from a bootstrap over question groups.", ""]
    rows = []
    for r in R:
        a, d = r["acc"], r["gain_vs_best"]
        rows.append(dict(bench=r["bench"], n=a["n"], best=a["best"], vote=a["vote"], self_conf=a["self_conf"],
                         skill_others=a["skill_others"], skill_all=a["skill_all"], full=a["full"], oracle=a["oracle"],
                         **{f"gain_{k}": f"{v[0]:+.3f} [{v[1]:+.3f}, {v[2]:+.3f}]" for k, v in d.items()}))
    L += [pd.DataFrame(rows).round(3).to_markdown(index=False), ""]
    for r in R:
        L += [f"## {r['bench']}", "", "Skill matrix: AUROC of row judge's doubt for column judge's errors", "",
              pd.DataFrame(r["skill"]).T.to_markdown(), "",
              "Who the routers pick: " + json.dumps(r["pick_share"]), "",
              "Cost per pair ($, both orders): " + json.dumps({k: round(v, 5) for k, v in r["cost_per_pair"].items()}), ""]
    (OUT / "sensor_router.md").write_text("\n".join(L))
    print("\n".join(L[:6]))


if __name__ == "__main__":
    main()
