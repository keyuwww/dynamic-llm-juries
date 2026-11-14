# Probes at position A — qwen3.5-9b

2199 judgments, 32 layers. Hidden state = residual stream at the last token of `...VERDICT:` before the judge writes anything. Probes are logistic regressions, cross-validated with whole questions held out. AUROC 0.5 = chance, 1.0 = perfect.

## 1. "Is this right?" probe vs. the judge's own verdict

Candidates that never wrote a final answer are dropped (always wrong, trivially detectable). 'Text baseline' = logistic regression on prompt length, benchmark, which model wrote the candidate and whether it has a final answer -- no hidden state.

Each cell: AUROC over all candidates / **within-question** AUROC (only compares candidates of the same question, so question difficulty and task type cancel out; the fair test). 'layer-1 probe' is the same probe on the first layer, a stronger surface baseline.

| Set | n | verdict at A | spoken verdict at C | text baseline | layer-1 probe | probe: best layer | probe |
|---|---|---|---|---|---|---|---|
| BBEH | 610 | 0.516 / **0.645** | 0.619 / **0.647** | 0.573 / **0.558** | 0.634 / **0.536** | 19 | 0.737 / **0.652** |
| RB2 Math | 732 | 0.807 / **0.837** | 0.803 / **0.804** | 0.512 / **0.518** | 0.702 / **0.736** | 31 | 0.836 / **0.849** |
| BBEH + RB2 Math | 1342 | 0.688 / **0.798** | 0.734 / **0.776** | 0.668 / **0.491** | 0.720 / **0.667** | 31 | 0.809 / **0.805** |
| JudgeBench (pairwise) | 547 | 0.726 / **nan** | nan / **nan** | 0.527 / **nan** | 0.555 / **nan** | 28 | 0.688 / **nan** |

Probe AUROC by layer:

| Layer | BBEH | RB2 Math | BBEH + RB2 Math | JudgeBench (pairwise) |
|---|---|---|---|---|
| 1 | 0.634 | 0.702 | 0.720 | 0.555 |
| 4 | 0.668 | 0.710 | 0.743 | 0.510 |
| 7 | 0.663 | 0.721 | 0.746 | 0.549 |
| 10 | 0.694 | 0.740 | 0.757 | 0.553 |
| 13 | 0.711 | 0.771 | 0.766 | 0.585 |
| 16 | 0.722 | 0.779 | 0.759 | 0.640 |
| 19 | 0.737 | 0.801 | 0.788 | 0.649 |
| 22 | 0.714 | 0.813 | 0.791 | 0.675 |
| 25 | 0.715 | 0.823 | 0.796 | 0.670 |
| 28 | 0.710 | 0.821 | 0.804 | 0.688 |
| 31 | 0.707 | 0.836 | 0.809 | 0.687 |
| 32 | 0.686 | 0.829 | 0.804 | 0.680 |

## 2. Wrong answers: what the judge says vs. what the layer-31 probe says

'Accepts' = says CORRECT. The probe's threshold is set so that, over all 1235 candidates, it accepts exactly as often as the spoken verdict (0.55); so any difference below is about WHICH answers it accepts, not how lenient it is.

| Candidates | n | verdict at A accepts | spoken verdict at C accepts | probe accepts |
|---|---|---|---|---|
| wrong, own answer matches | 126 | 0.45 | 0.73 | 0.48 |
| wrong, own answer differs | 632 | 0.26 | 0.30 | 0.35 |
| correct (any) | 477 | 0.48 | 0.84 | 0.82 |

Anchoring errors (wrong, matches the judge's own answer, accepted in the spoken verdict): n = 92; at the same leniency the probe rejects 0.45 of them.

## 3. "This matches my own answer" probe (wrong candidates only)

n = 760 wrong candidates (126 match). Holding correctness fixed, so the probe cannot just be reading 'is this right'.

Text baseline (no hidden state) AUROC: 0.661. The judge's own verdict margin at A, as a predictor of match: 0.676.

| Layer | AUROC |
|---|---|
| 1 | 0.641 |
| 4 | 0.684 |
| 7 | 0.649 |
| 10 | 0.684 |
| 13 | 0.652 |
| 16 | 0.684 |
| 19 | 0.726 |
| 22 | 0.717 |
| 25 | 0.722 |
| 28 | 0.711 |
| 31 | 0.706 |
| 32 | 0.707 |

Steering directions written: correctness (layer 28), agreement (layer 19), random control (layer 28); each scaled to one standard deviation of the projections; 910 items.
