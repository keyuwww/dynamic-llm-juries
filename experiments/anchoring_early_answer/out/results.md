# Early answering: is own-answer anchoring already there before the judge reasons?

Source: `out/`, answer matcher: GLM-5.3-Flash. Judges: the three Qwen models of the Tinker pool, thinking off, their own pool transcripts. Each judgment is read at A (before any reasoning), 25/50/75% of the reasoning, and C (the real verdict line), by appending `VERDICT:` and comparing the log-probabilities of the two verdict words.

Checks: rebuilt prompt length equals the pool's in 7974/7974 judgments; the C readout equals the parsed spoken verdict in 0.999 of 6519.

## 1. Wrong candidates: how often the judge accepts, by checkpoint

Single-answer benchmarks: *match* = the wrong answer equals the judge's own (wrong) answer; *differ* = the judge's own answer was something else. JudgeBench (pairwise): *match* = exactly one response reaches the judge's own answer and it is the wrong one; *differ* = neither response reaches it; 'accepts' = the judge picks the wrong response.

| Benchmark | Judge | Group | n | A | 25% | 50% | 75% | C |
|---|---|---|---|---|---|---|---|---|
| bbeh | qwen3.5-4b | match | 61 | 0.41 | – | 0.46 | – | 0.70 |
| bbeh | qwen3.5-4b | differ | 184 | 0.23 | – | 0.39 | – | 0.52 |
| bbeh | qwen3.5-9b | match | 65 | 0.54 | – | 0.58 | – | 0.77 |
| bbeh | qwen3.5-9b | differ | 184 | 0.27 | – | 0.41 | – | 0.50 |
| bbeh | qwen3.6-35b-a3b | match | 58 | 0.60 | – | 0.67 | – | 0.84 |
| bbeh | qwen3.6-35b-a3b | differ | 200 | 0.21 | – | 0.28 | – | 0.41 |
| bff | qwen3.5-4b | match | 31 | 0.29 | 0.55 | 0.58 | 0.58 | 0.61 |
| bff | qwen3.5-4b | differ | 149 | 0.12 | 0.32 | 0.31 | 0.32 | 0.33 |
| bff | qwen3.5-9b | match | 37 | 0.35 | 0.57 | 0.57 | 0.59 | 0.65 |
| bff | qwen3.5-9b | differ | 145 | 0.13 | 0.26 | 0.21 | 0.19 | 0.19 |
| bff | qwen3.6-35b-a3b | match | 36 | 0.64 | 0.53 | 0.47 | 0.50 | 0.56 |
| bff | qwen3.6-35b-a3b | differ | 147 | 0.24 | 0.23 | 0.12 | 0.09 | 0.08 |
| judgebench | qwen3.5-4b | match | 68 | 0.54 | – | 0.44 | – | 0.41 |
| judgebench | qwen3.5-4b | differ | 116 | 0.31 | – | 0.33 | – | 0.28 |
| judgebench | qwen3.5-9b | match | 52 | 0.52 | – | 0.54 | – | 0.54 |
| judgebench | qwen3.5-9b | differ | 56 | 0.30 | – | 0.27 | – | 0.25 |
| judgebench | qwen3.6-35b-a3b | match | 49 | 0.61 | – | 0.63 | – | 0.57 |
| judgebench | qwen3.6-35b-a3b | differ | 43 | 0.40 | – | 0.33 | – | 0.35 |
| rb2math | qwen3.5-4b | match | 67 | 0.42 | – | 0.60 | – | 0.63 |
| rb2math | qwen3.5-4b | differ | 442 | 0.26 | – | 0.32 | – | 0.30 |
| rb2math | qwen3.5-9b | match | 61 | 0.44 | – | 0.62 | – | 0.69 |
| rb2math | qwen3.5-9b | differ | 450 | 0.28 | – | 0.25 | – | 0.21 |
| rb2math | qwen3.6-35b-a3b | match | 60 | 0.47 | – | 0.48 | – | 0.57 |
| rb2math | qwen3.6-35b-a3b | differ | 451 | 0.25 | – | 0.12 | – | 0.07 |

## 2. The errors: was the judge already accepting at A?

Errors = wrong candidates the judge accepts at C. 'Already at A' = it also accepted at A, before writing any reasoning.

| Benchmark | Judge | Anchoring errors (match) | already at A | Other errors (differ) | already at A |
|---|---|---|---|---|---|
| bbeh | qwen3.5-4b | 43 | 0.49 | 96 | 0.42 |
| bbeh | qwen3.5-9b | 50 | 0.60 | 91 | 0.38 |
| bbeh | qwen3.6-35b-a3b | 49 | 0.63 | 82 | 0.38 |
| bff | qwen3.5-4b | 19 | 0.47 | 49 | 0.31 |
| bff | qwen3.5-9b | 24 | 0.50 | 27 | 0.41 |
| bff | qwen3.6-35b-a3b | 20 | 0.95 | 12 | 0.58 |
| judgebench | qwen3.5-4b | 28 | 0.79 | 32 | 0.59 |
| judgebench | qwen3.5-9b | 28 | 0.61 | 14 | 0.43 |
| judgebench | qwen3.6-35b-a3b | 28 | 0.75 | 15 | 0.60 |
| rb2math | qwen3.5-4b | 42 | 0.60 | 131 | 0.63 |
| rb2math | qwen3.5-9b | 42 | 0.64 | 95 | 0.69 |
| rb2math | qwen3.6-35b-a3b | 34 | 0.65 | 31 | 0.84 |

## 3. Does reasoning rescue the judge? (wrong candidates that were accepted at A)

Share that the judge rejects by C, after accepting at A.

| Benchmark | Judge | match: n | match: rescued | differ: n | differ: rescued |
|---|---|---|---|---|---|
| bbeh | qwen3.5-4b | 25 | 0.16 | 42 | 0.05 |
| bbeh | qwen3.5-9b | 35 | 0.14 | 49 | 0.29 |
| bbeh | qwen3.6-35b-a3b | 35 | 0.11 | 42 | 0.26 |
| bff | qwen3.5-4b | 9 | 0.00 | 18 | 0.17 |
| bff | qwen3.5-9b | 13 | 0.08 | 19 | 0.42 |
| bff | qwen3.6-35b-a3b | 23 | 0.17 | 36 | 0.81 |
| judgebench | qwen3.5-4b | 37 | 0.41 | 36 | 0.47 |
| judgebench | qwen3.5-9b | 27 | 0.37 | 17 | 0.65 |
| judgebench | qwen3.6-35b-a3b | 30 | 0.30 | 17 | 0.47 |
| rb2math | qwen3.5-4b | 28 | 0.11 | 115 | 0.28 |
| rb2math | qwen3.5-9b | 27 | 0.00 | 125 | 0.47 |
| rb2math | qwen3.6-35b-a3b | 28 | 0.21 | 112 | 0.77 |

## 4. Same for correct candidates (control)

| Benchmark | Judge | Group | n | accepts at A | accepts at C |
|---|---|---|---|---|---|
| bbeh | qwen3.5-4b | match | 144 | 0.36 | 0.78 |
| bbeh | qwen3.5-4b | differ | 145 | 0.19 | 0.52 |
| bbeh | qwen3.5-9b | match | 180 | 0.41 | 0.89 |
| bbeh | qwen3.5-9b | differ | 115 | 0.23 | 0.70 |
| bbeh | qwen3.6-35b-a3b | match | 186 | 0.38 | 0.90 |
| bbeh | qwen3.6-35b-a3b | differ | 102 | 0.22 | 0.56 |
| bff | qwen3.5-4b | match | 212 | 0.66 | 0.86 |
| bff | qwen3.5-4b | differ | 43 | 0.33 | 0.51 |
| bff | qwen3.5-9b | match | 217 | 0.68 | 0.87 |
| bff | qwen3.5-9b | differ | 38 | 0.29 | 0.50 |
| bff | qwen3.6-35b-a3b | match | 220 | 0.84 | 0.80 |
| bff | qwen3.6-35b-a3b | differ | 36 | 0.56 | 0.19 |
| judgebench | qwen3.5-4b | match | 327 | 0.65 | 0.87 |
| judgebench | qwen3.5-9b | match | 393 | 0.66 | 0.88 |
| judgebench | qwen3.6-35b-a3b | match | 407 | 0.73 | 0.98 |
| rb2math | qwen3.5-4b | match | 156 | 0.76 | 0.92 |
| rb2math | qwen3.5-4b | differ | 26 | 0.46 | 0.73 |
| rb2math | qwen3.5-9b | match | 153 | 0.78 | 0.91 |
| rb2math | qwen3.5-9b | differ | 29 | 0.52 | 0.69 |
| rb2math | qwen3.6-35b-a3b | match | 150 | 0.84 | 0.93 |
| rb2math | qwen3.6-35b-a3b | differ | 32 | 0.69 | 0.69 |

## 5. Pooled over judges, with 95% intervals (questions resampled)

Wrong candidates only. Gap = accept rate when the wrong answer matches the judge's own answer minus when it differs. Rescue gap = how much more often reasoning overturns an accept-at-A when the judge's own answer differs than when it matches.

| Benchmark | Gap at A | Gap at C | Rescue gap |
|---|---|---|---|
| main | +0.23 [+0.17, +0.30] | +0.37 [+0.31, +0.43] | +0.29 [+0.21, +0.37] |
| rb2math | +0.18 [+0.06, +0.30] | +0.44 [+0.33, +0.53] | +0.39 [+0.30, +0.48] |
| judgebench | +0.23 [+0.12, +0.34] | +0.21 [+0.10, +0.32] | +0.15 [-0.02, +0.32] |
| bff | +0.27 [+0.12, +0.38] | +0.41 [+0.27, +0.52] | +0.44 [+0.26, +0.62] |
| bbeh | +0.28 [+0.18, +0.39] | +0.29 [+0.21, +0.38] | +0.07 [-0.06, +0.18] |

## 6. Control: the same wrong candidate, judged by Qwens whose own answers differ

A wrong answer the judge also gave may just be a convincing wrong answer to everyone. This compares the three Qwens on the SAME wrong candidate (candidate fixed effects) and removes each judge's overall leniency (judge fixed effects). Single-answer benchmarks only (JudgeBench's groups are defined per pair, not per candidate).

| Benchmark | Own-answer effect at A | at 50% | at C |
|---|---|---|---|
| main | +0.139 [+0.051, +0.234] | +0.044 [-0.061, +0.150] | +0.061 [-0.033, +0.152] |
| rb2math | +0.086 [-0.059, +0.222] | -0.079 [-0.264, +0.107] | -0.020 [-0.192, +0.172] |
| bff | +0.173 [+0.051, +0.313] | +0.121 [-0.007, +0.249] | +0.112 [+0.001, +0.233] |
| bbeh | +0.062 [-0.037, +0.184] | +0.020 [-0.114, +0.162] | +0.055 [-0.081, +0.194] |
