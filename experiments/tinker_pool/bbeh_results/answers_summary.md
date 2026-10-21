# Phase 1 answers: bbeh

Rows: 3680 | models: qwen3.5-4b, gpt-oss-20b, nemotron3-nano-30b, qwen3.5-9b, qwen3.6-35b-a3b, nemotron3-super-120b, gpt-oss-120b, deepseek-v3.1

## Measured tokens and cost

| Model | Calls | Avg input tok | Avg output tok | $ / call | Total $ |
|---|---|---|---|---|---|
| deepseek-v3.1 | 460 | 1,153 | 1,921 | $0.01005 | $4.623 |
| gpt-oss-120b | 460 | 1,147 | 2,789 | $0.00272 | $1.252 |
| gpt-oss-20b | 460 | 1,147 | 3,224 | $0.00166 | $0.762 |
| nemotron3-nano-30b | 460 | 1,265 | 20 | $0.00026 | $0.118 |
| nemotron3-super-120b | 460 | 1,265 | 229 | $0.00105 | $0.484 |
| qwen3.5-4b | 460 | 1,263 | 2,834 | $0.00326 | $1.502 |
| qwen3.5-9b | 460 | 1,263 | 3,104 | $0.00703 | $3.232 |
| qwen3.6-35b-a3b | 460 | 1,263 | 2,937 | $0.00460 | $2.118 |

**Total: $14.09** (Tinker list prices; cached-prefill discounts not counted, so this is an upper bound)

## Truncated / malformed outputs (hit max tokens or no clean stop)

| Model | Share |
|---|---|
| deepseek-v3.1 | 0.146 |
| gpt-oss-120b | 0.509 |
| gpt-oss-20b | 0.670 |
| nemotron3-nano-30b | 0.002 |
| nemotron3-super-120b | 0.041 |
| qwen3.5-4b | 0.550 |
| qwen3.5-9b | 0.580 |
| qwen3.6-35b-a3b | 0.533 |

## Accuracy and routing headroom (auto-graded)

Items scored by every model: 460

| Model | Tier | Accuracy | Only model correct (# items) |
|---|---|---|---|
| deepseek-v3.1 | strong | 0.317 | 26 |
| qwen3.6-35b-a3b | mid | 0.278 | 7 |
| gpt-oss-120b | strong | 0.228 | 5 |
| qwen3.5-9b | mid | 0.213 | 2 |
| qwen3.5-4b | small | 0.178 | 6 |
| nemotron3-super-120b | mid | 0.152 | 10 |
| gpt-oss-20b | small | 0.137 | 0 |
| nemotron3-nano-30b | small | 0.093 | 3 |

| Headroom check | |
|---|---|
| Best single model | **deepseek-v3.1** (0.317) |
| Oracle (any model correct) | 0.496 |
| **Oracle − best single** (room a router can win) | **0.178** |
| Items the best model misses but another gets right | 82 (0.178) |
| Items no model gets right | 0.504 |

Rule of thumb from the plan: keep a model in the routing pool if no single model wins almost everywhere and oracle − best is ≥ ~0.08 (BFF-Bench's original six models gave only ~0.04).

## Accuracy by BBEH task

| Task | qwen3.5-4b | gpt-oss-20b | nemotron3-nano-30b | qwen3.5-9b | qwen3.6-35b-a3b | nemotron3-super-120b | gpt-oss-120b | deepseek-v3.1 |
|---|---|---|---|---|---|---|---|---|
| block00 | 0.10 | 0.05 | 0.15 | 0.10 | 0.10 | 0.10 | 0.15 | 0.25 |
| block01 | 0.10 | 0.20 | 0.15 | 0.15 | 0.15 | 0.10 | 0.25 | 0.35 |
| block02 | 0.15 | 0.10 | 0.05 | 0.10 | 0.20 | 0.05 | 0.20 | 0.10 |
| block03 | 0.30 | 0.15 | 0.15 | 0.30 | 0.40 | 0.20 | 0.20 | 0.35 |
| block04 | 0.15 | 0.15 | 0.05 | 0.40 | 0.35 | 0.10 | 0.20 | 0.30 |
| block05 | 0.10 | 0.10 | 0.05 | 0.30 | 0.20 | 0.15 | 0.15 | 0.35 |
| block06 | 0.20 | 0.15 | 0.20 | 0.15 | 0.40 | 0.30 | 0.40 | 0.40 |
| block07 | 0.25 | 0.20 | 0.10 | 0.25 | 0.35 | 0.10 | 0.20 | 0.30 |
| block08 | 0.20 | 0.15 | 0.15 | 0.25 | 0.20 | 0.25 | 0.30 | 0.25 |
| block09 | 0.25 | 0.20 | 0.10 | 0.30 | 0.50 | 0.05 | 0.35 | 0.40 |
| block10 | 0.00 | 0.10 | 0.10 | 0.20 | 0.25 | 0.05 | 0.15 | 0.30 |
| block11 | 0.10 | 0.05 | 0.15 | 0.10 | 0.30 | 0.35 | 0.20 | 0.25 |
| block12 | 0.20 | 0.15 | 0.05 | 0.10 | 0.30 | 0.20 | 0.30 | 0.30 |
| block13 | 0.25 | 0.15 | 0.05 | 0.35 | 0.30 | 0.15 | 0.20 | 0.45 |
| block14 | 0.30 | 0.30 | 0.15 | 0.25 | 0.35 | 0.20 | 0.30 | 0.25 |
| block15 | 0.30 | 0.20 | 0.15 | 0.30 | 0.25 | 0.20 | 0.25 | 0.35 |
| block16 | 0.10 | 0.15 | 0.00 | 0.25 | 0.25 | 0.20 | 0.15 | 0.30 |
| block17 | 0.20 | 0.10 | 0.25 | 0.25 | 0.30 | 0.20 | 0.25 | 0.45 |
| block18 | 0.10 | 0.15 | 0.00 | 0.30 | 0.35 | 0.05 | 0.30 | 0.25 |
| block19 | 0.10 | 0.15 | 0.05 | 0.10 | 0.20 | 0.10 | 0.15 | 0.25 |
| block20 | 0.20 | 0.05 | 0.05 | 0.15 | 0.20 | 0.15 | 0.15 | 0.35 |
| block21 | 0.20 | 0.05 | 0.00 | 0.05 | 0.15 | 0.15 | 0.20 | 0.30 |
| block22 | 0.25 | 0.10 | 0.00 | 0.20 | 0.35 | 0.10 | 0.25 | 0.45 |
