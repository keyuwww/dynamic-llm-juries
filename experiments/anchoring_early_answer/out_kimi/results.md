# Early answering: is own-answer anchoring already there before the judge reasons?

Source: `out_kimi/`, answer matcher: GLM-5.3-Flash. Judges: the three Qwen models of the Tinker pool, thinking off, their own pool transcripts. Each judgment is read at A (before any reasoning), 25/50/75% of the reasoning, and C (the real verdict line), by appending `VERDICT:` and comparing the log-probabilities of the two verdict words.

Checks: rebuilt prompt length equals the pool's in 1738/1738 judgments; the C readout equals the parsed spoken verdict in 1.000 of 1622.

## 1. Wrong candidates: how often the judge accepts, by checkpoint

Single-answer benchmarks: *match* = the wrong answer equals the judge's own (wrong) answer; *differ* = the judge's own answer was something else. JudgeBench (pairwise): *match* = exactly one response reaches the judge's own answer and it is the wrong one; *differ* = neither response reaches it; 'accepts' = the judge picks the wrong response.

| Benchmark | Judge | Group | n | A | 25% | 50% | 75% | C |
|---|---|---|---|---|---|---|---|---|
| bff | kimi-k2.6 | match | 42 | 0.43 | – | – | – | 0.43 |
| bff | kimi-k2.6 | differ | 140 | 0.11 | – | – | – | 0.04 |
| judgebench | kimi-k2.6 | match | 48 | 0.50 | – | – | – | 0.56 |
| judgebench | kimi-k2.6 | differ | 34 | 0.29 | – | – | – | 0.29 |
| rb2math | kimi-k2.6 | match | 66 | 0.32 | – | – | – | 0.55 |
| rb2math | kimi-k2.6 | differ | 448 | 0.17 | – | – | – | 0.02 |

## 2. The errors: was the judge already accepting at A?

Errors = wrong candidates the judge accepts at C. 'Already at A' = it also accepted at A, before writing any reasoning.

| Benchmark | Judge | Anchoring errors (match) | already at A | Other errors (differ) | already at A |
|---|---|---|---|---|---|
| bff | kimi-k2.6 | 18 | 0.56 | 5 | 0.40 |
| judgebench | kimi-k2.6 | 27 | 0.56 | 10 | 0.60 |
| rb2math | kimi-k2.6 | 36 | 0.42 | 8 | 0.50 |

## 3. Does reasoning rescue the judge? (wrong candidates that were accepted at A)

Share that the judge rejects by C, after accepting at A.

| Benchmark | Judge | match: n | match: rescued | differ: n | differ: rescued |
|---|---|---|---|---|---|
| bff | kimi-k2.6 | 18 | 0.44 | 15 | 0.87 |
| judgebench | kimi-k2.6 | 24 | 0.38 | 10 | 0.40 |
| rb2math | kimi-k2.6 | 21 | 0.29 | 77 | 0.95 |

## 4. Same for correct candidates (control)

| Benchmark | Judge | Group | n | accepts at A | accepts at C |
|---|---|---|---|---|---|
| bff | kimi-k2.6 | match | 226 | 0.76 | 0.74 |
| bff | kimi-k2.6 | differ | 27 | 0.22 | 0.22 |
| judgebench | kimi-k2.6 | match | 410 | 0.71 | 0.94 |
| rb2math | kimi-k2.6 | match | 157 | 0.75 | 0.91 |
| rb2math | kimi-k2.6 | differ | 26 | 0.38 | 0.50 |

## 5. Pooled over judges, with 95% intervals (questions resampled)

Wrong candidates only. Gap = accept rate when the wrong answer matches the judge's own answer minus when it differs. Rescue gap = how much more often reasoning overturns an accept-at-A when the judge's own answer differs than when it matches.

| Benchmark | Gap at A | Gap at C | Rescue gap |
|---|---|---|---|
| main | +0.24 [+0.15, +0.33] | +0.49 [+0.41, +0.56] | +0.52 [+0.38, +0.66] |
| rb2math | +0.15 [+0.04, +0.27] | +0.54 [+0.41, +0.66] | +0.66 [+0.46, +0.86] |
| judgebench | +0.21 [-0.01, +0.42] | +0.27 [+0.05, +0.48] | +0.03 [-0.35, +0.39] |
| bff | +0.32 [+0.12, +0.51] | +0.39 [+0.17, +0.54] | +0.42 [-0.02, +0.73] |
| bbeh | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |

## 6. Control: the same wrong candidate, judged by Qwens whose own answers differ

A wrong answer the judge also gave may just be a convincing wrong answer to everyone. This compares the three Qwens on the SAME wrong candidate (candidate fixed effects) and removes each judge's overall leniency (judge fixed effects). Single-answer benchmarks only (JudgeBench's groups are defined per pair, not per candidate).

| Benchmark | Own-answer effect at A | at 50% | at C |
|---|---|---|---|
| main | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
| rb2math | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
| bff | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
| bbeh | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
