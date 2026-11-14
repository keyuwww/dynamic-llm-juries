# qwen3.6-35b-a3b-think — anchoring and the cross-family test

Own answers: 1400 questions, 1353 finished within 64K tokens. Judgments: 2658; spoken verdict in the requested format: 2653, + 0 read by GLM. Analysed rows: 2201. Checkpoints: A, 25, 50, 75, E, C, S.

## 0. Does it tell right from wrong? Accept rate (right / wrong candidate)

| Benchmark | A (before writing) | 25% | 50% | 75% | E (end of thinking) | C (readout at verdict) | spoken verdict |
|---|---|---|---|---|---|---|---|
| rb2math | 0.88 / 0.35 | 0.88 / 0.11 | 0.90 / 0.11 | 0.90 / 0.11 | 0.90 / 0.11 | 0.90 / 0.11 | 0.90 / 0.11 |
| judgebench | 0.74 / 0.54 | 0.85 / 0.46 | 0.92 / 0.46 | 0.95 / 0.45 | 0.96 / 0.43 | 0.96 / 0.43 | 0.96 / 0.43 |
| bff | 0.85 / 0.40 | 0.82 / 0.18 | 0.84 / 0.24 | 0.85 / 0.24 | 0.85 / 0.24 | 0.85 / 0.24 | 0.85 / 0.24 |
| bbeh | 0.52 / 0.53 | 0.68 / 0.58 | 0.77 / 0.55 | 0.83 / 0.54 | 0.87 / 0.53 | 0.87 / 0.53 | 0.87 / 0.53 |

## 1. Wrong candidates: accept rate by checkpoint, own answer matches vs differs

| Benchmark | Group | n | A | 25 | 50 | 75 | E | C | S |
|---|---|---|---|---|---|---|---|---|---|
| rb2math | match | 63 | 0.52 | 0.54 | 0.60 | 0.60 | 0.60 | 0.60 | 0.60 |
| rb2math | differ | 451 | 0.33 | 0.06 | 0.05 | 0.04 | 0.04 | 0.04 | 0.04 |
| judgebench | match | 34 | 0.71 | 0.65 | 0.62 | 0.62 | 0.59 | 0.59 | 0.59 |
| judgebench | differ | 33 | 0.36 | 0.27 | 0.30 | 0.27 | 0.27 | 0.27 | 0.27 |
| bff | match | 30 | 0.63 | 0.70 | 0.83 | 0.83 | 0.83 | 0.83 | 0.83 |
| bff | differ | 147 | 0.35 | 0.07 | 0.12 | 0.12 | 0.12 | 0.12 | 0.12 |
| bbeh | match | 69 | 0.74 | 0.80 | 0.86 | 0.87 | 0.86 | 0.86 | 0.86 |
| bbeh | differ | 206 | 0.46 | 0.51 | 0.46 | 0.44 | 0.42 | 0.42 | 0.42 |

Gap = accept rate when the wrong answer matches the judge's own minus when it differs; rescue gap = how much more often reasoning overturns an accept-at-A when the judge's answer differs. 95% intervals, questions resampled.

| Benchmark | Gap at A (before writing) | Gap at E (end of thinking) | Gap at spoken verdict | Rescue gap |
|---|---|---|---|---|
| main | +0.27 [+0.17, +0.36] | +0.58 [+0.48, +0.66] | +0.58 [+0.48, +0.66] | +0.62 [+0.50, +0.73] |
| rb2math | +0.20 [+0.06, +0.33] | +0.56 [+0.44, +0.68] | +0.56 [+0.44, +0.68] | +0.70 [+0.54, +0.85] |
| judgebench | +0.34 [+0.13, +0.56] | +0.32 [+0.08, +0.53] | +0.32 [+0.08, +0.53] | +0.21 [-0.13, +0.55] |
| bff | +0.29 [+0.04, +0.46] | +0.71 [+0.51, +0.85] | +0.71 [+0.51, +0.85] | +0.73 [+0.52, +0.88] |
| bbeh | +0.28 [+0.14, +0.42] | +0.44 [+0.32, +0.55] | +0.44 [+0.32, +0.55] | +0.39 [+0.26, +0.52] |

## 2. Cross-family: does it accept the wrong answers the Qwens believe?

Wrong single-answer candidates. 'Qwens who gave it' = how many of the 3 Qwens produced that same wrong answer when solving. Split by whether this judge's own answer matches.

| Own answer | Qwens who gave it | n | accepts at A | spoken |
|---|---|---|---|---|
| differs | 0 | 718 | 0.34 | 0.11 |
| differs | 1 | 52 | 0.63 | 0.54 |
| differs | 2 | 29 | 0.48 | 0.52 |
| differs | 3 | 5 | 0.40 | 0.60 |
| matchs | 0 | 17 | 0.24 | 0.41 |
| matchs | 1 | 26 | 0.69 | 0.77 |
| matchs | 2 | 41 | 0.76 | 0.85 |
| matchs | 3 | 78 | 0.64 | 0.77 |

When its own answer differs: accept rate for wrong answers 2–3 Qwens gave minus wrong answers no Qwen gave (95% interval, questions resampled):

- A (before writing): +0.13 [-0.05, +0.32]
- spoken verdict: +0.42 [+0.24, +0.60]

## 3. Same wrong candidate, 3 Qwens + this judge (judge + candidate fixed effects)

| | effect of 'matches my own answer' |
|---|---|
| A | +0.067 [+0.012, +0.129] |
| C | +0.036 [-0.029, +0.099] |
