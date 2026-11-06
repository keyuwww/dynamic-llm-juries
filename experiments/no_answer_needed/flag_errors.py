#!/usr/bin/env python
"""Can a cheap signal flag the STRONGEST judge's mistakes? (Janys's question.)  Signals, all available at test time:
  probe     held-out P(strongest judge correct) from probe_analysis.py --save-scores (Qwen3.5-4B activations)
  disagree  share of the OTHER judges whose verdict differs from the strongest judge's verdict (no training, no labels)
  both      logistic regression on [probe logit, disagree], question-grouped 5-fold
Metric: AUROC for 'strongest judge is wrong' (0.5 = chance) with a paired question-bootstrap CI, and accuracy of the strongest
judge on the items it keeps when the least-trusted items are escalated."""
import argparse, os, sys
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
rc = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "role_conditioned_panels"); sys.path.insert(0, rc)
from data import load_judgments
from audit import match_matrix

ap = argparse.ArgumentParser(); ap.add_argument("--judgments", required=True); ap.add_argument("--bench", required=True)
ap.add_argument("--scores", required=True); ap.add_argument("--n-boot", type=int, default=2000); a = ap.parse_args()
d = load_judgments(a.judgments, a.bench, condition="none"); J = list(d.judge_names)
S = pd.read_csv(a.scores).set_index("item_id").loc[d.item_ids]; groups = S["group"].astype(str).values
C = match_matrix(d.Z, d.Y); b = int(C.mean(0).argmax()); err = 1 - C[:, b]; n = len(err)
others = [k for k in range(len(J)) if k != b]
dis = (d.Z[:, others] != d.Z[:, [b]]).mean(1)
p = np.clip(S[f"p_{J[b]}"].values, 1e-4, 1 - 1e-4); lg = np.log(p / (1 - p))
rng = np.random.default_rng(0); ug = np.unique(groups); fold = {g: i % 5 for i, g in enumerate(rng.permutation(ug))}; f = np.array([fold[g] for g in groups])
both = np.zeros(n)
for k in range(5):
    tr, te = f != k, f == k; X = np.column_stack([lg, dis])
    both[te] = LogisticRegression().fit(X[tr], err[tr]).predict_proba(X[te])[:, 1]
sig = {"probe (activations)": 1 - p, "other judges disagree": dis, "both combined": both}
idx_by_g = {g: np.where(groups == g)[0] for g in ug}; boots = [np.concatenate([idx_by_g[g] for g in rng.choice(ug, len(ug))]) for _ in range(a.n_boot)]
print(f"\n{a.bench}: strongest judge = {J[b]}, accuracy {1 - err.mean():.3f}, {n} items, {len(ug)} questions")
print("AUROC for 'strongest judge is wrong'  (mean [95% CI over questions])")
for k, s in sig.items():
    v = [roc_auc_score(err[i], s[i]) for i in boots if 0 < err[i].sum() < len(i)]
    print(f"  {k:24s} {roc_auc_score(err, s):.3f}  [{np.percentile(v, 2.5):.3f}, {np.percentile(v, 97.5):.3f}]")
dd = [roc_auc_score(err[i], sig["probe (activations)"][i]) - roc_auc_score(err[i], dis[i]) for i in boots]
print(f"  probe minus disagreement: {np.mean(dd):+.3f} [{np.percentile(dd, 2.5):+.3f}, {np.percentile(dd, 97.5):+.3f}]")
print(f"\nAccuracy of {J[b]} on the items it keeps, if the least-trusted items are escalated (random escalation keeps {1 - err.mean():.3f})")
print(f"  {'escalate':>8} | " + " | ".join(f"{k[:22]:>22}" for k in sig))
for esc in (0.1, 0.2, 0.3, 0.5):
    row = []
    for s in sig.values():
        keep = np.argsort(s)[: int(round((1 - esc) * n))]; row.append(f"{1 - err[keep].mean():.3f}")
    print(f"  {esc:>8.0%} | " + " | ".join(f"{r:>22}" for r in row))
