# Early answering: is own-answer anchoring already there before the judge reasons?

Source: `out_deepseek/`, answer matcher: GLM-5.3-Flash. Judges: the three Qwen models of the Tinker pool, thinking off, their own pool transcripts. Each judgment is read at A (before any reasoning), 25/50/75% of the reasoning, and C (the real verdict line), by appending `VERDICT:` and comparing the log-probabilities of the two verdict words.

Checks: rebuilt prompt length equals the pool's in 1738/1738 judgments; the C readout equals the parsed spoken verdict in 1.000 of 1628.

## 1. Wrong candidates: how often the judge accepts, by checkpoint

Single-answer benchmarks: *match* = the wrong answer equals the judge's own (wrong) answer; *differ* = the judge's own answer was something else. JudgeBench (pairwise): *match* = exactly one response reaches the judge's own answer and it is the wrong one; *differ* = neither response reaches it; 'accepts' = the judge picks the wrong response.

| Benchmark | Judge | Group | n | A | 25% | 50% | 75% | C |
|---|---|---|---|---|---|---|---|---|
| bff | deepseek-v4.1-flash | match | 44 | 0.43 | – | – | – | 0.52 |
| bff | deepseek-v4.1-flash | differ | 136 | 0.12 | – | – | – | 0.15 |
| judgebench | deepseek-v4.1-flash | match | 49 | 0.59 | – | – | – | 0.53 |
| judgebench | deepseek-v4.1-flash | differ | 37 | 0.30 | – | – | – | 0.24 |
| rb2math | deepseek-v4.1-flash | match | 60 | 0.50 | – | – | – | 0.75 |
| rb2math | deepseek-v4.1-flash | differ | 452 | 0.26 | – | – | – | 0.16 |

## 2. The errors: was the judge already accepting at A?

Errors = wrong candidates the judge accepts at C. 'Already at A' = it also accepted at A, before writing any reasoning.

| Benchmark | Judge | Anchoring errors (match) | already at A | Other errors (differ) | already at A |
|---|---|---|---|---|---|
| bff | deepseek-v4.1-flash | 23 | 0.74 | 21 | 0.24 |
| judgebench | deepseek-v4.1-flash | 26 | 0.73 | 9 | 0.67 |
| rb2math | deepseek-v4.1-flash | 45 | 0.64 | 73 | 0.78 |

## 3. Does reasoning rescue the judge? (wrong candidates that were accepted at A)

Share that the judge rejects by C, after accepting at A.

| Benchmark | Judge | match: n | match: rescued | differ: n | differ: rescued |
|---|---|---|---|---|---|
| bff | deepseek-v4.1-flash | 19 | 0.11 | 16 | 0.69 |
| judgebench | deepseek-v4.1-flash | 29 | 0.34 | 11 | 0.45 |
| rb2math | deepseek-v4.1-flash | 30 | 0.03 | 118 | 0.52 |

## 4. Same for correct candidates (control)

| Benchmark | Judge | Group | n | accepts at A | accepts at C |
|---|---|---|---|---|---|
| bff | deepseek-v4.1-flash | match | 223 | 0.85 | 0.91 |
| bff | deepseek-v4.1-flash | differ | 32 | 0.28 | 0.22 |
| judgebench | deepseek-v4.1-flash | match | 413 | 0.68 | 0.84 |
| rb2math | deepseek-v4.1-flash | match | 161 | 0.88 | 0.95 |
| rb2math | deepseek-v4.1-flash | differ | 21 | 0.57 | 0.52 |

## 5. Pooled over judges, with 95% intervals (questions resampled)

Wrong candidates only. Gap = accept rate when the wrong answer matches the judge's own answer minus when it differs. Rescue gap = how much more often reasoning overturns an accept-at-A when the judge's own answer differs than when it matches.

| Benchmark | Gap at A | Gap at C | Rescue gap |
|---|---|---|---|
| main | +0.28 [+0.20, +0.36] | +0.45 [+0.37, +0.53] | +0.36 [+0.24, +0.48] |
| rb2math | +0.24 [+0.10, +0.37] | +0.59 [+0.47, +0.70] | +0.48 [+0.36, +0.59] |
| judgebench | +0.29 [+0.09, +0.49] | +0.29 [+0.09, +0.48] | +0.11 [-0.24, +0.45] |
| bff | +0.31 [+0.15, +0.45] | +0.37 [+0.15, +0.53] | +0.58 [+0.22, +0.88] |
| bbeh | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |

## 6. Control: the same wrong candidate, judged by Qwens whose own answers differ

A wrong answer the judge also gave may just be a convincing wrong answer to everyone. This compares the three Qwens on the SAME wrong candidate (candidate fixed effects) and removes each judge's overall leniency (judge fixed effects). Single-answer benchmarks only (JudgeBench's groups are defined per pair, not per candidate).

| Benchmark | Own-answer effect at A | at 50% | at C |
|---|---|---|---|
| main | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
| rb2math | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
| bff | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
| bbeh | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
