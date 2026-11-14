# Does the hidden state before reasoning (A) encode the judge's belief in the candidate's answer?

belief = share of 7 fresh own solves reaching the candidate's answer. Probes on the hidden state at A, folds = whole questions, 95% intervals resample questions. 'Believed' = at least 4 of 7; 'never' = 0 of 7.


## qwen3.5-4b, rb2math (688 candidates, 506 wrong; wrong & believed 61, wrong & never 406)

### 1. Belief probe by layer (out-of-fold Spearman with the real belief)

| layer | all candidates | wrong candidates only |
|---|---|---|
| 0 | -0.07 | -0.14 |
| 2 | 0.30 | 0.17 |
| 4 | 0.34 | 0.18 |
| 6 | 0.32 | 0.14 |
| 8 | 0.33 | 0.14 |
| 10 | 0.35 | 0.12 |
| 12 | 0.38 | 0.14 |
| 14 | 0.39 | 0.13 |
| 16 | 0.47 | 0.26 |
| 18 | 0.48 | 0.24 |
| 20 | 0.49 | 0.27 |
| 22 | 0.49 | 0.28 |
| 24 | 0.49 | 0.26 |
| 26 | 0.49 | 0.26 |
| 28 | 0.49 | 0.24 |
| 30 | 0.49 | 0.25 |
| 32 | 0.50 | 0.25 |

### 2. Wrong candidates: telling believed from never-reached (best belief layer = 32)

| signal at A | AUROC |
|---|---|
| belief probe | 0.74 [0.67, 0.81] |
| correctness probe ('is this right?') | 0.60 [0.51, 0.70] |
| verdict at A (margin) | 0.65 [0.57, 0.73] |

### 3. Wrong candidates: does A foresee acceptance at the verdict (C)?

| signal at A | AUROC for accepted at C |
|---|---|
| verdict at A | 0.89 [0.86, 0.92] |
| belief probe | 0.87 [0.84, 0.91] |
| verdict at A + belief probe | 0.89 [0.86, 0.92] |
| real belief (7 solves; not available at A) | 0.61 [0.56, 0.65] |

## qwen3.5-4b, judgebench (508 candidates, 181 wrong; wrong & believed 49, wrong & never 70)

### 1. Belief probe by layer (out-of-fold Spearman with the real belief)

| layer | all candidates | wrong candidates only |
|---|---|---|
| 0 | -0.09 | -0.01 |
| 2 | 0.43 | -0.00 |
| 4 | 0.42 | -0.06 |
| 6 | 0.43 | -0.07 |
| 8 | 0.47 | -0.05 |
| 10 | 0.45 | -0.06 |
| 12 | 0.48 | -0.06 |
| 14 | 0.48 | -0.01 |
| 16 | 0.45 | -0.02 |
| 18 | 0.47 | 0.04 |
| 20 | 0.49 | 0.10 |
| 22 | 0.50 | 0.11 |
| 24 | 0.49 | 0.10 |
| 26 | 0.49 | 0.09 |
| 28 | 0.50 | 0.09 |
| 30 | 0.51 | 0.08 |
| 32 | 0.50 | 0.06 |

### 2. Wrong candidates: telling believed from never-reached (best belief layer = 30)

| signal at A | AUROC |
|---|---|
| belief probe | 0.55 [0.45, 0.66] |
| correctness probe ('is this right?') | 0.39 [0.29, 0.49] |
| verdict at A (margin) | 0.61 [0.50, 0.71] |

### 3. Wrong candidates: does A foresee acceptance at the verdict (C)?

| signal at A | AUROC for accepted at C |
|---|---|
| verdict at A | 0.78 [0.71, 0.85] |
| belief probe | 0.41 [0.32, 0.49] |
| verdict at A + belief probe | 0.78 [0.71, 0.84] |
| real belief (7 solves; not available at A) | 0.65 [0.56, 0.72] |

## qwen3.5-9b, rb2math (689 candidates, 507 wrong; wrong & believed 59, wrong & never 424)

### 1. Belief probe by layer (out-of-fold Spearman with the real belief)

| layer | all candidates | wrong candidates only |
|---|---|---|
| 0 | -0.06 | -0.06 |
| 2 | 0.31 | 0.13 |
| 4 | 0.38 | 0.22 |
| 6 | 0.39 | 0.22 |
| 8 | 0.39 | 0.19 |
| 10 | 0.41 | 0.22 |
| 12 | 0.39 | 0.16 |
| 14 | 0.40 | 0.20 |
| 16 | 0.45 | 0.26 |
| 18 | 0.47 | 0.28 |
| 20 | 0.50 | 0.30 |
| 22 | 0.50 | 0.30 |
| 24 | 0.51 | 0.29 |
| 26 | 0.50 | 0.28 |
| 28 | 0.50 | 0.27 |
| 30 | 0.50 | 0.28 |
| 32 | 0.51 | 0.27 |

### 2. Wrong candidates: telling believed from never-reached (best belief layer = 32)

| signal at A | AUROC |
|---|---|
| belief probe | 0.74 [0.67, 0.81] |
| correctness probe ('is this right?') | 0.59 [0.51, 0.67] |
| verdict at A (margin) | 0.71 [0.63, 0.77] |

### 3. Wrong candidates: does A foresee acceptance at the verdict (C)?

| signal at A | AUROC for accepted at C |
|---|---|
| verdict at A | 0.87 [0.83, 0.90] |
| belief probe | 0.85 [0.81, 0.89] |
| verdict at A + belief probe | 0.86 [0.82, 0.89] |
| real belief (7 solves; not available at A) | 0.66 [0.61, 0.71] |

## qwen3.5-9b, judgebench (501 candidates, 108 wrong; wrong & believed 42, wrong & never 42)

### 1. Belief probe by layer (out-of-fold Spearman with the real belief)

| layer | all candidates | wrong candidates only |
|---|---|---|
| 0 | -0.05 | 0.01 |
| 2 | 0.40 | 0.01 |
| 4 | 0.42 | -0.02 |
| 6 | 0.43 | 0.02 |
| 8 | 0.44 | -0.02 |
| 10 | 0.44 | -0.07 |
| 12 | 0.46 | 0.05 |
| 14 | 0.48 | 0.09 |
| 16 | 0.46 | 0.07 |
| 18 | 0.47 | 0.01 |
| 20 | 0.46 | -0.02 |
| 22 | 0.47 | -0.01 |
| 24 | 0.46 | 0.05 |
| 26 | 0.46 | 0.05 |
| 28 | 0.47 | 0.08 |
| 30 | 0.48 | 0.04 |
| 32 | 0.47 | 0.01 |

### 2. Wrong candidates: telling believed from never-reached (best belief layer = 30)

| signal at A | AUROC |
|---|---|
| belief probe | 0.51 [0.39, 0.63] |
| correctness probe ('is this right?') | 0.40 [0.28, 0.53] |
| verdict at A (margin) | 0.61 [0.49, 0.73] |

### 3. Wrong candidates: does A foresee acceptance at the verdict (C)?

| signal at A | AUROC for accepted at C |
|---|---|
| verdict at A | 0.65 [0.55, 0.76] |
| belief probe | 0.59 [0.48, 0.69] |
| verdict at A + belief probe | 0.65 [0.54, 0.75] |
| real belief (7 solves; not available at A) | 0.71 [0.60, 0.82] |
