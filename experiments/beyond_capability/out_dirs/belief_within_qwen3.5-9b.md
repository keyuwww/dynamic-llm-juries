# Believed vs never-reached WRONG answers to the same question — qwen3.5-9b, BBEH, audited labels

Pairwise AUROC within question (0.5 = no preference for the believed answer). 'axis' = the role's correctness direction (cross-fitted over question halves, mean of 20 splits; best layer = highest mean right-vs-wrong AUROC); 'verdict' = the model's own CORRECT-minus-INCORRECT log-odds at that position.

| role | questions with both | pairs | axis, best layer (layer) | 95% CI | axis, mean over the top-third layers | verdict log-odds | 95% CI | belief direction: best layer (layer), mean over the correctness top third |
|---|---|---|---|---|---|---|---|---|
| J judge (VERDICT:) | 39 | 135 | 0.64 (32) | [0.51, 0.76] | 0.60 | 0.69 | [0.57, 0.80] | 0.66 (32), top-third 0.60 |
| N neutral (FINAL:) | 39 | 135 | 0.60 (30) | [0.45, 0.71] | 0.60 | – | – | 0.65 (20), top-third 0.59 |
| S self-check (VERDICT:) | 39 | 135 | 0.64 (18) | [0.53, 0.80] | 0.63 | 0.63 | [0.51, 0.74] | 0.76 (26), top-third 0.66 |
| G generate (end of answer) | 39 | 135 | 0.67 (8) | [0.56, 0.78] | 0.66 | – | – | 0.72 (6), top-third 0.69 |
| JX judge after explanation | 39 | 135 | 0.71 (22) | [0.59, 0.84] | 0.71 | 0.70 | [0.59, 0.80] | 0.71 (30), top-third 0.69 |
| JT judge after thinking | 3 | 3 | 0.67 (32) | [0.00, 1.00] | 0.67 | 1.00 | [1.00, 1.00] | 0.75 (28), top-third 0.65 |

## Pairwise AUROC of the correctness axis by layer (mean over splits)

| layer | J | N | S | G | JX | JT |
|---|---|---|---|---|---|---|
| 0 | 0.50 | 0.50 | 0.50 | 0.61 | 0.50 | 0.50 |
| 2 | 0.54 | 0.54 | 0.59 | 0.59 | 0.50 | 0.53 |
| 4 | 0.60 | 0.53 | 0.50 | 0.65 | 0.62 | 0.77 |
| 6 | 0.59 | 0.53 | 0.53 | 0.68 | 0.62 | 0.85 |
| 8 | 0.54 | 0.57 | 0.53 | 0.67 | 0.63 | 0.83 |
| 10 | 0.46 | 0.63 | 0.51 | 0.64 | 0.64 | 0.75 |
| 12 | 0.58 | 0.59 | 0.50 | 0.65 | 0.72 | 0.60 |
| 14 | 0.60 | 0.57 | 0.52 | 0.65 | 0.71 | 0.67 |
| 16 | 0.58 | 0.56 | 0.58 | 0.60 | 0.68 | 0.67 |
| 18 | 0.66 | 0.53 | 0.64 | 0.58 | 0.70 | 0.67 |
| 20 | 0.68 | 0.61 | 0.71 | 0.60 | 0.69 | 0.67 |
| 22 | 0.63 | 0.61 | 0.73 | 0.58 | 0.71 | 0.67 |
| 24 | 0.63 | 0.60 | 0.75 | 0.56 | 0.71 | 0.67 |
| 26 | 0.63 | 0.59 | 0.74 | 0.60 | 0.72 | 0.67 |
| 28 | 0.67 | 0.61 | 0.73 | 0.61 | 0.70 | 0.92 |
| 30 | 0.66 | 0.60 | 0.72 | 0.61 | 0.71 | 0.92 |
| 32 | 0.64 | 0.58 | 0.69 | 0.63 | 0.70 | 0.67 |
