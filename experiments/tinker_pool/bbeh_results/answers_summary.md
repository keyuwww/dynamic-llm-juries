# Phase 1 answers: bbeh

Rows: 460 | models: deepseek-v3.1

## Measured tokens and cost

| Model | Calls | Avg input tok | Avg output tok | $ / call | Total $ |
|---|---|---|---|---|---|
| deepseek-v3.1 | 460 | 1,153 | 1,904 | $0.00998 | $4.592 |

**Total: $4.59** (Tinker list prices; cached-prefill discounts not counted, so this is an upper bound)

## Truncated / malformed outputs (hit max tokens or no clean stop)

| Model | Share |
|---|---|
| deepseek-v3.1 | 0.107 |

## Accuracy and routing headroom (auto-graded)

Items scored by every model: 460

| Model | Tier | Accuracy | Only model correct (# items) |
|---|---|---|---|
| deepseek-v3.1 | strong | 0.315 | 145 |

| Headroom check | |
|---|---|
| Best single model | **deepseek-v3.1** (0.315) |
| Oracle (any model correct) | 0.315 |
| **Oracle − best single** (room a router can win) | **0.000** |
| Items the best model misses but another gets right | 0 (0.000) |
| Items no model gets right | 0.685 |

Rule of thumb from the plan: keep a model in the routing pool if no single model wins almost everywhere and oracle − best is ≥ ~0.08 (BFF-Bench's original six models gave only ~0.04).

## Accuracy by BBEH task

| Task | deepseek-v3.1 |
|---|---|
| block00 | 0.25 |
| block01 | 0.35 |
| block02 | 0.15 |
| block03 | 0.25 |
| block04 | 0.20 |
| block05 | 0.20 |
| block06 | 0.40 |
| block07 | 0.30 |
| block08 | 0.35 |
| block09 | 0.40 |
| block10 | 0.30 |
| block11 | 0.40 |
| block12 | 0.25 |
| block13 | 0.50 |
| block14 | 0.30 |
| block15 | 0.40 |
| block16 | 0.35 |
| block17 | 0.40 |
| block18 | 0.30 |
| block19 | 0.25 |
| block20 | 0.25 |
| block21 | 0.35 |
| block22 | 0.35 |
