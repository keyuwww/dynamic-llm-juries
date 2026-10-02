# System One judge on BFF-Bench: results

Items with consensus human labels: 459 (dropped for no consensus: 501, missing reference: 3). Jev model: jeff-qwen3.5-0.8b.

Verdict = yes if Jev's probability ≥ 0.5. κ = Cohen's kappa vs consensus human label.

## Overall

| Condition | n | Accuracy | Cohen's κ | AUROC | FPR (wrong→'correct') | FNR | Says 'correct' |
|---|---|---|---|---|---|---|---|
| noref | 459 | 0.641 | 0.314 | 0.773 | 0.103 | 0.562 | 0.290 |
| ref | 456 | 0.680 | 0.397 | 0.895 | 0.000 | 0.573 | 0.239 |

Human base rate (share labelled Correct): 0.558

Reference point from No Free Labels (single + pairwise, overall κ): GPT-4o ≈ 0.69 with human reference, ≈ 0.46 without.

## By examinee model (κ)

| Examinee | n | κ noref | κ ref | acc noref | acc ref |
|---|---|---|---|---|---|
| gemma-2-2b | 76 | 0.334 | 0.244 | 0.711 | 0.697 |
| gpt-4o | 83 | 0.118 | 0.156 | 0.446 | 0.470 |
| llama-3.3-70b | 56 | 0.270 | 0.559 | 0.607 | 0.768 |
| phi-4 | 83 | 0.334 | 0.443 | 0.643 | 0.699 |
| qwen2.5-7b | 82 | 0.326 | 0.382 | 0.651 | 0.671 |
| yi1.5-34b-16k | 76 | 0.487 | 0.530 | 0.792 | 0.816 |

## By turn (κ)

| Turn | κ noref | κ ref |
|---|---|---|
| 1 | 0.362 | 0.298 |
| 2 | 0.116 | 0.508 |

## Selective judging (accept only Jev's most confident verdicts)

confidence = |p − 0.5| × 2. This is the Trust-or-Escalate / Path C tier-0 question: how much can Jev handle alone?

**noref**

| Coverage | Min confidence | Accuracy | κ |
|---|---|---|---|
| 100% | 0.00 | 0.641 | 0.314 |
| 90% | 0.06 | 0.666 | 0.359 |
| 80% | 0.14 | 0.684 | 0.381 |
| 70% | 0.23 | 0.713 | 0.422 |
| 60% | 0.28 | 0.724 | 0.418 |
| 50% | 0.36 | 0.730 | 0.419 |

**ref**

| Coverage | Min confidence | Accuracy | κ |
|---|---|---|---|
| 100% | 0.00 | 0.680 | 0.397 |
| 90% | 0.17 | 0.698 | 0.405 |
| 80% | 0.31 | 0.726 | 0.430 |
| 70% | 0.45 | 0.762 | 0.475 |
| 60% | 0.56 | 0.810 | 0.554 |
| 50% | 0.65 | 0.820 | 0.562 |

## Cost & latency

- Calls: 915; input tokens: 1,205,683; est. cost: $0.0506 (list price $0.042/1M input, output free)
- Latency p50 2.054s, p95 10.274s (includes network)
