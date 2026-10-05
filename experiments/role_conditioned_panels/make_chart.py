"""Held-out accuracy: best single / static top-3 / full jury / Role-conditioned panel (majority vote), across 3 benchmarks.

Numbers: the same 20 question-grouped fit/val/test splits as everywhere else (seed 0), tau=0.005, lambda=0, baselines
recomputed per split. Point = accuracy over test predictions pooled across repeats; whisker = 95% question bootstrap."""
import argparse, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data import load_judgments
from majority import run_all_repeats_mv
from splits import make_3way_splits

STRATS = [("path_a_panel", "Role-conditioned panel (majority vote)"), ("best_single", "Best single judge"),
          ("static_top3", "Static top-3 majority"), ("full_jury", "Full jury (8), majority")]


def accuracy_with_ci(o, groups, name, B=5000, seed=0):
    G = groups.max() + 1; c, n = np.zeros(G), np.zeros(G)
    for idx, corr in o["pooled"][name]:
        np.add.at(c, groups[idx], corr); np.add.at(n, groups[idx], 1)
    ok = n > 0; c, n = c[ok], n[ok]
    W = np.random.default_rng(seed).multinomial(len(c), np.ones(len(c)) / len(c), size=B)
    b = (W @ c) / (W @ n)
    return c.sum() / n.sum(), np.percentile(b, 2.5), np.percentile(b, 97.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bff", required=True); ap.add_argument("--rb2", required=True)
    ap.add_argument("--verdicts-path"); ap.add_argument("--rb2-path"); ap.add_argument("--out", default="results")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    jobs = [("BFF-Bench\nno reference", a.bff, "bff", "none"), ("BFF-Bench\nreference given", a.bff, "bff", "human"),
            ("RewardBench-2 Safety\nno reference", a.rb2, "rb2safety", "none")]
    rows = []
    for label, path, bench, cond in jobs:
        d = load_judgments(path, bench, condition=cond, verdicts_path=a.verdicts_path, rb2_path=a.rb2_path)
        o = run_all_repeats_mv(d, make_3way_splits(d.groups, 0, 20), verbose=False)
        for key, nice in STRATS:
            acc, lo, hi = accuracy_with_ci(o, d.groups, key)
            rows.append(dict(benchmark=label.replace("\n", " "), strategy=nice, acc=acc, ci_lo=lo, ci_hi=hi,
                             n_items=len(d.Y), n_questions=int(d.groups.max() + 1)))
    df = pd.DataFrame(rows); df.to_csv(os.path.join(a.out, "accuracy_comparison.csv"), index=False)
    print(df.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
