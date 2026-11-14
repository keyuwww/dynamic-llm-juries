# 'Your own answer' framing, and thinking on vs off

Cells: balanced accuracy (accept rate of right answers / of wrong answers). Δ vs the no-framing baseline, thinking off, on the same answers, with question-resampled 95% intervals.

## BBEH, thinking off (4 judges pooled)

| Framing | solved | not solved | Δ not solved |
|---|---|---|---|
| no framing (baseline) | 0.71 (0.88 / 0.46) | 0.55 (0.68 / 0.58) | — |
| shown as its own reply + 'is your answer correct?' | 0.61 (0.87 / 0.65) | 0.52 (0.74 / 0.70) | -3 [-5, -1] |
| 'here is the answer you gave earlier' | 0.69 (0.88 / 0.50) | 0.53 (0.68 / 0.61) | -2 [-4, -0] |
| same layout, relayed as another AI's answer + 'is that assistant's answer correct?' | 0.68 (0.83 / 0.47) | 0.54 (0.60 / 0.52) | -1 [-3, +1] |

## BBEH, thinking off: own reply vs another AI's (same layout)

Δ accept rate, own − another AI's, same answers and judge, ×100 [95% CI].

| Judge | solved: wrong answers | solved: right answers | not solved: wrong answers | not solved: right answers |
|---|---|---|---|---|
| qwen3.5-4b | +21 [+14, +29] | +10 [+5, +16] | +20 [+15, +24] | +17 [+11, +23] |
| qwen3.5-9b | +19 [+12, +25] | +6 [+3, +9] | +18 [+14, +23] | +14 [+6, +22] |
| qwen3.6-35b-a3b | +10 [+4, +17] | -2 [-5, +0] | +8 [+3, +13] | +3 [-7, +13] |
| nemotron3-super-120b | +26 [+19, +35] | +5 [-1, +10] | +23 [+19, +26] | +15 [+11, +19] |
| 4 judges pooled | +17 [+14, +21] | +4 [+2, +6] | +18 [+15, +20] | +14 [+11, +17] |

## BBEH, Qwen3.5-9B with thinking ON (one sample each)

| Condition | solved | not solved | Δ not solved vs thinking-off baseline |
|---|---|---|---|
| thinking on, no framing (baseline) | 0.74 (0.95 / 0.47) | 0.56 (0.75 / 0.63) | +5 [+0, +10] |
| thinking on, shown as its own reply + 'is your answer correct?' | 0.72 (0.95 / 0.51) | 0.55 (0.78 / 0.68) | +4 [+0, +9] |
| thinking on, 'here is the answer you gave earlier' | 0.76 (0.95 / 0.42) | 0.55 (0.76 / 0.66) | +4 [-0, +8] |
| thinking off, no framing (baseline) | 0.69 (0.90 / 0.52) | 0.51 (0.69 / 0.66) | — |

## BFF-Bench (finance, expert labels)

| Judges | Condition | solved | not solved | Δ not solved |
|---|---|---|---|---|
| 4 judges, thinking off | no framing (baseline) | 0.77 (0.85 / 0.30) | 0.69 (0.67 / 0.29) | +0 [+0, +0] |
| 4 judges, thinking off | shown as its own reply + 'is your answer correct?' | 0.78 (0.77 / 0.20) | 0.63 (0.48 / 0.23) | -6 [-11, -1] |
| 4 judges, thinking off | 'here is the answer you gave earlier' | 0.78 (0.85 / 0.29) | 0.69 (0.68 / 0.30) | +0 [-4, +4] |
| 4 judges, thinking off | same layout, relayed as another AI's answer + 'is that assistant's answer correct?' | 0.79 (0.75 / 0.17) | 0.65 (0.50 / 0.20) | -4 [-8, -0] |
| Qwen3.5-9B, thinking on | no framing (baseline) | 0.86 (0.84 / 0.12) | 0.77 (0.68 / 0.15) | +4 [-4, +12] |
| Qwen3.5-9B, thinking on | shown as its own reply + 'is your answer correct?' | 0.83 (0.77 / 0.12) | 0.73 (0.58 / 0.13) | +0 [-10, +10] |
| Qwen3.5-9B, thinking on | 'here is the answer you gave earlier' | 0.87 (0.88 / 0.14) | 0.71 (0.61 / 0.19) | -2 [-9, +7] |

## BFF-Bench, thinking off: own reply vs another AI's (same layout)

Δ accept rate, own − another AI's, ×100 [95% CI].

| Judges | solved: wrong answers | solved: right answers | not solved: wrong answers | not solved: right answers |
|---|---|---|---|---|
| 4 judges, thinking off | +4 [+0, +8] | +2 [-0, +4] | +2 [-2, +6] | -2 [-8, +6] |
