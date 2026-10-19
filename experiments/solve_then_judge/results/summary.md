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

## 5. Peer arm: every judge grades against gpt-oss-120b's answer

Reference correct = gpt-oss-120b's answer graded correct by DeepSeek-V3.1 with the expert reference. gpt-oss-120b's own peer verdicts are its self verdicts (same prompt).

| Judge | none | self | peer | human | Δ peer − none | 95% CI | Δ peer − self |
|---|---|---|---|---|---|---|---|
| gpt-oss-120b | 80.2 | 79.0 | 79.0 | 87.1 | -1.3 | [-4.1, +1.6] | +0.0 |
| gpt-oss-20b | 77.7 | 72.5 | 71.3 | 78.5 | -6.4 | [-10.3, -2.9] | -1.1 |
| deepseek-v3.1 | 75.5 | 78.0 | 77.6 | 85.6 | +2.1 | [-1.0, +5.1] | -0.4 |
| qwen3.6-35b-a3b | 73.6 | 72.5 | 73.2 | 79.1 | -0.4 | [-3.0, +2.3] | +0.8 |
| qwen3.5-9b | 70.5 | 73.3 | 76.0 | 81.9 | +5.5 | [+1.8, +8.9] | +2.6 |
| qwen3.5-4b | 71.0 | 70.5 | 75.3 | 81.0 | +4.4 | [+1.0, +7.9] | +4.9 |
| nemotron3-super-120b | 71.3 | 76.0 | 81.1 | 87.5 | +9.8 | [+6.3, +13.0] | +5.1 |
| nemotron3-nano-30b | 67.6 | 64.3 | 70.0 | 72.3 | +2.4 | [-2.0, +6.6] | +5.6 |

Mean Δ peer − none: +2.0; mean Δ peer − self: +2.2 points.

### Split by whether the reference was correct (grader: deepseek-v3.1; 625 responses with a correct reference, 174 with a wrong one)

| Judge | ref correct: none | peer | Δ | ref wrong: none | peer | Δ |
|---|---|---|---|---|---|---|
| gpt-oss-120b | 82.1 | 82.9 | +0.8 | 73.6 | 64.9 | -8.6 |
| gpt-oss-20b | 79.5 | 77.8 | -1.8 | 71.3 | 48.3 | -23.0 |
| deepseek-v3.1 | 77.3 | 79.8 | +2.6 | 69.0 | 69.5 | +0.6 |
| qwen3.6-35b-a3b | 72.2 | 73.0 | +0.8 | 78.7 | 74.1 | -4.6 |
| qwen3.5-9b | 70.9 | 77.1 | +6.2 | 69.0 | 71.8 | +2.9 |
| qwen3.5-4b | 73.8 | 77.0 | +3.2 | 60.9 | 69.5 | +8.6 |
| nemotron3-super-120b | 74.9 | 85.8 | +10.9 | 58.6 | 64.4 | +5.7 |
| nemotron3-nano-30b | 68.5 | 71.5 | +3.0 | 64.4 | 64.4 | +0.0 |

### Split by whether the reference was correct (grader: gpt-oss-120b; 510 responses with a correct reference, 249 with a wrong one)

| Judge | ref correct: none | peer | Δ | ref wrong: none | peer | Δ |
|---|---|---|---|---|---|---|
| gpt-oss-120b | 85.5 | 86.7 | +1.2 | 71.5 | 65.5 | -6.0 |
| gpt-oss-20b | 81.0 | 80.4 | -0.6 | 71.1 | 55.8 | -15.3 |
| deepseek-v3.1 | 78.6 | 82.9 | +4.3 | 69.1 | 68.7 | -0.4 |
| qwen3.6-35b-a3b | 74.3 | 75.3 | +1.0 | 71.9 | 68.3 | -3.6 |
| qwen3.5-9b | 72.9 | 79.4 | +6.5 | 65.5 | 70.7 | +5.2 |
| qwen3.5-4b | 75.1 | 79.2 | +4.1 | 64.7 | 67.5 | +2.8 |
| nemotron3-super-120b | 76.9 | 89.2 | +12.4 | 61.4 | 67.9 | +6.4 |
| nemotron3-nano-30b | 67.6 | 73.7 | +6.1 | 67.5 | 64.3 | -3.2 |
