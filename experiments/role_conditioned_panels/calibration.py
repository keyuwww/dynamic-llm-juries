"""Verdict rate vs gold rate, per-judge FPR/FNR, P(Y=1 | #judges saying correct), and the tuned vote threshold."""
import argparse, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data import load_judgments
from splits import make_3way_splits

ap = argparse.ArgumentParser()
ap.add_argument("--data", required=True); ap.add_argument("--bench", default="bff"); ap.add_argument("--condition", default="none")
ap.add_argument("--verdicts-path"); ap.add_argument("--rb2-path")
a = ap.parse_args()
d = load_judgments(a.data, a.bench, condition=a.condition, verdicts_path=a.verdicts_path, rb2_path=a.rb2_path)
Z, Y, names = d.Z, d.Y, d.judge_names
print(f"\n[{a.bench}/{a.condition}] gold rate P(Y=1) = {Y.mean():.3f} | mean judge verdict rate = {Z.mean():.3f}")
fp = ((Z == 1) & (Y[:, None] == 0)).sum(0) / (Y == 0).sum(); fn = ((Z == 0) & (Y[:, None] == 1)).sum(0) / (Y == 1).sum()
print(pd.DataFrame({"verdict_rate": Z.mean(0), "accuracy": (Z == Y[:, None]).mean(0), "FPR": fp, "FNR": fn}, index=names).round(3).to_string())
k = Z.sum(1)
print("P(Y=1 | #judges saying correct = k):", {int(i): (round(float(Y[k == i].mean()), 2), int((k == i).sum())) for i in range(Z.shape[1] + 1) if (k == i).any()}, "(value, n)")
ths = []
for fit, val, test in make_3way_splits(d.groups, 0, 20):
    sel = np.concatenate([fit, val]); kk = max(range(Z.shape[1] + 2), key=lambda t: ((k[sel] >= t).astype(int) == Y[sel]).mean()); ths.append(kk)
print(f"tuned vote threshold (>= k of {Z.shape[1]}) chosen on fit U val across 20 repeats: {dict(zip(*np.unique(ths, return_counts=True)))}; plain majority = 5")
