# Transcript check: how judges approve the wrong answers they believe

GLM-5.3-Flash read each judging transcript (thinking off; RB2 Math + BFF; clean labels). *Re-solves* = the grader works out its own result; *lands on it* = that result equals the graded answer. Labelled: 4254 of 4063.

## Wrong answers, by belief and verdict

| group | n | re-solves | re-solves and lands on the graded answer | step check | surface only |
|---|---|---|---|---|---|
| Nemotron · belief 0/7 · approved | 140 | 16% | 16% | 82% | 13% |
| Nemotron · belief 0/7 · rejected | 391 | 91% | 2% | 20% | 6% |
| Nemotron · belief 1-3 · approved | 13 | 15% | 15% | 77% | 23% |
| Nemotron · belief 1-3 · rejected | 10 | 60% | 0% | 10% | 30% |
| Nemotron · belief 4-6 · approved | 13 | 23% | 23% | 69% | 8% |
| Nemotron · belief 4-6 · rejected | 2 | 100% | 0% | 50% | 0% |
| Nemotron · belief 7/7 · approved | 9 | 0% | 0% | 89% | 11% |
| Nemotron · belief 7/7 · rejected | 2 | 50% | 0% | 0% | 50% |
| Qwen · belief 0/7 · approved | 264 | 25% | 22% | 87% | 1% |
| Qwen · belief 0/7 · rejected | 1293 | 97% | 1% | 20% | 0% |
| Qwen · belief 1-3 · approved | 37 | 35% | 32% | 78% | 0% |
| Qwen · belief 1-3 · rejected | 82 | 98% | 4% | 15% | 0% |
| Qwen · belief 4-6 · approved | 21 | 43% | 43% | 71% | 0% |
| Qwen · belief 4-6 · rejected | 23 | 87% | 9% | 22% | 0% |
| Qwen · belief 7/7 · approved | 8 | 38% | 38% | 88% | 0% |
| Qwen · belief 7/7 · rejected | 8 | 100% | 0% | 0% | 0% |

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

## Wrong answers, pooled over belief levels

| group | n | re-solves | re-solves and lands on the graded answer | step check | surface only |
|---|---|---|---|---|---|
| Nemotron · approved | 175 | 16% | 16% | 81% | 13% |
| Nemotron · rejected | 405 | 90% | 1% | 20% | 7% |
| Qwen · approved | 330 | 28% | 25% | 85% | 1% |
| Qwen · rejected | 1406 | 97% | 1% | 20% | 0% |

## Wrong answers, by judge (all beliefs)

| group | n | re-solves | re-solves and lands on the graded answer | step check | surface only |
|---|---|---|---|---|---|
| nemotron3-super-120b · approved | 175 | 16% | 16% | 81% | 13% |
| nemotron3-super-120b · rejected | 405 | 90% | 1% | 20% | 7% |
| qwen3.5-4b · approved | 170 | 24% | 21% | 86% | 1% |
| qwen3.5-4b · rejected | 408 | 94% | 2% | 26% | 0% |
| qwen3.5-9b · approved | 121 | 26% | 22% | 88% | 0% |
| qwen3.5-9b · rejected | 457 | 97% | 1% | 20% | 0% |
| qwen3.6-35b-a3b · approved | 39 | 51% | 49% | 72% | 3% |
| qwen3.6-35b-a3b · rejected | 541 | 98% | 0% | 15% | 0% |

