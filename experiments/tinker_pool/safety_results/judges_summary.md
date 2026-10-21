# Phase 2 judges: safety

Verdict = majority of the judge's votes; ties and unparseable outputs count as INCORRECT verdicts (reported separately as parse rate). kappa/accuracy vs gold labels.

## Judge quality by condition

| Judge | Tier | Condition | n | Parse rate | Accuracy | Cohen's κ | AUROC (vote share) |
|---|---|---|---|---|---|---|---|
| qwen3.5-4b | small | none | 1800 | 0.999 | 0.728 | 0.461 | 0.809 |
| gpt-oss-20b | small | none | 1800 | 0.978 | 0.847 | 0.635 | 0.854 |
| nemotron3-nano-30b | small | none | 1800 | 1.000 | 0.790 | 0.534 | 0.821 |
| qwen3.5-9b | mid | none | 1800 | 0.998 | 0.764 | 0.510 | 0.827 |
| qwen3.6-35b-a3b | mid | none | 1800 | 0.976 | 0.727 | 0.458 | 0.807 |
| nemotron3-super-120b | mid | none | 1800 | 1.000 | 0.746 | 0.489 | 0.823 |
| gpt-oss-120b | strong | none | 1800 | 0.997 | 0.776 | 0.526 | 0.833 |
| deepseek-v3.1 | strong | none | 1800 | 1.000 | 0.723 | 0.458 | 0.813 |

## Judge-routing headroom (condition = none; 1 = verdict matched gold)

Items scored by every model: 1800

| Model | Tier | Accuracy | Only model correct (# items) |
|---|---|---|---|
| gpt-oss-20b | small | 0.847 | 34 |
| nemotron3-nano-30b | small | 0.790 | 23 |
| gpt-oss-120b | strong | 0.776 | 6 |
| qwen3.5-9b | mid | 0.764 | 7 |
| nemotron3-super-120b | mid | 0.746 | 3 |
| qwen3.5-4b | small | 0.728 | 6 |
| qwen3.6-35b-a3b | mid | 0.727 | 0 |
| deepseek-v3.1 | strong | 0.723 | 2 |

| Headroom check | |
|---|---|
| Best single model | **gpt-oss-20b** (0.847) |
| Oracle (any model correct) | 0.959 |
| **Oracle − best single** (room a router can win) | **0.112** |
| Items the best model misses but another gets right | 202 (0.112) |
| Items no model gets right | 0.041 |

Rule of thumb from the plan: keep a model in the routing pool if no single model wins almost everywhere and oracle − best is ≥ ~0.08 (BFF-Bench's original six models gave only ~0.04).

## Judging cost

| Model | Calls | Avg input tok | Avg output tok | $ / call | Total $ |
|---|---|---|---|---|---|
| deepseek-v3.1 | 1800 | 392 | 106 | $0.00111 | $2.000 |
| gpt-oss-120b | 1800 | 386 | 219 | $0.00031 | $0.560 |
| gpt-oss-20b | 1800 | 386 | 278 | $0.00019 | $0.350 |
| nemotron3-nano-30b | 1800 | 414 | 74 | $0.00012 | $0.211 |
| nemotron3-super-120b | 1800 | 414 | 136 | $0.00043 | $0.778 |
| qwen3.5-4b | 1800 | 416 | 114 | $0.00025 | $0.453 |
| qwen3.5-9b | 1800 | 416 | 155 | $0.00058 | $1.050 |
| qwen3.6-35b-a3b | 1800 | 416 | 207 | $0.00050 | $0.902 |

**Total: $6.30** (Tinker list prices; cached-prefill discounts not counted, so this is an upper bound)
