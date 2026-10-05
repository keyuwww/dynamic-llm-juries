# Phase 2 judges: judgebench

Verdict = majority of the judge's votes; ties and unparseable outputs count as INCORRECT verdicts (reported separately as parse rate). kappa/accuracy vs gold labels.

## Judge quality by condition

| Judge | Tier | Condition | n | Parse rate | Accuracy | Cohen's κ | AUROC (vote share) |
|---|---|---|---|---|---|---|---|
| qwen3.5-4b | small | none | 620 | 0.989 | 0.790 | 0.582 | 0.793 |
| gpt-oss-20b | small | none | 620 | 0.905 | 0.761 | 0.526 | 0.767 |
| nemotron3-nano-30b | small | none | 620 | 0.995 | 0.582 | 0.160 | 0.580 |
| qwen3.5-9b | mid | none | 620 | 0.985 | 0.819 | 0.639 | 0.822 |
| qwen3.6-35b-a3b | mid | none | 620 | 0.992 | 0.895 | 0.789 | 0.895 |
| nemotron3-super-120b | mid | none | 620 | 0.971 | 0.750 | 0.499 | 0.751 |
| gpt-oss-120b | strong | none | 620 | 0.997 | 0.844 | 0.687 | 0.845 |
| deepseek-v3.1 | strong | none | 620 | 1.000 | 0.747 | 0.491 | 0.746 |

## Judge-routing headroom (condition = none; 1 = verdict matched gold)

Items scored by every model: 620

| Model | Tier | Accuracy | Only model correct (# items) |
|---|---|---|---|
| qwen3.6-35b-a3b | mid | 0.895 | 2 |
| gpt-oss-120b | strong | 0.844 | 1 |
| qwen3.5-9b | mid | 0.819 | 1 |
| qwen3.5-4b | small | 0.790 | 0 |
| gpt-oss-20b | small | 0.761 | 0 |
| nemotron3-super-120b | mid | 0.750 | 4 |
| deepseek-v3.1 | strong | 0.747 | 3 |
| nemotron3-nano-30b | small | 0.582 | 4 |

| Headroom check | |
|---|---|
| Best single model | **qwen3.6-35b-a3b** (0.895) |
| Oracle (any model correct) | 0.990 |
| **Oracle − best single** (room a router can win) | **0.095** |
| Items the best model misses but another gets right | 59 (0.095) |
| Items no model gets right | 0.010 |

Rule of thumb from the plan: keep a model in the routing pool if no single model wins almost everywhere and oracle − best is ≥ ~0.08 (BFF-Bench's original six models gave only ~0.04).

## Judging cost

| Model | Calls | Avg input tok | Avg output tok | $ / call | Total $ |
|---|---|---|---|---|---|
| deepseek-v3.1 | 620 | 1,221 | 363 | $0.00360 | $2.233 |
| gpt-oss-120b | 620 | 1,230 | 1,280 | $0.00148 | $0.918 |
| gpt-oss-20b | 620 | 1,230 | 2,209 | $0.00122 | $0.754 |
| nemotron3-nano-30b | 620 | 1,284 | 200 | $0.00035 | $0.217 |
| nemotron3-super-120b | 620 | 1,284 | 791 | $0.00187 | $1.160 |
| qwen3.5-4b | 620 | 1,331 | 1,220 | $0.00167 | $1.033 |
| qwen3.5-9b | 620 | 1,331 | 1,602 | $0.00407 | $2.526 |
| qwen3.6-35b-a3b | 620 | 1,331 | 1,671 | $0.00295 | $1.828 |

**Total: $10.67** (Tinker list prices; cached-prefill discounts not counted, so this is an upper bound)
