# Phase 2 judges: safety

Verdict = majority of the judge's votes; ties and unparseable outputs count as INCORRECT verdicts (reported separately as parse rate). kappa/accuracy vs gold labels.

## Judge quality by condition

| Judge | Tier | Condition | n | Parse rate | Accuracy | Cohen's κ | AUROC (vote share) |
|---|---|---|---|---|---|---|---|
| qwen3.5-4b | small | none | 1800 | 0.998 | 0.732 | 0.464 | 0.810 |
| gpt-oss-20b | small | none | 1800 | 0.976 | 0.847 | 0.637 | 0.859 |
| nemotron3-nano-30b | small | none | 1800 | 1.000 | 0.786 | 0.532 | 0.825 |
| qwen3.5-9b | mid | none | 1800 | 0.997 | 0.786 | 0.547 | 0.845 |
| qwen3.6-35b-a3b | mid | none | 1800 | 0.974 | 0.726 | 0.459 | 0.810 |
| nemotron3-super-120b | mid | none | 1800 | 1.000 | 0.741 | 0.480 | 0.820 |
| gpt-oss-120b | strong | none | 1800 | 0.999 | 0.779 | 0.533 | 0.835 |
| deepseek-v3.1 | strong | none | 1800 | 1.000 | 0.729 | 0.466 | 0.816 |

## Judge-routing headroom (condition = none; 1 = verdict matched gold)

Items scored by every model: 1800

| Model | Tier | Accuracy | Only model correct (# items) |
|---|---|---|---|
| gpt-oss-20b | small | 0.847 | 35 |
| nemotron3-nano-30b | small | 0.786 | 28 |
| qwen3.5-9b | mid | 0.786 | 7 |
| gpt-oss-120b | strong | 0.779 | 3 |
| nemotron3-super-120b | mid | 0.741 | 2 |
| qwen3.5-4b | small | 0.732 | 5 |
| deepseek-v3.1 | strong | 0.729 | 3 |
| qwen3.6-35b-a3b | mid | 0.726 | 2 |

| Headroom check | |
|---|---|
| Best single model | **gpt-oss-20b** (0.847) |
| Oracle (any model correct) | 0.964 |
| **Oracle − best single** (room a router can win) | **0.118** |
| Items the best model misses but another gets right | 212 (0.118) |
| Items no model gets right | 0.036 |

Rule of thumb from the plan: keep a model in the routing pool if no single model wins almost everywhere and oracle − best is ≥ ~0.08 (BFF-Bench's original six models gave only ~0.04).

## Judging cost

| Model | Calls | Avg input tok | Avg output tok | $ / call | Total $ |
|---|---|---|---|---|---|
| deepseek-v3.1 | 1800 | 392 | 106 | $0.00111 | $2.000 |
| gpt-oss-120b | 1800 | 386 | 217 | $0.00031 | $0.557 |
| gpt-oss-20b | 1800 | 386 | 284 | $0.00020 | $0.355 |
| nemotron3-nano-30b | 1800 | 414 | 72 | $0.00012 | $0.210 |
| nemotron3-super-120b | 1800 | 414 | 137 | $0.00043 | $0.781 |
| qwen3.5-4b | 1800 | 416 | 113 | $0.00025 | $0.451 |
| qwen3.5-9b | 1800 | 416 | 153 | $0.00058 | $1.044 |
| qwen3.6-35b-a3b | 1800 | 416 | 206 | $0.00050 | $0.900 |

**Total: $6.30** (Tinker list prices; cached-prefill discounts not counted, so this is an upper bound)
