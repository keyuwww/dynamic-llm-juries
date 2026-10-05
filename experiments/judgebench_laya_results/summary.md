# JudgeBench: pairwise judge results

n=620 (fully algorithmic gold -- NOT human-annotated). Backend: laya-rl-agent.

Accuracy: 0.526  Cohen's κ: 0.057

## By split

| Split | n | Accuracy |
|---|---|---|
| claude | 270 | 0.522 |
| gpt | 350 | 0.529 |

## Cost & latency

- Calls: 620; input tokens: 318,443
- Latency p50 0.255s, p95 0.334s