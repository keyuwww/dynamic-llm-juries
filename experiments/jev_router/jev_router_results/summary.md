# System One router: picking the best model per question (BFF-Bench, turn 1)

Questions with >=2-way consensus labels: 66 (dropped for no consensus: 242). Backend model: jev-1.13.0.

Strategy comparison below uses the 47 of those questions where the fixed-best model (**gpt-4o**) also has a consensus label, so every strategy is scored on the same denominator (19 questions excluded for this table only).

The backend never sees any model's actual response here -- only the question and a one-line description of each candidate model -- then answers three things per question: an independent yes/no per candidate, a single Choice across all candidates, and whether none would get it right.

## Routing accuracy (share of questions where the picked model's real response was correct)

| Strategy | Accuracy |
|---|---|
| Random pick | 0.760 |
| Always pick the single best-overall model (**gpt-4o**) | 0.872 |
| **Router (argmax of independent yes/no)** | **0.872** |
| **Router (single Choice call)** | **0.872** |
| Oracle (correct if *any* candidate got it right) | 0.915 |

Gap closed vs. always-gpt-4o (yes/no router): 0.000. Gap closed (choice router): 0.000. (share of the oracle − fixed-baseline gap that the router's pick recovers; 0 = no better than the fixed baseline, 1 = matches the oracle)

## Per-model correct rate (human labels, turn 1 only)

| Model | Correct rate |
|---|---|
| gpt-4o | 0.872 |
| qwen2.5-7b | 0.700 |
| llama-3.3-70b | 0.679 |
| phi-4 | 0.675 |
| gemma-2-2b | 0.559 |
| yi1.5-34b-16k | 0.500 |

## Calibration of the raw per-(question, model) prediction
(treating every prediction as its own yes/no call, ignoring routing/argmax)

| Signal | AUROC | Brier (lower better) |
|---|---|---|
| Independent yes/no (noul) | 0.837 | 0.181 |
| Choice probability | 0.646 | n/a |
| Prior baseline (model's own overall correct rate, no question signal) | 0.654 | 0.204 |

'None will be right' signal AUROC (predicting every candidate is wrong): 0.802

## Dynamic jury (P(correct) > 60%, capped at 3)

For each question, take the candidates with averaged P(correct) above the threshold, highest-probability first, up to the cap -- that's the jury. Scored by majority vote of the jury's REAL correctness (a split jury, e.g. 1-of-2, counts as incorrect); a question with zero qualifying candidates is escalated rather than scored.

| | |
|---|---|
| Coverage (share of questions with >=1 jury member) | 1.000 |
| Escalation rate (0 qualifying candidates) | 0.000 |
| Average jury size, when covered | 2.60 |
| **Jury majority-vote accuracy, on covered questions** | **0.766** |
| Jury 'any member correct' rate, on covered questions | 0.894 |
| (same-subset) always-pick-gpt-4o accuracy | 0.872 |
| (same-subset) oracle accuracy | 0.915 |

## Cost & latency

- Calls: 66 (one combined call per question); input tokens: 433,880; est. cost: $0.0182 (list price $0.042/1M input, output free)
- Latency p50 0.822s, p95 0.992s (includes network)
