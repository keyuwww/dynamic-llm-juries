# Phase 2 judges: bbeh

Verdict = majority of the judge's votes; ties and unparseable outputs count as INCORRECT verdicts (reported separately as parse rate). kappa/accuracy vs gold labels.

## Judge quality by condition

| Judge | Tier | Condition | n | Parse rate | Accuracy | Cohen's κ | AUROC (vote share) |
|---|---|---|---|---|---|---|---|
| qwen3.5-4b | small | none | 920 | 0.895 | 0.565 | 0.143 | 0.579 |
| gpt-oss-20b | small | none | 920 | 0.776 | 0.673 | 0.252 | 0.621 |
| nemotron3-nano-30b | small | none | 920 | 0.992 | 0.561 | 0.001 | 0.500 |
| qwen3.5-9b | mid | none | 920 | 0.911 | 0.564 | 0.171 | 0.599 |
| qwen3.6-35b-a3b | mid | none | 920 | 0.893 | 0.643 | 0.288 | 0.658 |
| nemotron3-super-120b | mid | none | 920 | 0.848 | 0.561 | 0.104 | 0.556 |
| gpt-oss-120b | strong | none | 920 | 0.940 | 0.717 | 0.393 | 0.700 |
| deepseek-v3.1 | strong | none | 920 | 1.000 | 0.585 | 0.221 | 0.629 |

## Does solving the question predict judging it well? (No Free Labels' key test)

Solved = the judge's own Phase 1 answer to that question/turn was correct (official auto-grader).

| Judge | Condition | κ when judge solved it (n) | κ when judge failed it (n) |
|---|---|---|---|
| qwen3.5-4b | none | 0.354 (214) | 0.030 (706) |
| gpt-oss-20b | none | 0.438 (232) | 0.067 (688) |
| nemotron3-nano-30b | none | -0.096 (190) | -0.041 (730) |
| qwen3.5-9b | none | 0.381 (250) | 0.049 (670) |
| qwen3.6-35b-a3b | none | 0.577 (236) | 0.122 (684) |
| nemotron3-super-120b | none | 0.366 (254) | -0.093 (666) |
| gpt-oss-120b | none | 0.504 (374) | 0.175 (546) |
| deepseek-v3.1 | none | 0.345 (404) | 0.046 (516) |

## Self-preference: false-positive rate on own-family vs other answers (condition = none)

| Judge | FPR own family (n) | FPR other families (n) |
|---|---|---|
| qwen3.5-4b | 0.571 (238) | 0.399 (358) |
| gpt-oss-20b | 0.265 (136) | 0.185 (460) |
| nemotron3-nano-30b | 0.248 (165) | 0.313 (431) |
| qwen3.5-9b | 0.647 (238) | 0.433 (358) |
| qwen3.6-35b-a3b | 0.496 (238) | 0.321 (358) |
| nemotron3-super-120b | 0.345 (165) | 0.459 (431) |
| gpt-oss-120b | 0.279 (136) | 0.230 (460) |
| deepseek-v3.1 | 0.544 (57) | 0.518 (539) |

## Judge-routing headroom (condition = none; 1 = verdict matched gold)

Items scored by every model: 920

| Model | Tier | Accuracy | Only model correct (# items) |
|---|---|---|---|
| gpt-oss-120b | strong | 0.717 | 10 |
| gpt-oss-20b | small | 0.673 | 14 |
| qwen3.6-35b-a3b | mid | 0.643 | 6 |
| deepseek-v3.1 | strong | 0.585 | 9 |
| qwen3.5-4b | small | 0.565 | 4 |
| qwen3.5-9b | mid | 0.564 | 6 |
| nemotron3-nano-30b | small | 0.561 | 14 |
| nemotron3-super-120b | mid | 0.561 | 2 |

| Headroom check | |
|---|---|
| Best single model | **gpt-oss-120b** (0.717) |
| Oracle (any model correct) | 0.954 |
| **Oracle − best single** (room a router can win) | **0.237** |
| Items the best model misses but another gets right | 218 (0.237) |
| Items no model gets right | 0.046 |

Rule of thumb from the plan: keep a model in the routing pool if no single model wins almost everywhere and oracle − best is ≥ ~0.08 (BFF-Bench's original six models gave only ~0.04).

## Judging cost

| Model | Calls | Avg input tok | Avg output tok | $ / call | Total $ |
|---|---|---|---|---|---|
| deepseek-v3.1 | 920 | 6,814 | 422 | $0.01333 | $12.264 |
| gpt-oss-120b | 920 | 6,745 | 1,747 | $0.00369 | $3.398 |
| gpt-oss-20b | 920 | 6,745 | 2,903 | $0.00252 | $2.319 |
| nemotron3-nano-30b | 920 | 7,392 | 76 | $0.00148 | $1.361 |
| nemotron3-super-120b | 920 | 7,392 | 1,778 | $0.00677 | $6.232 |
| qwen3.5-4b | 920 | 7,574 | 2,336 | $0.00485 | $4.459 |
| qwen3.5-9b | 920 | 7,574 | 2,069 | $0.00913 | $8.396 |
| qwen3.6-35b-a3b | 920 | 7,574 | 2,393 | $0.00728 | $6.702 |

**Total: $45.13** (Tinker list prices; cached-prefill discounts not counted, so this is an upper bound)
