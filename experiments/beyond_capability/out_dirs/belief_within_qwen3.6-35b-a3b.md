# Believed vs never-reached WRONG answers to the same question — qwen3.6-35b-a3b, BBEH, audited labels

Pairwise AUROC within question (0.5 = no preference for the believed answer). 'axis' = the role's correctness direction (cross-fitted over question halves, mean of 20 splits; best layer = highest mean right-vs-wrong AUROC); 'verdict' = the model's own CORRECT-minus-INCORRECT log-odds at that position.

| role | questions with both | pairs | axis, best layer (layer) | 95% CI | axis, mean over the top-third layers | verdict log-odds | 95% CI | belief direction: best layer (layer), mean over the correctness top third |
|---|---|---|---|---|---|---|---|---|
| J judge (VERDICT:) | 37 | 125 | 0.58 (32) | [0.48, 0.75] | 0.57 | 0.58 | [0.45, 0.72] | 0.66 (2), top-third 0.54 |
| N neutral (FINAL:) | 37 | 125 | 0.54 (40) | [0.33, 0.63] | 0.57 | – | – | 0.69 (30), top-third 0.58 |
| S self-check (VERDICT:) | 37 | 125 | 0.66 (26) | [0.52, 0.81] | 0.61 | 0.59 | [0.47, 0.71] | 0.69 (18), top-third 0.60 |
| G generate (end of answer) | 37 | 125 | 0.55 (6) | [0.41, 0.68] | 0.59 | – | – | 0.70 (38), top-third 0.61 |
| JX judge after explanation | 37 | 125 | 0.76 (26) | [0.65, 0.86] | 0.77 | 0.77 | [0.66, 0.86] | 0.80 (40), top-third 0.77 |
| JT judge after thinking | 5 | 5 | 1.00 (32) | [1.00, 1.00] | 0.97 | 1.00 | [1.00, 1.00] | 1.00 (34), top-third 0.95 |

## Pairwise AUROC of the correctness axis by layer (mean over splits)

| layer | J | N | S | G | JX | JT |
|---|---|---|---|---|---|---|
| 0 | 0.50 | 0.50 | 0.50 | 0.55 | 0.50 | 0.50 |
| 2 | 0.64 | 0.57 | 0.60 | 0.53 | 0.66 | 0.78 |
| 4 | 0.52 | 0.52 | 0.47 | 0.56 | 0.63 | 0.71 |
| 6 | 0.51 | 0.51 | 0.46 | 0.55 | 0.66 | 0.72 |
| 8 | 0.49 | 0.44 | 0.46 | 0.58 | 0.67 | 0.91 |
| 10 | 0.58 | 0.48 | 0.51 | 0.61 | 0.69 | 0.84 |
| 12 | 0.49 | 0.52 | 0.53 | 0.58 | 0.69 | 0.75 |
| 14 | 0.46 | 0.51 | 0.55 | 0.59 | 0.73 | 0.76 |
| 16 | 0.50 | 0.56 | 0.64 | 0.63 | 0.74 | 0.89 |
| 18 | 0.58 | 0.52 | 0.70 | 0.64 | 0.77 | 0.76 |
| 20 | 0.60 | 0.60 | 0.71 | 0.63 | 0.78 | 0.97 |
| 22 | 0.54 | 0.59 | 0.69 | 0.62 | 0.77 | 0.75 |
| 24 | 0.52 | 0.60 | 0.68 | 0.62 | 0.76 | 0.76 |
| 26 | 0.56 | 0.58 | 0.66 | 0.62 | 0.76 | 0.75 |
| 28 | 0.58 | 0.65 | 0.64 | 0.63 | 0.75 | 0.79 |
| 30 | 0.61 | 0.68 | 0.60 | 0.60 | 0.73 | 0.80 |
| 32 | 0.58 | 0.67 | 0.60 | 0.58 | 0.74 | 1.00 |
| 34 | 0.61 | 0.66 | 0.63 | 0.61 | 0.74 | 1.00 |
| 36 | 0.60 | 0.63 | 0.61 | 0.64 | 0.72 | 1.00 |
| 38 | 0.59 | 0.59 | 0.60 | 0.67 | 0.77 | 1.00 |
| 40 | 0.60 | 0.54 | 0.62 | 0.65 | 0.80 | 1.00 |
