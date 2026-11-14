# Agreement-aware vs family-aware jury (BBEH, condition = none) -- committed candidates only

Cases: 610 (item, examinee) pairs, each judged by all 8 pool models. Gold CORRECT share: 0.53. Unparsed verdicts count as INCORRECT.

A juror's own answer comes from its separate Phase-1 solve call; the judging prompt never shows it. 'Matches' = juror's committed answer equals the candidate's; 'differs' = committed a different answer; 'no answer' = juror's solve attempt was truncated.

## Unsupervised juries (no labels)

| Jury | Accuracy | κ | Mean jurors |
|---|---|---|---|
| Best single judge (gpt-oss-120b, picked in hindsight) | 0.634 | 0.267 | 1.0 |
| Majority, all 8 | 0.585 | 0.170 | 8.0 |
| Majority, self-recusal | 0.579 | 0.153 | 7.0 |
| Majority, family recusal (proposal method B) | 0.577 | 0.154 | 5.9 |
| Majority, agreement recusal (drop jurors whose own answer matches) | 0.503 | 0.025 | 4.8 |
| Majority, keep only jurors with a committed differing answer | 0.472 | -0.032 | 2.9 |
| No verdicts: CORRECT if >= 1 juror's own answer matches | 0.531 | 0.000 | 8.0 |
| No verdicts: CORRECT if >= 2 jurors' own answers match | 0.644 | 0.279 | 8.0 |
| No verdicts: CORRECT if >= 3 jurors' own answers match | 0.639 | 0.283 | 8.0 |

## Label-light juries (logistic regression on votes, 5-fold CV grouped by item, 50 repeats)

Each model sees the same 8 verdicts; they differ only in what each vote is allowed to depend on.

| Features | Accuracy (mean ± sd) | κ (mean ± sd) |
|---|---|---|
| verdicts | 0.640 ± 0.008 | 0.273 ± 0.017 |
| verdicts x family | 0.632 ± 0.007 | 0.254 ± 0.014 |
| verdicts x agreement | 0.673 ± 0.009 | 0.343 ± 0.018 |
| verdicts x family x agreement | 0.666 ± 0.009 | 0.328 ± 0.019 |
| agreement only (no verdicts) | 0.716 ± 0.007 | 0.427 ± 0.015 |
| verdicts x agreement + agreement | 0.726 ± 0.007 | 0.449 ± 0.014 |

## Head-to-head (κ)

| Comparison | Mean Δκ | Repeats where first wins | 95% item-bootstrap CI (repeat 0) |
|---|---|---|---|
| verdicts x agreement vs verdicts x family | +0.089 | 100% | [+0.044, +0.185] |
| verdicts x agreement vs verdicts | +0.070 | 100% | [-0.007, +0.135] |
| verdicts x family vs verdicts | -0.019 | 22% | [-0.098, -0.007] |
| verdicts x family x agreement vs verdicts x agreement | -0.015 | 22% | [-0.089, +0.021] |
| verdicts x agreement + agreement vs verdicts x agreement | +0.106 | 100% | [+0.018, +0.158] |
| verdicts x agreement + agreement vs agreement only (no verdicts) | +0.022 | 88% | [-0.036, +0.079] |

## By examinee strength (repeat-0 out-of-fold predictions; unsupervised rows exact)

Strong examinee = BBEH solve accuracy above the pool mean (0.293).

| Jury | κ weak examinees | κ strong examinees |
|---|---|---|
| Majority, all 8 | 0.312 | 0.030 |
| Majority, family recusal (proposal method B) | 0.317 | -0.025 |
| Majority, agreement recusal (drop jurors whose own answer matches) | 0.091 | -0.029 |
| LR: verdicts | 0.378 | 0.170 |
| LR: verdicts x family | 0.312 | 0.146 |
| LR: verdicts x agreement | 0.419 | 0.251 |
| LR: verdicts x agreement + agreement | 0.458 | 0.401 |

n weak = 361, n strong = 249.
