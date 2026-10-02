# System One judge on BFF-Bench: results

Items with consensus human labels: 80 (dropped for no consensus: 501, missing reference: 3). Jev model: clm-raw.

Verdict = yes if Jev's probability ≥ 0.5. κ = Cohen's kappa vs consensus human label.

## Overall

| Condition | n | Accuracy | Cohen's κ | AUROC | FPR (wrong→'correct') | FNR | Says 'correct' |
|---|---|---|---|---|---|---|---|
| noref | 80 | 0.487 | -0.000 | 0.428 | 0.000 | 1.000 | 0.000 |
| ref | 79 | 0.481 | 0.000 | 0.148 | 0.000 | 1.000 | 0.000 |

Human base rate (share labelled Correct): 0.512

Reference point from No Free Labels (single + pairwise, overall κ): GPT-4o ≈ 0.69 with human reference, ≈ 0.46 without.

## By examinee model (κ)

| Examinee | n | κ noref | κ ref | acc noref | acc ref |
|---|---|---|---|---|---|
| gemma-2-2b | 10 | 0.000 | 0.000 | 0.700 | 0.700 |
| gpt-4o | 13 | 0.000 | 0.000 | 0.154 | 0.154 |
| llama-3.3-70b | 7 | -0.000 | -0.000 | 0.429 | 0.429 |
| phi-4 | 16 | 0.000 | 0.000 | 0.375 | 0.375 |
| qwen2.5-7b | 23 | -0.000 | -0.000 | 0.565 | 0.565 |
| yi1.5-34b-16k | 10 | 0.000 | 0.000 | 0.727 | 0.700 |

## By turn (κ)

| Turn | κ noref | κ ref |
|---|---|---|
| 1 | 0.000 | 0.000 |
| 2 | 0.000 | 0.000 |

## Selective judging (accept only Jev's most confident verdicts)

confidence = |p − 0.5| × 2. This is the Trust-or-Escalate / Path C tier-0 question: how much can Jev handle alone?

**noref**

| Coverage | Min confidence | Accuracy | κ |
|---|---|---|---|
| 100% | 0.12 | 0.487 | -0.000 |
| 90% | 0.21 | 0.472 | 0.000 |
| 80% | 0.23 | 0.453 | 0.000 |
| 70% | 0.24 | 0.393 | -0.000 |
| 60% | 0.25 | 0.438 | 0.000 |
| 50% | 0.27 | 0.425 | -0.000 |

**ref**

| Coverage | Min confidence | Accuracy | κ |
|---|---|---|---|
| 100% | 0.31 | 0.481 | 0.000 |
| 90% | 0.39 | 0.423 | 0.000 |
| 80% | 0.45 | 0.365 | -0.000 |
| 70% | 0.47 | 0.291 | 0.000 |
| 59% | 0.49 | 0.255 | -0.000 |
| 51% | 0.51 | 0.250 | 0.000 |

## Cost & latency

- Calls: 159; input tokens: 188,528; est. cost: $0.0079 (list price $0.042/1M input, output free)
- Latency p50 0.141s, p95 0.199s (includes network)
