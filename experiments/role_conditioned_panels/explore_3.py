"""Exp 3: does an embedding-based slice (Ingrid's emb_pc5) rescue specialists?

Slice recipe = Ingrid's: MiniLM-L6 embedding of prompt[:1200] + "\\n[RESPONSE]\\n" + response[:1200]; PCA to 16
components (unsupervised, text only, fit on all items as in her notebook); emb_pc5 = 6th component.
pc5_hi / pc5_lo = above / at-or-below the FIT-split median of that component (so the threshold is frozen on fit).
Caveat: PC5 was picked by Ingrid from SHAP on all 459 items, so using it here is post-hoc selection (optimistic)."""
import argparse
import os
import sys

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit import baseline_predictions                                    # noqa: E402
from data import load_judgments                                           # noqa: E402
from evaluate import _metrics, pooled_bootstrap, run_all_repeats          # noqa: E402
from majority import mv_verdict, run_all_repeats_mv                       # noqa: E402
from slices import fit_slice_thresholds, slice_masks                      # noqa: E402
from splits import make_3way_splits                                       # noqa: E402


def pc_masks_factory(pcs, comp):
    def fn(data, fit):
        x = pcs[:, comp]; med = np.median(x[fit])
        return {f"pc{comp}_hi": x > med, f"pc{comp}_lo": x <= med}
    return fn


def hand_plus(pcs, comp):
    def fn(data, fit):
        thr = fit_slice_thresholds(data.prompt[fit], data.response[fit])
        return {**slice_masks(data.prompt, data.response, thr), **pc_masks_factory(pcs, comp)(data, fit)}
    return fn


def routed_policy(Z, Y, cost, fit, val, test, side_masks, k):
    """Slice-routed static panel: for each side of the slice, take the top-k judges by accuracy on that side's
    fit U val rows and majority-vote them on that side's test rows. k=1 -> routed best single judge."""
    sel = np.concatenate([fit, val]); v = np.zeros(len(test), int); c = np.zeros(len(test))
    for m in side_masks:
        rows, tr = sel[m[sel]], np.where(m[test])[0]
        if len(tr) == 0:
            continue
        acc = (Z[rows] == Y[rows][:, None]).mean(0); cols = [int(j) for j in np.argsort(-acc, kind="stable")[:k]]
        v[tr] = mv_verdict(Z[test][tr], cols, cols[0]); c[tr] = cost[cols].sum()
    return v, c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True); ap.add_argument("--bench", default="bff")
    ap.add_argument("--verdicts-path"); ap.add_argument("--rb2-path")
    ap.add_argument("--emb", required=True); ap.add_argument("--emb-ids", required=True)
    ap.add_argument("--comp", type=int, default=5); ap.add_argument("--n-repeats", type=int, default=20)
    ap.add_argument("--out", default="results/explore_3")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    pd.set_option("display.width", 220)

    d = load_judgments(a.data, a.bench, verdicts_path=a.verdicts_path, rb2_path=a.rb2_path)
    E = np.load(a.emb); assert (pd.read_parquet(a.emb_ids).item_id.values == d.item_ids).all(), "embedding ids misaligned"
    pcs = PCA(n_components=16, random_state=0).fit_transform(E)
    Z, Y, names = d.Z, d.Y, d.judge_names; cost = np.array([d.cost[j] for j in names])
    splits = make_3way_splits(d.groups, 0, a.n_repeats)

    # ---------- what does the slice separate?
    x = pcs[:, a.comp]; hi = x > np.median(x)
    wc = np.array([len(r.split()) for r in d.response]); dg = np.array([sum(c.isdigit() for c in p) / max(len(p), 1) for p in d.prompt])
    print(f"\n[{a.bench}] PC{a.comp} split (median over all items), hi vs lo:")
    print(pd.DataFrame({"n": [hi.sum(), (~hi).sum()], "mean_Y": [Y[hi].mean(), Y[~hi].mean()],
                        "resp_words": [wc[hi].mean(), wc[~hi].mean()], "prompt_digit_frac": [dg[hi].mean(), dg[~hi].mean()],
                        "n_questions": [len(set(d.groups[hi])), len(set(d.groups[~hi]))]}, index=["hi", "lo"]).round(3).to_string())
    for lab, m in (("hi", hi), ("lo", ~hi)):
        i = np.where(m)[0][np.argsort(-np.abs(x[m] - np.median(x)))[:2]]
        print(f"  extreme {lab}: " + " || ".join(d.prompt[j][-110:].replace("\n", " ") for j in i))

    # ---------- diagnostic: does any judge-by-slice interaction exist?
    acc_hi = (Z[hi] == Y[hi][:, None]).mean(0); acc_lo = (Z[~hi] == Y[~hi][:, None]).mean(0)
    G = d.groups.max() + 1; rng = np.random.default_rng(0)
    cor = (Z == Y[:, None]).astype(float)
    def qsum(m):
        s = np.zeros((G, Z.shape[1])); n = np.zeros(G); np.add.at(s, d.groups[m], cor[m]); np.add.at(n, d.groups[m], 1); return s, n
    (s1, n1), (s0, n0) = qsum(hi), qsum(~hi)
    bs = []
    for _ in range(2000):
        q = rng.integers(0, G, G); bs.append(s1[q].sum(0) / max(n1[q].sum(), 1) - s0[q].sum(0) / max(n0[q].sum(), 1))
    bs = np.array(bs)
    diag = pd.DataFrame({"acc_hi": acc_hi, "acc_lo": acc_lo, "diff": acc_hi - acc_lo, "ci_lo": np.percentile(bs, 2.5, 0),
                         "ci_hi": np.percentile(bs, 97.5, 0)}, index=names).round(3)
    diag["excludes0"] = (diag.ci_lo > 0) | (diag.ci_hi < 0)
    print(f"\nPer-judge accuracy on PC{a.comp}-hi vs lo (question-bootstrap CI on difference):"); print(diag.to_string())
    print(f"  best judge hi: {names[int(acc_hi.argmax())]} ({acc_hi.max():.3f}) | best judge lo: {names[int(acc_lo.argmax())]} ({acc_lo.max():.3f})"
          f" | best overall: {names[int((Z == Y[:, None]).mean(0).argmax())]}")

    # ---------- honest routing test: slice-routed best single / top-3, vs global (chosen per split), 20 repeats
    def run_routing(comp):
        rec, pooled = [], {}
        for fit, val, test in splits:
            sel = np.concatenate([fit, val]); ytest = Y[test]
            pm = pc_masks_factory(pcs, comp)(d, fit); sides = list(pm.values())
            strat = {k: (v[0], v[1]) for k, v in baseline_predictions(Z, Y, sel, test, cost).items() if k in ("best_single", "static_top3")}
            strat["routed_best_single"] = routed_policy(Z, Y, cost, fit, val, test, sides, 1)
            strat["routed_top3"] = routed_policy(Z, Y, cost, fit, val, test, sides, 3)
            for n_, (v, c) in strat.items():
                rec.append(dict(strategy=n_, **_metrics(v, ytest, c))); pooled.setdefault(n_, []).append((test, (v == ytest).astype(int)))
        return pd.DataFrame(rec), pooled
    res, pooled = run_routing(a.comp)
    print(f"\nSlice-routed static policies on PC{a.comp} (per-side top-k judges chosen on fit U val; test, {a.n_repeats} repeats):")
    print(res.groupby("strategy").agg(acc=("acc", "mean"), kappa=("kappa", "mean"), cost=("cost", "mean")).round(4).to_string())
    for s_, b_ in [("routed_best_single", "best_single"), ("routed_top3", "static_top3")]:
        b = pooled_bootstrap(pooled, d.groups, s_, b_)
        print(f"  {s_} minus {b_}: {b['diff']:+.4f}  95% CI [{b['lo']:+.4f}, {b['hi']:+.4f}]")
    # context: same routing test for every one of the 16 components (PC5 was chosen post hoc)
    gains = []
    for comp in range(16):
        r_, p_ = run_routing(comp)
        gains.append(dict(comp=comp, routed_best_minus_best=pooled_bootstrap(p_, d.groups, "routed_best_single", "best_single", n_boot=300)["diff"],
                          routed_top3_minus_top3=pooled_bootstrap(p_, d.groups, "routed_top3", "static_top3", n_boot=300)["diff"]))
    g = pd.DataFrame(gains).set_index("comp").round(4)
    print("\nSame routing test across all 16 PCs (accuracy change vs global policy; PC%d is the post-hoc pick):" % a.comp)
    print(g.T.to_string()); print(f"  PC{a.comp} rank among 16 (routed_top3_minus_top3): {int((g.routed_top3_minus_top3 > g.loc[a.comp, 'routed_top3_minus_top3']).sum()) + 1}/16")

    # ---------- the Path A pipeline with the embedding slice (both rules), alone and alongside the hand slices
    out = {}
    for rule, runner in (("eta", run_all_repeats), ("majority", run_all_repeats_mv)):
        for tag, fn in ((f"pc{a.comp}_only", pc_masks_factory(pcs, a.comp)), (f"hand+pc{a.comp}", hand_plus(pcs, a.comp))):
            o = runner(d, splits, mask_fn=fn, verbose=False)
            out[(rule, tag)] = o
    base = out[("majority", f"pc{a.comp}_only")]["results"]
    rows = [(f"[ref] {s}", base[base.strategy == s].acc.mean(), base[base.strategy == s].kappa.mean(), base[base.strategy == s].cost.mean())
            for s in ("best_single", "static_top3")]
    for (rule, tag), o in out.items():
        p = o["results"].query("strategy == 'path_a_panel'")
        sp = o["roles"].role.str.startswith("Specialist").sum() / a.n_repeats
        b = pooled_bootstrap(o["pooled"], d.groups, "path_a_panel", "static_top3")
        rows.append((f"Path A [{rule}] slices={tag}", p.acc.mean(), p.kappa.mean(), p.cost.mean(), sp, b["diff"], b["lo"], b["hi"]))
    T = pd.DataFrame(rows, columns=["strategy", "acc", "kappa", "cost", "specialists/repeat", "minus_top3", "ci_lo", "ci_hi"])
    print("\nPath A with the embedding slice:"); print(T.round(4).to_string(index=False))
    for (rule, tag), o in out.items():
        r_ = o["roles"]; sp = r_[r_.role.str.startswith("Specialist")]
        if len(sp):
            print(f"  [{rule}, {tag}] specialist roles (counts over {a.n_repeats} repeats):", sp.groupby(["judge", "role"]).size().to_dict())
    T.to_csv(os.path.join(a.out, f"explore_3_{a.bench}.csv"), index=False)


if __name__ == "__main__":
    main()
