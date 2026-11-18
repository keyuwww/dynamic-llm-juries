# Early answering: is own-answer anchoring already there before the judge reasons?

Source: `out_nano/`, answer matcher: GLM-5.3-Flash. Judges: the three Qwen models of the Tinker pool, thinking off, their own pool transcripts. Each judgment is read at A (before any reasoning), 25/50/75% of the reasoning, and C (the real verdict line), by appending `VERDICT:` and comparing the log-probabilities of the two verdict words.

Checks: rebuilt prompt length equals the pool's in 1735/1735 judgments; the C readout equals the parsed spoken verdict in 1.000 of 1648.

## 1. Wrong candidates: how often the judge accepts, by checkpoint

Single-answer benchmarks: *match* = the wrong answer equals the judge's own (wrong) answer; *differ* = the judge's own answer was something else. JudgeBench (pairwise): *match* = exactly one response reaches the judge's own answer and it is the wrong one; *differ* = neither response reaches it; 'accepts' = the judge picks the wrong response.

| Benchmark | Judge | Group | n | A | 25% | 50% | 75% | C |
|---|---|---|---|---|---|---|---|---|
| bff | nemotron3-nano-30b | match | 42 | – | – | – | – | 0.43 |
| bff | nemotron3-nano-30b | differ | 141 | – | – | – | – | 0.33 |
| judgebench | nemotron3-nano-30b | match | 90 | – | – | – | – | 0.37 |
| judgebench | nemotron3-nano-30b | differ | 296 | – | – | – | – | 0.42 |
| rb2math | nemotron3-nano-30b | match | 72 | – | – | – | – | 0.65 |
| rb2math | nemotron3-nano-30b | differ | 440 | – | – | – | – | 0.41 |

## 2. The errors: was the judge already accepting at A?

Errors = wrong candidates the judge accepts at C. 'Already at A' = it also accepted at A, before writing any reasoning.

| Benchmark | Judge | Anchoring errors (match) | already at A | Other errors (differ) | already at A |
|---|---|---|---|---|---|
| bff | nemotron3-nano-30b | 0 | – | 0 | – |
| judgebench | nemotron3-nano-30b | 0 | – | 0 | – |
| rb2math | nemotron3-nano-30b | 0 | – | 0 | – |

## 3. Does reasoning rescue the judge? (wrong candidates that were accepted at A)

Share that the judge rejects by C, after accepting at A.

| Benchmark | Judge | match: n | match: rescued | differ: n | differ: rescued |
|---|---|---|---|---|---|
| bff | nemotron3-nano-30b | 0 | – | 0 | – |
| judgebench | nemotron3-nano-30b | 0 | – | 0 | – |
| rb2math | nemotron3-nano-30b | 0 | – | 0 | – |

## 4. Same for correct candidates (control)

| Benchmark | Judge | Group | n | accepts at A | accepts at C |
|---|---|---|---|---|---|

## 5. Pooled over judges, with 95% intervals (questions resampled)

Wrong candidates only. Gap = accept rate when the wrong answer matches the judge's own answer minus when it differs. Rescue gap = how much more often reasoning overturns an accept-at-A when the judge's own answer differs than when it matches.

| Benchmark | Gap at A | Gap at C | Rescue gap |
|---|---|---|---|
| main | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
| rb2math | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
| judgebench | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
| bff | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
| bbeh | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |

## 6. Control: the same wrong candidate, judged by Qwens whose own answers differ

A wrong answer the judge also gave may just be a convincing wrong answer to everyone. This compares the three Qwens on the SAME wrong candidate (candidate fixed effects) and removes each judge's overall leniency (judge fixed effects). Single-answer benchmarks only (JudgeBench's groups are defined per pair, not per candidate).

| Benchmark | Own-answer effect at A | at 50% | at C |
|---|---|---|---|
| main | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
| rb2math | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
| bff | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
| bbeh | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
