## A. How often each judge answers the BFF-Bench question correctly itself

3 answers per question (thinking off; Kimi: 1, high reasoning), graded by GLM-5.3-Flash against the expert reference. Turn-2 questions are asked after the expert's turn-1 answer.

| Model | Questions graded | Mean share correct | Solved (≥2 of 3 correct) |
|---|---|---|---|
| qwen3.5-4b | 160 | 0.53 | 0.52 |
| qwen3.5-9b | 160 | 0.63 | 0.65 |
| qwen3.6-35b-a3b | 160 | 0.75 | 0.76 |
| nemotron3-super-120b | 160 | 0.71 | 0.71 |
| kimi-k3.1-pro | 160 | 0.88 | 0.88 |

## B. Judging quality by whether the judge solved the question, per condition

Gold = unanimous expert label. Balanced accuracy (κ); Δ vs the no-reference baseline on the same items. Within-question AUROC (no reference only) compares answers by different models to the same question.

| Condition | Judge | solved: n | solved: bal. acc. (κ) | Δ | **not solved**: n | not solved: bal. acc. (κ) | Δ |
|---|---|---|---|---|---|---|---|
| No reference (baseline) | qwen3.5-4b | 239 | 0.73 (0.47) | +0 | 217 | 0.68 (0.34) | +0 |
| Expert reference | qwen3.5-4b | 239 | 0.90 (0.74) | +16 | 217 | 0.85 (0.72) | +17 |
| Stronger model's answer as reference | qwen3.5-4b | 239 | 0.87 (0.66) | +14 | 217 | 0.81 (0.64) | +13 |
| Own earlier answer as reference | qwen3.5-4b | 239 | 0.87 (0.66) | +14 | 217 | 0.60 (0.21) | -8 |
| Verify-the-steps prompt | qwen3.5-4b | 239 | 0.84 (0.62) | +10 | 217 | 0.72 (0.45) | +4 |
| Route to the stronger judge (Kimi) | qwen3.5-4b | 239 | 0.82 (0.55) | +9 | 217 | 0.79 (0.60) | +11 |
| No reference (baseline) | qwen3.5-9b | 293 | 0.77 (0.53) | +0 | 163 | 0.72 (0.38) | +0 |
| Expert reference | qwen3.5-9b | 293 | 0.92 (0.77) | +15 | 163 | 0.83 (0.65) | +11 |
| Stronger model's answer as reference | qwen3.5-9b | 293 | 0.88 (0.67) | +11 | 163 | 0.76 (0.52) | +4 |
| Own earlier answer as reference | qwen3.5-9b | 293 | 0.84 (0.63) | +7 | 163 | 0.54 (0.07) | -18 |
| Verify-the-steps prompt | qwen3.5-9b | 293 | 0.82 (0.57) | +5 | 163 | 0.74 (0.47) | +2 |
| Route to the stronger judge (Kimi) | qwen3.5-9b | 293 | 0.83 (0.55) | +5 | 163 | 0.77 (0.55) | +5 |
| No reference (baseline) | qwen3.6-35b-a3b | 333 | 0.82 (0.58) | +0 | 123 | 0.62 (0.23) | +0 |
| Expert reference | qwen3.6-35b-a3b | 333 | 0.90 (0.74) | +8 | 123 | 0.82 (0.61) | +20 |
| Stronger model's answer as reference | qwen3.6-35b-a3b | 333 | 0.85 (0.61) | +2 | 123 | 0.70 (0.38) | +8 |
| Own earlier answer as reference | qwen3.6-35b-a3b | 333 | 0.85 (0.61) | +3 | 123 | 0.52 (0.04) | -10 |
| Verify-the-steps prompt | qwen3.6-35b-a3b | 333 | 0.84 (0.61) | +1 | 123 | 0.70 (0.37) | +8 |
| Route to the stronger judge (Kimi) | qwen3.6-35b-a3b | 333 | 0.86 (0.63) | +3 | 123 | 0.67 (0.34) | +4 |
| No reference (baseline) | nemotron3-super-120b | 316 | 0.74 (0.52) | +0 | 140 | 0.70 (0.32) | +0 |
| Expert reference | nemotron3-super-120b | 316 | 0.95 (0.88) | +22 | 140 | 0.87 (0.78) | +17 |
| Stronger model's answer as reference | nemotron3-super-120b | 316 | 0.91 (0.80) | +17 | 140 | 0.76 (0.48) | +5 |
| Own earlier answer as reference | nemotron3-super-120b | 316 | 0.86 (0.76) | +12 | 140 | 0.70 (0.36) | -0 |
| Verify-the-steps prompt | nemotron3-super-120b | 316 | 0.82 (0.62) | +8 | 140 | 0.63 (0.21) | -8 |
| Route to the stronger judge (Kimi) | nemotron3-super-120b | 316 | 0.86 (0.64) | +12 | 140 | 0.70 (0.39) | -1 |

### B2. Pooled over the 4 judges

| Condition | solved: bal. acc. | Δ | not solved: bal. acc. | Δ [95% CI] |
|---|---|---|---|---|
| No reference (baseline) | 0.77 | +0 | 0.69 | +0 |
| Expert reference | 0.92 | +15 | 0.85 | +15 [+10, +20] |
| Stronger model's answer as reference | 0.88 | +11 | 0.77 | +8 [+2, +14] |
| Own earlier answer as reference | 0.86 | +8 | 0.59 | -10 [-17, -4] |
| Verify-the-steps prompt | 0.83 | +6 | 0.70 | +1 [-4, +6] |
| Route to the stronger judge (Kimi) | 0.84 | +7 | 0.75 | +5 [-1, +12] |

### B3. No reference: TPR / FPR / within-question AUROC by solved

| Judge | Questions | n (right / wrong) | TPR | FPR | Balanced acc. [95% CI] | Within-Q AUROC (pairs) |
|---|---|---|---|---|---|---|
| qwen3.5-4b | solved | 239 (177 / 62) | 0.87 | 0.40 | 0.73 [0.67, 0.81] | 0.91 (58) |
| qwen3.5-4b | **not solved** | 217 (78 / 139) | 0.69 | 0.33 | 0.68 [0.60, 0.75] | 0.68 (73) |
| qwen3.5-9b | solved | 293 (217 / 76) | 0.85 | 0.30 | 0.77 [0.71, 0.84] | 0.86 (85) |
| qwen3.5-9b | **not solved** | 163 (38 / 125) | 0.68 | 0.24 | 0.72 [0.63, 0.81] | 0.84 (46) |
| qwen3.6-35b-a3b | solved | 333 (228 / 105) | 0.76 | 0.11 | 0.82 [0.78, 0.86] | 0.91 (107) |
| qwen3.6-35b-a3b | **not solved** | 123 (27 / 96) | 0.44 | 0.20 | 0.62 [0.49, 0.73] | 0.73 (24) |
| nemotron3-super-120b | solved | 316 (220 / 96) | 0.93 | 0.45 | 0.74 [0.68, 0.80] | 0.83 (94) |
| nemotron3-super-120b | **not solved** | 140 (35 / 105) | 0.77 | 0.36 | 0.70 [0.60, 0.80] | 0.72 (37) |
| kimi-k3.1-pro (thinking, 1 vote) | solved | 384 (248 / 136) | 0.75 | 0.06 | 0.85 [0.80, 0.89] | 0.93 (119) |
| kimi-k3.1-pro (thinking, 1 vote) | **not solved** | 72 (7 / 65) | 0.14 | 0.18 | 0.48 [0.37, 0.67] | 0.46 (12) |

### B4. Stronger model's answer as reference, split by whether that answer is itself right

| Judge | Kimi's answer right: bal. acc. none → strong (n) | Kimi's answer wrong: none → strong (n) |
|---|---|---|
| qwen3.5-4b | 0.73 → 0.89 (384) | 0.61 → 0.44 (72) |
| qwen3.5-9b | 0.79 → 0.88 (384) | 0.64 → 0.55 (72) |
| qwen3.6-35b-a3b | 0.81 → 0.85 (384) | 0.53 → 0.46 (72) |
| nemotron3-super-120b | 0.75 → 0.91 (384) | 0.66 → 0.65 (72) |
