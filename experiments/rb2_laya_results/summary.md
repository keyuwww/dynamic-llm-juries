# RewardBench 2 (non-Safety domains): judge results

n=7177 (NOT human-annotated -- LLM-judged/algorithmic gold; read as capability, not human-preference agreement). Backend: laya-rl-agent.

Overall -- Accuracy: 0.441  Cohen's κ: 0.078

## By domain

| Domain | n | Accuracy | Cohen's κ |
|---|---|---|---|
| Factuality | 1900 | 0.324 | -0.005 |
| Focus | 1980 | 0.364 | 0.064 |
| Math | 732 | 0.448 | 0.059 |
| Precise IF | 640 | 0.367 | 0.006 |
| Ties | 1925 | 0.659 | 0.257 |

## Cost & latency

- Calls: 7177; input tokens: 2,601,386
- Latency p50 0.744s, p95 0.985s