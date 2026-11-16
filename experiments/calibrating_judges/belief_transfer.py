#!/usr/bin/env python
"""Does belief escalation work on a benchmark it was not trained on? BFF <-> RB2 Math, Qwen3.5-4B / 9B, belief from 1 own solve. Saved records only.
  within      combiner trained on other questions of the same benchmark (5 folds by question, 3 seeds)   [needs labels from this benchmark]
  cross       combiner trained on ALL items of the other benchmark, same judge                           [no labels from this benchmark]  PRIMARY
  zero-label  no training at all: escalate first the items where the verdict disagrees with the judge's own solve
              (says CORRECT but its own answer differs, or INCORRECT but its own answer matches); random order otherwise
Baselines: judge's own confidence, verdict-only rule, random. Accuracy with 20% escalated to the stronger judge (BFF: top-3 pool vote; RB2 Math: 35B).
Pre-registered: 'cross' beats BOTH the confidence baseline and the verdict-only rule at 20% with 95% paired bootstrap CIs above 0 in >= 3 of 4 settings."""
import json, numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
exec(open("belief_variants.py").read().split("r1, r2, r3, passes = [], [], [], 0")[0])     # loads data, helpers and the four settings
def fit_pred(Xtr, ytr, Xte):
    sc = StandardScaler().fit(Xtr); return LogisticRegression(max_iter=2000).fit(sc.transform(Xtr), ytr).predict_proba(sc.transform(Xte))[:, 1]
F = {}
for st in settings:
    b1 = belief_k(st["j"], st["items"], 1); m0 = np.nan_to_num(b1, nan=0.5); st["X"] = feats(b1, st["v"], m0)
    st["disagree"] = ((st["v"] == 1) != (np.nan_to_num(b1, nan=0.5) >= 0.5)) & ~np.isnan(b1)
rows, passes = [], 0
for st in settings:
    other = [o for o in settings if o["j"] == st["j"] and o is not st][0]; ol, oh, fin, v, g = st["ol"], st["oh"], st["fin"], st["v"], st["g"]; n = len(ol); tie = np.random.default_rng(12345).random(n)
    S_in = oof(st["X"], ol, g); s_cross = fit_pred(other["X"], other["ol"], st["X"])
    f = {"within": lambda bi: np.mean([acc(ol[bi], oh[bi], escmask(S_in[s][bi], fin[bi], tie[bi], 0.2)) for s in range(3)]),
         "cross": lambda bi: acc(ol[bi], oh[bi], escmask(s_cross[bi], fin[bi], tie[bi], 0.2)),
         "zero_label": lambda bi: np.mean([acc(ol[bi], oh[bi], escmask((~st["disagree"]).astype(float)[bi] + 0.5 * np.random.default_rng(s).random(n)[bi], fin[bi], tie[bi], 0.2)) for s in range(20)]),
         "confidence": lambda bi: acc(ol[bi], oh[bi], escmask(st["conf"][bi], fin[bi], tie[bi], 0.2)),
         "verdict_only": lambda bi: np.mean([acc(ol[bi], oh[bi], escmask((np.where(v == 1, 0, 1) + 0.5 * np.random.default_rng(s).random(n))[bi], fin[bi], tie[bi], 0.2)) for s in range(20)])}
    al = np.arange(n); row = dict(setting=st["name"], trained_on=other["name"].split(" Qwen")[0], random=(ol.mean() + 0.2 * (oh.mean() - ol.mean())) * 100, **{k: fn(al) * 100 for k, fn in f.items()},
                                  disagree_share=st["disagree"].mean() * 100)
    lo1, hi1 = boot(lambda bi: f["cross"](bi) - f["confidence"](bi), g); lo2, hi2 = boot(lambda bi: f["cross"](bi) - f["verdict_only"](bi), g)
    row["cross_minus_conf"] = f"{row['cross'] - row['confidence']:+.1f} [{lo1:+.1f},{hi1:+.1f}]"; row["cross_minus_verdict"] = f"{row['cross'] - row['verdict_only']:+.1f} [{lo2:+.1f},{hi2:+.1f}]"
    passes += (lo1 > 0) and (lo2 > 0); rows.append(row)
pd.set_option("display.width", 260); print(pd.DataFrame(rows).round(1).to_string(index=False))
print(f"\nPRE-REGISTERED ('cross' beats confidence AND verdict-only with CIs above 0 in >= 3 of 4): {passes} -> {'PASS' if passes >= 3 else 'FAIL'}")
