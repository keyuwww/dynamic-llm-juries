# System One judge on BFF-Bench: results

Items with consensus human labels: 459 (dropped for no consensus: 501, missing reference: 3). Jev model: clm-latest.

Verdict = yes if Jev's probability ≥ 0.5. κ = Cohen's kappa vs consensus human label.

## Overall

| Condition | n | Accuracy | Cohen's κ | AUROC | FPR (wrong→'correct') | FNR | Says 'correct' |
|---|---|---|---|---|---|---|---|
| noref | 459 | 0.442 | 0.000 | 0.411 | 0.000 | 1.000 | 0.000 |
| ref | 456 | 0.439 | -0.012 | 0.453 | 0.045 | 0.969 | 0.037 |

Human base rate (share labelled Correct): 0.558

Reference point from No Free Labels (single + pairwise, overall κ): GPT-4o ≈ 0.69 with human reference, ≈ 0.46 without.

## By examinee model (κ)

| Examinee | n | κ noref | κ ref | acc noref | acc ref |
|---|---|---|---|---|---|
| gemma-2-2b | 76 | 0.000 | -0.052 | 0.618 | 0.592 |
| gpt-4o | 83 | 0.000 | -0.016 | 0.157 | 0.169 |
| llama-3.3-70b | 56 | -0.000 | 0.034 | 0.393 | 0.429 |
| phi-4 | 83 | 0.000 | -0.017 | 0.405 | 0.398 |
| qwen2.5-7b | 82 | 0.000 | -0.055 | 0.434 | 0.415 |
| yi1.5-34b-16k | 76 | 0.000 | 0.000 | 0.662 | 0.658 |

## By turn (κ)

| Turn | κ noref | κ ref |
|---|---|---|
| 1 | 0.000 | -0.018 |
| 2 | 0.000 | 0.004 |

## Selective judging (accept only Jev's most confident verdicts)

confidence = |p − 0.5| × 2. This is the Trust-or-Escalate / Path C tier-0 question: how much can Jev handle alone?

**noref**

| Coverage | Min confidence | Accuracy | κ |
|---|---|---|---|
| 100% | 0.31 | 0.442 | 0.000 |
| 90% | 0.74 | 0.419 | -0.000 |
| 80% | 0.80 | 0.403 | 0.000 |
| 70% | 0.82 | 0.389 | -0.000 |
| 60% | 0.85 | 0.385 | -0.000 |
| 50% | 0.86 | 0.361 | 0.000 |

**ref**

| Coverage | Min confidence | Accuracy | κ |
|---|---|---|---|
| 100% | 0.00 | 0.439 | -0.012 |
| 90% | 0.15 | 0.434 | -0.007 |
| 80% | 0.25 | 0.436 | 0.004 |
| 70% | 0.35 | 0.442 | 0.000 |
| 60% | 0.42 | 0.420 | 0.000 |
| 50% | 0.48 | 0.408 | -0.000 |

## Cost & latency

- Calls: 915; input tokens: 1,061,938; est. cost: $0.0446 (list price $0.042/1M input, output free)
- Latency p50 0.145s, p95 0.232s (includes network)
