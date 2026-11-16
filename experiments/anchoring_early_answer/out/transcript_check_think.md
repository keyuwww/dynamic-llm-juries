# Transcript check: how judges approve the wrong answers they believe (THINKING ON)

GLM-5.3-Flash read each judging transcript (thinking ON: the written reasoning plus the answer; RB2 Math + BFF; clean labels). *Re-solves* = the grader works out its own result; *lands on it* = that result equals the graded answer. Labelled: 3181 of 3189.

## Wrong answers, by belief and verdict

| group | n | re-solves | re-solves and lands on the graded answer | step check | surface only |
|---|---|---|---|---|---|
| Qwen · belief 0/7 · approved | 44 | 100% | 89% | 20% | 0% |
| Qwen · belief 0/7 · rejected | 1541 | 100% | 0% | 3% | 0% |
| Qwen · belief 1-3 · approved | 37 | 100% | 89% | 19% | 0% |
| Qwen · belief 1-3 · rejected | 118 | 100% | 7% | 3% | 0% |
| Qwen · belief 4-6 · approved | 37 | 92% | 86% | 22% | 0% |
| Qwen · belief 4-6 · rejected | 37 | 97% | 11% | 8% | 0% |
| Qwen · belief 7/7 · approved | 49 | 100% | 96% | 18% | 0% |
| Qwen · belief 7/7 · rejected | 13 | 100% | 31% | 23% | 0% |

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

## Wrong answers, by judge (all beliefs)

| group | n | re-solves | re-solves and lands on the graded answer | step check | surface only |
|---|---|---|---|---|---|
| qwen3.5-4b · approved | 53 | 96% | 89% | 30% | 0% |
| qwen3.5-4b · rejected | 571 | 99% | 1% | 4% | 0% |
| qwen3.5-9b · approved | 46 | 98% | 96% | 24% | 0% |
| qwen3.5-9b · rejected | 579 | 100% | 2% | 5% | 0% |
| qwen3.6-35b-a3b · approved | 68 | 100% | 88% | 9% | 0% |
| qwen3.6-35b-a3b · rejected | 559 | 100% | 0% | 1% | 0% |

