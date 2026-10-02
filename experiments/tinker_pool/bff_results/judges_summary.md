# Phase 2 judges: bff

Verdict = majority of the judge's votes; ties and unparseable outputs count as INCORRECT verdicts (reported separately as parse rate). kappa/accuracy vs gold labels.

## Judge quality by condition

| Judge | Tier | Condition | n | Parse rate | Accuracy | Cohen's κ | AUROC (vote share) |
|---|---|---|---|---|---|---|---|
| qwen3.5-4b | small | none | 459 | 0.893 | 0.745 | 0.481 | 0.739 |
| qwen3.5-4b | small | human | 456 | 0.895 | 0.908 | 0.817 | 0.917 |
| gpt-oss-20b | small | none | 459 | 0.721 | 0.826 | 0.653 | 0.833 |
| gpt-oss-20b | small | human | 456 | 0.818 | 0.879 | 0.756 | 0.880 |
| nemotron3-nano-30b | small | none | 459 | 1.000 | 0.667 | 0.325 | 0.663 |
| nemotron3-nano-30b | small | human | 456 | 0.998 | 0.792 | 0.587 | 0.800 |
| qwen3.5-9b | mid | none | 459 | 0.889 | 0.739 | 0.473 | 0.738 |
| qwen3.5-9b | mid | human | 456 | 0.908 | 0.890 | 0.782 | 0.899 |
| qwen3.6-35b-a3b | mid | none | 459 | 0.802 | 0.765 | 0.537 | 0.777 |
| qwen3.6-35b-a3b | mid | human | 456 | 0.882 | 0.875 | 0.753 | 0.886 |
| nemotron3-super-120b | mid | none | 459 | 0.943 | 0.741 | 0.459 | 0.723 |
| nemotron3-super-120b | mid | human | 456 | 0.991 | 0.928 | 0.855 | 0.931 |
| gpt-oss-120b | strong | none | 459 | 0.834 | 0.854 | 0.705 | 0.854 |
| gpt-oss-120b | strong | human | 456 | 0.950 | 0.921 | 0.842 | 0.926 |
| deepseek-v3.1 | strong | none | 459 | 0.993 | 0.806 | 0.603 | 0.799 |
| deepseek-v3.1 | strong | human | 456 | 0.998 | 0.930 | 0.858 | 0.931 |

## Judge-routing headroom (condition = none; 1 = verdict matched gold)

Items scored by every model: 459

| Model | Tier | Accuracy | Only model correct (# items) |
|---|---|---|---|
| gpt-oss-120b | strong | 0.854 | 0 |
| gpt-oss-20b | small | 0.826 | 1 |
| deepseek-v3.1 | strong | 0.806 | 1 |
| qwen3.6-35b-a3b | mid | 0.765 | 1 |
| qwen3.5-4b | small | 0.745 | 0 |
| nemotron3-super-120b | mid | 0.741 | 1 |
| qwen3.5-9b | mid | 0.739 | 0 |
| nemotron3-nano-30b | small | 0.667 | 8 |

| Headroom check | |
|---|---|
| Best single model | **gpt-oss-120b** (0.854) |
| Oracle (any model correct) | 0.974 |
| **Oracle − best single** (room a router can win) | **0.120** |
| Items the best model misses but another gets right | 55 (0.120) |
| Items no model gets right | 0.026 |

Rule of thumb from the plan: keep a model in the routing pool if no single model wins almost everywhere and oracle − best is ≥ ~0.08 (BFF-Bench's original six models gave only ~0.04).

## Judging cost

| Model | Calls | Avg input tok | Avg output tok | $ / call | Total $ |
|---|---|---|---|---|---|
| deepseek-v3.1 | 915 | 1,069 | 188 | $0.00261 | $2.385 |
| gpt-oss-120b | 915 | 1,067 | 437 | $0.00072 | $0.658 |
| gpt-oss-20b | 915 | 1,067 | 558 | $0.00044 | $0.406 |
| nemotron3-nano-30b | 915 | 1,195 | 122 | $0.00029 | $0.268 |
| nemotron3-super-120b | 915 | 1,195 | 190 | $0.00095 | $0.873 |
| qwen3.5-4b | 915 | 1,209 | 327 | $0.00073 | $0.665 |
| qwen3.5-9b | 915 | 1,209 | 323 | $0.00144 | $1.319 |
| qwen3.6-35b-a3b | 915 | 1,209 | 448 | $0.00125 | $1.144 |

**Total: $7.72** (Tinker list prices; cached-prefill discounts not counted, so this is an upper bound)
