# System One judge on BFF-Bench: results

Items with consensus human labels: 459 (dropped for no consensus: 501, missing reference: 3). Jev model: jev-1.13.0.

Verdict = yes if Jev's probability ≥ 0.5. κ = Cohen's kappa vs consensus human label.

## Overall

| Condition | n | Accuracy | Cohen's κ | AUROC | FPR (wrong→'correct') | FNR | Says 'correct' |
|---|---|---|---|---|---|---|---|
| noref | 459 | 0.760 | 0.505 | 0.848 | 0.365 | 0.141 | 0.641 |
| ref | 456 | 0.928 | 0.856 | 0.985 | 0.005 | 0.125 | 0.491 |

Human base rate (share labelled Correct): 0.558

Reference point from No Free Labels (single + pairwise, overall κ): GPT-4o ≈ 0.69 with human reference, ≈ 0.46 without.

## By examinee model (κ)

| Examinee | n | κ noref | κ ref | acc noref | acc ref |
|---|---|---|---|---|---|
| gemma-2-2b | 76 | 0.522 | 0.501 | 0.789 | 0.789 |
| gpt-4o | 83 | 0.576 | 0.914 | 0.892 | 0.976 |
| llama-3.3-70b | 56 | 0.325 | 0.963 | 0.714 | 0.982 |
| phi-4 | 83 | 0.376 | 0.950 | 0.726 | 0.976 |
| qwen2.5-7b | 82 | 0.358 | 0.830 | 0.687 | 0.915 |
| yi1.5-34b-16k | 76 | 0.478 | 0.850 | 0.740 | 0.934 |

## By turn (κ)

| Turn | κ noref | κ ref |
|---|---|---|
| 1 | 0.525 | 0.810 |
| 2 | 0.464 | 0.886 |

## Selective judging (accept only Jev's most confident verdicts)

confidence = |p − 0.5| × 2. This is the Trust-or-Escalate / Path C tier-0 question: how much can Jev handle alone?

**noref**

| Coverage | Min confidence | Accuracy | κ |
|---|---|---|---|
| 100% | 0.00 | 0.760 | 0.505 |
| 90% | 0.16 | 0.789 | 0.560 |
| 80% | 0.34 | 0.812 | 0.600 |
| 70% | 0.46 | 0.835 | 0.645 |
| 60% | 0.58 | 0.865 | 0.702 |
| 50% | 0.68 | 0.900 | 0.772 |

**ref**

| Coverage | Min confidence | Accuracy | κ |
|---|---|---|---|
| 100% | 0.00 | 0.928 | 0.856 |
| 90% | 0.44 | 0.954 | 0.907 |
| 80% | 0.72 | 0.964 | 0.928 |
| 70% | 0.84 | 0.981 | 0.961 |
| 60% | 0.88 | 0.985 | 0.968 |
| 50% | 0.92 | 0.987 | 0.969 |

## Cost & latency

- Calls: 915; input tokens: 1,391,725; est. cost: $0.0585 (list price $0.042/1M input, output free)
- Latency p50 0.219s, p95 12.695s (includes network)
