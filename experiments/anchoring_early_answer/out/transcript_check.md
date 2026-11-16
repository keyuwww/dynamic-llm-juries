# Transcript check: how judges approve the wrong answers they believe

GLM-5.3-Flash read each judging transcript (thinking off; RB2 Math + BFF; clean labels). *Re-solves* = the grader works out its own result; *lands on it* = that result equals the graded answer. Labelled: 4254 of 4254.

## Wrong answers, by belief and verdict

| group | n | re-solves | re-solves and lands on the graded answer | step check | surface only |
|---|---|---|---|---|---|
| Nemotron · belief 0/7 · approved | 143 | 17% | 17% | 82% | 13% |
| Nemotron · belief 0/7 · rejected | 399 | 91% | 2% | 20% | 6% |
| Nemotron · belief 1-3 · approved | 18 | 22% | 22% | 83% | 17% |
| Nemotron · belief 1-3 · rejected | 13 | 62% | 0% | 15% | 23% |
| Nemotron · belief 4-6 · approved | 21 | 19% | 19% | 71% | 14% |
| Nemotron · belief 4-6 · rejected | 5 | 100% | 20% | 20% | 0% |
| Nemotron · belief 7/7 · approved | 26 | 0% | 0% | 81% | 19% |
| Nemotron · belief 7/7 · rejected | 3 | 67% | 0% | 0% | 33% |
| Qwen · belief 0/7 · approved | 274 | 26% | 23% | 86% | 1% |
| Qwen · belief 0/7 · rejected | 1314 | 96% | 1% | 20% | 0% |
| Qwen · belief 1-3 · approved | 56 | 41% | 39% | 75% | 0% |
| Qwen · belief 1-3 · rejected | 99 | 97% | 4% | 16% | 0% |
| Qwen · belief 4-6 · approved | 43 | 44% | 40% | 67% | 0% |
| Qwen · belief 4-6 · rejected | 31 | 90% | 10% | 16% | 0% |
| Qwen · belief 7/7 · approved | 46 | 43% | 43% | 76% | 0% |
| Qwen · belief 7/7 · rejected | 16 | 94% | 19% | 6% | 0% |

## Correct answers, by belief and verdict (control)

| group | n | re-solves | re-solves and lands on the graded answer | step check | surface only |
|---|---|---|---|---|---|
| Nemotron · belief 0/7 · approved | 18 | 22% | 22% | 61% | 28% |
| Nemotron · belief 0/7 · rejected | 16 | 81% | 0% | 38% | 12% |
| Nemotron · belief 1-3 · approved | 13 | 54% | 46% | 31% | 15% |
| Nemotron · belief 1-3 · rejected | 2 | 100% | 0% | 50% | 0% |
| Nemotron · belief 4-6 · approved | 45 | 27% | 27% | 67% | 11% |
| Nemotron · belief 4-6 · rejected | 4 | 75% | 25% | 25% | 25% |
| Nemotron · belief 7/7 · approved | 318 | 15% | 15% | 80% | 11% |
| Nemotron · belief 7/7 · rejected | 21 | 71% | 33% | 24% | 24% |
| Qwen · belief 0/7 · approved | 29 | 48% | 41% | 69% | 0% |
| Qwen · belief 0/7 · rejected | 68 | 99% | 0% | 29% | 0% |
| Qwen · belief 1-3 · approved | 55 | 44% | 44% | 76% | 0% |
| Qwen · belief 1-3 · rejected | 22 | 95% | 0% | 45% | 0% |
| Qwen · belief 4-6 · approved | 173 | 40% | 39% | 69% | 1% |
| Qwen · belief 4-6 · rejected | 37 | 76% | 11% | 46% | 0% |
| Qwen · belief 7/7 · approved | 820 | 32% | 32% | 79% | 2% |
| Qwen · belief 7/7 · rejected | 106 | 91% | 34% | 56% | 1% |

## Wrong answers, by judge (all beliefs)

| group | n | re-solves | re-solves and lands on the graded answer | step check | surface only |
|---|---|---|---|---|---|
| nemotron3-super-120b · approved | 208 | 15% | 15% | 81% | 14% |
| nemotron3-super-120b · rejected | 420 | 90% | 2% | 20% | 6% |
| qwen3.5-4b · approved | 201 | 25% | 23% | 85% | 1% |
| qwen3.5-4b · rejected | 424 | 94% | 3% | 26% | 0% |
| qwen3.5-9b · approved | 149 | 26% | 22% | 87% | 0% |
| qwen3.5-9b · rejected | 477 | 96% | 1% | 20% | 0% |
| qwen3.6-35b-a3b · approved | 69 | 64% | 61% | 62% | 1% |
| qwen3.6-35b-a3b · rejected | 559 | 98% | 0% | 14% | 0% |

