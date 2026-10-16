"""Cascade variants + fresh-seed robustness + cost/accuracy plot. Verdicts only; no new API calls.

Cascade: escalation judge E = best single on fit U val. Tier 0 = k judges other than E, chosen either as the
cheapest ('cheap') or by fit+val accuracy per dollar ('acc/$'). If the larger side of the tier-0 vote has >= m
votes, accept that verdict, else use E's verdict. Cost: tier-0 prices + E's price on escalated items."""
import argparse, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit import baseline_predictions
from cost_ci import boot, per_question
from data import load_judgments
from splits import make_3way_splits

VARIANTS = [(2, 2), (3, 3), (4, 4), (4, 3), (5, 5), (5, 4)]     # (k tier-0 judges, m votes needed to accept)
SELECT = ["cheap", "acc/$"]


def run(d, seed):
    Z, Y = d.Z, d.Y; cost = np.array([d.cost[j] for j in d.judge_names])
    pooled, pcost, esc = {}, {}, {}
    for fit, val, test in make_3way_splits(d.groups, seed, 20):
        sel = np.concatenate([fit, val]); y = Y[test]
        acc = (Z[sel] == Y[sel][:, None]).mean(0); E = int(np.argmax(acc))
        strat = {k: (v[0], v[1]) for k, v in baseline_predictions(Z, Y, sel, test, cost).items()}
        for how in SELECT:
            order = [int(j) for j in (np.argsort(cost) if how == "cheap" else np.argsort(-(acc / cost))) if j != E]
            for k, m in VARIANTS:
                t0 = order[:k]; ones = Z[np.ix_(test, t0)].sum(1); big = np.maximum(ones, k - ones)
                accept = big >= m; maj = (ones * 2 > k).astype(int)
                v = np.where(accept, maj, Z[test, E]); c = cost[t0].sum() + (~accept) * cost[E]
                name = f"{how} k={k} m={m}"; strat[name] = (v, c); esc.setdefault(name, []).append((~accept).mean())
        for n_, (v, c) in strat.items():
            pooled.setdefault(n_, []).append((test, (v == y).astype(int)))
            pcost.setdefault(n_, []).append((test, np.broadcast_to(c, len(test)).astype(float)))
    return pooled, pcost, esc


ap = argparse.ArgumentParser()
ap.add_argument("--bff", required=True); ap.add_argument("--rb2", required=True)
ap.add_argument("--seeds", type=int, nargs="*", default=[1, 2, 3]); a = ap.parse_args()
pd.set_option("display.width", 220); pd.set_option("display.max_rows", 100)
allpts = {}
for label, path, bench, cond in [("BFF none", a.bff, "bff", "none"), ("BFF human", a.bff, "bff", "human"), ("RB2 safety", a.rb2, "rb2safety", "none")]:
    d = load_judgments(path, bench, condition=cond); G = d.groups.max() + 1
    pooled, pcost, esc = run(d, 0)
    t3 = per_question(pooled, pcost, d.groups, "static_top3", G); bs = per_question(pooled, pcost, d.groups, "best_single", G)
    other = {s: run(d, s) for s in a.seeds}
    rows = []
    for n_ in pooled:
        pq = per_question(pooled, pcost, d.groups, n_, G)
        _, dd, rr, pd_, pr, _ = boot(pq, t3, B=4000); _, d2, _, pd2, _, _ = boot(pq, bs, B=4000)
        sd_diffs = []
        for s, (po, pc, _) in other.items():
            a_ = per_question(po, pc, d.groups, n_, G); b_ = per_question(po, pc, d.groups, "static_top3", G)
            sd_diffs.append(a_[0].sum() / a_[1].sum() - b_[0].sum() / b_[1].sum())
        rows.append(dict(strategy=n_, acc=pq[0].sum() / pq[1].sum(), cost=pq[2].sum() / pq[1].sum(), escalated=np.mean(esc[n_]) if n_ in esc else np.nan,
                         vs_top3=pd_, ci=f"[{np.percentile(dd,2.5):+.3f},{np.percentile(dd,97.5):+.3f}]", cost_vs_top3=pr,
                         vs_best=pd2, seeds_vs_top3=" ".join(f"{x:+.3f}" for x in sd_diffs), mean4=np.mean([pd_] + sd_diffs)))
    T = pd.DataFrame(rows); allpts[label] = T
    print(f"\n######## {label}  (seed 0 with CI; seeds {a.seeds} point estimates of acc diff vs top-3)")
    print(T.round(4).to_string(index=False))

import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, axs = plt.subplots(1, 3, figsize=(15, 4.5))
for ax, (label, T) in zip(axs, allpts.items()):
    for _, r in T.iterrows():
        casc = r.strategy not in ("best_single", "static_top3", "full_jury")
        ax.scatter(r.cost, r.acc, marker="o" if casc else "s", color="C0" if casc else "C3", s=30 if casc else 60)
        if not casc or r.strategy in ("cheap k=3 m=3",):
            ax.annotate(r.strategy if casc else r.strategy.replace("_", " "), (r.cost, r.acc), fontsize=7, xytext=(3, 3), textcoords="offset points")
    ax.set_title(label); ax.set_xlabel("cost per item ($)"); ax.set_ylabel("accuracy")
fig.tight_layout(); os.makedirs("results", exist_ok=True); fig.savefig("results/cascade_frontier.png", dpi=130); print("saved results/cascade_frontier.png")
