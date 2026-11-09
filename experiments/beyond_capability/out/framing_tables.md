# 'Your own answer' framing, and thinking on vs off

Cells: balanced accuracy (accept rate of right answers / of wrong answers). Δ vs the no-framing baseline, thinking off, on the same answers, with question-resampled 95% intervals.

## BBEH, thinking off (4 judges pooled)

| Framing | solved | not solved | Δ not solved |
|---|---|---|---|
| no framing (baseline) | 0.71 (0.88 / 0.46) | 0.55 (0.68 / 0.58) | — |
| shown as its own reply + 'is your answer correct?' | 0.61 (0.87 / 0.65) | 0.52 (0.74 / 0.70) | -3 [-5, -1] |
| 'here is the answer you gave earlier' | 0.69 (0.88 / 0.50) | 0.53 (0.68 / 0.61) | -2 [-4, -0] |

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
| Qwen3.5-9B, thinking on | no framing (baseline) | 0.86 (0.84 / 0.12) | 0.77 (0.68 / 0.15) | +4 [-4, +12] |
| Qwen3.5-9B, thinking on | shown as its own reply + 'is your answer correct?' | 0.83 (0.77 / 0.12) | 0.73 (0.58 / 0.13) | +0 [-10, +10] |
| Qwen3.5-9B, thinking on | 'here is the answer you gave earlier' | 0.87 (0.88 / 0.14) | 0.71 (0.61 / 0.19) | -2 [-9, +7] |
