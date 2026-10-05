"""Does the eta-hat stacker's advantage on RewardBench-2 survive at BFF's size?

Draws random subsets of K questions from a bench, reruns the full 20-repeat pipeline on each, and reports
mean accuracy per strategy plus the pooled Path-A / stacker margins over static top-3 majority."""
import argparse
import dataclasses
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data import load_judgments                                   # noqa: E402
from evaluate import pooled_bootstrap, run_all_repeats            # noqa: E402
from majority import run_all_repeats_mv                           # noqa: E402
from splits import make_3way_splits                               # noqa: E402


def subset(d, idx):
    g = pd.factorize(d.groups[idx])[0]
    kw = {f.name: getattr(d, f.name) for f in dataclasses.fields(d)}
    for k in ("Z", "Y", "examinee", "prompt", "response", "item_ids"):
        kw[k] = kw[k][idx]
    kw["groups"] = g
    return dataclasses.replace(d, **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True); ap.add_argument("--bench", default="rb2safety")
    ap.add_argument("--rb2-path"); ap.add_argument("--k-questions", type=int, default=80)
    ap.add_argument("--n-subsamples", type=int, default=20); ap.add_argument("--n-repeats", type=int, default=20)
    ap.add_argument("--rule", default="eta", choices=["eta", "majority"])
    ap.add_argument("--out", default="results/subsample.csv")
    a = ap.parse_args()
    d = load_judgments(a.data, a.bench, rb2_path=a.rb2_path)
    rng = np.random.default_rng(1)
    rows = []
    for s in range(a.n_subsamples):
        qs = rng.choice(np.unique(d.groups), a.k_questions, replace=False)
        ds = subset(d, np.where(np.isin(d.groups, qs))[0])
        run = run_all_repeats_mv if a.rule == "majority" else run_all_repeats
        out = run(ds, make_3way_splits(ds.groups, s, a.n_repeats), verbose=False)
        acc = out["results"].groupby("strategy").acc.mean()
        row = dict(subsample=s, n_items=len(ds.Y), **acc.to_dict())
        for b in ("static_top3", "best_single"):
            row[f"pathA_minus_{b}"] = pooled_bootstrap(out["pooled"], ds.groups, "path_a_panel", b, n_boot=500)["diff"]
        for st in [x for x in ("stacked_top3", "stacked_full", "tuned_vote_top3", "tuned_vote_all8") if x in out["pooled"]]:
            row[f"{st}_minus_static_top3"] = pooled_bootstrap(out["pooled"], ds.groups, st, "static_top3", n_boot=500)["diff"]
        rows.append(row)
        print(f"[{s:2d}] items={row['n_items']} pathA={row['path_a_panel']:.3f} top3={row['static_top3']:.3f} "
              f"best={row['best_single']:.3f}", flush=True)
    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(a.out), exist_ok=True); df.to_csv(a.out, index=False)
    cols = [c for c in ["best_single", "static_top3", "full_jury", "stacked_top3", "stacked_full", "tuned_vote_top3", "tuned_vote_all8", "path_a_panel"] if c in df]
    print(f"\nMean over {a.n_subsamples} subsamples of {a.k_questions} questions (~{df.n_items.mean():.0f} items):")
    print(df[cols].agg(["mean", "std"]).round(4).T.to_string())
    for c in [c for c in df if "_minus_" in c]:
        print(f"{c:34s} mean {df[c].mean():+.4f}  (sd {df[c].std():.4f}; positive in {(df[c] > 0).mean():.0%} of subsamples)")


if __name__ == "__main__":
    main()
