# Phase 2 judges: safety

Verdict = majority of the judge's votes; ties and unparseable outputs count as INCORRECT verdicts (reported separately as parse rate). kappa/accuracy vs gold labels.

## Judge quality by condition

| Judge | Tier | Condition | n | Parse rate | Accuracy | Cohen's κ | AUROC (vote share) |
|---|---|---|---|---|---|---|---|
| deepseek-v3.1 | strong | none | 1800 | 1.000 | 0.730 | 0.468 | 0.816 |

## Judge-routing headroom (condition = none; 1 = verdict matched gold)

Items scored by every model: 1800

| Model | Tier | Accuracy | Only model correct (# items) |
|---|---|---|---|
| deepseek-v3.1 | strong | 0.730 | 1314 |

| Headroom check | |
|---|---|
| Best single model | **deepseek-v3.1** (0.730) |
| Oracle (any model correct) | 0.730 |
| **Oracle − best single** (room a router can win) | **0.000** |
| Items the best model misses but another gets right | 0 (0.000) |
| Items no model gets right | 0.270 |

Rule of thumb from the plan: keep a model in the routing pool if no single model wins almost everywhere and oracle − best is ≥ ~0.08 (BFF-Bench's original six models gave only ~0.04).

## Judging cost

| Model | Calls | Avg input tok | Avg output tok | $ / call | Total $ |
|---|---|---|---|---|---|
| deepseek-v3.1 | 1800 | 392 | 107 | $0.00111 | $2.005 |

**Total: $2.00** (Tinker list prices; cached-prefill discounts not counted, so this is an upper bound)
