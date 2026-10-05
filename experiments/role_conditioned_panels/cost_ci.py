"""Is "same accuracy, much cheaper" real?  Proper CIs on Path A's cost/accuracy operating points.

For every (condition, rule, lambda): per-question paired bootstrap of  acc(Path A) - acc(top-3)  and
cost(Path A) / cost(top-3), on test predictions pooled across the 20 repeats. Because lambda=10 was picked from
7 settings, also: White's reality check on the max accuracy gain over the 7 lambdas, and the same sweep on
fresh split seeds. Cost-aware static controls (cost-penalised best single / best majority panel, chosen on
fit U val) say whether Path A beats a cheap baseline, not just top-3."""
import argparse, itertools, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit import baseline_predictions
from data import load_judgments
from evaluate import run_all_repeats
from majority import mv_verdict, run_all_repeats_mv
from splits import make_3way_splits

LAMS = [0, 1, 2, 5, 10, 20, 50]


def per_question(pooled, pooled_cost, groups, name, G):
    c, n, k = np.zeros(G), np.zeros(G), np.zeros(G)
    for (idx, corr), (_, cost) in zip(pooled[name], pooled_cost[name]):
        np.add.at(c, groups[idx], corr); np.add.at(n, groups[idx], 1); np.add.at(k, groups[idx], cost)
    return c, n, k


def boot(parts_a, parts_b, B=10000, seed=0, W=None):
    """parts = (correct, n, cost) per question. Returns W (draws), acc diff and cost ratio per draw + point values."""
    ca, na, ka = parts_a; cb, nb, kb = parts_b
    ok = nb > 0
    ca, na, ka, cb, nb, kb = (x[ok] for x in (ca, na, ka, cb, nb, kb))
    if W is None:
        W = np.random.default_rng(seed).multinomial(len(ca), np.ones(len(ca)) / len(ca), size=B).astype(float)
    d = (W @ ca) / (W @ na) - (W @ cb) / (W @ nb)
    r = (W @ ka / (W @ na)) / (W @ kb / (W @ nb))
    pt_d = ca.sum() / na.sum() - cb.sum() / nb.sum(); pt_r = (ka.sum() / na.sum()) / (kb.sum() / nb.sum())
    return W, d, r, pt_d, pt_r, ok


def extra_baselines(d, splits, lam):
    """Cost-aware static controls, chosen on fit U val: best single by (acc - lam*cost); best majority panel
    over all subsets by (acc - lam*cost); also fixed top-k for k=1,2,3."""
    Z, Y = d.Z, d.Y; J = Z.shape[1]; cost = np.array([d.cost[j] for j in d.judge_names])
    subsets = [list(c) for r in range(1, J + 1) for c in itertools.combinations(range(J), r)]
    out = {k: ([], []) for k in ("costaware_single", "costaware_panel", "top1", "top2", "top3")}
    for fit, val, test in splits:
        sel = np.concatenate([fit, val]); y = Y[test]
        acc = (Z[sel] == Y[sel][:, None]).mean(0); order = np.argsort(-acc, kind="stable")
        pol = {}
        j = int(np.argmax(acc - lam * cost)); pol["costaware_single"] = ([j])
        best = max(subsets, key=lambda s: ((mv_verdict(Z[sel], s, max(s, key=lambda c: acc[c])) == Y[sel]).mean() - lam * cost[s].sum(), -len(s)))
        pol["costaware_panel"] = best
        for k in (1, 2, 3):
            pol[f"top{k}"] = [int(x) for x in order[:k]]
        for name, cols in pol.items():
            v = mv_verdict(Z[test], cols, max(cols, key=lambda c: acc[c]))
            out[name][0].append((test, (v == y).astype(int))); out[name][1].append((test, np.full(len(test), cost[cols].sum())))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True); ap.add_argument("--verdicts-path")
    ap.add_argument("--B", type=int, default=10000); ap.add_argument("--seeds", type=int, nargs="*", default=[1, 2, 3])
    a = ap.parse_args(); pd.set_option("display.width", 220)

    for cond in ("human", "none"):
        d = load_judgments(a.data, "bff", condition=cond, verdicts_path=a.verdicts_path); G = d.groups.max() + 1
        splits = make_3way_splits(d.groups, 0, 20)
        for rule, runner in (("eta", run_all_repeats), ("majority", run_all_repeats_mv)):
            print(f"\n################ condition={cond}  rule={rule}  (Path A minus static top-3; paired question bootstrap, B={a.B})")
            rows, Ds, pts, W = [], [], [], None
            for lam in LAMS:
                o = runner(d, splits, lam=lam, verbose=False)
                pa = per_question(o["pooled"], o["pooled_cost"], d.groups, "path_a_panel", G)
                t3 = per_question(o["pooled"], o["pooled_cost"], d.groups, "static_top3", G)
                W, dd, rr, pd_, pr, ok = boot(pa, t3, B=a.B, W=W)
                Ds.append(dd); pts.append(pd_)
                res = o["results"]; p = res[res.strategy == "path_a_panel"]
                rows.append(dict(lam=lam, acc=p.acc.mean(), cost=p.cost.mean(), panel=p.panel_size.mean(), d_acc=pd_,
                                 lo=np.percentile(dd, 2.5), hi=np.percentile(dd, 97.5), bonf_lo=np.percentile(dd, 0.25 / 7 * 100),
                                 cost_ratio=pr, cr_lo=np.percentile(rr, 2.5), cr_hi=np.percentile(rr, 97.5),
                                 p_noninf_1pt=float(np.mean(dd > -0.01))))
            T = pd.DataFrame(rows)
            t3r = o["results"][o["results"].strategy == "static_top3"]; bsr = o["results"][o["results"].strategy == "best_single"]
            print(f"top-3 acc {t3r.acc.mean():.4f} cost {t3r.cost.mean():.5f} | best single acc {bsr.acc.mean():.4f} cost {bsr.cost.mean():.5f}")
            print(T.round(4).to_string(index=False))
            D = np.array(Ds).T; pts = np.array(pts)
            null_max = (D - pts[None, :]).max(1)
            print(f"White reality check, max accuracy gain over 7 lambdas: observed {pts.max():+.4f} (lambda={LAMS[int(pts.argmax())]}), "
                  f"p = {float(np.mean(null_max >= pts.max())):.3f}  (H0: no lambda beats top-3)")

            if cond == "human" and rule == "eta":
                print("\n-- Same sweep on fresh question-split seeds (is lambda=10 stable?) --")
                for sd in a.seeds:
                    sp2 = make_3way_splits(d.groups, sd, 20); line = []
                    for lam in LAMS:
                        o2 = runner(d, sp2, lam=lam, verbose=False)
                        r2 = o2["results"]; p2 = r2[r2.strategy == "path_a_panel"].acc.mean() - r2[r2.strategy == "static_top3"].acc.mean()
                        line.append(f"{p2:+.3f}")
                    print(f"seed {sd}: acc diff vs top-3 for lambda {LAMS}: {line}")

                print("\n-- Cost-aware static controls at lambda=10 vs Path A (eta, lambda=10), same splits --")
                o = runner(d, splits, lam=10, verbose=False)
                ex = extra_baselines(d, splits, 10)
                pooled = dict(o["pooled"]); pcost = dict(o["pooled_cost"])
                for k, (pc, kc) in ex.items():
                    pooled[k] = pc; pcost[k] = kc
                t3 = per_question(pooled, pcost, d.groups, "static_top3", G)
                pa = per_question(pooled, pcost, d.groups, "path_a_panel", G)
                recs = []
                for name in ("path_a_panel", "costaware_single", "costaware_panel", "top1", "top2", "top3", "best_single", "full_jury"):
                    pq = per_question(pooled, pcost, d.groups, name, G)
                    _, dd, rr, pd_, pr, ok = boot(pq, t3, B=a.B, W=W)
                    _, d2, _, pd2, _, _ = boot(pa, pq, B=a.B, W=W)
                    recs.append(dict(strategy=name, acc=pq[0].sum() / pq[1].sum(), cost=pq[2].sum() / pq[1].sum(), vs_top3=pd_,
                                     lo=np.percentile(dd, 2.5), hi=np.percentile(dd, 97.5), cost_ratio_vs_top3=pr,
                                     pathA_minus_this=pd2, p_lo=np.percentile(d2, 2.5), p_hi=np.percentile(d2, 97.5)))
                print(pd.DataFrame(recs).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
