# Phase 1 answers: bbeh

Rows: 3680 | models: qwen3.5-4b, gpt-oss-20b, nemotron3-nano-30b, qwen3.5-9b, qwen3.6-35b-a3b, nemotron3-super-120b, gpt-oss-120b, deepseek-v3.1

## Measured tokens and cost

| Model | Calls | Avg input tok | Avg output tok | $ / call | Total $ |
|---|---|---|---|---|---|
| deepseek-v3.1 | 460 | 1,153 | 8,261 | $0.03678 | $16.917 |
| gpt-oss-120b | 460 | 1,147 | 5,871 | $0.00531 | $2.443 |
| gpt-oss-20b | 460 | 1,147 | 9,771 | $0.00460 | $2.118 |
| nemotron3-nano-30b | 460 | 1,265 | 10,164 | $0.00528 | $2.428 |
| nemotron3-super-120b | 460 | 1,265 | 10,248 | $0.01548 | $7.120 |
| qwen3.5-4b | 460 | 1,261 | 12,991 | $0.01347 | $6.197 |
| qwen3.5-9b | 460 | 1,261 | 12,846 | $0.02646 | $12.172 |
| qwen3.6-35b-a3b | 460 | 1,261 | 11,387 | $0.01588 | $7.306 |

**Total: $56.70** (Tinker list prices; cached-prefill discounts not counted, so this is an upper bound)

## Truncated / malformed outputs (hit max tokens or no clean stop)

| Model | Share |
|---|---|
| deepseek-v3.1 | 0.237 |
| gpt-oss-120b | 0.098 |
| gpt-oss-20b | 0.424 |
| nemotron3-nano-30b | 0.511 |
| nemotron3-super-120b | 0.509 |
| qwen3.5-4b | 0.561 |
| qwen3.5-9b | 0.537 |
| qwen3.6-35b-a3b | 0.533 |

## Accuracy and routing headroom (auto-graded)

Items scored by every model: 460

| Model | Tier | Accuracy | Only model correct (# items) |
|---|---|---|---|
| deepseek-v3.1 | strong | 0.439 | 36 |
| gpt-oss-120b | strong | 0.407 | 28 |
| nemotron3-super-120b | mid | 0.276 | 0 |
| qwen3.5-9b | mid | 0.272 | 3 |
| qwen3.6-35b-a3b | mid | 0.257 | 4 |
| gpt-oss-20b | small | 0.252 | 6 |
| qwen3.5-4b | small | 0.233 | 3 |
| nemotron3-nano-30b | small | 0.207 | 5 |

| Headroom check | |
|---|---|
| Best single model | **deepseek-v3.1** (0.439) |
| Oracle (any model correct) | 0.654 |
| **Oracle − best single** (room a router can win) | **0.215** |
| Items the best model misses but another gets right | 99 (0.215) |
| Items no model gets right | 0.346 |

Rule of thumb from the plan: keep a model in the routing pool if no single model wins almost everywhere and oracle − best is ≥ ~0.08 (BFF-Bench's original six models gave only ~0.04).

## Accuracy by BBEH task

| Task | qwen3.5-4b | gpt-oss-20b | nemotron3-nano-30b | qwen3.5-9b | qwen3.6-35b-a3b | nemotron3-super-120b | gpt-oss-120b | deepseek-v3.1 |
|---|---|---|---|---|---|---|---|---|
| block00 | 0.10 | 0.05 | 0.10 | 0.10 | 0.15 | 0.15 | 0.15 | 0.35 |
| block01 | 0.10 | 0.20 | 0.25 | 0.20 | 0.25 | 0.10 | 0.55 | 0.45 |
| block02 | 0.20 | 0.35 | 0.15 | 0.30 | 0.25 | 0.30 | 0.45 | 0.45 |
| block03 | 0.25 | 0.30 | 0.10 | 0.35 | 0.20 | 0.20 | 0.35 | 0.35 |
| block04 | 0.35 | 0.25 | 0.25 | 0.35 | 0.30 | 0.40 | 0.55 | 0.55 |
| block05 | 0.25 | 0.15 | 0.20 | 0.20 | 0.15 | 0.40 | 0.35 | 0.40 |
| block06 | 0.30 | 0.30 | 0.25 | 0.40 | 0.25 | 0.40 | 0.50 | 0.50 |
| block07 | 0.15 | 0.35 | 0.25 | 0.30 | 0.35 | 0.25 | 0.35 | 0.35 |
| block08 | 0.30 | 0.20 | 0.20 | 0.25 | 0.25 | 0.30 | 0.30 | 0.40 |
| block09 | 0.25 | 0.40 | 0.30 | 0.35 | 0.30 | 0.45 | 0.60 | 0.65 |
| block10 | 0.10 | 0.20 | 0.15 | 0.30 | 0.20 | 0.25 | 0.30 | 0.40 |
| block11 | 0.15 | 0.20 | 0.25 | 0.20 | 0.20 | 0.20 | 0.30 | 0.30 |
| block12 | 0.20 | 0.25 | 0.35 | 0.15 | 0.30 | 0.35 | 0.35 | 0.35 |
| block13 | 0.25 | 0.15 | 0.15 | 0.25 | 0.25 | 0.25 | 0.30 | 0.45 |
| block14 | 0.35 | 0.45 | 0.35 | 0.40 | 0.30 | 0.40 | 0.60 | 0.50 |
| block15 | 0.40 | 0.25 | 0.25 | 0.30 | 0.35 | 0.25 | 0.40 | 0.45 |
| block16 | 0.20 | 0.30 | 0.10 | 0.30 | 0.35 | 0.40 | 0.30 | 0.40 |
| block17 | 0.25 | 0.25 | 0.25 | 0.30 | 0.20 | 0.25 | 0.55 | 0.65 |
| block18 | 0.25 | 0.40 | 0.25 | 0.35 | 0.30 | 0.25 | 0.40 | 0.40 |
| block19 | 0.30 | 0.15 | 0.10 | 0.25 | 0.30 | 0.20 | 0.60 | 0.40 |
| block20 | 0.15 | 0.15 | 0.10 | 0.15 | 0.15 | 0.15 | 0.25 | 0.30 |
| block21 | 0.20 | 0.20 | 0.15 | 0.20 | 0.20 | 0.20 | 0.35 | 0.45 |
| block22 | 0.30 | 0.30 | 0.25 | 0.30 | 0.35 | 0.25 | 0.50 | 0.60 |
