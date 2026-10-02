# B5 Jury-on-Demand (lite reproduction): reliability-weighted top-K judge voting

Pool of 4 pseudo-judges (2 backends x 2 conditions) on 456 items common to all four. Reliability predicted out-of-fold (5-fold CV) by a from-scratch logistic regression over structural features (log input tokens, turn, annotator count, examinee model, the judge's own p/confidence) -- substituting for the paper's XGBoost + token-distribution/embedding features, which need infra not available offline here.

| Strategy | Accuracy | Cohen's kappa |
|---|---|---|
| single judge: jev_ref | 0.928 | 0.856 |
| top-1 reliability-weighted | 0.917 | 0.834 |
| top-2 reliability-weighted | 0.904 | 0.808 |
| top-3 reliability-weighted | 0.893 | 0.787 |
| top-4 reliability-weighted | 0.879 | 0.762 |
| unweighted majority (all 4) | 0.768 | 0.553 |
| single judge: jev_noref | 0.761 | 0.505 |
| single judge: clm_noref | 0.441 | 0.000 |
| single judge: clm_ref | 0.439 | -0.012 |

## Per-judge reliability predictor quality
(AUROC of the out-of-fold predictor for 'will THIS judge be correct on this item', from structural features alone)

| Judge | Reliability-predictor AUROC |
|---|---|
| jev_noref | 0.723 |
| jev_ref | 0.883 |
| clm_noref | 0.820 |
| clm_ref | 0.785 |