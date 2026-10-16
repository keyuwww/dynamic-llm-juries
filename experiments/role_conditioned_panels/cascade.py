"""Cheap-first cascade, simulated from saved verdicts (no new API calls).

Per split: the escalation judge E = best single judge on fit U val. Tier 0 = the k cheapest judges other than E.
If all tier-0 judges agree, accept their verdict; otherwise take E's verdict. Cost per item = tier-0 prices + E's
price only on escalated items. Compared with static top-3 and best single (both re-picked per split)."""
import argparse, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit import baseline_predictions
from cost_ci import boot, per_question
from data import load_judgments
from splits import make_3way_splits

ap = argparse.ArgumentParser()
ap.add_argument("--bff", required=True); ap.add_argument("--rb2", required=True)
a = ap.parse_args(); pd.set_option("display.width", 220)
rows = []
for label, path, bench, cond in [("BFF none", a.bff, "bff", "none"), ("BFF human", a.bff, "bff", "human"), ("RB2 safety", a.rb2, "rb2safety", "none")]:
    d = load_judgments(path, bench, condition=cond)
    Z, Y = d.Z, d.Y; cost = np.array([d.cost[j] for j in d.judge_names]); G = d.groups.max() + 1
    pooled, pcost, esc = {}, {}, {}
    for fit, val, test in make_3way_splits(d.groups, 0, 20):
        sel = np.concatenate([fit, val]); y = Y[test]
        acc = (Z[sel] == Y[sel][:, None]).mean(0); E = int(np.argmax(acc))
        others = [j for j in np.argsort(cost) if j != E]
        strat = {k: (v[0], v[1]) for k, v in baseline_predictions(Z, Y, sel, test, cost).items() if k in ("best_single", "static_top3")}
        for k in (2, 3):
            t0 = [int(j) for j in others[:k]]
            agree = (Z[np.ix_(test, t0)].min(1) == Z[np.ix_(test, t0)].max(1))
            v = np.where(agree, Z[test, t0[0]], Z[test, E]); c = cost[t0].sum() + (~agree) * cost[E]
            strat[f"cascade_{k}cheap"] = (v, c); esc.setdefault(f"cascade_{k}cheap", []).append((~agree).mean())
        for n_, (v, c) in strat.items():
            pooled.setdefault(n_, []).append((test, (v == y).astype(int))); pcost.setdefault(n_, []).append((test, np.broadcast_to(c, len(test)).astype(float)))
    t3 = per_question(pooled, pcost, d.groups, "static_top3", G); bs = per_question(pooled, pcost, d.groups, "best_single", G)
    for n_ in ("best_single", "static_top3", "cascade_2cheap", "cascade_3cheap"):
        pq = per_question(pooled, pcost, d.groups, n_, G)
        _, dd, rr, pd_, pr, _ = boot(pq, t3, B=5000)
        _, d2, _, pd2, _, _ = boot(pq, bs, B=5000)
        rows.append(dict(setting=label, strategy=n_, acc=pq[0].sum() / pq[1].sum(), cost=pq[2].sum() / pq[1].sum(),
                         escalated=np.mean(esc[n_]) if n_ in esc else np.nan, vs_top3=pd_, ci_top3=f"[{np.percentile(dd,2.5):+.3f},{np.percentile(dd,97.5):+.3f}]",
                         cost_vs_top3=pr, vs_best=pd2, ci_best=f"[{np.percentile(d2,2.5):+.3f},{np.percentile(d2,97.5):+.3f}]"))
print(pd.DataFrame(rows).round(4).to_string(index=False))
