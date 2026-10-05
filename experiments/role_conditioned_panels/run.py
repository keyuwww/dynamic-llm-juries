"""CLI:  python run.py --data ../tinker_pool_8models_judgments.jsonl --n-repeats 20 --tau 0.005 --lambda 0.0

Writes results/results.csv (+ roles / slice logs) and prints the Evaluation Protocol table with real numbers."""
import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit import e0_audit                                                   # noqa: E402
from data import load_judgments                                              # noqa: E402
from evaluate import copy_stress_test, pooled_bootstrap, run_all_repeats     # noqa: E402
from majority import run_all_repeats_mv                                      # noqa: E402
from splits import make_3way_splits, make_item_splits                        # noqa: E402

REFERENCE = [   # Ingrid's full-data numbers: reference only (picked and scored on all 459 BFF items)
    ("REF best single, full-data pick (gpt-oss-120b)", 0.854, 0.7055, 0.00072),
    ("REF static top-3 majority, full-data pick", 0.8736, 0.7454, 0.0038),
    ("REF learned router (logreg top-1)", 0.837, 0.6724, 0.0009),
    ("REF oracle", 0.974, 0.9471, np.nan),
]
LABELS = {"best_single": "Best single judge (per split)", "static_top3": "Static top-3 majority (per split)",
          "full_jury": "Full jury of 8, majority (per split)",
          "stacked_top3": "[extra] eta-hat stacker over top-3, no selection", "stacked_full": "[extra] eta-hat stacker over all 8, no selection",
          "tuned_vote_top3": "[extra] top-3, vote-count threshold tuned", "tuned_vote_all8": "[extra] all 8, vote-count threshold tuned",
          "path_a_panel": "Role-conditioned panel (this spec)",
          "oracle": "Oracle (per split test)"}


def summarize(res):
    g = res.groupby("strategy")
    t = g.agg(acc=("acc", "mean"), acc_sd=("acc", "std"), kappa=("kappa", "mean"), kappa_sd=("kappa", "std"),
              cost=("cost", "mean")).reindex(list(LABELS)).dropna(how="all")
    t.insert(0, "strategy", [LABELS[s] for s in t.index])
    return t.reset_index(drop=True)


def stability(roles, n_repeats):
    t = roles.assign(n=1).pivot_table(index="judge", columns="role", values="n", aggfunc="sum", fill_value=0) / n_repeats
    t["modal_role"] = t.idxmax(axis=1)
    t["modal_share"] = t.drop(columns="modal_role").max(axis=1)
    t["reportable(>=80%)"] = t["modal_share"] >= 0.8
    return t.round(2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--bench", default="bff", choices=["bff", "rb2safety"])
    ap.add_argument("--condition", default="none", help="judge condition: none (no reference) or human (reference answer given)")
    ap.add_argument("--n-repeats", type=int, default=20)
    ap.add_argument("--tau", type=float, default=0.005)
    ap.add_argument("--lambda", dest="lam", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--rule", default="eta", choices=["eta", "majority"],
                    help="eta = spec as written (eta-hat gains + serving); majority = majority-vote gains + serving, no eta-hat")
    ap.add_argument("--mv-step", default="pair", choices=["pair", "single"])
    ap.add_argument("--serving-fit", default="all", choices=["all", "matched"])
    ap.add_argument("--verdicts-path"); ap.add_argument("--rb2-path")
    ap.add_argument("--out-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "results"))
    ap.add_argument("--lambda-sweep", action="store_true", help="re-run with lambda in {0,1,2,5,10,20,50}")
    ap.add_argument("--sanity", action="store_true", help="label-shuffle and leaky-split controls")
    ap.add_argument("--stress", action="store_true", help="copy stress test")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    pd.set_option("display.width", 200); pd.set_option("display.max_columns", 30)

    d = load_judgments(a.data, a.bench, condition=a.condition, verdicts_path=a.verdicts_path, rb2_path=a.rb2_path)
    e0 = e0_audit(d.Z, d.Y, d.judge_names, d.cost)
    print(f"[E0] best single {e0['best']} = {e0['best_acc']:.3f} | oracle {e0['oracle_acc']:.3f} | "
          f"headroom {e0['oracle_acc'] - e0['best_acc']:.3f} | mean err corr {e0['mean_err_corr']:.3f}")
    splits = make_3way_splits(d.groups, a.seed, a.n_repeats)
    kw = dict(tau_P=a.tau, tau_f=a.tau, serving_fit=a.serving_fit, verbose=not a.quiet)

    if a.rule == "majority":
        runner = lambda *x, **k: run_all_repeats_mv(*x, step=a.mv_step, **k)
    else:
        runner = run_all_repeats
    out = runner(d, splits, lam=a.lam, **kw)
    res = out["results"]
    res.to_csv(os.path.join(a.out_dir, "results.csv"), index=False)
    out["roles"].to_csv(os.path.join(a.out_dir, "roles.csv"), index=False)
    out["slice_log"].to_csv(os.path.join(a.out_dir, "slice_log.csv"), index=False)

    T = summarize(res)
    ref = pd.DataFrame(REFERENCE, columns=["strategy", "acc", "kappa", "cost"])
    print("\n=== Evaluation Protocol (final-test, mean over %d repeats; bench=%s, lambda=%g, tau=%g) ===" %
          (a.n_repeats, a.bench, a.lam, a.tau))
    print(T.round(4).to_string(index=False))
    if a.bench == "bff":
        print("\nReference only (not comparable):"); print(ref.round(4).to_string(index=False))
    else:
        print("\n(Reference rows from Ingrid's BFF run are omitted: this is a different benchmark.)")

    print("\nPaired question-bootstrap on pooled test predictions (Path A minus ...):")
    for b in ["static_top3", "best_single", "full_jury"]:
        r = pooled_bootstrap(out["pooled"], d.groups, "path_a_panel", b)
        flag = "CI includes 0" if r["lo"] <= 0 <= r["hi"] else "CI excludes 0"
        print(f"  vs {b:12s}: diff acc = {r['diff']:+.4f}  95% CI [{r['lo']:+.4f}, {r['hi']:+.4f}]  ({flag}; {r['n_questions']} questions)")

    print("\nRole assignment stability (fraction of repeats):"); print(stability(out["roles"], a.n_repeats).to_string())
    sl = out["slice_log"].groupby("slice").agg(prevalence=("prevalence_fit", "mean"), n_fit=("n_fit", "mean"),
                                              n_val=("n_val", "mean"), kept_frac=("kept", "mean"))
    print("\nSlice gating (mean over repeats):"); print(sl.round(2).to_string())

    if a.lambda_sweep:
        rows = []
        for lam in [0, 1, 2, 5, 10, 20, 50]:
            o = runner(d, splits, lam=lam, **{**kw, "verbose": False})
            p = o["results"].query("strategy == 'path_a_panel'")
            rows.append(dict(lam=lam, acc=p.acc.mean(), kappa=p.kappa.mean(), cost=p.cost.mean(), panel=p.panel_size.mean()))
        sw = pd.DataFrame(rows); sw.to_csv(os.path.join(a.out_dir, "lambda_sweep.csv"), index=False)
        print("\nLambda sweep (Path A):"); print(sw.round(5).to_string(index=False))

    if a.sanity:
        print("\n=== Sanity: label shuffle (Y permuted within fit and val; test labels real) ===")
        o = runner(d, splits, lam=a.lam, shuffle_labels=True, **{**kw, "verbose": False})
        print(summarize(o["results"]).round(4).to_string(index=False))
        print(stability(o["roles"], a.n_repeats).to_string())
        print("\n=== Sanity: leaky item-level splits ===")
        o = runner(d, make_item_splits(len(d.Y), a.seed, a.n_repeats), lam=a.lam, **{**kw, "verbose": False})
        lk = summarize(o["results"])
        print(lk.round(4).to_string(index=False))
        g = T.set_index("strategy").acc["Role-conditioned panel (this spec)"]
        l = lk.set_index("strategy").acc["Role-conditioned panel (this spec)"]
        print(f"leaky - grouped accuracy for Path A: {l - g:+.4f}")

    if a.stress and a.rule == "majority":
        print("\nCopy stress test skipped: under majority vote a duplicated judge casts two votes, so it is not redundant (the test only holds for eta-hat).")
    elif a.stress:
        st = copy_stress_test(d, splits, tau_P=a.tau, tau_f=a.tau, lam=a.lam)
        st.to_csv(os.path.join(a.out_dir, "copy_stress.csv"), index=False)
        print(f"\nCopy stress test over {len(st)} repeats: duplicates all Copies in "
              f"{st.all_dups_are_copies.mean():.0%}, real roles unchanged in {st.real_roles_unchanged.mean():.0%}")


if __name__ == "__main__":
    main()
