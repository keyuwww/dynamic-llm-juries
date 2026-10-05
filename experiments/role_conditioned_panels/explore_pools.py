"""Specialization test on a reduced judge pool: PC5 + the three hand-crafted slices.

For each slice family: (a) is one judge best on both sides, (b) honest routed-policy test (per-side judges chosen
on fit U val, scored on test, 20 repeats), (c) in-sample oracle routing ceiling, (d) Path A with these slices."""
import argparse
import os
import sys

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit import baseline_predictions                                     # noqa: E402
from data import drop_judges, load_judgments                               # noqa: E402
from evaluate import _metrics, pooled_bootstrap, run_all_repeats           # noqa: E402
from explore_3 import pc_masks_factory, routed_policy                      # noqa: E402
from majority import run_all_repeats_mv                                    # noqa: E402
from slices import fit_slice_thresholds, slice_masks                       # noqa: E402
from splits import make_3way_splits                                        # noqa: E402


def families(pcs, comp=5):
    def hand(name):
        def fn(data, fit):
            thr = fit_slice_thresholds(data.prompt[fit], data.response[fit])
            return {name: slice_masks(data.prompt, data.response, thr)[name]}
        return fn
    return {f"pc{comp}": lambda data, fit: {f"pc{comp}_hi": pc_masks_factory(pcs, comp)(data, fit)[f"pc{comp}_hi"]},
            "calc_heavy": hand("calc_heavy"), "long_response": hand("long_response"), "numeric_prompt": hand("numeric_prompt")}


def hand_plus_pc(pcs, comp=5):
    fam = families(pcs, comp)
    def fn(data, fit):
        out = {}
        for f in fam.values():
            out.update(f(data, fit))
        out[f"pc{comp}_lo"] = ~out[f"pc{comp}_hi"]
        return out
    return fn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True); ap.add_argument("--bench", default="bff")
    ap.add_argument("--verdicts-path"); ap.add_argument("--rb2-path")
    ap.add_argument("--emb", required=True); ap.add_argument("--emb-ids", required=True)
    ap.add_argument("--exclude", nargs="*", default=[]); ap.add_argument("--n-repeats", type=int, default=20)
    a = ap.parse_args()
    pd.set_option("display.width", 220)

    d0 = load_judgments(a.data, a.bench, verdicts_path=a.verdicts_path, rb2_path=a.rb2_path)
    d = drop_judges(d0, a.exclude) if a.exclude else d0
    E = np.load(a.emb); assert (pd.read_parquet(a.emb_ids).item_id.values == d.item_ids).all()
    pcs = PCA(n_components=16, random_state=0).fit_transform(E)
    Z, Y, names = d.Z, d.Y, d.judge_names; cost = np.array([d.cost[j] for j in names])
    splits = make_3way_splits(d.groups, 0, a.n_repeats)
    N, J = Z.shape; allidx = np.arange(N)
    glob_acc = (Z == Y[:, None]).mean(0)
    print(f"\n##### pool = {names}  ({J} judges)  | global best = {names[int(glob_acc.argmax())]} {glob_acc.max():.3f}")

    fams = families(pcs)
    rows = []
    for fam, fn in fams.items():
        m = list(fn(d, allidx).values())[0]               # all-item threshold: diagnostics only
        sides = [m, ~m]
        acc = [(Z[s] == Y[s][:, None]).mean(0) for s in sides]
        best = [int(x.argmax()) for x in acc]
        # in-sample oracle routing: best judge per side, scored on the same rows
        routed_in = (m.sum() * acc[0].max() + (~m).sum() * acc[1].max()) / N
        # honest routed test
        rec, pooled = [], {}
        for fit, val, test in splits:
            sel = np.concatenate([fit, val]); ytest = Y[test]
            fm = list(fn(d, fit).values())[0]
            strat = {k: (v[0], v[1]) for k, v in baseline_predictions(Z, Y, sel, test, cost).items() if k in ("best_single", "static_top3")}
            strat["routed_best"] = routed_policy(Z, Y, cost, fit, val, test, [fm, ~fm], 1)
            strat["routed_top3"] = routed_policy(Z, Y, cost, fit, val, test, [fm, ~fm], 3)
            for n_, (v, c) in strat.items():
                rec.append(dict(strategy=n_, **_metrics(v, ytest, c))); pooled.setdefault(n_, []).append((test, (v == ytest).astype(int)))
        r = pd.DataFrame(rec).groupby("strategy").acc.mean()
        b1 = pooled_bootstrap(pooled, d.groups, "routed_best", "best_single")
        b3 = pooled_bootstrap(pooled, d.groups, "routed_top3", "static_top3")
        rows.append(dict(slice=fam, prevalence=round(float(m.mean()), 2), best_judge_side1=names[best[0]], acc1=round(float(acc[0].max()), 3),
                         best_judge_side0=names[best[1]], acc0=round(float(acc[1].max()), 3), same_best=best[0] == best[1],
                         insample_routed_gain=round(float(routed_in - glob_acc.max()), 4),
                         routed_best_minus_best=round(b1["diff"], 4), rb_ci=f"[{b1['lo']:+.3f},{b1['hi']:+.3f}]",
                         routed_top3_minus_top3=round(b3["diff"], 4), rt3_ci=f"[{b3['lo']:+.3f},{b3['hi']:+.3f}]"))
    T = pd.DataFrame(rows)
    print("\nSpecialization diagnostics (side1 = slice on, side0 = slice off):"); print(T.to_string(index=False))

    out = {}
    for rule, runner in (("eta", run_all_repeats), ("majority", run_all_repeats_mv)):
        for tag, fnm in (("hand-only", None), ("pc5+hand", hand_plus_pc(pcs))):
            out[(rule, tag)] = runner(d, splits, mask_fn=fnm, verbose=False)
    base = out[("majority", "hand-only")]["results"]
    rr = [(f"[ref] {s}", base[base.strategy == s].acc.mean(), base[base.strategy == s].kappa.mean(), base[base.strategy == s].cost.mean(), np.nan, np.nan, np.nan, np.nan)
          for s in ("best_single", "static_top3")]
    for (rule, tag), o in out.items():
        p = o["results"].query("strategy == 'path_a_panel'"); b = pooled_bootstrap(o["pooled"], d.groups, "path_a_panel", "static_top3")
        sp = o["roles"].role.str.startswith("Specialist").sum() / a.n_repeats
        rr.append((f"Path A [{rule}] slices={tag}", p.acc.mean(), p.kappa.mean(), p.cost.mean(), sp, b["diff"], b["lo"], b["hi"]))
    print("\nPath A on this pool:")
    print(pd.DataFrame(rr, columns=["strategy", "acc", "kappa", "cost", "specialists/repeat", "minus_top3", "ci_lo", "ci_hi"]).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
