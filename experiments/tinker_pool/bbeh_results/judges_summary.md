# Phase 2 judges: bbeh

Verdict = majority of the judge's votes; ties and unparseable outputs count as INCORRECT verdicts (reported separately as parse rate). kappa/accuracy vs gold labels.

## Judge quality by condition

| Judge | Tier | Condition | n | Parse rate | Accuracy | Cohen's κ | AUROC (vote share) |
|---|---|---|---|---|---|---|---|
| qwen3.5-4b | small | none | 920 | 0.873 | 0.668 | 0.325 | 0.711 |
| gpt-oss-20b | small | none | 920 | 0.752 | 0.774 | 0.409 | 0.707 |
| nemotron3-nano-30b | small | none | 920 | 0.992 | 0.675 | 0.248 | 0.642 |
| qwen3.5-9b | mid | none | 920 | 0.908 | 0.678 | 0.371 | 0.751 |
| qwen3.6-35b-a3b | mid | none | 920 | 0.845 | 0.727 | 0.430 | 0.772 |
| nemotron3-super-120b | mid | none | 920 | 0.889 | 0.671 | 0.312 | 0.697 |
| gpt-oss-120b | strong | none | 920 | 0.937 | 0.777 | 0.477 | 0.769 |
| deepseek-v3.1 | strong | none | 920 | 1.000 | 0.577 | 0.239 | 0.676 |

## Does solving the question predict judging it well? (No Free Labels' key test)

Solved = the judge's own Phase 1 answer to that question/turn was correct (official auto-grader).

| Judge | Condition | κ when judge solved it (n) | κ when judge failed it (n) |
|---|---|---|---|
| qwen3.5-4b | none | 0.512 (164) | 0.234 (756) |
| gpt-oss-20b | none | 0.645 (126) | 0.289 (794) |
| nemotron3-nano-30b | none | 0.270 (86) | 0.239 (834) |
| qwen3.5-9b | none | 0.540 (196) | 0.273 (724) |
| qwen3.6-35b-a3b | none | 0.620 (256) | 0.263 (664) |
| nemotron3-super-120b | none | 0.252 (140) | 0.307 (780) |
| gpt-oss-120b | none | 0.664 (210) | 0.328 (710) |
| deepseek-v3.1 | none | 0.535 (292) | 0.079 (628) |

## Self-preference: false-positive rate on own-family vs other answers (condition = none)

| Judge | FPR own family (n) | FPR other families (n) |
|---|---|---|
| qwen3.5-4b | 0.409 (247) | 0.357 (440) |
| gpt-oss-20b | 0.205 (156) | 0.143 (531) |
| nemotron3-nano-30b | 0.230 (209) | 0.318 (478) |
| qwen3.5-9b | 0.417 (247) | 0.384 (440) |
| qwen3.6-35b-a3b | 0.372 (247) | 0.289 (440) |
| nemotron3-super-120b | 0.206 (209) | 0.423 (478) |
| gpt-oss-120b | 0.359 (156) | 0.171 (531) |
| deepseek-v3.1 | 0.733 (75) | 0.498 (612) |

## Judge-routing headroom (condition = none; 1 = verdict matched gold)

Items scored by every model: 920

| Model | Tier | Accuracy | Only model correct (# items) |
|---|---|---|---|
| gpt-oss-120b | strong | 0.777 | 7 |
| gpt-oss-20b | small | 0.774 | 12 |
| qwen3.6-35b-a3b | mid | 0.727 | 5 |
| qwen3.5-9b | mid | 0.678 | 2 |
| nemotron3-nano-30b | small | 0.675 | 21 |
| nemotron3-super-120b | mid | 0.671 | 0 |
| qwen3.5-4b | small | 0.668 | 2 |
| deepseek-v3.1 | strong | 0.577 | 2 |

| Headroom check | |
|---|---|
| Best single model | **gpt-oss-120b** (0.777) |
| Oracle (any model correct) | 0.966 |
| **Oracle − best single** (room a router can win) | **0.189** |
| Items the best model misses but another gets right | 174 (0.189) |
| Items no model gets right | 0.034 |

Rule of thumb from the plan: keep a model in the routing pool if no single model wins almost everywhere and oracle − best is ≥ ~0.08 (BFF-Bench's original six models gave only ~0.04).

## Judging cost

| Model | Calls | Avg input tok | Avg output tok | $ / call | Total $ |
|---|---|---|---|---|---|
| deepseek-v3.1 | 920 | 2,939 | 457 | $0.00691 | $6.356 |
| gpt-oss-120b | 920 | 2,911 | 1,683 | $0.00237 | $2.184 |
| gpt-oss-20b | 920 | 2,911 | 3,223 | $0.00197 | $1.816 |
| nemotron3-nano-30b | 920 | 3,194 | 157 | $0.00070 | $0.644 |
| nemotron3-super-120b | 920 | 3,194 | 1,335 | $0.00374 | $3.444 |
| qwen3.5-4b | 920 | 3,242 | 2,477 | $0.00356 | $3.275 |
| qwen3.5-9b | 920 | 3,242 | 2,030 | $0.00619 | $5.695 |
| qwen3.6-35b-a3b | 920 | 3,242 | 3,026 | $0.00579 | $5.327 |

**Total: $28.74** (Tinker list prices; cached-prefill discounts not counted, so this is an upper bound)
