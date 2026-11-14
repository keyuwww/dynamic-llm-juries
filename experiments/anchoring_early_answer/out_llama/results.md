# llama3.1-8b — anchoring and the cross-family test

Own answers: 1102 questions, 1047 finished within 64K tokens. Judgments: 2199; spoken verdict in the requested format: 2012, + 101 read by GLM. Analysed rows: 1712. Checkpoints: A, S.

## 0. Does it tell right from wrong? Accept rate (right / wrong candidate)

| Benchmark | A (before writing) | spoken verdict |
|---|---|---|
| bbeh | 0.55 / 0.62 | 0.52 / 0.55 |
| rb2math | 0.80 / 0.63 | 0.83 / 0.67 |
| judgebench | 0.62 / 0.46 | 0.56 / 0.46 |

## 1. Wrong candidates: accept rate by checkpoint, own answer matches vs differs

| Benchmark | Group | n | A | S |
|---|---|---|---|---|
| bbeh | match | 30 | 0.77 | 0.60 |
| bbeh | differ | 222 | 0.60 | 0.54 |
| rb2math | match | 78 | 0.60 | 0.65 |
| rb2math | differ | 418 | 0.63 | 0.67 |
| judgebench | match | 77 | 0.42 | 0.52 |
| judgebench | differ | 308 | 0.47 | 0.44 |

Gap = accept rate when the wrong answer matches the judge's own minus when it differs; rescue gap = how much more often reasoning overturns an accept-at-A when the judge's answer differs. 95% intervals, questions resampled.

| Benchmark | Gap at A (before writing) | Gap at spoken verdict | Rescue gap |
|---|---|---|---|
| all | -0.02 [-0.10, +0.06] | +0.02 [-0.06, +0.10] | +0.01 [-0.08, +0.09] |
| bbeh | +0.16 [-0.02, +0.33] | +0.06 [-0.14, +0.24] | +0.00 [-0.22, +0.20] |
| judgebench | -0.05 [-0.18, +0.07] | +0.07 [-0.05, +0.19] | +0.10 [-0.06, +0.24] |
| rb2math | -0.03 [-0.15, +0.09] | -0.02 [-0.13, +0.10] | -0.04 [-0.16, +0.08] |

## 2. Cross-family: does it accept the wrong answers the Qwens believe?

Wrong single-answer candidates. 'Qwens who gave it' = how many of the 3 Qwens produced that same wrong answer when solving. Split by whether this judge's own answer matches.

| Own answer | Qwens who gave it | n | accepts at A | spoken |
|---|---|---|---|---|
| differs | 0 | 511 | 0.61 | 0.64 |
| differs | 1 | 48 | 0.75 | 0.58 |
| differs | 2 | 39 | 0.72 | 0.54 |
| differs | 3 | 42 | 0.52 | 0.64 |
| matchs | 0 | 62 | 0.60 | 0.63 |
| matchs | 1 | 9 | 0.67 | 0.56 |
| matchs | 2 | 12 | 0.83 | 0.58 |
| matchs | 3 | 25 | 0.68 | 0.72 |

When its own answer differs: accept rate for wrong answers 2–3 Qwens gave minus wrong answers no Qwen gave (95% interval, questions resampled):

- A (before writing): +0.01 [-0.12, +0.13]
- spoken verdict: -0.04 [-0.17, +0.08]

## 3. Same wrong candidate, 3 Qwens + this judge (judge + candidate fixed effects)

| | effect of 'matches my own answer' |
|---|---|
| A | +0.077 [+0.006, +0.147] |
| C | +0.128 [+0.063, +0.196] |
