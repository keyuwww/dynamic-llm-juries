# Phase 2 judges: bff

Verdict = majority of the judge's votes; ties and unparseable outputs count as INCORRECT verdicts (reported separately as parse rate). kappa/accuracy vs gold labels.

## Judge quality by condition

| Judge | Tier | Condition | n | Parse rate | Accuracy | Cohen's κ | AUROC (vote share) |
|---|---|---|---|---|---|---|---|
| qwen3.5-4b | small | none | 459 | 0.959 | 0.741 | 0.472 | 0.734 |
| qwen3.5-4b | small | rules2 | 459 | 0.946 | 0.739 | 0.460 | 0.725 |
| qwen3.5-4b | small | rules2_norule2 | 459 | 0.952 | 0.741 | 0.465 | 0.729 |
| gpt-oss-20b | small | none | 459 | 0.917 | 0.841 | 0.677 | 0.838 |
| gpt-oss-20b | small | rules2 | 459 | 0.928 | 0.824 | 0.641 | 0.819 |
| gpt-oss-20b | small | rules2_norule2 | 459 | 0.946 | 0.841 | 0.673 | 0.832 |
| nemotron3-nano-30b | small | none | 459 | 1.000 | 0.675 | 0.348 | 0.676 |
| nemotron3-nano-30b | small | rules2 | 459 | 0.993 | 0.662 | 0.304 | 0.650 |
| nemotron3-nano-30b | small | rules2_norule2 | 459 | 0.996 | 0.695 | 0.356 | 0.671 |
| qwen3.5-9b | mid | none | 459 | 0.961 | 0.784 | 0.564 | 0.783 |
| qwen3.5-9b | mid | rules2 | 459 | 0.917 | 0.802 | 0.600 | 0.802 |
| qwen3.5-9b | mid | rules2_norule2 | 459 | 0.939 | 0.804 | 0.597 | 0.795 |
| qwen3.6-35b-a3b | mid | none | 459 | 0.946 | 0.769 | 0.542 | 0.777 |
| qwen3.6-35b-a3b | mid | rules2 | 459 | 0.874 | 0.821 | 0.645 | 0.829 |
| qwen3.6-35b-a3b | mid | rules2_norule2 | 459 | 0.908 | 0.806 | 0.610 | 0.808 |
| nemotron3-super-120b | mid | none | 459 | 0.976 | 0.763 | 0.502 | 0.743 |
| nemotron3-super-120b | mid | rules2 | 459 | 0.861 | 0.793 | 0.581 | 0.791 |
| nemotron3-super-120b | mid | rules2_norule2 | 459 | 0.889 | 0.800 | 0.585 | 0.786 |
| gpt-oss-120b | strong | none | 459 | 0.963 | 0.839 | 0.674 | 0.838 |
| gpt-oss-120b | strong | rules2 | 459 | 0.980 | 0.841 | 0.678 | 0.840 |
| gpt-oss-120b | strong | rules2_norule2 | 459 | 0.980 | 0.834 | 0.663 | 0.831 |
| deepseek-v3.1 | strong | none | 459 | 1.000 | 0.800 | 0.589 | 0.791 |
| deepseek-v3.1 | strong | rules2 | 459 | 1.000 | 0.800 | 0.586 | 0.787 |
| deepseek-v3.1 | strong | rules2_norule2 | 459 | 1.000 | 0.745 | 0.461 | 0.721 |

## Judge-routing headroom (condition = none; 1 = verdict matched gold)

Items scored by every model: 459

| Model | Tier | Accuracy | Only model correct (# items) |
|---|---|---|---|
| gpt-oss-20b | small | 0.841 | 1 |
| gpt-oss-120b | strong | 0.839 | 0 |
| deepseek-v3.1 | strong | 0.800 | 1 |
| qwen3.5-9b | mid | 0.784 | 1 |
| qwen3.6-35b-a3b | mid | 0.769 | 1 |
| nemotron3-super-120b | mid | 0.763 | 0 |
| qwen3.5-4b | small | 0.741 | 2 |
| nemotron3-nano-30b | small | 0.675 | 8 |

| Headroom check | |
|---|---|
| Best single model | **gpt-oss-20b** (0.841) |
| Oracle (any model correct) | 0.974 |
| **Oracle − best single** (room a router can win) | **0.133** |
| Items the best model misses but another gets right | 61 (0.133) |
| Items no model gets right | 0.026 |

Rule of thumb from the plan: keep a model in the routing pool if no single model wins almost everywhere and oracle − best is ≥ ~0.08 (BFF-Bench's original six models gave only ~0.04).

## Judging cost

| Model | Calls | Avg input tok | Avg output tok | $ / call | Total $ |
|---|---|---|---|---|---|
| deepseek-v3.1 | 1836 | 1,076 | 294 | $0.00306 | $5.627 |
| gpt-oss-120b | 1836 | 1,072 | 666 | $0.00091 | $1.676 |
| gpt-oss-20b | 1836 | 1,072 | 800 | $0.00055 | $1.015 |
| nemotron3-nano-30b | 1836 | 1,183 | 249 | $0.00035 | $0.650 |
| nemotron3-super-120b | 1836 | 1,183 | 669 | $0.00164 | $3.006 |
| qwen3.5-4b | 1836 | 1,197 | 513 | $0.00091 | $1.671 |
| qwen3.5-9b | 1836 | 1,197 | 636 | $0.00206 | $3.781 |
| qwen3.6-35b-a3b | 1836 | 1,197 | 834 | $0.00176 | $3.230 |

**Total: $20.66** (Tinker list prices; cached-prefill discounts not counted, so this is an upper bound)
