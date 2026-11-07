# Gap check: Qwen3.5-0.8B, forced verdict, thinking off (held-out test split)

Probe layer and regularization chosen on dev, refit on train+dev, scored once on test. 95% CIs: bootstrap over test questions/pairs/prompts. Gap = probe − verdict (paired).

## rb2safety

900 items (50% positive); test 168 items from 84 groups; 0 truncated. Verdict says positive 10% of test items, accuracy 48%.

| Score | Test AUROC [95% CI] | minus verdict [95% CI] |
|---|---|---|
| Verdict P(positive) | 0.51 [0.45, 0.58] |  |
| Logit lens, layer 19 | 0.64 [0.58, 0.70] | +0.06 to +0.19 |
| Hidden-state probe, layer 14 | 0.97 [0.95, 0.99] | +0.39 to +0.52 |
| Surface features only | 0.97 [0.93, 0.99] | +0.37 to +0.52 |
| Surface features + probe | 1.00 [0.99, 1.00] | +0.41 to +0.54 |

- within response model x refusal (strata with both labels) (5 strata, test): verdict 0.56, probe 0.97
- All items, 5-fold CV grouped by question/pair/prompt (layer 14): verdict 0.52, probe 0.96, surface 0.97; within response model x refusal (strata with both labels): verdict 0.55, probe 0.90, surface 0.55
- Probe dev AUROC by layer (0 = embeddings): 0.50 0.79 0.81 0.78 0.87 0.88 0.90 0.90 0.89 0.91 0.93 0.94 0.94 0.95 0.98 0.97 0.96 0.95 0.96 0.95 0.95 0.94 0.95 0.94 0.94

## bff

459 items (56% positive); test 74 items from 15 groups; 0 truncated. Verdict says positive 45% of test items, accuracy 62%.

| Score | Test AUROC [95% CI] | minus verdict [95% CI] |
|---|---|---|
| Verdict P(positive) | 0.71 [0.51, 0.86] |  |
| Logit lens, layer 17 | 0.77 [0.47, 0.95] | -0.12 to +0.21 |
| Hidden-state probe, layer 21 | 0.92 [0.83, 0.99] | +0.08 to +0.40 |
| Surface features only | 0.87 [0.77, 0.95] | -0.00 to +0.38 |
| Surface features + probe | 0.92 [0.84, 0.98] | +0.08 to +0.40 |

- within answer model (6 strata, test): verdict 0.72, probe 0.92
- All items, 5-fold CV grouped by question/pair/prompt (layer 21): verdict 0.63, probe 0.85, surface 0.84; within answer model: verdict 0.64, probe 0.84, surface 0.80
- Probe dev AUROC by layer (0 = embeddings): 0.50 0.85 0.87 0.83 0.83 0.77 0.81 0.82 0.84 0.86 0.84 0.85 0.85 0.87 0.89 0.85 0.87 0.87 0.87 0.87 0.88 0.90 0.89 0.88 0.86

## judgebench

700 items (50% positive); test 150 items from 75 groups; 0 truncated. Verdict says positive 84% of test items, accuracy 55%.

| Score | Test AUROC [95% CI] | minus verdict [95% CI] |
|---|---|---|
| Verdict P(positive) | 0.55 [0.47, 0.62] |  |
| Logit lens, layer 17 | 0.54 [0.47, 0.61] | -0.06 to +0.04 |
| Hidden-state probe, layer 23 | 0.63 [0.54, 0.71] | +0.01 to +0.15 |
| Surface features only | 0.61 [0.49, 0.74] | -0.09 to +0.22 |
| Surface features + probe | 0.64 [0.56, 0.72] | +0.02 to +0.17 |

- within category (16 strata, test): verdict 0.53, probe 0.62
- All items, 5-fold CV grouped by question/pair/prompt (layer 23): verdict 0.55, probe 0.60, surface 0.53; within category: verdict 0.54, probe 0.60, surface 0.53
- Position bias (test pairs): same slot picked in both orders for 76% of 75 pairs; says A for 84% of test items
- Verdict averaged over both orders (constant A bias removed): AUROC 0.63, accuracy 57%
- Probe dev AUROC by layer (0 = embeddings): 0.50 0.55 0.53 0.53 0.56 0.55 0.57 0.57 0.52 0.53 0.53 0.57 0.59 0.59 0.61 0.60 0.62 0.61 0.61 0.61 0.63 0.63 0.64 0.64 0.64
