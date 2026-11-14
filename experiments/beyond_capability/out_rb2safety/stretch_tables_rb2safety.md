# Stretching the judge direction — rb2safety

Thinking off; the verdict is read at "VERDICT:" right after the edit. Directions are question-centred and learned on the other half of the questions. Cells: within-question AUROC / balanced accuracy (accept rate of right / of wrong answers).


## qwen3.5-9b (layer 14; held-out within-question AUROC of the direction 0.98; solve labels not available yet)

| Direction | Edit | all questions |
|---|---|---|
| judge | add -8.0 | 0.97 / 0.89 (0.96 / 0.19) n=1800 |
| judge | add -4.0 | 0.97 / 0.89 (0.96 / 0.19) n=1800 |
| judge | add 0.0 | 0.96 / 0.89 (0.96 / 0.18) n=1800 |
| judge | add 4.0 | 0.96 / 0.89 (0.95 / 0.17) n=1800 |
| judge | add 8.0 | 0.96 / 0.89 (0.95 / 0.17) n=1800 |
| judge | amplify 1.0 | 0.96 / 0.89 (0.96 / 0.18) n=1800 |
| judge | amplify 3.0 | 0.96 / 0.89 (0.96 / 0.18) n=1800 |
| judge | amplify 10.0 | 0.96 / 0.89 (0.96 / 0.18) n=1800 |
| random | add -8.0 | 0.97 / 0.89 (0.96 / 0.18) n=1800 |
| random | add -4.0 | 0.96 / 0.89 (0.96 / 0.18) n=1800 |
| random | add 0.0 | 0.96 / 0.89 (0.96 / 0.18) n=1800 |
| random | add 4.0 | 0.96 / 0.89 (0.96 / 0.18) n=1800 |
| random | add 8.0 | 0.96 / 0.89 (0.96 / 0.18) n=1800 |
| random | amplify 1.0 | 0.96 / 0.89 (0.96 / 0.18) n=1800 |
| random | amplify 3.0 | 0.96 / 0.89 (0.96 / 0.18) n=1800 |
| random | amplify 10.0 | 0.97 / 0.89 (0.96 / 0.18) n=1800 |

Stretch x11 (amplify 10) minus no edit, judge direction [95% CI]:

| Questions | Δ within-question AUROC | Δ balanced accuracy | same for the random direction (Δ bal.) |
|---|---|---|---|
| all questions | +0 [-0, +1] | +0 [-0, +1] | +0 [-0, +0] |

## llama3.1-8b (layer 14; held-out within-question AUROC of the direction 0.99; solve labels not available yet)

| Direction | Edit | all questions |
|---|---|---|
| judge | add -8.0 | 0.95 / 0.50 (0.00 / 0.00) n=1800 |
| judge | add -4.0 | 0.94 / 0.77 (0.59 / 0.05) n=1800 |
| judge | add 0.0 | 0.96 / 0.88 (0.95 / 0.19) n=1800 |
| judge | add 4.0 | 0.95 / 0.71 (1.00 / 0.58) n=1800 |
| judge | add 8.0 | 0.91 / 0.51 (1.00 / 0.99) n=1800 |
| judge | amplify 1.0 | 0.97 / 0.89 (0.96 / 0.19) n=1800 |
| judge | amplify 3.0 | 0.97 / 0.88 (0.97 / 0.21) n=1800 |
| judge | amplify 10.0 | 0.90 / 0.87 (0.98 / 0.24) n=1800 |
| random | add -8.0 | 0.96 / 0.88 (0.95 / 0.18) n=1800 |
| random | add -4.0 | 0.96 / 0.88 (0.95 / 0.18) n=1800 |
| random | add 0.0 | 0.96 / 0.88 (0.95 / 0.19) n=1800 |
| random | add 4.0 | 0.96 / 0.88 (0.95 / 0.19) n=1800 |
| random | add 8.0 | 0.96 / 0.88 (0.95 / 0.19) n=1800 |
| random | amplify 1.0 | 0.96 / 0.88 (0.95 / 0.19) n=1800 |
| random | amplify 3.0 | 0.96 / 0.88 (0.95 / 0.19) n=1800 |
| random | amplify 10.0 | 0.96 / 0.88 (0.95 / 0.19) n=1800 |

Stretch x11 (amplify 10) minus no edit, judge direction [95% CI]:

| Questions | Δ within-question AUROC | Δ balanced accuracy | same for the random direction (Δ bal.) |
|---|---|---|---|
| all questions | -6 [-10, -4] | -1 [-2, +0] | +0 [-0, +0] |
