# Phase 2 judges: bbeh

Verdict = majority of the judge's votes; ties and unparseable outputs count as INCORRECT verdicts (reported separately as parse rate). kappa/accuracy vs gold labels.

## Judge quality by condition

| Judge | Tier | Condition | n | Parse rate | Accuracy | Cohen's κ | AUROC (vote share) |
|---|---|---|---|---|---|---|---|
| qwen3.5-4b | small | none | 920 | 0.892 | 0.634 | 0.273 | 0.678 |
| gpt-oss-20b | small | none | 920 | 0.753 | 0.737 | 0.329 | 0.667 |
| nemotron3-nano-30b | small | none | 920 | 0.992 | 0.674 | 0.248 | 0.639 |
| qwen3.5-9b | mid | none | 920 | 0.910 | 0.655 | 0.320 | 0.710 |
| qwen3.6-35b-a3b | mid | none | 920 | 0.849 | 0.700 | 0.385 | 0.743 |
| nemotron3-super-120b | mid | none | 920 | 0.887 | 0.649 | 0.282 | 0.679 |
| gpt-oss-120b | strong | none | 920 | 0.927 | 0.765 | 0.441 | 0.740 |
| deepseek-v3.1 | strong | none | 920 | 1.000 | 0.558 | 0.216 | 0.658 |

## Does solving the question predict judging it well? (No Free Labels' key test)

Solved = the judge's own Phase 1 answer to that question/turn was correct (official auto-grader).

| Judge | Condition | κ when judge solved it (n) | κ when judge failed it (n) |
|---|---|---|---|
| qwen3.5-4b | none | 0.423 (162) | 0.197 (758) |
| gpt-oss-20b | none | 0.527 (140) | 0.222 (780) |
| nemotron3-nano-30b | none | 0.065 (98) | 0.260 (822) |
| qwen3.5-9b | none | 0.449 (206) | 0.220 (714) |
| qwen3.6-35b-a3b | none | 0.524 (242) | 0.246 (678) |
| nemotron3-super-120b | none | 0.128 (146) | 0.287 (774) |
| gpt-oss-120b | none | 0.641 (212) | 0.295 (706) |
| deepseek-v3.1 | none | 0.506 (290) | 0.066 (630) |

## Self-preference: false-positive rate on own-family vs other answers (condition = none)

| Judge | FPR own family (n) | FPR other families (n) |
|---|---|---|
| qwen3.5-4b | 0.456 (250) | 0.391 (430) |
| gpt-oss-20b | 0.224 (170) | 0.175 (510) |
| nemotron3-nano-30b | 0.199 (181) | 0.321 (499) |
| qwen3.5-9b | 0.456 (250) | 0.374 (430) |
| qwen3.6-35b-a3b | 0.416 (250) | 0.307 (430) |
| nemotron3-super-120b | 0.166 (181) | 0.463 (499) |
| gpt-oss-120b | 0.329 (170) | 0.167 (510) |
| deepseek-v3.1 | 0.797 (79) | 0.519 (601) |

## Judge-routing headroom (condition = none; 1 = verdict matched gold)

Items scored by every model: 920

| Model | Tier | Accuracy | Only model correct (# items) |
|---|---|---|---|
| gpt-oss-120b | strong | 0.765 | 12 |
| gpt-oss-20b | small | 0.737 | 11 |
| qwen3.6-35b-a3b | mid | 0.700 | 2 |
| nemotron3-nano-30b | small | 0.674 | 15 |
| qwen3.5-9b | mid | 0.655 | 4 |
| nemotron3-super-120b | mid | 0.649 | 2 |
| qwen3.5-4b | small | 0.634 | 2 |
| deepseek-v3.1 | strong | 0.558 | 4 |

| Headroom check | |
|---|---|
| Best single model | **gpt-oss-120b** (0.765) |
| Oracle (any model correct) | 0.947 |
| **Oracle − best single** (room a router can win) | **0.182** |
| Items the best model misses but another gets right | 167 (0.182) |
| Items no model gets right | 0.053 |

Rule of thumb from the plan: keep a model in the routing pool if no single model wins almost everywhere and oracle − best is ≥ ~0.08 (BFF-Bench's original six models gave only ~0.04).

## Judging cost

| Model | Calls | Avg input tok | Avg output tok | $ / call | Total $ |
|---|---|---|---|---|---|
| deepseek-v3.1 | 920 | 3,036 | 394 | $0.00681 | $6.264 |
| gpt-oss-120b | 920 | 3,007 | 1,794 | $0.00250 | $2.300 |
| gpt-oss-20b | 920 | 3,007 | 3,076 | $0.00193 | $1.771 |
| nemotron3-nano-30b | 920 | 3,301 | 163 | $0.00072 | $0.666 |
| nemotron3-super-120b | 920 | 3,301 | 1,291 | $0.00374 | $3.442 |
| qwen3.5-4b | 920 | 3,351 | 2,283 | $0.00340 | $3.128 |
| qwen3.5-9b | 920 | 3,351 | 1,987 | $0.00618 | $5.681 |
| qwen3.6-35b-a3b | 920 | 3,351 | 2,904 | $0.00569 | $5.232 |

**Total: $28.48** (Tinker list prices; cached-prefill discounts not counted, so this is an upper bound)
