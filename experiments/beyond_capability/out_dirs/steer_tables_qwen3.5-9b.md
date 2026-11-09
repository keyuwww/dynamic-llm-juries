# Steering the judge — qwen3.5-9b

*add* = h + α·v (same push for every answer); *amplify* = h + β·((h·v) − μ)·v (stretches answers apart along v). Cells: within-question AUROC of the verdict / share of right answers accepted / share of wrong answers accepted.


## bbeh

| Direction | Edit | solved: AUROC / acc. right / acc. wrong | **not solved**: AUROC / acc. right / acc. wrong |
|---|---|---|---|
| generate-role direction | add -8.0 | 0.68 / 0.45 / 0.27 | 0.49 / 0.24 / 0.32 |
| generate-role direction | add -4.0 | 0.68 / 0.45 / 0.27 | 0.51 / 0.25 / 0.32 |
| generate-role direction | add 0.0 | 0.68 / 0.45 / 0.27 | 0.50 / 0.26 / 0.32 |
| generate-role direction | add 4.0 | 0.69 / 0.45 / 0.27 | 0.50 / 0.26 / 0.32 |
| generate-role direction | add 8.0 | 0.69 / 0.45 / 0.27 | 0.50 / 0.25 / 0.32 |
| generate-role direction | amplify 1.0 | 0.69 / 0.46 / 0.27 | 0.49 / 0.27 / 0.32 |
| generate-role direction | amplify 3.0 | 0.68 / 0.45 / 0.28 | 0.49 / 0.25 / 0.32 |
| generate-role direction | amplify 10.0 | 0.69 / 0.45 / 0.28 | 0.50 / 0.25 / 0.32 |
| generate-role direction, question-centred | add -8.0 | 0.68 / 0.43 / 0.24 | 0.50 / 0.24 / 0.30 |
| generate-role direction, question-centred | add -4.0 | 0.68 / 0.44 / 0.25 | 0.49 / 0.25 / 0.31 |
| generate-role direction, question-centred | add 0.0 | 0.68 / 0.45 / 0.27 | 0.50 / 0.26 / 0.32 |
| generate-role direction, question-centred | add 4.0 | 0.68 / 0.46 / 0.28 | 0.50 / 0.27 / 0.32 |
| generate-role direction, question-centred | add 8.0 | 0.67 / 0.47 / 0.28 | 0.51 / 0.26 / 0.34 |
| generate-role direction, question-centred | amplify 1.0 | 0.68 / 0.45 / 0.27 | 0.51 / 0.26 / 0.32 |
| generate-role direction, question-centred | amplify 3.0 | 0.68 / 0.44 / 0.28 | 0.50 / 0.25 / 0.32 |
| generate-role direction, question-centred | amplify 10.0 | 0.67 / 0.44 / 0.28 | 0.49 / 0.25 / 0.32 |
| judge-role direction | add -8.0 | 0.68 / 0.45 / 0.25 | 0.51 / 0.24 / 0.30 |
| judge-role direction | add -4.0 | 0.68 / 0.45 / 0.26 | 0.50 / 0.26 / 0.32 |
| judge-role direction | add 0.0 | 0.68 / 0.45 / 0.27 | 0.50 / 0.26 / 0.32 |
| judge-role direction | add 4.0 | 0.68 / 0.46 / 0.28 | 0.51 / 0.27 / 0.32 |
| judge-role direction | add 8.0 | 0.67 / 0.46 / 0.28 | 0.50 / 0.25 / 0.32 |
| judge-role direction | amplify 1.0 | 0.70 / 0.46 / 0.28 | 0.49 / 0.25 / 0.32 |
| judge-role direction | amplify 3.0 | 0.69 / 0.46 / 0.28 | 0.50 / 0.26 / 0.32 |
| judge-role direction | amplify 10.0 | 0.68 / 0.45 / 0.27 | 0.50 / 0.26 / 0.31 |
| judge-role direction, question-centred | add -8.0 | 0.68 / 0.23 / 0.10 | 0.50 / 0.08 / 0.14 |
| judge-role direction, question-centred | add -4.0 | 0.67 / 0.33 / 0.17 | 0.49 / 0.14 / 0.24 |
| judge-role direction, question-centred | add 0.0 | 0.68 / 0.45 / 0.27 | 0.50 / 0.26 / 0.32 |
| judge-role direction, question-centred | add 4.0 | 0.68 / 0.59 / 0.41 | 0.50 / 0.42 / 0.45 |
| judge-role direction, question-centred | add 8.0 | 0.67 / 0.77 / 0.60 | 0.49 / 0.64 / 0.59 |
| judge-role direction, question-centred | amplify 1.0 | 0.69 / 0.47 / 0.27 | 0.51 / 0.28 / 0.32 |
| judge-role direction, question-centred | amplify 3.0 | 0.70 / 0.48 / 0.25 | 0.51 / 0.28 / 0.34 |
| judge-role direction, question-centred | amplify 10.0 | 0.69 / 0.51 / 0.33 | 0.51 / 0.37 / 0.42 |
| random direction | add -8.0 | 0.68 / 0.46 / 0.27 | 0.48 / 0.25 / 0.32 |
| random direction | add -4.0 | 0.69 / 0.46 / 0.26 | 0.50 / 0.26 / 0.32 |
| random direction | add 0.0 | 0.68 / 0.45 / 0.27 | 0.50 / 0.26 / 0.32 |
| random direction | add 4.0 | 0.69 / 0.46 / 0.27 | 0.48 / 0.26 / 0.32 |
| random direction | add 8.0 | 0.68 / 0.46 / 0.26 | 0.49 / 0.26 / 0.31 |
| random direction | amplify 1.0 | 0.69 / 0.45 / 0.27 | 0.50 / 0.26 / 0.32 |
| random direction | amplify 3.0 | 0.69 / 0.45 / 0.27 | 0.49 / 0.26 / 0.32 |
| random direction | amplify 10.0 | 0.68 / 0.45 / 0.26 | 0.49 / 0.25 / 0.32 |
| random direction (centred run) | add -8.0 | 0.68 / 0.45 / 0.27 | 0.50 / 0.26 / 0.32 |
| random direction (centred run) | add -4.0 | 0.69 / 0.45 / 0.26 | 0.50 / 0.27 / 0.32 |
| random direction (centred run) | add 0.0 | 0.68 / 0.45 / 0.27 | 0.50 / 0.26 / 0.32 |
| random direction (centred run) | add 4.0 | 0.68 / 0.45 / 0.27 | 0.51 / 0.24 / 0.32 |
| random direction (centred run) | add 8.0 | 0.68 / 0.46 / 0.27 | 0.50 / 0.26 / 0.32 |
| random direction (centred run) | amplify 1.0 | 0.69 / 0.45 / 0.26 | 0.50 / 0.24 / 0.32 |
| random direction (centred run) | amplify 3.0 | 0.68 / 0.46 / 0.26 | 0.50 / 0.26 / 0.32 |
| random direction (centred run) | amplify 10.0 | 0.69 / 0.46 / 0.27 | 0.50 / 0.26 / 0.31 |

## rb2math

| Direction | Edit | solved: AUROC / acc. right / acc. wrong | **not solved**: AUROC / acc. right / acc. wrong |
|---|---|---|---|
| generate-role direction | add -8.0 | 0.85 / 0.78 / 0.27 | 0.78 / 0.52 / 0.25 |
| generate-role direction | add -4.0 | 0.85 / 0.78 / 0.27 | 0.78 / 0.52 / 0.26 |
| generate-role direction | add 0.0 | 0.85 / 0.78 / 0.27 | 0.78 / 0.52 / 0.26 |
| generate-role direction | add 4.0 | 0.85 / 0.78 / 0.27 | 0.78 / 0.52 / 0.25 |
| generate-role direction | add 8.0 | 0.85 / 0.78 / 0.27 | 0.78 / 0.52 / 0.26 |
| generate-role direction | amplify 1.0 | 0.85 / 0.78 / 0.27 | 0.79 / 0.52 / 0.25 |
| generate-role direction | amplify 3.0 | 0.85 / 0.78 / 0.27 | 0.79 / 0.52 / 0.26 |
| generate-role direction | amplify 10.0 | 0.84 / 0.79 / 0.28 | 0.78 / 0.52 / 0.26 |
| judge-role direction | add -8.0 | 0.78 / 0.00 / 0.00 | 0.74 / 0.00 / 0.00 |
| judge-role direction | add -4.0 | 0.86 / 0.00 / 0.00 | 0.78 / 0.00 / 0.00 |
| judge-role direction | add 0.0 | 0.85 / 0.78 / 0.27 | 0.78 / 0.52 / 0.26 |
| judge-role direction | add 4.0 | 0.84 / 1.00 / 1.00 | 0.71 / 1.00 / 1.00 |
| judge-role direction | add 8.0 | 0.75 / 1.00 / 1.00 | 0.56 / 1.00 / 1.00 |
| judge-role direction | amplify 1.0 | 0.86 / 0.84 / 0.32 | 0.77 / 0.62 / 0.30 |
| judge-role direction | amplify 3.0 | 0.86 / 0.86 / 0.34 | 0.78 / 0.62 / 0.32 |
| judge-role direction | amplify 10.0 | 0.85 / 0.89 / 0.37 | 0.78 / 0.66 / 0.32 |
| random direction | add -8.0 | 0.85 / 0.78 / 0.27 | 0.79 / 0.52 / 0.26 |
| random direction | add -4.0 | 0.85 / 0.78 / 0.27 | 0.79 / 0.52 / 0.26 |
| random direction | add 0.0 | 0.85 / 0.78 / 0.27 | 0.78 / 0.52 / 0.26 |
| random direction | add 4.0 | 0.85 / 0.78 / 0.27 | 0.78 / 0.52 / 0.25 |
| random direction | add 8.0 | 0.85 / 0.78 / 0.27 | 0.78 / 0.52 / 0.25 |
| random direction | amplify 1.0 | 0.85 / 0.78 / 0.27 | 0.78 / 0.52 / 0.26 |
| random direction | amplify 3.0 | 0.84 / 0.78 / 0.27 | 0.79 / 0.52 / 0.24 |
| random direction | amplify 10.0 | 0.85 / 0.78 / 0.25 | 0.78 / 0.52 / 0.24 |
