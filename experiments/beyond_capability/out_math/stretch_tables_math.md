# Stretching the judge direction — math

Thinking off; the verdict is read at "VERDICT:" right after the edit. Directions are question-centred and learned on the other half of the questions. Cells: within-question AUROC / balanced accuracy (accept rate of right / of wrong answers).


## qwen3.5-9b (layer 22; held-out within-question AUROC of the direction 0.71; solves 98% of questions)

| Direction | Edit | all questions | solved | not solved |
|---|---|---|---|---|
| judge | add -8.0 | 0.67 / 0.50 (0.00 / 0.00) n=2384 | 0.68 / 0.50 (0.00 / 0.00) n=2122 | 0.60 / 0.50 (0.00 / 0.00) n=262 |
| judge | add -4.0 | 0.68 / 0.62 (0.37 / 0.12) n=2384 | 0.69 / 0.63 (0.38 / 0.13) n=2122 | 0.59 / 0.57 (0.24 / 0.09) n=262 |
| judge | add 0.0 | 0.66 / 0.59 (0.85 / 0.67) n=2384 | 0.68 / 0.61 (0.86 / 0.65) n=2122 | 0.56 / 0.48 (0.70 / 0.74) n=262 |
| judge | add 4.0 | 0.65 / 0.52 (0.95 / 0.92) n=2384 | 0.66 / 0.52 (0.95 / 0.91) n=2122 | 0.57 / 0.48 (0.90 / 0.93) n=262 |
| judge | add 8.0 | 0.65 / 0.50 (1.00 / 1.00) n=2384 | 0.66 / 0.50 (1.00 / 1.00) n=2122 | 0.57 / 0.51 (1.00 / 0.98) n=262 |
| judge | amplify 1.0 | 0.68 / 0.62 (0.82 / 0.58) n=2384 | 0.69 / 0.63 (0.84 / 0.58) n=2122 | 0.59 / 0.53 (0.65 / 0.58) n=262 |
| judge | amplify 3.0 | 0.70 / 0.64 (0.78 / 0.50) n=2384 | 0.71 / 0.65 (0.80 / 0.51) n=2122 | 0.63 / 0.56 (0.57 / 0.45) n=262 |
| judge | amplify 10.0 | 0.68 / 0.66 (0.72 / 0.40) n=2384 | 0.69 / 0.66 (0.74 / 0.42) n=2122 | 0.63 / 0.59 (0.50 / 0.32) n=262 |
| random | add -8.0 | 0.66 / 0.59 (0.85 / 0.67) n=2384 | 0.67 / 0.60 (0.86 / 0.65) n=2122 | 0.56 / 0.48 (0.70 / 0.74) n=262 |
| random | add -4.0 | 0.66 / 0.59 (0.85 / 0.66) n=2384 | 0.67 / 0.61 (0.86 / 0.65) n=2122 | 0.56 / 0.48 (0.70 / 0.73) n=262 |
| random | add 0.0 | 0.66 / 0.59 (0.85 / 0.67) n=2384 | 0.68 / 0.61 (0.86 / 0.65) n=2122 | 0.56 / 0.48 (0.70 / 0.74) n=262 |
| random | add 4.0 | 0.66 / 0.59 (0.85 / 0.66) n=2384 | 0.68 / 0.60 (0.86 / 0.65) n=2122 | 0.56 / 0.49 (0.70 / 0.72) n=262 |
| random | add 8.0 | 0.66 / 0.59 (0.85 / 0.66) n=2384 | 0.68 / 0.61 (0.86 / 0.65) n=2122 | 0.56 / 0.48 (0.70 / 0.73) n=262 |
| random | amplify 1.0 | 0.66 / 0.59 (0.85 / 0.67) n=2384 | 0.68 / 0.60 (0.86 / 0.65) n=2122 | 0.56 / 0.48 (0.70 / 0.74) n=262 |
| random | amplify 3.0 | 0.66 / 0.59 (0.85 / 0.66) n=2384 | 0.67 / 0.61 (0.86 / 0.65) n=2122 | 0.57 / 0.48 (0.70 / 0.74) n=262 |
| random | amplify 10.0 | 0.66 / 0.59 (0.85 / 0.67) n=2384 | 0.67 / 0.60 (0.86 / 0.65) n=2122 | 0.56 / 0.48 (0.70 / 0.74) n=262 |

Stretch x11 (amplify 10) minus no edit, judge direction [95% CI]:

| Questions | Δ within-question AUROC | Δ balanced accuracy | same for the random direction (Δ bal.) |
|---|---|---|---|
| all questions | +2 [-1, +5] | +7 [+5, +9] | -0 [-0, -0] |
| solved | +2 [-2, +5] | +6 [+4, +7] | -0 [-0, +0] |
| not solved | +7 [-1, +15] | +11 [+5, +16] | -0 [-1, +0] |

## llama3.1-8b (layer 14; held-out within-question AUROC of the direction 0.67; solve labels not available yet)

| Direction | Edit | all questions |
|---|---|---|
| judge | add -8.0 | 0.54 / 0.51 (0.95 / 0.92) n=2384 |
| judge | add -4.0 | 0.54 / 0.52 (0.95 / 0.91) n=2384 |
| judge | add 0.0 | 0.54 / 0.52 (0.95 / 0.91) n=2384 |
| judge | add 4.0 | 0.53 / 0.52 (0.95 / 0.91) n=2384 |
| judge | add 8.0 | 0.53 / 0.52 (0.95 / 0.92) n=2384 |
| judge | amplify 1.0 | 0.53 / 0.52 (0.95 / 0.91) n=2384 |
| judge | amplify 3.0 | 0.52 / 0.52 (0.95 / 0.90) n=2384 |
| judge | amplify 10.0 | 0.56 / 0.54 (0.92 / 0.84) n=2384 |
| random | add -8.0 | 0.54 / 0.52 (0.95 / 0.91) n=2384 |
| random | add -4.0 | 0.54 / 0.52 (0.95 / 0.91) n=2384 |
| random | add 0.0 | 0.54 / 0.52 (0.95 / 0.91) n=2384 |
| random | add 4.0 | 0.54 / 0.52 (0.95 / 0.91) n=2384 |
| random | add 8.0 | 0.54 / 0.52 (0.95 / 0.91) n=2384 |
| random | amplify 1.0 | 0.54 / 0.52 (0.95 / 0.91) n=2384 |
| random | amplify 3.0 | 0.54 / 0.52 (0.95 / 0.91) n=2384 |
| random | amplify 10.0 | 0.54 / 0.52 (0.95 / 0.91) n=2384 |

Stretch x11 (amplify 10) minus no edit, judge direction [95% CI]:

| Questions | Δ within-question AUROC | Δ balanced accuracy | same for the random direction (Δ bal.) |
|---|---|---|---|
| all questions | +1 [-2, +5] | +2 [+1, +3] | +0 [-0, +0] |
