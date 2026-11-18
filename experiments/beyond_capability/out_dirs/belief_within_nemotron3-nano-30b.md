# Believed vs never-reached WRONG answers to the same question — nemotron3-nano-30b, BBEH, audited labels

Pairwise AUROC within question (0.5 = no preference for the believed answer). 'axis' = the role's correctness direction (cross-fitted over question halves, mean of 20 splits; best layer = highest mean right-vs-wrong AUROC); 'verdict' = the model's own CORRECT-minus-INCORRECT log-odds at that position.

| role | questions with both | pairs | axis, best layer (layer) | 95% CI | axis, mean over the top-third layers | verdict log-odds | 95% CI | belief direction: best layer (layer), mean over the correctness top third |
|---|---|---|---|---|---|---|---|---|
| J judge (VERDICT:) | 22 | 67 | 0.56 (8) | [0.39, 0.68] | 0.59 | 0.47 | [0.27, 0.71] | 0.69 (4), top-third 0.59 |
| N neutral (FINAL:) | 22 | 67 | 0.59 (46) | [0.41, 0.82] | 0.59 | – | – | 0.77 (42), top-third 0.69 |
| S self-check (VERDICT:) | 22 | 67 | 0.52 (12) | [0.38, 0.61] | 0.57 | 0.53 | [0.33, 0.79] | 0.67 (18), top-third 0.59 |
| G generate (end of answer) | 22 | 67 | 0.42 (12) | [0.22, 0.67] | 0.46 | – | – | 0.80 (28), top-third 0.53 |

## Pairwise AUROC of the correctness axis by layer (mean over splits)

| layer | J | N | S | G |
|---|---|---|---|---|
| 0 | 0.50 | 0.50 | 0.50 | 0.37 |
| 2 | 0.49 | 0.58 | 0.53 | 0.44 |
| 4 | 0.63 | 0.56 | 0.59 | 0.53 |
| 6 | 0.68 | 0.51 | 0.58 | 0.50 |
| 8 | 0.56 | 0.47 | 0.42 | 0.51 |
| 10 | 0.59 | 0.49 | 0.59 | 0.49 |
| 12 | 0.58 | 0.59 | 0.52 | 0.42 |
| 14 | 0.51 | 0.53 | 0.55 | 0.42 |
| 16 | 0.59 | 0.59 | 0.60 | 0.42 |
| 18 | 0.60 | 0.61 | 0.72 | 0.43 |
| 20 | 0.63 | 0.65 | 0.62 | 0.41 |
| 22 | 0.54 | 0.59 | 0.58 | 0.41 |
| 24 | 0.63 | 0.62 | 0.60 | 0.49 |
| 26 | 0.56 | 0.57 | 0.61 | 0.63 |
| 28 | 0.64 | 0.55 | 0.54 | 0.71 |
| 30 | 0.62 | 0.51 | 0.61 | 0.65 |
| 32 | 0.65 | 0.66 | 0.62 | 0.64 |
| 34 | 0.66 | 0.62 | 0.61 | 0.54 |
| 36 | 0.59 | 0.65 | 0.63 | 0.55 |
| 38 | 0.57 | 0.67 | 0.60 | 0.56 |
| 40 | 0.56 | 0.67 | 0.62 | 0.56 |
| 42 | 0.54 | 0.67 | 0.51 | 0.56 |
| 44 | 0.53 | 0.58 | 0.55 | 0.59 |
| 46 | 0.49 | 0.59 | 0.57 | 0.61 |
| 48 | 0.49 | 0.56 | 0.49 | 0.59 |
| 50 | 0.46 | 0.56 | 0.52 | 0.58 |
| 52 | 0.57 | 0.58 | 0.56 | 0.51 |
