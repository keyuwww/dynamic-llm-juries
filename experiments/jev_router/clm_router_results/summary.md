# System One router: picking the best model per question (BFF-Bench, turn 1)

Questions with >=2-way consensus labels: 5 (dropped for no consensus: 242). Backend model: clm-latest.

Strategy comparison below uses the 5 of those questions where the fixed-best model (**gemma-2-2b**) also has a consensus label, so every strategy is scored on the same denominator (0 questions excluded for this table only).

The backend never sees any model's actual response here -- only the question and a one-line description of each candidate model -- then answers three things per question: an independent yes/no per candidate, a single Choice across all candidates, and whether none would get it right.

## Routing accuracy (share of questions where the picked model's real response was correct)

| Strategy | Accuracy |
|---|---|
| Random pick | 0.450 |
| Always pick the single best-overall model (**gemma-2-2b**) | 0.600 |
| **Router (argmax of independent yes/no)** | **0.400** |
| **Router (single Choice call)** | **0.600** |
| Oracle (correct if *any* candidate got it right) | 0.600 |

Gap closed vs. always-gemma-2-2b (yes/no router): n/a. Gap closed (choice router): n/a. (share of the oracle − fixed-baseline gap that the router's pick recovers; 0 = no better than the fixed baseline, 1 = matches the oracle)

## Per-model correct rate (human labels, turn 1 only)

| Model | Correct rate |
|---|---|
| gemma-2-2b | 0.600 |
| gpt-4o | 0.500 |
| phi-4 | 0.400 |
| llama-3.3-70b | 0.333 |
| yi1.5-34b-16k | 0.333 |
| qwen2.5-7b | 0.000 |

## Calibration of the raw per-(question, model) prediction
(treating every prediction as its own yes/no call, ignoring routing/argmax)

| Signal | AUROC | Brier (lower better) |
|---|---|---|
| Independent yes/no (noul) | 0.177 | 0.496 |
| Choice probability | 0.656 | n/a |
| Prior baseline (model's own overall correct rate, no question signal) | 0.682 | 0.212 |

'None will be right' signal AUROC (predicting every candidate is wrong): 1.000

## Dynamic jury (P(correct) > 60%, capped at 3)

For each question, take the candidates with averaged P(correct) above the threshold, highest-probability first, up to the cap -- that's the jury. Scored by majority vote of the jury's REAL correctness (a split jury, e.g. 1-of-2, counts as incorrect); a question with zero qualifying candidates is escalated rather than scored.

| | |
|---|---|
| Coverage (share of questions with >=1 jury member) | 1.000 |
| Escalation rate (0 qualifying candidates) | 0.000 |
| Average jury size, when covered | 2.60 |
| **Jury majority-vote accuracy, on covered questions** | **0.400** |
| Jury 'any member correct' rate, on covered questions | 0.400 |
| (same-subset) always-pick-gemma-2-2b accuracy | 0.600 |
| (same-subset) oracle accuracy | 0.600 |

## Cost & latency

- Calls: 5 (one combined call per question); input tokens: 12,793; est. cost: $0.0005 (list price $0.042/1M input, output free)
- Latency p50 0.876s, p95 0.878s (includes network)
