# Where is the judge's belief readable? Position x layer, chosen on validation folds

Ridge probe hidden -> belief (share of 7 own solves reaching the candidate's answer), trained on all candidates. Score: AUROC among WRONG candidates, believed (>= 4/7) vs never reached (0/7). Folds = whole questions. 95% intervals resample questions.


## qwen3.5-9b, rb2math: 689 candidates; wrong & believed 59, wrong & never 424

### 1. Cross-validated score by position and layer (every 4th layer shown)

| position | L4 | L8 | L12 | L16 | L20 | L24 | L28 | L32 | best layer |
|---|---|---|---|---|---|---|---|---|---|
| A | 0.71 | 0.69 | 0.66 | 0.71 | 0.76 | 0.75 | 0.73 | 0.74 | L21: 0.77 |
| 25 | 0.73 | 0.74 | 0.73 | 0.79 | 0.78 | 0.76 | 0.75 | 0.73 | L17: 0.79 |
| 50 | 0.68 | 0.69 | 0.68 | 0.78 | 0.81 | 0.81 | 0.81 | 0.80 | L28: 0.81 |
| 75 | 0.74 | 0.74 | 0.79 | 0.84 | 0.87 | 0.85 | 0.86 | 0.86 | L20: 0.87 |
| C | 0.82 | 0.84 | 0.85 | 0.87 | 0.88 | 0.86 | 0.87 | 0.86 | L20: 0.88 |

### 2. Held-out (nested) score: 0.86 [0.81, 0.90]

Cells chosen in the 5 outer folds: C/L21, C/L21, C/L21, C/L17, C/L21

### 3. At C / L21: belief probe vs other signals (wrong candidates, believed vs never)

| signal | AUROC |
|---|---|
| belief probe | 0.87 [0.83, 0.91] |
| correctness probe (same position and layer) | 0.79 [0.72, 0.85] |
| verdict the judge would give at C | 0.82 [0.76, 0.88] |

## qwen3.5-9b, bff: 434 candidates; wrong & believed 39, wrong & never 112

### 1. Cross-validated score by position and layer (every 4th layer shown)

| position | L4 | L8 | L12 | L16 | L20 | L24 | L28 | L32 | best layer |
|---|---|---|---|---|---|---|---|---|---|
| A | 0.51 | 0.59 | 0.66 | 0.76 | 0.80 | 0.83 | 0.82 | 0.82 | L25: 0.83 |
| 25 | 0.70 | 0.68 | 0.69 | 0.71 | 0.77 | 0.78 | 0.77 | 0.77 | L24: 0.78 |
| 50 | 0.74 | 0.73 | 0.77 | 0.78 | 0.83 | 0.81 | 0.83 | 0.82 | L28: 0.83 |
| 75 | 0.73 | 0.73 | 0.76 | 0.78 | 0.81 | 0.82 | 0.82 | 0.82 | L31: 0.82 |
| C | 0.77 | 0.79 | 0.79 | 0.79 | 0.83 | 0.84 | 0.83 | 0.81 | L25: 0.84 |

### 2. Held-out (nested) score: 0.80 [0.71, 0.87]

Cells chosen in the 5 outer folds: 50/L11, C/L25, C/L21, C/L25, C/L25

### 3. At C / L25: belief probe vs other signals (wrong candidates, believed vs never)

| signal | AUROC |
|---|---|
| belief probe | 0.84 [0.77, 0.90] |
| correctness probe (same position and layer) | 0.80 [0.72, 0.87] |
| verdict the judge would give at C | 0.74 [0.63, 0.83] |

## qwen3.5-4b, rb2math: 688 candidates; wrong & believed 61, wrong & never 406

### 1. Cross-validated score by position and layer (every 4th layer shown)

| position | L4 | L8 | L12 | L16 | L20 | L24 | L28 | L32 | best layer |
|---|---|---|---|---|---|---|---|---|---|
| A | 0.68 | 0.66 | 0.69 | 0.75 | 0.75 | 0.75 | 0.74 | 0.74 | L22: 0.76 |
| 25 | 0.70 | 0.70 | 0.72 | 0.71 | 0.69 | 0.71 | 0.71 | 0.70 | L10: 0.73 |
| 50 | 0.69 | 0.66 | 0.72 | 0.75 | 0.74 | 0.75 | 0.75 | 0.75 | L16: 0.75 |
| 75 | 0.73 | 0.71 | 0.74 | 0.77 | 0.76 | 0.76 | 0.77 | 0.76 | L19: 0.77 |
| C | 0.76 | 0.77 | 0.78 | 0.79 | 0.78 | 0.79 | 0.80 | 0.80 | L30: 0.81 |

### 2. Held-out (nested) score: 0.78 [0.72, 0.83]

Cells chosen in the 5 outer folds: C/L29, C/L17, C/L25, C/L27, C/L17

### 3. At C / L17: belief probe vs other signals (wrong candidates, believed vs never)

| signal | AUROC |
|---|---|
| belief probe | 0.78 [0.72, 0.85] |
| correctness probe (same position and layer) | 0.73 [0.64, 0.81] |
| verdict the judge would give at C | 0.76 [0.69, 0.82] |

## qwen3.5-4b, bff: 433 candidates; wrong & believed 37, wrong & never 103

### 1. Cross-validated score by position and layer (every 4th layer shown)

| position | L4 | L8 | L12 | L16 | L20 | L24 | L28 | L32 | best layer |
|---|---|---|---|---|---|---|---|---|---|
| A | 0.47 | 0.56 | 0.67 | 0.75 | 0.76 | 0.74 | 0.75 | 0.75 | L19: 0.79 |
| 25 | 0.67 | 0.64 | 0.65 | 0.68 | 0.69 | 0.66 | 0.66 | 0.64 | L20: 0.69 |
| 50 | 0.63 | 0.62 | 0.65 | 0.69 | 0.72 | 0.71 | 0.70 | 0.71 | L21: 0.73 |
| 75 | 0.69 | 0.69 | 0.73 | 0.74 | 0.73 | 0.72 | 0.74 | 0.72 | L13: 0.75 |
| C | 0.70 | 0.75 | 0.73 | 0.72 | 0.75 | 0.75 | 0.76 | 0.76 | L27: 0.76 |

### 2. Held-out (nested) score: 0.72 [0.63, 0.80]

Cells chosen in the 5 outer folds: A/L19, 75/L27, A/L17, C/L23, A/L19

### 3. At A / L19: belief probe vs other signals (wrong candidates, believed vs never)

| signal | AUROC |
|---|---|
| belief probe | 0.79 [0.71, 0.86] |
| correctness probe (same position and layer) | 0.63 [0.54, 0.73] |
| verdict the judge would give at A | 0.70 [0.60, 0.79] |
