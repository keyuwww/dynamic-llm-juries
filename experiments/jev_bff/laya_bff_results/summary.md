# System One judge on BFF-Bench: results

Items with consensus human labels: 459 (dropped for no consensus: 501, missing reference: 3). Jev model: laya-rl-agent.

Verdict = yes if Jev's probability ≥ 0.5. κ = Cohen's kappa vs consensus human label.

## Overall

| Condition | n | Accuracy | Cohen's κ | AUROC | FPR (wrong→'correct') | FNR | Says 'correct' |
|---|---|---|---|---|---|---|---|
| noref | 459 | 0.593 | 0.095 | 0.675 | 0.882 | 0.031 | 0.930 |
| ref | 456 | 0.601 | 0.115 | 0.670 | 0.856 | 0.039 | 0.914 |

Human base rate (share labelled Correct): 0.558

Reference point from No Free Labels (single + pairwise, overall κ): GPT-4o ≈ 0.69 with human reference, ≈ 0.46 without.

## By examinee model (κ)

| Examinee | n | κ noref | κ ref | acc noref | acc ref |
|---|---|---|---|---|---|
| gemma-2-2b | 76 | 0.135 | 0.153 | 0.487 | 0.500 |
| gpt-4o | 83 | -0.044 | -0.080 | 0.819 | 0.795 |
| llama-3.3-70b | 56 | 0.073 | 0.073 | 0.625 | 0.625 |
| phi-4 | 83 | 0.132 | 0.206 | 0.631 | 0.663 |
| qwen2.5-7b | 82 | 0.100 | 0.038 | 0.602 | 0.573 |
| yi1.5-34b-16k | 76 | 0.028 | 0.088 | 0.377 | 0.434 |

## By turn (κ)

| Turn | κ noref | κ ref |
|---|---|---|
| 1 | 0.131 | 0.170 |
| 2 | 0.055 | 0.073 |

## Selective judging (accept only Jev's most confident verdicts)

confidence = |p − 0.5| × 2. This is the Trust-or-Escalate / Path C tier-0 question: how much can Jev handle alone?

**noref**

| Coverage | Min confidence | Accuracy | κ |
|---|---|---|---|
| 100% | 0.00 | 0.593 | 0.095 |
| 90% | 0.04 | 0.617 | 0.092 |
| 80% | 0.09 | 0.632 | 0.070 |
| 70% | 0.12 | 0.629 | 0.043 |
| 60% | 0.17 | 0.662 | 0.053 |
| 50% | 0.25 | 0.678 | 0.000 |

**ref**

| Coverage | Min confidence | Accuracy | κ |
|---|---|---|---|
| 100% | 0.00 | 0.601 | 0.115 |
| 90% | 0.04 | 0.617 | 0.117 |
| 80% | 0.07 | 0.627 | 0.102 |
| 70% | 0.11 | 0.643 | 0.051 |
| 60% | 0.16 | 0.661 | 0.065 |
| 50% | 0.23 | 0.689 | 0.054 |

## Cost & latency

- Calls: 915; input tokens: 466,386; est. cost: $0.0196 (list price $0.042/1M input, output free)
- Latency p50 0.844s, p95 0.974s (includes network)
