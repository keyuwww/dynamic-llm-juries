# Phase 2 judges: mtb

Verdict = majority of the judge's votes; ties and unparseable outputs count as INCORRECT verdicts (reported separately as parse rate). kappa/accuracy vs gold labels.

## Judge quality by condition

| Judge | Tier | Condition | n | Parse rate | Accuracy | Cohen's κ | AUROC (vote share) |
|---|---|---|---|---|---|---|---|
| qwen3.5-4b | small | none | 232 | 1.000 | 0.862 | 0.633 | 0.803 |
| qwen3.5-4b | small | human | 232 | 0.996 | 0.935 | 0.836 | 0.920 |
| gpt-oss-20b | small | none | 232 | 0.996 | 0.914 | 0.782 | 0.895 |
| gpt-oss-20b | small | human | 232 | 1.000 | 0.935 | 0.831 | 0.905 |
| nemotron3-nano-30b | small | none | 232 | 1.000 | 0.741 | 0.359 | 0.685 |
| nemotron3-nano-30b | small | human | 232 | 1.000 | 0.875 | 0.709 | 0.889 |
| qwen3.5-9b | mid | none | 232 | 1.000 | 0.892 | 0.718 | 0.850 |
| qwen3.5-9b | mid | human | 232 | 1.000 | 0.948 | 0.869 | 0.939 |
| qwen3.6-35b-a3b | mid | none | 232 | 1.000 | 0.901 | 0.746 | 0.871 |
| qwen3.6-35b-a3b | mid | human | 232 | 1.000 | 0.957 | 0.893 | 0.960 |
| nemotron3-super-120b | mid | none | 232 | 0.991 | 0.892 | 0.708 | 0.834 |
| nemotron3-super-120b | mid | human | 232 | 1.000 | 0.944 | 0.855 | 0.921 |
| gpt-oss-120b | strong | none | 232 | 1.000 | 0.905 | 0.763 | 0.889 |
| gpt-oss-120b | strong | human | 232 | 1.000 | 0.970 | 0.923 | 0.964 |
| deepseek-v3.1 | strong | none | 232 | 1.000 | 0.866 | 0.638 | 0.801 |
| deepseek-v3.1 | strong | human | 232 | 1.000 | 0.948 | 0.867 | 0.929 |

## Judge-routing headroom (condition = none; 1 = verdict matched gold)

Items scored by every model: 232

| Model | Tier | Accuracy | Only model correct (# items) |
|---|---|---|---|
| gpt-oss-20b | small | 0.914 | 0 |
| gpt-oss-120b | strong | 0.905 | 0 |
| qwen3.6-35b-a3b | mid | 0.901 | 0 |
| qwen3.5-9b | mid | 0.892 | 0 |
| nemotron3-super-120b | mid | 0.892 | 0 |
| deepseek-v3.1 | strong | 0.866 | 0 |
| qwen3.5-4b | small | 0.862 | 0 |
| nemotron3-nano-30b | small | 0.741 | 3 |

| Headroom check | |
|---|---|
| Best single model | **gpt-oss-20b** (0.914) |
| Oracle (any model correct) | 0.987 |
| **Oracle − best single** (room a router can win) | **0.073** |
| Items the best model misses but another gets right | 17 (0.073) |
| Items no model gets right | 0.013 |

Rule of thumb from the plan: keep a model in the routing pool if no single model wins almost everywhere and oracle − best is ≥ ~0.08 (BFF-Bench's original six models gave only ~0.04).

## Judging cost

| Model | Calls | Avg input tok | Avg output tok | $ / call | Total $ |
|---|---|---|---|---|---|
| deepseek-v3.1 | 464 | 590 | 125 | $0.00153 | $0.709 |
| gpt-oss-120b | 464 | 594 | 303 | $0.00045 | $0.209 |
| gpt-oss-20b | 464 | 594 | 436 | $0.00030 | $0.141 |
| nemotron3-nano-30b | 464 | 619 | 62 | $0.00015 | $0.070 |
| nemotron3-super-120b | 464 | 619 | 177 | $0.00061 | $0.282 |
| qwen3.5-4b | 464 | 637 | 248 | $0.00046 | $0.213 |
| qwen3.5-9b | 464 | 637 | 199 | $0.00082 | $0.380 |
| qwen3.6-35b-a3b | 464 | 637 | 338 | $0.00080 | $0.369 |

**Total: $2.37** (Tinker list prices; cached-prefill discounts not counted, so this is an upper bound)
