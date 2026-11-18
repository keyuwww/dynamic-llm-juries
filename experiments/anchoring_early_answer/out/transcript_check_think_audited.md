# Transcript check: how judges approve the wrong answers they believe (THINKING ON)

GLM-5.3-Flash read each judging transcript (thinking ON: the written reasoning plus the answer; RB2 Math + BFF; clean labels). *Re-solves* = the grader works out its own result; *lands on it* = that result equals the graded answer. Labelled: 3181 of 3046.

## Wrong answers, by belief and verdict

| group | n | re-solves | re-solves and lands on the graded answer | step check | surface only |
|---|---|---|---|---|---|
| Qwen · belief 0/7 · approved | 33 | 100% | 94% | 18% | 0% |
| Qwen · belief 0/7 · rejected | 1521 | 100% | 0% | 3% | 0% |
| Qwen · belief 1-3 · approved | 18 | 100% | 94% | 17% | 0% |
| Qwen · belief 1-3 · rejected | 101 | 100% | 5% | 2% | 0% |
| Qwen · belief 4-6 · approved | 14 | 93% | 86% | 21% | 0% |
| Qwen · belief 4-6 · rejected | 30 | 97% | 7% | 7% | 0% |
| Qwen · belief 7/7 · approved | 9 | 100% | 100% | 11% | 0% |
| Qwen · belief 7/7 · rejected | 7 | 100% | 0% | 0% | 0% |

## Correct answers, by belief and verdict (control)

| group | n | re-solves | re-solves and lands on the graded answer | step check | surface only |
|---|---|---|---|---|---|
| Qwen · belief 0/7 · approved | 19 | 100% | 79% | 16% | 0% |
| Qwen · belief 0/7 · rejected | 76 | 96% | 0% | 12% | 0% |
| Qwen · belief 1-3 · approved | 54 | 94% | 91% | 17% | 0% |
| Qwen · belief 1-3 · rejected | 22 | 95% | 0% | 9% | 0% |
| Qwen · belief 4-6 · approved | 182 | 91% | 86% | 19% | 0% |
| Qwen · belief 4-6 · rejected | 27 | 100% | 30% | 15% | 0% |
| Qwen · belief 7/7 · approved | 866 | 84% | 82% | 28% | 0% |
| Qwen · belief 7/7 · rejected | 59 | 97% | 32% | 32% | 0% |

## Wrong answers, pooled over belief levels

| group | n | re-solves | re-solves and lands on the graded answer | step check | surface only |
|---|---|---|---|---|---|
| Qwen · approved | 74 | 99% | 93% | 18% | 0% |
| Qwen · rejected | 1659 | 100% | 1% | 3% | 0% |

## Wrong answers, by judge (all beliefs)

| group | n | re-solves | re-solves and lands on the graded answer | step check | surface only |
|---|---|---|---|---|---|
| qwen3.5-4b · approved | 24 | 100% | 100% | 25% | 0% |
| qwen3.5-4b · rejected | 553 | 99% | 1% | 3% | 0% |
| qwen3.5-9b · approved | 18 | 94% | 94% | 28% | 0% |
| qwen3.5-9b · rejected | 559 | 100% | 1% | 4% | 0% |
| qwen3.6-35b-a3b · approved | 32 | 100% | 88% | 6% | 0% |
| qwen3.6-35b-a3b · rejected | 547 | 100% | 0% | 1% | 0% |

