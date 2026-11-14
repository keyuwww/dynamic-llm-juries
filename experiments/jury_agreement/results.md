# Agreement-aware vs family-aware jury (BBEH, condition = none)

Cases: 920 (item, examinee) pairs, each judged by all 8 pool models. Gold CORRECT share: 0.35. Unparsed verdicts count as INCORRECT.

A juror's own answer comes from its separate Phase-1 solve call; the judging prompt never shows it. 'Matches' = juror's committed answer equals the candidate's; 'differs' = committed a different answer; 'no answer' = juror's solve attempt was truncated.

## Unsupervised juries (no labels)

| Jury | Accuracy | κ | Mean jurors |
|---|---|---|---|
| Best single judge (gpt-oss-120b, picked in hindsight) | 0.717 | 0.393 | 1.0 |
| Majority, all 8 | 0.667 | 0.288 | 8.0 |
| Majority, self-recusal | 0.653 | 0.275 | 7.0 |
| Majority, family recusal (proposal method B) | 0.660 | 0.272 | 5.8 |
| Majority, agreement recusal (drop jurors whose own answer matches) | 0.613 | 0.116 | 5.9 |
| Majority, keep only jurors with a committed differing answer | 0.602 | 0.071 | 2.8 |
| No verdicts: CORRECT if >= 1 juror's own answer matches | 0.689 | 0.433 | 8.0 |
| No verdicts: CORRECT if >= 2 jurors' own answers match | 0.764 | 0.498 | 8.0 |
| No verdicts: CORRECT if >= 3 jurors' own answers match | 0.761 | 0.457 | 8.0 |

## Label-light juries (logistic regression on votes, 5-fold CV grouped by item, 50 repeats)

Each model sees the same 8 verdicts; they differ only in what each vote is allowed to depend on.

| Features | Accuracy (mean ± sd) | κ (mean ± sd) |
|---|---|---|
| verdicts | 0.717 ± 0.003 | 0.361 ± 0.007 |
| verdicts x family | 0.721 ± 0.005 | 0.371 ± 0.012 |
| verdicts x agreement | 0.763 ± 0.005 | 0.455 ± 0.012 |
| verdicts x family x agreement | 0.752 ± 0.007 | 0.432 ± 0.016 |
| agreement only (no verdicts) | 0.805 ± 0.005 | 0.558 ± 0.011 |
| verdicts x agreement + agreement | 0.811 ± 0.005 | 0.575 ± 0.012 |

## Head-to-head (κ)

| Comparison | Mean Δκ | Repeats where first wins | 95% item-bootstrap CI (repeat 0) |
|---|---|---|---|
| verdicts x agreement vs verdicts x family | +0.084 | 100% | [+0.029, +0.127] |
| verdicts x agreement vs verdicts | +0.094 | 100% | [+0.037, +0.134] |
| verdicts x family vs verdicts | +0.010 | 80% | [-0.032, +0.051] |
| verdicts x family x agreement vs verdicts x agreement | -0.022 | 8% | [-0.056, +0.012] |
| verdicts x agreement + agreement vs verdicts x agreement | +0.121 | 100% | [+0.043, +0.158] |
| verdicts x agreement + agreement vs agreement only (no verdicts) | +0.017 | 92% | [-0.052, +0.028] |

## By examinee strength (repeat-0 out-of-fold predictions; unsupervised rows exact)

Strong examinee = BBEH solve accuracy above the pool mean (0.293).

| Jury | κ weak examinees | κ strong examinees |
|---|---|---|
| Majority, all 8 | 0.406 | 0.095 |
| Majority, family recusal (proposal method B) | 0.398 | 0.050 |
| Majority, agreement recusal (drop jurors whose own answer matches) | 0.188 | 0.021 |
| LR: verdicts | 0.457 | 0.160 |
| LR: verdicts x family | 0.441 | 0.208 |
| LR: verdicts x agreement | 0.540 | 0.261 |
| LR: verdicts x agreement + agreement | 0.599 | 0.388 |

n weak = 640, n strong = 280.
