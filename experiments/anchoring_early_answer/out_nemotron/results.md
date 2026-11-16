# Early answering: is own-answer anchoring already there before the judge reasons?

Source: `out_nemotron/`, answer matcher: GLM-5.3-Flash. Judges: the three Qwen models of the Tinker pool, thinking off, their own pool transcripts. Each judgment is read at A (before any reasoning), 25/50/75% of the reasoning, and C (the real verdict line), by appending `VERDICT:` and comparing the log-probabilities of the two verdict words.

Checks: rebuilt prompt length equals the pool's in 1738/1738 judgments; the C readout equals the parsed spoken verdict in 0.967 of 1635.

## 1. Wrong candidates: how often the judge accepts, by checkpoint

Single-answer benchmarks: *match* = the wrong answer equals the judge's own (wrong) answer; *differ* = the judge's own answer was something else. JudgeBench (pairwise): *match* = exactly one response reaches the judge's own answer and it is the wrong one; *differ* = neither response reaches it; 'accepts' = the judge picks the wrong response.

| Benchmark | Judge | Group | n | A | 25% | 50% | 75% | C |
|---|---|---|---|---|---|---|---|---|
| bff | nemotron3-super-120b | match | 39 | 0.77 | 0.85 | 0.79 | 0.82 | 0.82 |
| bff | nemotron3-super-120b | differ | 143 | 0.34 | 0.36 | 0.36 | 0.38 | 0.38 |
| judgebench | nemotron3-super-120b | match | 63 | 0.49 | 0.51 | 0.46 | 0.44 | 0.43 |
| judgebench | nemotron3-super-120b | differ | 77 | 0.36 | 0.35 | 0.34 | 0.32 | 0.34 |
| rb2math | nemotron3-super-120b | match | 64 | 0.58 | 0.78 | 0.73 | 0.78 | 0.83 |
| rb2math | nemotron3-super-120b | differ | 448 | 0.33 | 0.34 | 0.28 | 0.25 | 0.25 |

## 2. The errors: was the judge already accepting at A?

Errors = wrong candidates the judge accepts at C. 'Already at A' = it also accepted at A, before writing any reasoning.

| Benchmark | Judge | Anchoring errors (match) | already at A | Other errors (differ) | already at A |
|---|---|---|---|---|---|
| bff | nemotron3-super-120b | 32 | 0.88 | 55 | 0.73 |
| judgebench | nemotron3-super-120b | 27 | 0.89 | 26 | 0.81 |
| rb2math | nemotron3-super-120b | 53 | 0.70 | 113 | 0.83 |

## 3. Does reasoning rescue the judge? (wrong candidates that were accepted at A)

Share that the judge rejects by C, after accepting at A.

| Benchmark | Judge | match: n | match: rescued | differ: n | differ: rescued |
|---|---|---|---|---|---|
| bff | nemotron3-super-120b | 30 | 0.07 | 49 | 0.18 |
| judgebench | nemotron3-super-120b | 31 | 0.23 | 28 | 0.25 |
| rb2math | nemotron3-super-120b | 37 | 0.00 | 146 | 0.36 |

## 4. Same for correct candidates (control)

| Benchmark | Judge | Group | n | accepts at A | accepts at C |
|---|---|---|---|---|---|
| bff | nemotron3-super-120b | match | 224 | 0.91 | 0.92 |
| bff | nemotron3-super-120b | differ | 32 | 0.62 | 0.75 |
| judgebench | nemotron3-super-120b | match | 362 | 0.64 | 0.72 |
| rb2math | nemotron3-super-120b | match | 158 | 0.89 | 0.93 |
| rb2math | nemotron3-super-120b | differ | 25 | 0.40 | 0.68 |

## 5. Pooled over judges, with 95% intervals (questions resampled)

Wrong candidates only. Gap = accept rate when the wrong answer matches the judge's own answer minus when it differs. Rescue gap = how much more often reasoning overturns an accept-at-A when the judge's own answer differs than when it matches.

| Benchmark | Gap at A | Gap at C | Rescue gap |
|---|---|---|---|
| main | +0.26 [+0.17, +0.35] | +0.38 [+0.30, +0.47] | +0.21 [+0.13, +0.30] |
| rb2math | +0.25 [+0.11, +0.38] | +0.58 [+0.46, +0.67] | +0.36 [+0.28, +0.44] |
| judgebench | +0.13 [-0.04, +0.30] | +0.09 [-0.07, +0.26] | +0.02 [-0.20, +0.25] |
| bff | +0.43 [+0.24, +0.57] | +0.44 [+0.25, +0.59] | +0.12 [-0.05, +0.27] |
| bbeh | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |

## 6. Control: the same wrong candidate, judged by Qwens whose own answers differ

A wrong answer the judge also gave may just be a convincing wrong answer to everyone. This compares the three Qwens on the SAME wrong candidate (candidate fixed effects) and removes each judge's overall leniency (judge fixed effects). Single-answer benchmarks only (JudgeBench's groups are defined per pair, not per candidate).

| Benchmark | Own-answer effect at A | at 50% | at C |
|---|---|---|---|
| main | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
| rb2math | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
| bff | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
| bbeh | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
