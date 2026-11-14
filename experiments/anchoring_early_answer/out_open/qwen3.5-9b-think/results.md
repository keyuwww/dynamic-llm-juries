# qwen3.5-9b-think — anchoring and the cross-family test

Own answers: 1400 questions, 1262 finished within 64K tokens. Judgments: 2658; spoken verdict in the requested format: 2576, + 1 read by GLM. Analysed rows: 2049. Checkpoints: A, 25, 50, 75, E, C, S.

## 0. Does it tell right from wrong? Accept rate (right / wrong candidate)

| Benchmark | A (before writing) | 25% | 50% | 75% | E (end of thinking) | C (readout at verdict) | spoken verdict |
|---|---|---|---|---|---|---|---|
| rb2math | 0.79 / 0.35 | 0.80 / 0.14 | 0.85 / 0.12 | 0.88 / 0.11 | 0.88 / 0.12 | 0.88 / 0.12 | 0.88 / 0.12 |
| judgebench | 0.63 / 0.41 | 0.75 / 0.42 | 0.92 / 0.47 | 0.95 / 0.45 | 0.97 / 0.47 | 0.97 / 0.47 | 0.97 / 0.47 |
| bff | 0.72 / 0.23 | 0.74 / 0.11 | 0.80 / 0.12 | 0.83 / 0.15 | 0.84 / 0.14 | 0.84 / 0.14 | 0.84 / 0.14 |
| bbeh | 0.56 / 0.49 | 0.58 / 0.51 | 0.78 / 0.62 | 0.85 / 0.60 | 0.88 / 0.62 | 0.88 / 0.62 | 0.88 / 0.62 |

## 1. Wrong candidates: accept rate by checkpoint, own answer matches vs differs

| Benchmark | Group | n | A | 25 | 50 | 75 | E | C | S |
|---|---|---|---|---|---|---|---|---|---|
| rb2math | match | 60 | 0.47 | 0.47 | 0.65 | 0.67 | 0.70 | 0.70 | 0.70 |
| rb2math | differ | 373 | 0.33 | 0.09 | 0.03 | 0.02 | 0.02 | 0.02 | 0.02 |
| judgebench | match | 42 | 0.52 | 0.50 | 0.64 | 0.64 | 0.64 | 0.64 | 0.64 |
| judgebench | differ | 43 | 0.30 | 0.35 | 0.30 | 0.26 | 0.30 | 0.30 | 0.30 |
| bff | match | 30 | 0.50 | 0.43 | 0.53 | 0.53 | 0.53 | 0.53 | 0.53 |
| bff | differ | 149 | 0.17 | 0.05 | 0.04 | 0.07 | 0.06 | 0.06 | 0.06 |
| bbeh | match | 68 | 0.66 | 0.63 | 0.87 | 0.90 | 0.93 | 0.93 | 0.93 |
| bbeh | differ | 178 | 0.44 | 0.47 | 0.53 | 0.48 | 0.50 | 0.50 | 0.50 |

Gap = accept rate when the wrong answer matches the judge's own minus when it differs; rescue gap = how much more often reasoning overturns an accept-at-A when the judge's answer differs. 95% intervals, questions resampled.

| Benchmark | Gap at A (before writing) | Gap at E (end of thinking) | Gap at spoken verdict | Rescue gap |
|---|---|---|---|---|
| main | +0.21 [+0.11, +0.30] | +0.59 [+0.50, +0.67] | +0.59 [+0.50, +0.67] | +0.73 [+0.62, +0.83] |
| rb2math | +0.14 [+0.01, +0.27] | +0.68 [+0.56, +0.79] | +0.68 [+0.56, +0.79] | +0.79 [+0.64, +0.92] |
| judgebench | +0.22 [+0.02, +0.43] | +0.34 [+0.14, +0.53] | +0.34 [+0.14, +0.53] | +0.36 [+0.03, +0.67] |
| bff | +0.33 [+0.11, +0.51] | +0.47 [+0.30, +0.65] | +0.47 [+0.30, +0.65] | +0.66 [+0.39, +0.92] |
| bbeh | +0.22 [+0.07, +0.37] | +0.43 [+0.32, +0.52] | +0.43 [+0.32, +0.52] | +0.28 [+0.15, +0.40] |

## 2. Cross-family: does it accept the wrong answers the Qwens believe?

Wrong single-answer candidates. 'Qwens who gave it' = how many of the 3 Qwens produced that same wrong answer when solving. Split by whether this judge's own answer matches.

| Own answer | Qwens who gave it | n | accepts at A | spoken |
|---|---|---|---|---|
| differs | 0 | 629 | 0.31 | 0.12 |
| differs | 1 | 47 | 0.47 | 0.43 |
| differs | 2 | 16 | 0.31 | 0.38 |
| differs | 3 | 8 | 0.50 | 0.62 |
| matchs | 0 | 16 | 0.19 | 0.69 |
| matchs | 1 | 22 | 0.73 | 0.82 |
| matchs | 2 | 54 | 0.57 | 0.76 |
| matchs | 3 | 66 | 0.58 | 0.77 |

When its own answer differs: accept rate for wrong answers 2–3 Qwens gave minus wrong answers no Qwen gave (95% interval, questions resampled):

- A (before writing): +0.06 [-0.16, +0.29]
- spoken verdict: +0.34 [+0.09, +0.58]

## 3. Same wrong candidate, 3 Qwens + this judge (judge + candidate fixed effects)

| | effect of 'matches my own answer' |
|---|---|
| A | +0.075 [+0.011, +0.132] |
| C | +0.087 [+0.021, +0.147] |
