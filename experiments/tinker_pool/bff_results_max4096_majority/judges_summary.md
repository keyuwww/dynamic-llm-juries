# Phase 2 judges: bff

Verdict = majority of the judge's votes; ties and unparseable outputs count as INCORRECT verdicts (reported separately as parse rate). kappa/accuracy vs gold labels.

## Judge quality by condition

| Judge | Tier | Condition | n | Parse rate | Accuracy | Cohen's κ | AUROC (vote share) |
|---|---|---|---|---|---|---|---|
| deepseek-v3.1 | strong | none | 878 | 1.000 | 0.753 | 0.494 | 0.745 |
| deepseek-v3.1 | strong | human | 866 | 1.000 | 0.848 | 0.693 | 0.850 |

## Judge-routing headroom (condition = none; 1 = verdict matched gold)

Items scored by every model: 878

| Model | Tier | Accuracy | Only model correct (# items) |
|---|---|---|---|
| deepseek-v3.1 | strong | 0.753 | 661 |

| Headroom check | |
|---|---|
| Best single model | **deepseek-v3.1** (0.753) |
| Oracle (any model correct) | 0.753 |
| **Oracle − best single** (room a router can win) | **0.000** |
| Items the best model misses but another gets right | 0 (0.000) |
| Items no model gets right | 0.247 |

Rule of thumb from the plan: keep a model in the routing pool if no single model wins almost everywhere and oracle − best is ≥ ~0.08 (BFF-Bench's original six models gave only ~0.04).

## Judging cost

| Model | Calls | Avg input tok | Avg output tok | $ / call | Total $ |
|---|---|---|---|---|---|
| deepseek-v3.1 | 1744 | 1,088 | 194 | $0.00266 | $4.640 |

**Total: $4.64** (Tinker list prices; cached-prefill discounts not counted, so this is an upper bound)
