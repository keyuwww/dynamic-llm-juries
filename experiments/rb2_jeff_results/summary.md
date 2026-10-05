# RewardBench 2 (non-Safety domains): judge results

n=7172 (NOT human-annotated -- LLM-judged/algorithmic gold; read as capability, not human-preference agreement). Backend: jeff-qwen3.5-0.8b.

Overall -- Accuracy: 0.746  Cohen's κ: 0.225

## By domain

| Domain | n | Accuracy | Cohen's κ |
|---|---|---|---|
| Factuality | 1898 | 0.742 | 0.010 |
| Focus | 1979 | 0.766 | 0.150 |
| Math | 732 | 0.657 | 0.203 |
| Precise IF | 638 | 0.708 | 0.010 |
| Ties | 1925 | 0.775 | 0.467 |

## Cost & latency

- Calls: 7172; input tokens: 3,875,893
- Latency p50 0.578s, p95 5.120s