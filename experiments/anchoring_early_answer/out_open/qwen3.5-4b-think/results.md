# qwen3.5-4b-think — anchoring and the cross-family test

Own answers: 1400 questions, 1199 finished within 64K tokens. Judgments: 2658; spoken verdict in the requested format: 2499, + 4 read by GLM. Analysed rows: 2016. Checkpoints: A, 25, 50, 75, E, C, S.

## 0. Does it tell right from wrong? Accept rate (right / wrong candidate)

| Benchmark | A (before writing) | 25% | 50% | 75% | E (end of thinking) | C (readout at verdict) | spoken verdict |
|---|---|---|---|---|---|---|---|
| rb2math | 0.73 / 0.30 | 0.74 / 0.09 | 0.81 / 0.08 | 0.83 / 0.08 | 0.86 / 0.09 | 0.86 / 0.09 | 0.86 / 0.09 |
| judgebench | 0.66 / 0.43 | 0.76 / 0.42 | 0.89 / 0.46 | 0.95 / 0.49 | 0.94 / 0.45 | 0.94 / 0.45 | 0.94 / 0.45 |
| bff | 0.67 / 0.21 | 0.71 / 0.13 | 0.76 / 0.15 | 0.80 / 0.17 | 0.82 / 0.21 | 0.82 / 0.21 | 0.82 / 0.21 |
| bbeh | 0.34 / 0.35 | 0.36 / 0.29 | 0.66 / 0.47 | 0.79 / 0.55 | 0.84 / 0.59 | 0.84 / 0.59 | 0.84 / 0.59 |

## 1. Wrong candidates: accept rate by checkpoint, own answer matches vs differs

| Benchmark | Group | n | A | 25 | 50 | 75 | E | C | S |
|---|---|---|---|---|---|---|---|---|---|
| rb2math | match | 49 | 0.45 | 0.35 | 0.53 | 0.59 | 0.59 | 0.59 | 0.59 |
| rb2math | differ | 383 | 0.28 | 0.05 | 0.02 | 0.02 | 0.02 | 0.02 | 0.02 |
| judgebench | match | 53 | 0.53 | 0.53 | 0.64 | 0.66 | 0.64 | 0.64 | 0.64 |
| judgebench | differ | 66 | 0.36 | 0.33 | 0.32 | 0.36 | 0.29 | 0.29 | 0.29 |
| bff | match | 33 | 0.36 | 0.45 | 0.52 | 0.58 | 0.70 | 0.70 | 0.70 |
| bff | differ | 146 | 0.17 | 0.06 | 0.08 | 0.08 | 0.10 | 0.10 | 0.10 |
| bbeh | match | 59 | 0.53 | 0.39 | 0.78 | 0.88 | 0.90 | 0.90 | 0.90 |
| bbeh | differ | 171 | 0.29 | 0.26 | 0.38 | 0.45 | 0.49 | 0.49 | 0.49 |

Gap = accept rate when the wrong answer matches the judge's own minus when it differs; rescue gap = how much more often reasoning overturns an accept-at-A when the judge's answer differs. 95% intervals, questions resampled.

| Benchmark | Gap at A (before writing) | Gap at E (end of thinking) | Gap at spoken verdict | Rescue gap |
|---|---|---|---|---|
| main | +0.19 [+0.10, +0.28] | +0.57 [+0.48, +0.65] | +0.57 [+0.48, +0.65] | +0.69 [+0.56, +0.80] |
| rb2math | +0.16 [+0.02, +0.31] | +0.57 [+0.43, +0.71] | +0.57 [+0.43, +0.71] | +0.74 [+0.54, +0.91] |
| judgebench | +0.16 [-0.01, +0.35] | +0.35 [+0.18, +0.51] | +0.35 [+0.18, +0.51] | +0.38 [+0.11, +0.62] |
| bff | +0.19 [-0.02, +0.37] | +0.60 [+0.41, +0.76] | +0.60 [+0.41, +0.76] | +0.79 [+0.41, +1.00] |
| bbeh | +0.23 [+0.08, +0.38] | +0.41 [+0.30, +0.52] | +0.41 [+0.30, +0.52] | +0.32 [+0.19, +0.47] |

## 2. Cross-family: does it accept the wrong answers the Qwens believe?

Wrong single-answer candidates. 'Qwens who gave it' = how many of the 3 Qwens produced that same wrong answer when solving. Split by whether this judge's own answer matches.

| Own answer | Qwens who gave it | n | accepts at A | spoken |
|---|---|---|---|---|
| differs | 0 | 619 | 0.26 | 0.11 |
| differs | 1 | 47 | 0.28 | 0.47 |
| differs | 2 | 25 | 0.16 | 0.48 |
| differs | 3 | 9 | 0.67 | 0.56 |
| matchs | 0 | 21 | 0.29 | 0.48 |
| matchs | 1 | 17 | 0.53 | 0.94 |
| matchs | 2 | 45 | 0.56 | 0.76 |
| matchs | 3 | 58 | 0.43 | 0.78 |

When its own answer differs: accept rate for wrong answers 2–3 Qwens gave minus wrong answers no Qwen gave (95% interval, questions resampled):

- A (before writing): +0.03 [-0.14, +0.22]
- spoken verdict: +0.39 [+0.20, +0.57]

## 3. Same wrong candidate, 3 Qwens + this judge (judge + candidate fixed effects)

| | effect of 'matches my own answer' |
|---|---|
| A | +0.069 [+0.014, +0.128] |
| C | +0.071 [+0.004, +0.137] |
