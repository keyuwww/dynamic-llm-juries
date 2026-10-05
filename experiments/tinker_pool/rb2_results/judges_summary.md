# Phase 2 judges: rb2

Verdict = majority of the judge's votes; ties and unparseable outputs count as INCORRECT verdicts (reported separately as parse rate). kappa/accuracy vs gold labels.

## Judge quality by condition

| Judge | Tier | Condition | n | Parse rate | Accuracy | Cohen's κ | AUROC (vote share) |
|---|---|---|---|---|---|---|---|
| qwen3.5-4b | small | none | 7177 | 0.988 | 0.814 | 0.544 | 0.797 |
| gpt-oss-20b | small | none | 7177 | 0.930 | 0.870 | 0.646 | 0.818 |
| nemotron3-nano-30b | small | none | 7177 | 0.998 | 0.751 | 0.418 | 0.739 |
| qwen3.5-9b | mid | none | 7177 | 0.978 | 0.849 | 0.605 | 0.811 |
| qwen3.6-35b-a3b | mid | none | 7177 | 0.963 | 0.869 | 0.631 | 0.800 |
| nemotron3-super-120b | mid | none | 7177 | 0.990 | 0.862 | 0.655 | 0.851 |
| gpt-oss-120b | strong | none | 7177 | 0.974 | 0.883 | 0.683 | 0.839 |
| deepseek-v3.1 | strong | none | 7177 | 1.000 | 0.841 | 0.623 | 0.851 |

## Judge quality by domain (condition = none)

| Judge | Factuality | Focus | Math | Precise IF | Ties |
|---|---|---|---|---|---|
| qwen3.5-4b | 0.420 | 0.589 | 0.442 | 0.060 | 0.800 |
| gpt-oss-20b | 0.475 | 0.563 | 0.699 | 0.317 | 0.965 |
| nemotron3-nano-30b | 0.408 | 0.256 | 0.284 | 0.032 | 0.852 |
| qwen3.5-9b | 0.469 | 0.612 | 0.507 | 0.222 | 0.877 |
| qwen3.6-35b-a3b | 0.489 | 0.523 | 0.653 | 0.311 | 0.936 |
| nemotron3-super-120b | 0.606 | 0.647 | 0.476 | 0.213 | 0.965 |
| gpt-oss-120b | 0.587 | 0.573 | 0.737 | 0.362 | 0.968 |
| deepseek-v3.1 | 0.582 | 0.697 | 0.409 | 0.138 | 0.901 |

(Only Safety is human-annotated; these domains use LLM-judged/algorithmic gold labels -- read as capability/algorithmic-agreement, not human-preference agreement.)

## Judge-routing headroom (condition = none; 1 = verdict matched gold)

Items scored by every model: 7177

| Model | Tier | Accuracy | Only model correct (# items) |
|---|---|---|---|
| gpt-oss-120b | strong | 0.883 | 7 |
| gpt-oss-20b | small | 0.870 | 10 |
| qwen3.6-35b-a3b | mid | 0.869 | 23 |
| nemotron3-super-120b | mid | 0.862 | 16 |
| qwen3.5-9b | mid | 0.849 | 10 |
| deepseek-v3.1 | strong | 0.841 | 49 |
| qwen3.5-4b | small | 0.814 | 10 |
| nemotron3-nano-30b | small | 0.751 | 22 |

| Headroom check | |
|---|---|
| Best single model | **gpt-oss-120b** (0.883) |
| Oracle (any model correct) | 0.978 |
| **Oracle − best single** (room a router can win) | **0.095** |
| Items the best model misses but another gets right | 682 (0.095) |
| Items no model gets right | 0.022 |

Rule of thumb from the plan: keep a model in the routing pool if no single model wins almost everywhere and oracle − best is ≥ ~0.08 (BFF-Bench's original six models gave only ~0.04).

## Judging cost

| Model | Calls | Avg input tok | Avg output tok | $ / call | Total $ |
|---|---|---|---|---|---|
| deepseek-v3.1 | 7177 | 452 | 115 | $0.00125 | $8.978 |
| gpt-oss-120b | 7177 | 453 | 303 | $0.00040 | $2.903 |
| gpt-oss-20b | 7177 | 453 | 368 | $0.00025 | $1.774 |
| nemotron3-nano-30b | 7177 | 479 | 99 | $0.00014 | $1.022 |
| nemotron3-super-120b | 7177 | 479 | 143 | $0.00048 | $3.436 |
| qwen3.5-4b | 7177 | 485 | 134 | $0.00030 | $2.119 |
| qwen3.5-9b | 7177 | 485 | 184 | $0.00069 | $4.934 |
| qwen3.6-35b-a3b | 7177 | 485 | 255 | $0.00060 | $4.323 |

**Total: $29.49** (Tinker list prices; cached-prefill discounts not counted, so this is an upper bound)
