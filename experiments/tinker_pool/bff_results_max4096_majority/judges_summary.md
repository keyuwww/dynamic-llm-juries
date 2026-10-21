# Phase 2 judges: bff

Verdict = majority of the judge's votes; ties and unparseable outputs count as INCORRECT verdicts (reported separately as parse rate). kappa/accuracy vs gold labels.

## Judge quality by condition

| Judge | Tier | Condition | n | Parse rate | Accuracy | Cohen's κ | AUROC (vote share) |
|---|---|---|---|---|---|---|---|
| gpt-oss-20b | small | peer | 866 | 0.986 | 0.695 | 0.356 | 0.671 |
| deepseek-v3.1 | strong | peer | 866 | 1.000 | 0.762 | 0.522 | 0.763 |
| qwen3.6-35b-a3b | mid | peer | 866 | 0.999 | 0.724 | 0.460 | 0.738 |
| qwen3.5-9b | mid | peer | 866 | 0.993 | 0.749 | 0.503 | 0.757 |
| qwen3.5-4b | small | peer | 866 | 0.987 | 0.738 | 0.481 | 0.747 |
| nemotron3-super-120b | mid | peer | 866 | 0.999 | 0.794 | 0.573 | 0.780 |
| nemotron3-nano-30b | small | peer | 866 | 0.998 | 0.679 | 0.349 | 0.675 |

## Judge-routing headroom (condition = none; 1 = verdict matched gold)

Items scored by every model: 878

| Model | Tier | Accuracy | Only model correct (# items) |
|---|---|---|---|
| gpt-oss-20b | small | 0.763 | 8 |
| deepseek-v3.1 | strong | 0.745 | 0 |
| qwen3.6-35b-a3b | mid | 0.732 | 5 |
| qwen3.5-4b | small | 0.710 | 2 |
| nemotron3-super-120b | mid | 0.708 | 8 |
| qwen3.5-9b | mid | 0.705 | 2 |
| nemotron3-nano-30b | small | 0.662 | 20 |

| Headroom check | |
|---|---|
| Best single model | **gpt-oss-20b** (0.763) |
| Oracle (any model correct) | 0.952 |
| **Oracle − best single** (room a router can win) | **0.189** |
| Items the best model misses but another gets right | 166 (0.189) |
| Items no model gets right | 0.048 |

Rule of thumb from the plan: keep a model in the routing pool if no single model wins almost everywhere and oracle − best is ≥ ~0.08 (BFF-Bench's original six models gave only ~0.04).

## Judging cost

| Model | Calls | Avg input tok | Avg output tok | $ / call | Total $ |
|---|---|---|---|---|---|
| deepseek-v3.1 | 3476 | 1,630 | 182 | $0.00353 | $12.270 |
| gpt-oss-20b | 3476 | 1,580 | 674 | $0.00059 | $2.043 |
| nemotron3-nano-30b | 3476 | 1,882 | 134 | $0.00043 | $1.505 |
| nemotron3-super-120b | 3476 | 1,892 | 172 | $0.00133 | $4.608 |
| qwen3.5-4b | 3476 | 1,835 | 477 | $0.00108 | $3.770 |
| qwen3.5-9b | 3476 | 1,826 | 423 | $0.00205 | $7.123 |
| qwen3.6-35b-a3b | 3476 | 1,829 | 499 | $0.00165 | $5.748 |

**Total: $37.07** (Tinker list prices; cached-prefill discounts not counted, so this is an upper bound)
