# Belief bias on minimal pairs (JudgeBench, answer-only)

Same question, same response text ("The answer is (X)." + XXXXX); only the letter X changes. Belief = share of the judge's own 7 solves ending in X. Margin = log p(CORRECT) - log p(INCORRECT) right after "VERDICT:" (no written reasoning). Accept = margin > 0. 95% intervals resample whole questions.


## qwen3.5-9b: 245 questions, 2296 letters

| letter | n | accept | mean margin |
|---|---|---|---|
| wrong, 0/7 | 1866 | 11% [8, 13] | -1.64 |
| wrong, 1-3/7 | 123 | 34% [25, 44] | -0.59 |
| wrong, 4-6/7 | 41 | 68% [54, 83] | +0.25 |
| wrong, 7/7 | 21 | 81% [67, 95] | +0.96 |
| correct, < 4/7 | 77 | 29% [18, 39] | -0.78 |
| correct, >= 4/7 | 168 | 46% [39, 54] | +0.03 |

Within-question slope among WRONG letters (question + letter fixed effects), belief 0 -> 1: accept +82 points [+71, +94], margin +3.27 [+2.77, +3.76].

Pair-difference direction: 62 questions have both a believed (>= 4/7) and a never-reached wrong letter. Held-out score = AUROC believed vs never among wrong letters of the other half (0.5 = chance); 'correct vs never' = how the same direction ranks the correct letter.

| layer | believed vs never (held out) | correct vs never (held out) | margin alone, believed vs never | cos with ridge belief dir (RB2 / BFF) |
|---|---|---|---|---|
| 2 | 0.50 | 0.51 | 0.88 | – / – |
| 4 | 0.55 | 0.52 | 0.88 | – / – |
| 6 | 0.56 | 0.52 | 0.88 | – / – |
| 8 | 0.56 | 0.51 | 0.88 | – / – |
| 10 | 0.55 | 0.51 | 0.88 | – / – |
| 12 | 0.55 | 0.53 | 0.88 | – / – |
| 14 | 0.60 | 0.57 | 0.88 | +0.03 / +0.00 |
| 16 | 0.60 | 0.60 | 0.88 | +0.04 / -0.01 |
| 18 | 0.68 | 0.66 | 0.88 | +0.09 / +0.05 |
| 20 | 0.70 | 0.66 | 0.88 | +0.08 / +0.04 |
| 22 | 0.70 | 0.67 | 0.88 | +0.08 / +0.04 |
| 24 | 0.84 | 0.73 | 0.88 | +0.06 / +0.03 |
| 26 | 0.83 | 0.73 | 0.88 | +0.06 / +0.03 |
| 28 | 0.82 | 0.72 | 0.88 | – / – |
| 30 | 0.84 | 0.74 | 0.88 | – / – |
| 32 | 0.86 | 0.75 | 0.88 | – / – |

## qwen3.5-4b: 172 questions, 1589 letters

| letter | n | accept | mean margin |
|---|---|---|---|
| wrong, 0/7 | 1237 | 3% [2, 4] | -2.09 |
| wrong, 1-3/7 | 131 | 8% [4, 14] | -1.47 |
| wrong, 4-6/7 | 37 | 19% [8, 32] | -0.67 |
| wrong, 7/7 | 12 | 42% [17, 67] | -0.39 |
| correct, < 4/7 | 73 | 11% [4, 18] | -1.43 |
| correct, >= 4/7 | 99 | 25% [17, 34] | -0.84 |

Within-question slope among WRONG letters (question + letter fixed effects), belief 0 -> 1: accept +31 points [+18, +44], margin +2.26 [+1.82, +2.80].

Pair-difference direction: 49 questions have both a believed (>= 4/7) and a never-reached wrong letter. Held-out score = AUROC believed vs never among wrong letters of the other half (0.5 = chance); 'correct vs never' = how the same direction ranks the correct letter.

| layer | believed vs never (held out) | correct vs never (held out) | margin alone, believed vs never | cos with ridge belief dir (RB2 / BFF) |
|---|---|---|---|---|
| 2 | 0.50 | 0.50 | 0.84 | – / – |
| 4 | 0.44 | 0.53 | 0.84 | – / – |
| 6 | 0.56 | 0.52 | 0.84 | – / – |
| 8 | 0.52 | 0.51 | 0.84 | – / – |
| 10 | 0.41 | 0.51 | 0.84 | – / – |
| 12 | 0.39 | 0.49 | 0.84 | – / – |
| 14 | 0.53 | 0.58 | 0.84 | – / – |
| 16 | 0.71 | 0.67 | 0.84 | – / – |
| 18 | 0.81 | 0.74 | 0.84 | – / – |
| 20 | 0.82 | 0.75 | 0.84 | – / – |
| 22 | 0.84 | 0.75 | 0.84 | – / – |
| 24 | 0.84 | 0.75 | 0.84 | – / – |
| 26 | 0.85 | 0.75 | 0.84 | – / – |
| 28 | 0.85 | 0.75 | 0.84 | – / – |
| 30 | 0.85 | 0.75 | 0.84 | – / – |
| 32 | 0.85 | 0.75 | 0.84 | – / – |
