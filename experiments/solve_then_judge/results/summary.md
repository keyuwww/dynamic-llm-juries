# Solve-then-judge on BFF-Bench (core): none vs self vs human

808 responses with a 2-of-3 human label (459 unanimous). 8 Tinker judges, 1 sample, T = 0.7, max 4,096 tokens. Agreement = verdict matches the human label. Δ = self − none on the same responses, 95% CI resampling whole conversations.

## 1. Headline

| Judge | n | none | self | human | Δ self − none | 95% CI | κ none | κ self | parsed none / self |
|---|---|---|---|---|---|---|---|---|---|
| gpt-oss-120b | 799 | 80.2 | 79.0 | 87.1 | -1.3 | [-4.1, +1.6] | 0.600 | 0.575 | 1.00 / 1.00 |
| gpt-oss-20b | 799 | 77.7 | 72.5 | 78.5 | -5.3 | [-8.5, -1.9] | 0.549 | 0.423 | 0.98 / 0.99 |
| deepseek-v3.1 | 799 | 75.5 | 78.0 | 85.6 | +2.5 | [-0.6, +5.5] | 0.497 | 0.561 | 1.00 / 1.00 |
| qwen3.6-35b-a3b | 799 | 73.6 | 72.5 | 79.1 | -1.1 | [-3.5, +1.3] | 0.479 | 0.465 | 1.00 / 1.00 |
| qwen3.5-9b | 799 | 70.5 | 73.3 | 81.9 | +2.9 | [-0.6, +6.1] | 0.405 | 0.473 | 0.99 / 0.99 |
| qwen3.5-4b | 799 | 71.0 | 70.5 | 81.0 | -0.5 | [-4.1, +3.3] | 0.407 | 0.420 | 0.99 / 0.99 |
| nemotron3-super-120b | 799 | 71.3 | 76.0 | 87.5 | +4.6 | [+1.1, +8.1] | 0.397 | 0.499 | 0.99 / 1.00 |
| nemotron3-nano-30b | 799 | 67.6 | 64.3 | 72.3 | -3.3 | [-7.6, +1.3] | 0.343 | 0.283 | 1.00 / 1.00 |

Mean Δ over judges: -0.2 points.

## 2. When the judge solved the question vs failed it

Solved = the judge's own answer was graded correct (both graders agree; DeepSeek only for gpt-oss judges). Uncertain items are left out.

| Judge | solved: n | none | self | Δ | failed: n | none | self | Δ |
|---|---|---|---|---|---|---|---|---|
| gpt-oss-120b | 625 | 82.1 | 82.9 | +0.8 | 174 | 73.6 | 64.9 | -8.6 |
| gpt-oss-20b | 603 | 80.3 | 78.6 | -1.7 | 196 | 69.9 | 53.6 | -16.3 |
| deepseek-v3.1 | 520 | 79.2 | 81.2 | +1.9 | 178 | 65.2 | 72.5 | +7.3 |
| qwen3.6-35b-a3b | 508 | 73.4 | 71.9 | -1.6 | 170 | 78.2 | 78.2 | +0.0 |
| qwen3.5-9b | 431 | 75.2 | 78.0 | +2.8 | 236 | 64.0 | 68.6 | +4.7 |
| qwen3.5-4b | 355 | 77.2 | 78.0 | +0.8 | 286 | 65.0 | 64.7 | -0.3 |
| nemotron3-super-120b | 494 | 77.5 | 83.2 | +5.7 | 171 | 59.6 | 62.6 | +2.9 |
| nemotron3-nano-30b | 383 | 69.7 | 70.5 | +0.8 | 292 | 64.7 | 61.3 | -3.4 |

## 3. Flips between none and self

| Judge | right → wrong | wrong → right | right → wrong when own answer failed | wrong → right when own answer solved |
|---|---|---|---|---|
| gpt-oss-120b | 72 | 62 | 30 | 47 |
| gpt-oss-20b | 119 | 77 | 48 | 61 |
| deepseek-v3.1 | 63 | 83 | 16 | 42 |
| qwen3.6-35b-a3b | 52 | 43 | 16 | 22 |
| qwen3.5-9b | 85 | 108 | 33 | 46 |
| qwen3.5-4b | 109 | 105 | 51 | 31 |
| nemotron3-super-120b | 84 | 121 | 31 | 64 |
| nemotron3-nano-30b | 185 | 159 | 70 | 77 |

## 4. Unanimous vs split-vote responses

| Judge | Δ unanimous | Δ split |
|---|---|---|
| gpt-oss-120b | -0.7 | -2.0 |
| gpt-oss-20b | -7.5 | -2.3 |
| deepseek-v3.1 | +6.4 | -2.6 |
| qwen3.6-35b-a3b | -0.9 | -1.5 |
| qwen3.5-9b | +4.2 | +1.2 |
| qwen3.5-4b | +3.3 | -5.5 |
| nemotron3-super-120b | +6.4 | +2.3 |
| nemotron3-nano-30b | -3.9 | -2.3 |
