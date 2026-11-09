## A. How often each judge solves BBEH itself

Thinking off (the mode it judges in), 5 samples per question, whole 64K context as budget. *Solved* = the majority answer of the 5 samples is correct.

| Model | Questions | Mean share of samples correct | Majority answer correct (= solved) | At least 1 of 5 correct | Thinking-on, 1 sample (questions) | Cut-off samples left |
|---|---|---|---|---|---|---|
| qwen3.5-4b | 460 | 0.33 | 0.38 | 0.58 | 0.38 (428) | 11 |
| qwen3.5-9b | 460 | 0.38 | 0.47 | 0.64 | 0.46 (428) | 4 |
| qwen3.6-35b-a3b | 460 | 0.47 | 0.57 | 0.74 | 0.48 (458) | 0 |
| nemotron3-super-120b | 460 | 0.16 | 0.17 | 0.37 | 0.52 (460) | 0 |
| kimi-k3.1-pro | 460 | 0.63 | 0.63 | 0.63 | high reasoning | 0 |

## B. Judging quality on questions the judge solved vs did not solve (no reference)

TPR = share of right answers the judge accepts; FPR = share of wrong answers it accepts; balanced accuracy = (TPR + (1 − FPR)) / 2, 0.5 = chance; κ = Cohen's kappa vs the official grader; within-question AUROC = over pairs of a right and a wrong answer to the same question, how often the judge's vote share (3 samples) is higher for the right one.

| Judge | Questions | n (right / wrong) | TPR | FPR | Balanced acc. [95% CI] | κ | Within-Q AUROC (pairs) |
|---|---|---|---|---|---|---|---|
| qwen3.5-4b | solved | 845 (581 / 264) | 0.83 | 0.47 | 0.68 [0.64, 0.71] | 0.37 | 0.71 (652) |
| qwen3.5-4b | **not solved** | 1187 (389 / 798) | 0.64 | 0.54 | 0.55 [0.51, 0.58] | 0.09 | 0.58 (624) |
| qwen3.5-9b | solved | 1036 (716 / 320) | 0.90 | 0.52 | 0.69 [0.65, 0.72] | 0.41 | 0.74 (836) |
| qwen3.5-9b | **not solved** | 982 (236 / 746) | 0.69 | 0.66 | 0.51 [0.47, 0.56] | 0.02 | 0.58 (452) |
| qwen3.6-35b-a3b | solved | 1194 (797 / 397) | 0.92 | 0.38 | 0.77 [0.74, 0.81] | 0.57 | 0.84 (915) |
| qwen3.6-35b-a3b | **not solved** | 818 (162 / 656) | 0.62 | 0.63 | 0.49 [0.44, 0.55] | -0.01 | 0.50 (374) |
| nemotron3-super-120b | solved | 462 (310 / 152) | 0.84 | 0.53 | 0.65 [0.60, 0.71] | 0.32 | 0.69 (413) |
| nemotron3-super-120b | **not solved** | 1546 (640 / 906) | 0.72 | 0.50 | 0.61 [0.58, 0.64] | 0.21 | 0.71 (866) |
| kimi-k3.1-pro (thinking, 1 vote) | solved | 1368 (860 / 508) | 0.98 | 0.13 | 0.93 [0.90, 0.95] | 0.87 | 0.92 (1116) |
| kimi-k3.1-pro (thinking, 1 vote) | **not solved** | 876 (217 / 659) | 0.76 | 0.50 | 0.63 [0.57, 0.69] | 0.18 | 0.58 (505) |

### B2. Finer: by how many of its 5 samples the judge got right

| Judge | 0 of 5 | 1–2 of 5 | 3–4 of 5 | 5 of 5 |
|---|---|---|---|---|
| qwen3.5-4b | 0.52 (n=802) | 0.60 (n=526) | 0.66 (n=438) | 0.75 (n=266) |
| qwen3.5-9b | 0.44 (n=702) | 0.60 (n=441) | 0.66 (n=452) | 0.75 (n=423) |
| qwen3.6-35b-a3b | 0.39 (n=544) | 0.62 (n=407) | 0.72 (n=509) | 0.83 (n=552) |
| nemotron3-super-120b | 0.58 (n=1104) | 0.63 (n=573) | 0.68 (n=233) | 0.73 (n=98) |

### B3. Is it solving ability or just difficulty? Same outside difficulty, solved vs not

Outside difficulty = share of the 8 pool models (thinking on) that answered the question correctly. Cells: balanced accuracy (n) for solved / not solved, pooled over the 4 judges.

| Pool solve rate | solved | not solved |
|---|---|---|
| 0–1 of 8 (hardest) | 0.65 (n=455) | 0.44 (n=2745) |
| 2–3 of 8 | 0.65 (n=679) | 0.56 (n=694) |
| 4–5 of 8 | 0.70 (n=882) | 0.62 (n=570) |
| 6–8 of 8 (easiest) | 0.77 (n=1521) | 0.72 (n=524) |

Linear-probability fit of *verdict matches the grader* on solved (0/1) and outside difficulty, with question-resampled 95% intervals (balanced weights so right/wrong count equally):

| Judge | effect of solved (points) | effect of difficulty, easiest vs hardest (points) |
|---|---|---|
| qwen3.5-4b | +9 [+4, +14] | +36 [+28, +44] |
| qwen3.5-9b | +13 [+8, +19] | +51 [+43, +59] |
| qwen3.6-35b-a3b | +27 [+19, +34] | +32 [+23, +40] |
| nemotron3-super-120b | -2 [-8, +4] | +50 [+42, +57] |

### B3b. Strongest control: the same answer judged by a judge that solved the question and one that did not

Linear model: verdict-is-right ~ solved + judge + candidate (a separate intercept for every candidate answer, so the question, its difficulty and the answer itself cancel out; judge dummies absorb overall judge quality). Only candidates judged by ≥2 of the 4 judges with different solve status contribute. 95% interval: questions resampled.

Effect of having solved the question on getting the verdict right: **+6 points** [+3, +10] (4547 judgments). Qwens only: +8 points (2224 judgments).


### B4. On questions it did not solve: what does the judge accept?

| Judge | right answers accepted | wrong answers equal to its own (wrong) majority answer, accepted | other wrong answers accepted | right answers it never produced in 5 samples, accepted |
|---|---|---|---|---|
| qwen3.5-4b | 0.64 (n=389) | 0.68 (n=276) | 0.46 (n=522) | 0.59 (n=198) |
| qwen3.5-9b | 0.69 (n=236) | 0.85 (n=290) | 0.54 (n=456) | 0.57 (n=107) |
| qwen3.6-35b-a3b | 0.62 (n=162) | 0.90 (n=271) | 0.44 (n=385) | 0.42 (n=62) |
| nemotron3-super-120b | 0.72 (n=640) | 0.73 (n=213) | 0.43 (n=693) | 0.67 (n=394) |

### B4b. The cleanest test: can it recognise a right answer it could not produce?

Only answers that differ from ALL of the judge's 5 own samples, on questions it did not solve. Gap = acceptance of right answers − acceptance of wrong answers (0 = cannot tell them apart), with question-resampled 95% intervals.

| Judge | right answers accepted | wrong answers accepted | gap (points) [95% CI] |
|---|---|---|---|
| qwen3.5-4b | 0.59 (n=197) | 0.43 (n=424) | +16 [+6, +27] |
| qwen3.5-9b | 0.57 (n=107) | 0.49 (n=351) | +8 [-6, +21] |
| qwen3.6-35b-a3b | 0.42 (n=62) | 0.37 (n=293) | +5 [-10, +20] |
| nemotron3-super-120b | 0.68 (n=387) | 0.41 (n=578) | +27 [+19, +35] |

### B5. Same split with the thinking-ON solve (1 sample) as the definition of solved

| Judge | solved: balanced acc. (n) | not solved: balanced acc. (n) | agreement of the two solve labels |
|---|---|---|---|
| qwen3.5-4b | 0.68 (868) | 0.53 (1093) | 0.77 |
| qwen3.5-9b | 0.69 (991) | 0.51 (962) | 0.75 |
| qwen3.6-35b-a3b | 0.77 (1084) | 0.54 (924) | 0.78 |
| nemotron3-super-120b | 0.71 (1116) | 0.50 (892) | 0.57 |

## C. Interventions: what each buys on unsolved questions, and what it costs on solved ones

Balanced accuracy (κ in brackets). Δ = change vs the no-reference baseline on the same candidates. Rules (no extra LLM call): *solve-and-compare* = accept iff the candidate's final answer equals the judge's own 5-sample majority answer; *match the stronger model* = accept iff it equals Kimi-K3.1-Pro's answer.

| Method | Judge | solved: bal. acc. (κ) | Δ | **not solved**: bal. acc. (κ) | Δ | n solved / not |
|---|---|---|---|---|---|---|
| Official answer as reference (ceiling) | qwen3.5-4b | 0.91 (0.83) | +23 | 0.93 (0.84) | +38 | 845 / 1187 |
| Official answer as reference (ceiling) | qwen3.5-9b | 0.92 (0.87) | +23 | 0.96 (0.85) | +45 | 1036 / 982 |
| Official answer as reference (ceiling) | qwen3.6-35b-a3b | 0.94 (0.90) | +17 | 0.96 (0.86) | +47 | 1194 / 818 |
| Official answer as reference (ceiling) | nemotron3-super-120b | 0.94 (0.90) | +28 | 0.95 (0.89) | +34 | 462 / 1546 |
| Stronger model's answer as reference | qwen3.5-4b | 0.80 (0.60) | +12 | 0.76 (0.46) | +21 | 845 / 1187 |
| Stronger model's answer as reference | qwen3.5-9b | 0.85 (0.73) | +17 | 0.73 (0.34) | +21 | 1036 / 982 |
| Stronger model's answer as reference | qwen3.6-35b-a3b | 0.90 (0.82) | +13 | 0.67 (0.24) | +17 | 1194 / 818 |
| Stronger model's answer as reference | nemotron3-super-120b | 0.87 (0.75) | +22 | 0.80 (0.57) | +19 | 462 / 1546 |
| Own earlier answer as reference | qwen3.5-4b | 0.82 (0.69) | +14 | 0.40 (-0.19) | -16 | 845 / 1187 |
| Own earlier answer as reference | qwen3.5-9b | 0.80 (0.67) | +11 | 0.34 (-0.23) | -17 | 1036 / 981 |
| Own earlier answer as reference | qwen3.6-35b-a3b | 0.94 (0.91) | +17 | 0.32 (-0.25) | -17 | 1194 / 818 |
| Own earlier answer as reference | nemotron3-super-120b | 0.95 (0.91) | +29 | 0.45 (-0.10) | -16 | 462 / 1543 |
| Verify-the-steps prompt | qwen3.5-4b | 0.66 (0.34) | -1 | 0.53 (0.05) | -2 | 845 / 1187 |
| Verify-the-steps prompt | qwen3.5-9b | 0.76 (0.55) | +7 | 0.52 (0.03) | +1 | 1036 / 982 |
| Verify-the-steps prompt | qwen3.6-35b-a3b | 0.82 (0.67) | +5 | 0.49 (-0.01) | +0 | 1194 / 818 |
| Verify-the-steps prompt | nemotron3-super-120b | 0.64 (0.28) | -1 | 0.58 (0.16) | -3 | 462 / 1546 |
| Framing: candidate shown as its own reply, then 'is your answer correct?' | qwen3.5-4b | 0.60 (0.22) | -7 | 0.52 (0.04) | -3 | 845 / 1187 |
| Framing: candidate shown as its own reply, then 'is your answer correct?' | qwen3.5-9b | 0.64 (0.33) | -4 | 0.52 (0.02) | +1 | 1036 / 982 |
| Framing: candidate shown as its own reply, then 'is your answer correct?' | qwen3.6-35b-a3b | 0.63 (0.28) | -14 | 0.50 (0.00) | +1 | 1194 / 818 |
| Framing: candidate shown as its own reply, then 'is your answer correct?' | nemotron3-super-120b | 0.53 (0.07) | -12 | 0.51 (0.03) | -10 | 462 / 1546 |
| Framing: 'here is the answer you gave earlier' | qwen3.5-4b | 0.62 (0.25) | -6 | 0.52 (0.04) | -3 | 845 / 1187 |
| Framing: 'here is the answer you gave earlier' | qwen3.5-9b | 0.69 (0.41) | +0 | 0.50 (0.00) | -1 | 1036 / 982 |
| Framing: 'here is the answer you gave earlier' | qwen3.6-35b-a3b | 0.76 (0.55) | -2 | 0.48 (-0.02) | -1 | 1194 / 818 |
| Framing: 'here is the answer you gave earlier' | nemotron3-super-120b | 0.63 (0.29) | -2 | 0.57 (0.13) | -4 | 462 / 1546 |
| No reference (baseline) | qwen3.5-4b | 0.68 (0.37) | +0 | 0.55 (0.09) | +0 | 845 / 1187 |
| No reference (baseline) | qwen3.5-9b | 0.69 (0.41) | +0 | 0.51 (0.02) | +0 | 1036 / 982 |
| No reference (baseline) | qwen3.6-35b-a3b | 0.77 (0.57) | +0 | 0.49 (-0.01) | +0 | 1194 / 818 |
| No reference (baseline) | nemotron3-super-120b | 0.65 (0.32) | +0 | 0.61 (0.21) | +0 | 462 / 1546 |
| Rule: solve-and-compare (own 5-sample majority) | qwen3.5-4b | 1.00 (1.00) | +32 | 0.33 (-0.37) | -22 | 845 / 1187 |
| Rule: solve-and-compare (own 5-sample majority) | qwen3.5-9b | 1.00 (1.00) | +31 | 0.31 (-0.36) | -21 | 1036 / 982 |
| Rule: solve-and-compare (own 5-sample majority) | qwen3.6-35b-a3b | 1.00 (1.00) | +23 | 0.29 (-0.33) | -20 | 1194 / 818 |
| Rule: solve-and-compare (own 5-sample majority) | nemotron3-super-120b | 1.00 (1.00) | +35 | 0.38 (-0.26) | -23 | 462 / 1546 |
| Rule: solve-and-compare only when own samples agree (≥4/5), else own verdict | qwen3.5-4b | 0.84 (0.70) | +17 | 0.49 (-0.01) | -6 | 845 / 1187 |
| Rule: solve-and-compare only when own samples agree (≥4/5), else own verdict | qwen3.5-9b | 0.82 (0.68) | +14 | 0.43 (-0.09) | -8 | 1036 / 982 |
| Rule: solve-and-compare only when own samples agree (≥4/5), else own verdict | qwen3.6-35b-a3b | 0.89 (0.79) | +12 | 0.45 (-0.06) | -5 | 1194 / 818 |
| Rule: solve-and-compare only when own samples agree (≥4/5), else own verdict | nemotron3-super-120b | 0.79 (0.61) | +14 | 0.59 (0.17) | -2 | 462 / 1546 |
| Rule: match the plurality answer of the 4 weak judges (20 samples) | qwen3.5-4b | 0.94 (0.88) | +26 | 0.62 (0.21) | +7 | 845 / 1187 |
| Rule: match the plurality answer of the 4 weak judges (20 samples) | qwen3.5-9b | 0.95 (0.89) | +26 | 0.52 (0.03) | +1 | 1036 / 982 |
| Rule: match the plurality answer of the 4 weak judges (20 samples) | qwen3.6-35b-a3b | 0.90 (0.79) | +13 | 0.48 (-0.02) | -1 | 1194 / 818 |
| Rule: match the plurality answer of the 4 weak judges (20 samples) | nemotron3-super-120b | 0.89 (0.79) | +24 | 0.72 (0.42) | +11 | 462 / 1546 |
| Rule: match the most common answer among all candidates | qwen3.5-4b | 0.81 (0.65) | +13 | 0.66 (0.27) | +11 | 845 / 1187 |
| Rule: match the most common answer among all candidates | qwen3.5-9b | 0.83 (0.69) | +14 | 0.62 (0.16) | +10 | 1036 / 982 |
| Rule: match the most common answer among all candidates | qwen3.6-35b-a3b | 0.83 (0.68) | +5 | 0.56 (0.06) | +6 | 1194 / 818 |
| Rule: match the most common answer among all candidates | nemotron3-super-120b | 0.84 (0.71) | +18 | 0.68 (0.34) | +7 | 462 / 1546 |
| Rule: match the stronger model's answer | qwen3.5-4b | 0.82 (0.59) | +15 | 0.80 (0.58) | +25 | 845 / 1187 |
| Rule: match the stronger model's answer | qwen3.5-9b | 0.88 (0.68) | +19 | 0.76 (0.43) | +24 | 1036 / 982 |
| Rule: match the stronger model's answer | qwen3.6-35b-a3b | 0.90 (0.74) | +13 | 0.69 (0.29) | +20 | 1194 / 818 |
| Rule: match the stronger model's answer | nemotron3-super-120b | 0.82 (0.57) | +16 | 0.81 (0.61) | +20 | 462 / 1546 |
| Route everything to the stronger judge (Kimi) | qwen3.5-4b | 0.83 (0.70) | +15 | 0.78 (0.48) | +23 | 845 / 1187 |
| Route everything to the stronger judge (Kimi) | qwen3.5-9b | 0.87 (0.76) | +18 | 0.76 (0.37) | +24 | 1036 / 982 |
| Route everything to the stronger judge (Kimi) | qwen3.6-35b-a3b | 0.89 (0.80) | +12 | 0.69 (0.25) | +20 | 1194 / 818 |
| Route everything to the stronger judge (Kimi) | nemotron3-super-120b | 0.84 (0.69) | +19 | 0.79 (0.55) | +18 | 462 / 1546 |
| Majority of the 4 judges | qwen3.5-4b | 0.77 (0.54) | +9 | 0.60 (0.18) | +4 | 535 / 803 |
| Majority of the 4 judges | qwen3.5-9b | 0.79 (0.58) | +10 | 0.52 (0.02) | +1 | 672 / 666 |
| Majority of the 4 judges | qwen3.6-35b-a3b | 0.77 (0.53) | -1 | 0.52 (0.03) | +4 | 785 / 553 |
| Majority of the 4 judges | nemotron3-super-120b | 0.73 (0.48) | +6 | 0.65 (0.29) | +3 | 285 / 1053 |
| Defer to Kimi judge when own samples disagree (<4/5) | qwen3.5-4b | 0.77 (0.55) | +9 | 0.71 (0.36) | +16 | 845 / 1187 |
| Defer to Kimi judge when own samples disagree (<4/5) | qwen3.5-9b | 0.81 (0.64) | +12 | 0.67 (0.24) | +16 | 1036 / 982 |
| Defer to Kimi judge when own samples disagree (<4/5) | qwen3.6-35b-a3b | 0.84 (0.71) | +7 | 0.64 (0.16) | +14 | 1194 / 818 |
| Defer to Kimi judge when own samples disagree (<4/5) | nemotron3-super-120b | 0.74 (0.51) | +9 | 0.75 (0.46) | +14 | 462 / 1546 |
| Use the stronger model's reference when own samples disagree (<4/5) | qwen3.5-4b | 0.75 (0.50) | +7 | 0.70 (0.36) | +15 | 845 / 1187 |
| Use the stronger model's reference when own samples disagree (<4/5) | qwen3.5-9b | 0.80 (0.63) | +11 | 0.67 (0.24) | +16 | 1036 / 982 |
| Use the stronger model's reference when own samples disagree (<4/5) | qwen3.6-35b-a3b | 0.85 (0.73) | +8 | 0.62 (0.15) | +13 | 1194 / 818 |
| Use the stronger model's reference when own samples disagree (<4/5) | nemotron3-super-120b | 0.76 (0.53) | +10 | 0.75 (0.46) | +14 | 462 / 1546 |

### C2. Pooled over the 4 judges

| Method | solved: bal. acc. | Δ | not solved: bal. acc. | Δ [95% CI] |
|---|---|---|---|---|
| Official answer as reference (ceiling) | 0.93 | +22 | 0.95 | +40 [+37, +42] |
| Stronger model's answer as reference | 0.86 | +15 | 0.76 | +20 [+17, +24] |
| Own earlier answer as reference | 0.87 | +16 | 0.39 | -17 [-19, -14] |
| Verify-the-steps prompt | 0.74 | +3 | 0.54 | -2 [-3, +0] |
| Framing: candidate shown as its own reply, then 'is your answer correct?' | 0.61 | -10 | 0.52 | -3 [-5, -1] |
| Framing: 'here is the answer you gave earlier' | 0.69 | -2 | 0.53 | -2 [-4, -0] |
| No reference (baseline) | 0.71 | +0 | 0.55 | +0 [+0, +0] |
| Rule: solve-and-compare (own 5-sample majority) | 1.00 | +29 | 0.33 | -22 [-25, -20] |
| Rule: solve-and-compare only when own samples agree (≥4/5), else own verdict | 0.85 | +14 | 0.51 | -4 [-6, -2] |
| Rule: match the plurality answer of the 4 weak judges (20 samples) | 0.92 | +21 | 0.63 | +7 [+3, +12] |
| Rule: match the most common answer among all candidates | 0.82 | +11 | 0.65 | +10 [+6, +13] |
| Rule: match the stronger model's answer | 0.86 | +15 | 0.78 | +23 [+18, +27] |
| Route everything to the stronger judge (Kimi) | 0.86 | +15 | 0.77 | +22 [+18, +25] |
| Majority of the 4 judges | 0.77 | +6 | 0.59 | +4 [+2, +6] |
| Defer to Kimi judge when own samples disagree (<4/5) | 0.80 | +9 | 0.71 | +15 [+12, +18] |
| Use the stronger model's reference when own samples disagree (<4/5) | 0.80 | +9 | 0.70 | +15 [+12, +18] |

### C3. Stronger model's reference: what happens when the reference itself is wrong

| Judge | Questions | Kimi's answer right: bal. acc. none → strong-ref | Kimi's answer wrong: bal. acc. none → strong-ref |
|---|---|---|---|
| qwen3.5-4b | solved | 0.72 → 0.89 (n=615) | 0.61 → 0.60 (n=230) |
| qwen3.5-4b | not solved | 0.58 → 0.88 (n=626) | 0.59 → 0.58 (n=561) |
| qwen3.5-9b | solved | 0.72 → 0.91 (n=797) | 0.61 → 0.69 (n=239) |
| qwen3.5-9b | not solved | 0.56 → 0.92 (n=431) | 0.50 → 0.41 (n=551) |
| qwen3.6-35b-a3b | solved | 0.81 → 0.96 (n=928) | 0.68 → 0.74 (n=266) |
| qwen3.6-35b-a3b | not solved | 0.58 → 0.94 (n=309) | 0.43 → 0.34 (n=509) |
| nemotron3-super-120b | solved | 0.68 → 0.97 (n=328) | 0.60 → 0.66 (n=134) |
| nemotron3-super-120b | not solved | 0.71 → 0.95 (n=889) | 0.50 → 0.53 (n=657) |

## D. Knowing when not to trust the judge: own self-consistency as a warning light

Share of the judge's 5 own solve samples that agree with its majority answer (1.0 = all five agree). Cells: balanced accuracy of the baseline verdict (n).

| Judge | agreement 1.0 | 0.8 | 0.6 | ≤ 0.4 | AUROC of agreement for 'solved' |
|---|---|---|---|---|---|
| qwen3.5-4b | 0.66 (n=397) | 0.60 (n=491) | 0.60 (n=446) | 0.57 (n=698) | 0.72 |
| qwen3.5-9b | 0.61 (n=620) | 0.60 (n=442) | 0.59 (n=422) | 0.57 (n=534) | 0.70 |
| qwen3.6-35b-a3b | 0.68 (n=764) | 0.63 (n=425) | 0.63 (n=437) | 0.64 (n=386) | 0.68 |
| nemotron3-super-120b | 0.59 (n=243) | 0.62 (n=319) | 0.63 (n=424) | 0.65 (n=1022) | 0.72 |

## E. Difficulty-aware threshold on the judge's own vote share

The baseline judge gave 3 votes per candidate. Instead of majority (≥ 2 of 3), pick the vote threshold separately for each level of the judge's own solve agreement, choosing it on the other half of the questions (2-fold, by question). Balanced accuracy on not-solved / solved questions.

| Judge | majority vote: not solved | adaptive: not solved | majority: solved | adaptive: solved |
|---|---|---|---|---|
| qwen3.5-4b | 0.52 | 0.57 | 0.67 | 0.66 |
| qwen3.5-9b | 0.49 | 0.52 | 0.71 | 0.70 |
| qwen3.6-35b-a3b | 0.49 | 0.50 | 0.80 | 0.80 |
| nemotron3-super-120b | 0.58 | 0.63 | 0.67 | 0.67 |

## G. Cascades: let the cheap judge decide only when a label-free signal says it is safe, else ask Kimi

Each rule decides, without any gold labels, which candidates go to the stronger judge (Kimi-K3.1-Pro, high reasoning). Cells: balanced accuracy on questions the cheap judge solved / did not solve / all, and the share of candidates routed (the cost). Only candidates Kimi also judged.

| Judge | Rule | routed | solved | not solved | all |
|---|---|---|---|---|---|
| qwen3.5-4b | never route (cheap judge alone) | 0% | 0.68 | 0.55 | 0.62 |
| qwen3.5-4b | always route (Kimi alone) | 100% | 0.83 | 0.78 | 0.80 |
| qwen3.5-4b | route if own 5 samples disagree (<4/5 agree) | 56% | 0.77 | 0.71 | 0.74 |
| qwen3.5-4b | route if the judge's 3 verdict votes are not unanimous | 39% | 0.76 | 0.66 | 0.71 |
| qwen3.5-4b | route if own majority answer ≠ most common candidate answer | 51% | 0.70 | 0.74 | 0.72 |
| qwen3.5-4b | route if either of the last two | 68% | 0.78 | 0.74 | 0.76 |
| qwen3.5-9b | never route (cheap judge alone) | 0% | 0.69 | 0.51 | 0.61 |
| qwen3.5-9b | always route (Kimi alone) | 100% | 0.87 | 0.76 | 0.80 |
| qwen3.5-9b | route if own 5 samples disagree (<4/5 agree) | 47% | 0.81 | 0.67 | 0.73 |
| qwen3.5-9b | route if the judge's 3 verdict votes are not unanimous | 33% | 0.78 | 0.62 | 0.70 |
| qwen3.5-9b | route if own majority answer ≠ most common candidate answer | 38% | 0.76 | 0.69 | 0.71 |
| qwen3.5-9b | route if either of the last two | 54% | 0.83 | 0.70 | 0.75 |
| qwen3.6-35b-a3b | never route (cheap judge alone) | 0% | 0.77 | 0.49 | 0.67 |
| qwen3.6-35b-a3b | always route (Kimi alone) | 100% | 0.89 | 0.69 | 0.81 |
| qwen3.6-35b-a3b | route if own 5 samples disagree (<4/5 agree) | 41% | 0.84 | 0.64 | 0.75 |
| qwen3.6-35b-a3b | route if the judge's 3 verdict votes are not unanimous | 28% | 0.85 | 0.60 | 0.75 |
| qwen3.6-35b-a3b | route if own majority answer ≠ most common candidate answer | 35% | 0.82 | 0.63 | 0.73 |
| qwen3.6-35b-a3b | route if either of the last two | 49% | 0.88 | 0.65 | 0.78 |
| nemotron3-super-120b | never route (cheap judge alone) | 0% | 0.65 | 0.61 | 0.63 |
| nemotron3-super-120b | always route (Kimi alone) | 100% | 0.84 | 0.79 | 0.80 |
| nemotron3-super-120b | route if own 5 samples disagree (<4/5 agree) | 72% | 0.74 | 0.75 | 0.74 |
| nemotron3-super-120b | route if the judge's 3 verdict votes are not unanimous | 36% | 0.76 | 0.72 | 0.73 |
| nemotron3-super-120b | route if own majority answer ≠ most common candidate answer | 68% | 0.73 | 0.77 | 0.76 |
| nemotron3-super-120b | route if either of the last two | 77% | 0.80 | 0.77 | 0.78 |

## F. Cost of each condition (tokens per judgment, sample 0; the baseline drew 3 samples)

| Judge | Condition | n | mean input tokens | mean output tokens | cut off after retries |
|---|---|---|---|---|---|
| qwen3.5-4b | none | 2032 | 2,106 | 1,922 | 0 |
| qwen3.5-4b | gold | 2032 | 2,122 | 1,382 | 0 |
| qwen3.5-4b | strong | 2032 | 2,143 | 1,987 | 2 |
| qwen3.5-4b | self | 2032 | 5,900 | 920 | 0 |
| qwen3.5-4b | verify | 2032 | 2,211 | 3,199 | 0 |
| qwen3.5-9b | none | 2018 | 2,084 | 2,136 | 1 |
| qwen3.5-9b | gold | 2018 | 2,100 | 1,152 | 0 |
| qwen3.5-9b | strong | 2018 | 2,120 | 1,355 | 0 |
| qwen3.5-9b | self | 2017 | 6,172 | 522 | 0 |
| qwen3.5-9b | verify | 2018 | 2,189 | 3,571 | 3 |
| qwen3.6-35b-a3b | none | 2012 | 2,064 | 2,600 | 0 |
| qwen3.6-35b-a3b | gold | 2012 | 2,080 | 1,499 | 0 |
| qwen3.6-35b-a3b | strong | 2012 | 2,100 | 1,660 | 0 |
| qwen3.6-35b-a3b | self | 2012 | 5,847 | 476 | 0 |
| qwen3.6-35b-a3b | verify | 2012 | 2,169 | 3,103 | 0 |
| nemotron3-super-120b | none | 2008 | 2,139 | 4,818 | 8 |
| nemotron3-super-120b | gold | 2008 | 2,157 | 1,777 | 2 |
| nemotron3-super-120b | strong | 2008 | 2,178 | 1,454 | 0 |
| nemotron3-super-120b | self | 2005 | 2,177 | 2,732 | 3 |
| nemotron3-super-120b | verify | 2008 | 2,240 | 4,336 | 0 |
| kimi-k3.1-pro | none | 2244 | 2,014 | 1,301 | 0 |
