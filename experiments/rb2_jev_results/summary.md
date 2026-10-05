# RewardBench 2 (non-Safety domains): judge results

n=7177 (NOT human-annotated -- LLM-judged/algorithmic gold; read as capability, not human-preference agreement). Backend: jev-1.13.0.

Overall -- Accuracy: 0.854  Cohen's κ: 0.625

## By domain

| Domain | n | Accuracy | Cohen's κ |
|---|---|---|---|
| Factuality | 1900 | 0.852 | 0.584 |
| Focus | 1980 | 0.849 | 0.622 |
| Math | 732 | 0.730 | 0.435 |
| Precise IF | 640 | 0.670 | 0.193 |
| Ties | 1925 | 0.970 | 0.920 |

## Cost & latency

- Calls: 7177; input tokens: 5,419,581
- Latency p50 0.153s, p95 0.223s