#!/usr/bin/env python
"""Does the probe's P(judge correct) improve routing? Uses the held-out scores from `probe_analysis.py --save-scores`
(each item scored by a probe that never saw its question) and the saved verdicts.

Policies (accuracy = verdict matches the human label; cost = $/item at list price):
  single judge j            every item goes to j
  static top-3 vote         the 3 most accurate judges, majority vote (chosen on all items, so slightly favourable to this baseline)
  probe-routed              each item goes to argmax_j  alpha*P_j - (1-alpha)*price_j/max_price   (IRT-Router's cost-aware rule)
  shuffled-score control    same rule, but each judge's scores are shuffled across items -> the accuracy/cost you get from the
                            same *kind* of routing with no information about the item (what 'random' means here)
Reports a paired question-bootstrap 95% CI for (probe-routed minus control) and (probe-routed minus the best single judge)."""
import argparse, os, sys
import numpy as np, pandas as pd
here = os.path.dirname(os.path.abspath(__file__)); rc = os.path.join(here, "..", "role_conditioned_panels")
sys.path.insert(0, rc)
from data import load_judgments
from audit import match_matrix

ALPHAS = [1.0, 0.9, 0.8, 0.65, 0.5, 0.35, 0.2]


def route(P, price, alpha):
    return np.argmax(alpha * P - (1 - alpha) * (price / price.max())[None, :], axis=1)


def vote(Z, js):
    return (Z[:, js].sum(1) * 2 > len(js)).astype(int)            # strict majority of 3 -> never a tie


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judgments", required=True); ap.add_argument("--bench", choices=["bff", "rb2safety"], required=True)
    ap.add_argument("--scores", required=True); ap.add_argument("--n-boot", type=int, default=2000); ap.add_argument("--n-shuffle", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0); ap.add_argument("--out")
    a = ap.parse_args(); pd.set_option("display.width", 200)
    d = load_judgments(a.judgments, a.bench, condition="none")
    S = pd.read_csv(a.scores).set_index("item_id").loc[d.item_ids]
    J = list(d.judge_names); P = S[[f"p_{j}" for j in J]].values; groups = S["group"].astype(str).values
    C = match_matrix(d.Z, d.Y).astype(float); price = np.array([d.cost[j] for j in J]); n = len(C)
    assert (C == S[[f"ok_{j}" for j in J]].values).all(), "correctness in the score file disagrees with the saved verdicts"
    acc = C.mean(0); top3 = list(np.argsort(-acc)[:3]); best = int(np.argmax(acc)); rng = np.random.default_rng(a.seed)
    print(f"{a.bench}: {n} items, {len(np.unique(groups))} questions.  best single = {J[best]} ({acc[best]:.3f}), top-3 = {[J[i] for i in top3]}")

    top3_ok = (vote(d.Z, top3) == d.Y).astype(float); top3_cost = price[top3].sum()
    ug = np.unique(groups); idx_by_g = {g: np.where(groups == g)[0] for g in ug}
    boots = [np.concatenate([idx_by_g[g] for g in rng.choice(ug, len(ug))]) for _ in range(a.n_boot)]

    rows = []
    for j in range(len(J)):
        rows.append(dict(policy=f"single: {J[j]}", alpha=np.nan, acc=acc[j], cost=price[j]))
    rows.append(dict(policy="static top-3 vote", alpha=np.nan, acc=top3_ok.mean(), cost=top3_cost))
    detail = {}
    for al in ALPHAS:
        ch = route(P, price, al); ok = C[np.arange(n), ch]; cost = price[ch]
        ctl_ok, ctl_cost = [], []
        for _ in range(a.n_shuffle):                                 # shuffle each judge's scores across items
            Ps = np.column_stack([rng.permutation(P[:, k]) for k in range(P.shape[1])]); c2 = route(Ps, price, al)
            ctl_ok.append(C[np.arange(n), c2]); ctl_cost.append(price[c2])
        ctl_ok = np.mean(ctl_ok, 0); ctl_cost = np.mean(ctl_cost, 0)
        d_ctl = np.array([ok[b].mean() - ctl_ok[b].mean() for b in boots]); d_best = np.array([ok[b].mean() - C[b, best].mean() for b in boots])
        d_top3 = np.array([ok[b].mean() - top3_ok[b].mean() for b in boots])
        ci = lambda x: f"{x.mean() - 0:+.3f} [{np.percentile(x, 2.5):+.3f},{np.percentile(x, 97.5):+.3f}]"
        rows.append(dict(policy="probe-routed", alpha=al, acc=ok.mean(), cost=cost.mean()))
        rows.append(dict(policy="shuffled control", alpha=al, acc=ctl_ok.mean(), cost=ctl_cost.mean()))
        detail[al] = (ci(d_ctl), ci(d_best), ci(d_top3), np.bincount(ch, minlength=len(J)) / n)
    R = pd.DataFrame(rows); print("\n", R.round(4).to_string(index=False))
    print("\nPaired question-bootstrap differences in accuracy (mean [95% CI]):")
    print(f"{'alpha':>6} | {'probe - shuffled control':>26} | {'probe - best single':>26} | {'probe - top-3 vote':>26}")
    for al, (c1, c2, c3, _) in detail.items():
        print(f"{al:>6} | {c1:>26} | {c2:>26} | {c3:>26}")
    print("\nShare of items sent to each judge, by alpha:"); print(pd.DataFrame({al: v[3] for al, v in detail.items()}, index=J).round(2).to_string())
    if a.out:
        R.to_csv(a.out, index=False)


if __name__ == "__main__":
    main()
