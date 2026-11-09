# Steering the judge — llama3.1-8b

*add* = h + α·v (same push for every answer); *amplify* = h + β·((h·v) − μ)·v (stretches answers apart along v). Cells: within-question AUROC of the verdict / share of right answers accepted / share of wrong answers accepted.


## bbeh

| Direction | Edit | solved: AUROC / acc. right / acc. wrong | **not solved**: AUROC / acc. right / acc. wrong |
|---|---|---|---|
| generate-role direction | add -8.0 | 0.68 / 0.73 / 0.59 | 0.54 / 0.62 / 0.67 |
| generate-role direction | add -4.0 | 0.68 / 0.73 / 0.57 | 0.54 / 0.59 / 0.65 |
| generate-role direction | add 0.0 | 0.68 / 0.69 / 0.55 | 0.53 / 0.53 / 0.62 |
| generate-role direction | add 4.0 | 0.69 / 0.67 / 0.53 | 0.53 / 0.50 / 0.59 |
| generate-role direction | add 8.0 | 0.69 / 0.66 / 0.52 | 0.53 / 0.48 / 0.56 |
| generate-role direction | amplify 1.0 | 0.68 / 0.69 / 0.55 | 0.53 / 0.54 / 0.61 |
| generate-role direction | amplify 3.0 | 0.68 / 0.72 / 0.55 | 0.53 / 0.54 / 0.63 |
| generate-role direction | amplify 10.0 | 0.68 / 0.73 / 0.54 | 0.53 / 0.52 / 0.61 |
| generate-role direction, question-centred | add -8.0 | 0.69 / 0.69 / 0.51 | 0.52 / 0.52 / 0.61 |
| generate-role direction, question-centred | add -4.0 | 0.68 / 0.67 / 0.53 | 0.53 / 0.53 / 0.62 |
| generate-role direction, question-centred | add 0.0 | 0.68 / 0.69 / 0.55 | 0.53 / 0.53 / 0.62 |
| generate-role direction, question-centred | add 4.0 | 0.69 / 0.69 / 0.56 | 0.53 / 0.56 / 0.62 |
| generate-role direction, question-centred | add 8.0 | 0.68 / 0.69 / 0.56 | 0.53 / 0.58 / 0.65 |
| generate-role direction, question-centred | amplify 1.0 | 0.68 / 0.68 / 0.55 | 0.54 / 0.54 / 0.63 |
| generate-role direction, question-centred | amplify 3.0 | 0.69 / 0.69 / 0.54 | 0.54 / 0.54 / 0.63 |
| generate-role direction, question-centred | amplify 10.0 | 0.69 / 0.69 / 0.52 | 0.55 / 0.55 / 0.61 |
| judge-role direction | add -8.0 | 0.68 / 0.90 / 0.70 | 0.53 / 0.78 / 0.82 |
| judge-role direction | add -4.0 | 0.68 / 0.82 / 0.65 | 0.53 / 0.71 / 0.76 |
| judge-role direction | add 0.0 | 0.68 / 0.69 / 0.55 | 0.53 / 0.53 / 0.62 |
| judge-role direction | add 4.0 | 0.68 / 0.59 / 0.44 | 0.53 / 0.41 / 0.44 |
| judge-role direction | add 8.0 | 0.68 / 0.46 / 0.27 | 0.53 / 0.27 / 0.33 |
| judge-role direction | amplify 1.0 | 0.68 / 0.70 / 0.54 | 0.53 / 0.52 / 0.60 |
| judge-role direction | amplify 3.0 | 0.68 / 0.65 / 0.52 | 0.53 / 0.52 / 0.59 |
| judge-role direction | amplify 10.0 | 0.67 / 0.65 / 0.51 | 0.51 / 0.45 / 0.57 |
| judge-role direction, question-centred | add -8.0 | 0.67 / 0.59 / 0.51 | 0.55 / 0.42 / 0.44 |
| judge-role direction, question-centred | add -4.0 | 0.68 / 0.72 / 0.54 | 0.54 / 0.53 / 0.60 |
| judge-role direction, question-centred | add 0.0 | 0.68 / 0.69 / 0.55 | 0.53 / 0.53 / 0.62 |
| judge-role direction, question-centred | add 4.0 | 0.69 / 0.72 / 0.64 | 0.54 / 0.59 / 0.65 |
| judge-role direction, question-centred | add 8.0 | 0.70 / 0.78 / 0.66 | 0.56 / 0.69 / 0.73 |
| judge-role direction, question-centred | amplify 1.0 | 0.69 / 0.69 / 0.55 | 0.54 / 0.55 / 0.62 |
| judge-role direction, question-centred | amplify 3.0 | 0.69 / 0.69 / 0.57 | 0.54 / 0.54 / 0.60 |
| judge-role direction, question-centred | amplify 10.0 | 0.69 / 0.69 / 0.56 | 0.60 / 0.56 / 0.56 |
| random direction | add -8.0 | 0.69 / 0.69 / 0.55 | 0.53 / 0.54 / 0.62 |
| random direction | add -4.0 | 0.68 / 0.69 / 0.54 | 0.52 / 0.55 / 0.62 |
| random direction | add 0.0 | 0.68 / 0.69 / 0.55 | 0.53 / 0.53 / 0.62 |
| random direction | add 4.0 | 0.68 / 0.69 / 0.55 | 0.54 / 0.55 / 0.63 |
| random direction | add 8.0 | 0.68 / 0.68 / 0.55 | 0.54 / 0.55 / 0.62 |
| random direction | amplify 1.0 | 0.69 / 0.69 / 0.55 | 0.53 / 0.53 / 0.63 |
| random direction | amplify 3.0 | 0.69 / 0.69 / 0.55 | 0.54 / 0.53 / 0.62 |
| random direction | amplify 10.0 | 0.68 / 0.69 / 0.56 | 0.54 / 0.54 / 0.62 |
| random direction (centred run) | add -8.0 | 0.68 / 0.69 / 0.57 | 0.53 / 0.55 / 0.64 |
| random direction (centred run) | add -4.0 | 0.68 / 0.69 / 0.57 | 0.54 / 0.54 / 0.62 |
| random direction (centred run) | add 0.0 | 0.68 / 0.69 / 0.55 | 0.53 / 0.53 / 0.62 |
| random direction (centred run) | add 4.0 | 0.68 / 0.69 / 0.55 | 0.54 / 0.54 / 0.62 |
| random direction (centred run) | add 8.0 | 0.69 / 0.69 / 0.55 | 0.53 / 0.53 / 0.62 |
| random direction (centred run) | amplify 1.0 | 0.69 / 0.69 / 0.55 | 0.54 / 0.54 / 0.63 |
| random direction (centred run) | amplify 3.0 | 0.69 / 0.69 / 0.55 | 0.53 / 0.54 / 0.62 |
| random direction (centred run) | amplify 10.0 | 0.69 / 0.69 / 0.55 | 0.52 / 0.53 / 0.63 |

## rb2math

| Direction | Edit | solved: AUROC / acc. right / acc. wrong | **not solved**: AUROC / acc. right / acc. wrong |
|---|---|---|---|
| generate-role direction | add -8.0 | 0.76 / 0.82 / 0.56 | 0.72 / 0.77 / 0.58 |
| generate-role direction | add -4.0 | 0.76 / 0.82 / 0.57 | 0.71 / 0.79 / 0.60 |
| generate-role direction | add 0.0 | 0.77 / 0.82 / 0.58 | 0.72 / 0.79 / 0.62 |
| generate-role direction | add 4.0 | 0.76 / 0.83 / 0.59 | 0.71 / 0.81 / 0.62 |
| generate-role direction | add 8.0 | 0.76 / 0.83 / 0.59 | 0.71 / 0.81 / 0.63 |
| generate-role direction | amplify 1.0 | 0.76 / 0.82 / 0.57 | 0.71 / 0.79 / 0.61 |
| generate-role direction | amplify 3.0 | 0.76 / 0.82 / 0.58 | 0.71 / 0.79 / 0.61 |
| generate-role direction | amplify 10.0 | 0.75 / 0.82 / 0.57 | 0.72 / 0.78 / 0.60 |
| judge-role direction | add -8.0 | 0.69 / 0.00 / 0.00 | 0.65 / 0.00 / 0.00 |
| judge-role direction | add -4.0 | 0.75 / 0.00 / 0.00 | 0.69 / 0.00 / 0.00 |
| judge-role direction | add 0.0 | 0.77 / 0.82 / 0.58 | 0.72 / 0.79 / 0.62 |
| judge-role direction | add 4.0 | 0.77 / 1.00 / 1.00 | 0.70 / 1.00 / 1.00 |
| judge-role direction | add 8.0 | 0.74 / 1.00 / 1.00 | 0.71 / 1.00 / 1.00 |
| judge-role direction | amplify 1.0 | 0.77 / 0.82 / 0.52 | 0.72 / 0.76 / 0.54 |
| judge-role direction | amplify 3.0 | 0.75 / 0.78 / 0.47 | 0.71 / 0.76 / 0.50 |
| judge-role direction | amplify 10.0 | 0.75 / 0.78 / 0.46 | 0.71 / 0.75 / 0.47 |
| random direction | add -8.0 | 0.77 / 0.82 / 0.57 | 0.71 / 0.79 / 0.62 |
| random direction | add -4.0 | 0.76 / 0.82 / 0.57 | 0.71 / 0.79 / 0.62 |
| random direction | add 0.0 | 0.77 / 0.82 / 0.58 | 0.72 / 0.79 / 0.62 |
| random direction | add 4.0 | 0.77 / 0.82 / 0.57 | 0.71 / 0.80 / 0.62 |
| random direction | add 8.0 | 0.77 / 0.82 / 0.57 | 0.71 / 0.79 / 0.61 |
| random direction | amplify 1.0 | 0.77 / 0.82 / 0.57 | 0.71 / 0.80 / 0.62 |
| random direction | amplify 3.0 | 0.77 / 0.82 / 0.57 | 0.71 / 0.79 / 0.62 |
| random direction | amplify 10.0 | 0.76 / 0.82 / 0.57 | 0.72 / 0.80 / 0.61 |
