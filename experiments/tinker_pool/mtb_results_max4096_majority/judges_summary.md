# Phase 2 judges: mtb

Verdict = majority of the judge's votes; ties and unparseable outputs count as INCORRECT verdicts (reported separately as parse rate). kappa/accuracy vs gold labels.

## Judge quality by condition

| Judge | Tier | Condition | n | Parse rate | Accuracy | Cohen's κ | AUROC (vote share) |
|---|---|---|---|---|---|---|---|
| qwen3.5-4b | small | none | 232 | 0.996 | 0.853 | 0.606 | 0.787 |
| qwen3.5-4b | small | human | 232 | 0.996 | 0.935 | 0.837 | 0.925 |
| gpt-oss-20b | small | none | 232 | 0.996 | 0.892 | 0.726 | 0.865 |
| gpt-oss-20b | small | human | 232 | 1.000 | 0.922 | 0.796 | 0.886 |
| nemotron3-nano-30b | small | none | 232 | 1.000 | 0.754 | 0.400 | 0.709 |
| nemotron3-nano-30b | small | human | 232 | 1.000 | 0.901 | 0.767 | 0.917 |
| qwen3.5-9b | mid | none | 232 | 1.000 | 0.909 | 0.763 | 0.872 |
| qwen3.5-9b | mid | human | 232 | 1.000 | 0.953 | 0.880 | 0.942 |
| qwen3.6-35b-a3b | mid | none | 232 | 0.996 | 0.901 | 0.748 | 0.876 |
| qwen3.6-35b-a3b | mid | human | 232 | 1.000 | 0.953 | 0.883 | 0.957 |
| nemotron3-super-120b | mid | none | 232 | 0.983 | 0.892 | 0.708 | 0.834 |
| nemotron3-super-120b | mid | human | 232 | 1.000 | 0.953 | 0.877 | 0.932 |
| gpt-oss-120b | strong | none | 232 | 1.000 | 0.897 | 0.741 | 0.878 |
| gpt-oss-120b | strong | human | 232 | 1.000 | 0.983 | 0.956 | 0.983 |
| deepseek-v3.1 | strong | none | 232 | 1.000 | 0.888 | 0.698 | 0.831 |
| deepseek-v3.1 | strong | human | 232 | 1.000 | 0.948 | 0.867 | 0.929 |

## Judge-routing headroom (condition = none; 1 = verdict matched gold)

Items scored by every model: 232

| Model | Tier | Accuracy | Only model correct (# items) |
|---|---|---|---|
| qwen3.5-9b | mid | 0.909 | 0 |
| qwen3.6-35b-a3b | mid | 0.901 | 1 |
| gpt-oss-120b | strong | 0.897 | 0 |
| gpt-oss-20b | small | 0.892 | 0 |
| nemotron3-super-120b | mid | 0.892 | 0 |
| deepseek-v3.1 | strong | 0.888 | 0 |
| qwen3.5-4b | small | 0.853 | 0 |
| nemotron3-nano-30b | small | 0.754 | 2 |

| Headroom check | |
|---|---|
| Best single model | **qwen3.5-9b** (0.909) |
| Oracle (any model correct) | 0.974 |
| **Oracle − best single** (room a router can win) | **0.065** |
| Items the best model misses but another gets right | 15 (0.065) |
| Items no model gets right | 0.026 |

Rule of thumb from the plan: keep a model in the routing pool if no single model wins almost everywhere and oracle − best is ≥ ~0.08 (BFF-Bench's original six models gave only ~0.04).

## Judging cost

| Model | Calls | Avg input tok | Avg output tok | $ / call | Total $ |
|---|---|---|---|---|---|
| deepseek-v3.1 | 464 | 590 | 131 | $0.00155 | $0.720 |
| gpt-oss-120b | 464 | 594 | 304 | $0.00045 | $0.209 |
| gpt-oss-20b | 464 | 594 | 433 | $0.00030 | $0.140 |
| nemotron3-nano-30b | 464 | 619 | 67 | $0.00015 | $0.071 |
| nemotron3-super-120b | 464 | 619 | 192 | $0.00063 | $0.292 |
| qwen3.5-4b | 464 | 637 | 264 | $0.00048 | $0.221 |
| qwen3.5-9b | 464 | 637 | 202 | $0.00082 | $0.382 |
| qwen3.6-35b-a3b | 464 | 637 | 346 | $0.00081 | $0.374 |

**Total: $2.41** (Tinker list prices; cached-prefill discounts not counted, so this is an upper bound)
