# Probes at position A — llama3.1-8b

2199 judgments, 32 layers. Hidden state = residual stream at the last token of `...VERDICT:` before the judge writes anything. Probes are logistic regressions, cross-validated with whole questions held out. AUROC 0.5 = chance, 1.0 = perfect.

## 1. "Is this right?" probe vs. the judge's own verdict

Candidates that never wrote a final answer are dropped (always wrong, trivially detectable). 'Text baseline' = logistic regression on prompt length, benchmark, which model wrote the candidate and whether it has a final answer -- no hidden state.

Each cell: AUROC over all candidates / **within-question** AUROC (only compares candidates of the same question, so question difficulty and task type cancel out; the fair test). 'layer-1 probe' is the same probe on the first layer, a stronger surface baseline.

| Set | n | verdict at A | spoken verdict at C | text baseline | layer-1 probe | probe: best layer | probe |
|---|---|---|---|---|---|---|---|
| BBEH | 610 | 0.485 / **0.572** | 0.484 / **0.492** | 0.573 / **0.558** | 0.670 / **0.572** | 29 | 0.740 / **0.681** |
| RB2 Math | 732 | 0.699 / **0.738** | 0.578 / **0.579** | 0.514 / **0.523** | 0.711 / **0.736** | 31 | 0.769 / **0.792** |
| BBEH + RB2 Math | 1342 | 0.562 / **0.705** | 0.504 / **0.562** | 0.674 / **0.533** | 0.711 / **0.684** | 21 | 0.784 / **0.786** |
| JudgeBench (pairwise) | 547 | 0.578 / **nan** | nan / **nan** | 0.533 / **nan** | 0.548 / **nan** | 15 | 0.594 / **nan** |

Probe AUROC by layer:

| Layer | BBEH | RB2 Math | BBEH + RB2 Math | JudgeBench (pairwise) |
|---|---|---|---|---|
| 1 | 0.670 | 0.711 | 0.711 | 0.548 |
| 3 | 0.682 | 0.686 | 0.736 | 0.563 |
| 5 | 0.680 | 0.718 | 0.739 | 0.566 |
| 7 | 0.680 | 0.703 | 0.733 | 0.578 |
| 9 | 0.705 | 0.706 | 0.747 | 0.562 |
| 11 | 0.727 | 0.721 | 0.741 | 0.561 |
| 13 | 0.712 | 0.718 | 0.739 | 0.584 |
| 15 | 0.718 | 0.761 | 0.759 | 0.594 |
| 17 | 0.739 | 0.756 | 0.778 | 0.579 |
| 19 | 0.728 | 0.762 | 0.784 | 0.547 |
| 21 | 0.727 | 0.762 | 0.784 | 0.532 |
| 23 | 0.732 | 0.751 | 0.777 | 0.516 |
| 25 | 0.735 | 0.757 | 0.778 | 0.547 |
| 27 | 0.737 | 0.749 | 0.777 | 0.555 |
| 29 | 0.740 | 0.753 | 0.779 | 0.574 |
| 31 | 0.736 | 0.769 | 0.781 | 0.577 |
| 32 | 0.721 | 0.766 | 0.784 | 0.580 |

## 2. Wrong answers: what the judge says vs. what the layer-21 probe says

'Accepts' = says CORRECT. The probe's threshold is set so that, over all 1207 candidates, it accepts exactly as often as the spoken verdict (0.63); so any difference below is about WHICH answers it accepts, not how lenient it is.

| Candidates | n | verdict at A accepts | spoken verdict at C accepts | probe accepts |
|---|---|---|---|---|
| wrong, own answer matches | 108 | 0.65 | 0.64 | 0.61 |
| wrong, own answer differs | 640 | 0.62 | 0.63 | 0.48 |
| correct (any) | 459 | 0.65 | 0.64 | 0.85 |

Anchoring errors (wrong, matches the judge's own answer, accepted in the spoken verdict): n = 69; at the same leniency the probe rejects 0.29 of them.

## 3. "This matches my own answer" probe (wrong candidates only)

n = 758 wrong candidates (110 match). Holding correctness fixed, so the probe cannot just be reading 'is this right'.

Text baseline (no hidden state) AUROC: 0.547. The judge's own verdict margin at A, as a predictor of match: 0.517.

| Layer | AUROC |
|---|---|
| 1 | 0.592 |
| 3 | 0.610 |
| 5 | 0.644 |
| 7 | 0.609 |
| 9 | 0.597 |
| 11 | 0.600 |
| 13 | 0.596 |
| 15 | 0.659 |
| 17 | 0.642 |
| 19 | 0.637 |
| 21 | 0.633 |
| 23 | 0.624 |
| 25 | 0.626 |
| 27 | 0.627 |
| 29 | 0.627 |
| 31 | 0.635 |
| 32 | 0.646 |

Steering directions written: correctness (layer 21), agreement (layer 15), random control (layer 21); each scaled to one standard deviation of the projections; 908 items.
