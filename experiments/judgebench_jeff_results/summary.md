# JudgeBench: pairwise judge results

n=620 (fully algorithmic gold -- NOT human-annotated). Backend: jeff-qwen3.5-0.8b.

Accuracy: 0.592  Cohen's κ: 0.159

## By split

| Split | n | Accuracy |
|---|---|---|
| claude | 270 | 0.548 |
| gpt | 350 | 0.626 |

## Cost & latency

- Calls: 620; input tokens: 874,694
- Latency p50 0.959s, p95 3.296s