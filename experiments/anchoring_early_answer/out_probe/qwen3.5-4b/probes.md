# Probes at position A — qwen3.5-4b

2199 judgments, 32 layers. Hidden state = residual stream at the last token of `...VERDICT:` before the judge writes anything. Probes are logistic regressions, cross-validated with whole questions held out. AUROC 0.5 = chance, 1.0 = perfect.

## 1. "Is this right?" probe vs. the judge's own verdict

Candidates that never wrote a final answer are dropped (always wrong, trivially detectable). 'Text baseline' = logistic regression on prompt length, benchmark, which model wrote the candidate and whether it has a final answer -- no hidden state.

Each cell: AUROC over all candidates / **within-question** AUROC (only compares candidates of the same question, so question difficulty and task type cancel out; the fair test). 'layer-1 probe' is the same probe on the first layer, a stronger surface baseline.

| Set | n | verdict at A | spoken verdict at C | text baseline | layer-1 probe | probe: best layer | probe |
|---|---|---|---|---|---|---|---|
| BBEH | 610 | 0.490 / **0.583** | 0.542 / **0.570** | 0.573 / **0.558** | 0.663 / **0.580** | 25 | 0.728 / **0.638** |
| RB2 Math | 732 | 0.795 / **0.808** | 0.775 / **0.777** | 0.512 / **0.518** | 0.707 / **0.734** | 32 | 0.824 / **0.832** |
| BBEH + RB2 Math | 1342 | 0.641 / **0.763** | 0.665 / **0.741** | 0.668 / **0.491** | 0.743 / **0.705** | 25 | 0.793 / **0.773** |
| JudgeBench (pairwise) | 547 | 0.716 / **nan** | nan / **nan** | 0.527 / **nan** | 0.535 / **nan** | 22 | 0.681 / **nan** |

Probe AUROC by layer:

| Layer | BBEH | RB2 Math | BBEH + RB2 Math | JudgeBench (pairwise) |
|---|---|---|---|---|
| 1 | 0.663 | 0.707 | 0.743 | 0.535 |
| 4 | 0.717 | 0.711 | 0.759 | 0.550 |
| 7 | 0.705 | 0.745 | 0.757 | 0.568 |
| 10 | 0.718 | 0.731 | 0.758 | 0.566 |
| 13 | 0.710 | 0.766 | 0.782 | 0.536 |
| 16 | 0.703 | 0.771 | 0.764 | 0.665 |
| 19 | 0.714 | 0.796 | 0.780 | 0.661 |
| 22 | 0.717 | 0.780 | 0.785 | 0.681 |
| 25 | 0.728 | 0.788 | 0.793 | 0.669 |
| 28 | 0.706 | 0.798 | 0.785 | 0.681 |
| 31 | 0.719 | 0.815 | 0.788 | 0.665 |
| 32 | 0.710 | 0.824 | 0.792 | 0.670 |

## 2. Wrong answers: what the judge says vs. what the layer-25 probe says

'Accepts' = says CORRECT. The probe's threshold is set so that, over all 1225 candidates, it accepts exactly as often as the spoken verdict (0.54); so any difference below is about WHICH answers it accepts, not how lenient it is.

| Candidates | n | verdict at A accepts | spoken verdict at C accepts | probe accepts |
|---|---|---|---|---|
| wrong, own answer matches | 128 | 0.40 | 0.67 | 0.46 |
| wrong, own answer differs | 626 | 0.24 | 0.36 | 0.36 |
| correct (any) | 471 | 0.44 | 0.74 | 0.81 |

Anchoring errors (wrong, matches the judge's own answer, accepted in the spoken verdict): n = 86; at the same leniency the probe rejects 0.43 of them.

## 3. "This matches my own answer" probe (wrong candidates only)

n = 754 wrong candidates (128 match). Holding correctness fixed, so the probe cannot just be reading 'is this right'.

Text baseline (no hidden state) AUROC: 0.644. The judge's own verdict margin at A, as a predictor of match: 0.634.

| Layer | AUROC |
|---|---|
| 1 | 0.676 |
| 4 | 0.671 |
| 7 | 0.653 |
| 10 | 0.723 |
| 13 | 0.680 |
| 16 | 0.729 |
| 19 | 0.722 |
| 22 | 0.706 |
| 25 | 0.704 |
| 28 | 0.693 |
| 31 | 0.736 |
| 32 | 0.724 |

Steering directions written: correctness (layer 25), agreement (layer 16), random control (layer 25); each scaled to one standard deviation of the projections; 904 items.
