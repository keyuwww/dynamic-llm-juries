# Belief vs correctness axes: qwen3.6-35b-a3b, rb2math

732 answers (183 right). Wrong answers with a belief score: 446; believed (>= 0.57): 9, never reached (0): 422.

## 1. Does each role's correctness axis score believed WRONG answers as more 'right'?

AUROC of the projection on the role's own right-minus-wrong direction (learned on the other half of the questions), believed vs never-reached wrong answers. 0.5 = ignores belief; > 0.5 = treats belief as rightness. Same axis, right vs wrong answers (all), for reference.

| layer | J: belief / right-vs-wrong | G: belief / right-vs-wrong | S: belief / right-vs-wrong | N: belief / right-vs-wrong |
|---|---|---|---|---|
| 0 | 0.50 / 0.50 | 0.55 / 0.57 | 0.50 / 0.50 | 0.50 / 0.50 |
| 2 | 0.67 / 0.68 | 0.62 / 0.60 | 0.63 / 0.68 | 0.63 / 0.73 |
| 4 | 0.62 / 0.69 | 0.64 / 0.61 | 0.61 / 0.71 | 0.70 / 0.74 |
| 6 | 0.60 / 0.71 | 0.62 / 0.61 | 0.58 / 0.75 | 0.74 / 0.73 |
| 8 | 0.55 / 0.73 | 0.58 / 0.62 | 0.59 / 0.76 | 0.64 / 0.65 |
| 10 | 0.56 / 0.75 | 0.61 / 0.64 | 0.52 / 0.76 | 0.50 / 0.75 |
| 12 | 0.51 / 0.67 | 0.63 / 0.64 | 0.47 / 0.76 | 0.46 / 0.72 |
| 14 | 0.54 / 0.69 | 0.61 / 0.65 | 0.45 / 0.77 | 0.48 / 0.74 |
| 16 | 0.53 / 0.77 | 0.57 / 0.66 | 0.47 / 0.81 | 0.51 / 0.78 |
| 18 | 0.52 / 0.80 | 0.56 / 0.70 | 0.43 / 0.82 | 0.47 / 0.79 |
| 20 | 0.52 / 0.85 | 0.55 / 0.75 | 0.46 / 0.83 | 0.44 / 0.81 |
| 22 | 0.52 / 0.84 | 0.56 / 0.76 | 0.52 / 0.84 | 0.44 / 0.81 |
| 24 | 0.56 / 0.86 | 0.54 / 0.76 | 0.56 / 0.87 | 0.44 / 0.82 |
| 26 | 0.56 / 0.85 | 0.53 / 0.78 | 0.51 / 0.87 | 0.47 / 0.83 |
| 28 | 0.55 / 0.86 | 0.53 / 0.79 | 0.50 / 0.87 | 0.51 / 0.85 |
| 30 | 0.53 / 0.87 | 0.53 / 0.82 | 0.56 / 0.86 | 0.52 / 0.86 |
| 32 | 0.50 / 0.88 | 0.52 / 0.82 | 0.58 / 0.88 | 0.54 / 0.85 |
| 34 | 0.60 / 0.90 | 0.52 / 0.83 | 0.62 / 0.89 | 0.54 / 0.85 |
| 36 | 0.63 / 0.90 | 0.53 / 0.82 | 0.63 / 0.89 | 0.53 / 0.85 |
| 38 | 0.64 / 0.90 | 0.54 / 0.81 | 0.68 / 0.87 | 0.52 / 0.85 |
| 40 | 0.65 / 0.89 | 0.52 / 0.79 | 0.69 / 0.86 | 0.57 / 0.84 |

## 2. Is belief readable in each role? (probe, believed vs never-reached wrong answers)

| role | layer (role's best right-vs-wrong) | probe AUROC | cosine(belief dir, own correctness dir) | cosine(belief dir, judge correctness dir) |
|---|---|---|---|---|
| J judge (VERDICT:) | 36 | 0.56 | +0.36 | +0.36 |
| G generate (end of answer) | 34 | 0.30 | +0.06 | -0.02 |
| S self-check (VERDICT:) | 34 | 0.38 | +0.42 | +0.33 |
| N neutral (FINAL:) | 30 | 0.35 | +0.16 | -0.03 |

# Belief vs correctness axes: qwen3.6-35b-a3b, bff

459 answers (256 right). Wrong answers with a belief score: 182; believed (>= 0.57): 32, never reached (0): 128.

## 1. Does each role's correctness axis score believed WRONG answers as more 'right'?

AUROC of the projection on the role's own right-minus-wrong direction (learned on the other half of the questions), believed vs never-reached wrong answers. 0.5 = ignores belief; > 0.5 = treats belief as rightness. Same axis, right vs wrong answers (all), for reference.

| layer | J: belief / right-vs-wrong | G: belief / right-vs-wrong | S: belief / right-vs-wrong | N: belief / right-vs-wrong |
|---|---|---|---|---|
| 0 | 0.50 / 0.50 | 0.46 / 0.47 | 0.50 / 0.50 | 0.50 / 0.50 |
| 2 | 0.41 / 0.52 | 0.51 / 0.47 | 0.44 / 0.47 | 0.48 / 0.50 |
| 4 | 0.40 / 0.49 | 0.47 / 0.47 | 0.44 / 0.47 | 0.47 / 0.54 |
| 6 | 0.39 / 0.48 | 0.47 / 0.49 | 0.48 / 0.49 | 0.46 / 0.51 |
| 8 | 0.48 / 0.48 | 0.46 / 0.45 | 0.51 / 0.49 | 0.54 / 0.51 |
| 10 | 0.43 / 0.47 | 0.44 / 0.45 | 0.48 / 0.48 | 0.50 / 0.50 |
| 12 | 0.42 / 0.50 | 0.43 / 0.46 | 0.49 / 0.47 | 0.51 / 0.49 |
| 14 | 0.36 / 0.49 | 0.42 / 0.46 | 0.50 / 0.51 | 0.47 / 0.48 |
| 16 | 0.47 / 0.52 | 0.40 / 0.46 | 0.53 / 0.50 | 0.47 / 0.46 |
| 18 | 0.46 / 0.52 | 0.39 / 0.47 | 0.49 / 0.49 | 0.49 / 0.46 |
| 20 | 0.44 / 0.51 | 0.39 / 0.47 | 0.44 / 0.48 | 0.44 / 0.46 |
| 22 | 0.45 / 0.50 | 0.41 / 0.48 | 0.45 / 0.48 | 0.42 / 0.47 |
| 24 | 0.47 / 0.48 | 0.42 / 0.49 | 0.46 / 0.48 | 0.48 / 0.48 |
| 26 | 0.43 / 0.50 | 0.44 / 0.49 | 0.44 / 0.49 | 0.50 / 0.50 |
| 28 | 0.47 / 0.53 | 0.47 / 0.48 | 0.49 / 0.55 | 0.54 / 0.52 |
| 30 | 0.51 / 0.54 | 0.44 / 0.50 | 0.46 / 0.51 | 0.54 / 0.53 |
| 32 | 0.56 / 0.54 | 0.44 / 0.51 | 0.50 / 0.53 | 0.55 / 0.54 |
| 34 | 0.63 / 0.56 | 0.45 / 0.49 | 0.60 / 0.56 | 0.55 / 0.56 |
| 36 | 0.66 / 0.54 | 0.46 / 0.49 | 0.62 / 0.55 | 0.55 / 0.53 |
| 38 | 0.62 / 0.54 | 0.42 / 0.49 | 0.63 / 0.56 | 0.55 / 0.54 |
| 40 | 0.62 / 0.55 | 0.40 / 0.48 | 0.65 / 0.56 | 0.57 / 0.54 |

## 2. Is belief readable in each role? (probe, believed vs never-reached wrong answers)

| role | layer (role's best right-vs-wrong) | probe AUROC | cosine(belief dir, own correctness dir) | cosine(belief dir, judge correctness dir) |
|---|---|---|---|---|
| J judge (VERDICT:) | 34 | 0.73 | +0.72 | +0.72 |
| G generate (end of answer) | 32 | 0.60 | +0.22 | -0.03 |
| S self-check (VERDICT:) | 38 | 0.78 | +0.95 | +0.64 |
| N neutral (FINAL:) | 34 | 0.64 | +0.44 | -0.05 |

# Belief vs correctness axes: qwen3.6-35b-a3b, bbeh

2012 answers (959 right). Wrong answers with a belief score: 1053; believed (>= 0.50): 250, never reached (0): 601.

## 1. Does each role's correctness axis score believed WRONG answers as more 'right'?

AUROC of the projection on the role's own right-minus-wrong direction (learned on the other half of the questions), believed vs never-reached wrong answers. 0.5 = ignores belief; > 0.5 = treats belief as rightness. Same axis, right vs wrong answers (all), for reference.

| layer | J: belief / right-vs-wrong | G: belief / right-vs-wrong | S: belief / right-vs-wrong | N: belief / right-vs-wrong |
|---|---|---|---|---|
| 0 | 0.50 / 0.50 | 0.54 / 0.57 | 0.50 / 0.50 | 0.50 / 0.50 |
| 2 | 0.55 / 0.56 | 0.56 / 0.56 | 0.54 / 0.56 | 0.53 / 0.56 |
| 4 | 0.51 / 0.55 | 0.59 / 0.58 | 0.53 / 0.56 | 0.53 / 0.57 |
| 6 | 0.49 / 0.55 | 0.60 / 0.59 | 0.53 / 0.57 | 0.54 / 0.58 |
| 8 | 0.49 / 0.56 | 0.59 / 0.59 | 0.53 / 0.55 | 0.55 / 0.57 |
| 10 | 0.51 / 0.56 | 0.60 / 0.58 | 0.54 / 0.56 | 0.54 / 0.57 |
| 12 | 0.53 / 0.57 | 0.60 / 0.58 | 0.52 / 0.54 | 0.53 / 0.55 |
| 14 | 0.52 / 0.57 | 0.61 / 0.58 | 0.50 / 0.54 | 0.51 / 0.55 |
| 16 | 0.52 / 0.55 | 0.61 / 0.57 | 0.54 / 0.55 | 0.55 / 0.54 |
| 18 | 0.56 / 0.55 | 0.61 / 0.57 | 0.57 / 0.56 | 0.54 / 0.54 |
| 20 | 0.60 / 0.57 | 0.59 / 0.57 | 0.59 / 0.57 | 0.59 / 0.55 |
| 22 | 0.59 / 0.57 | 0.59 / 0.57 | 0.60 / 0.57 | 0.59 / 0.55 |
| 24 | 0.60 / 0.58 | 0.60 / 0.57 | 0.59 / 0.56 | 0.59 / 0.55 |
| 26 | 0.62 / 0.58 | 0.59 / 0.57 | 0.60 / 0.57 | 0.61 / 0.55 |
| 28 | 0.62 / 0.57 | 0.59 / 0.56 | 0.60 / 0.56 | 0.61 / 0.56 |
| 30 | 0.64 / 0.57 | 0.60 / 0.56 | 0.60 / 0.55 | 0.62 / 0.56 |
| 32 | 0.65 / 0.56 | 0.60 / 0.55 | 0.57 / 0.53 | 0.62 / 0.55 |
| 34 | 0.65 / 0.56 | 0.60 / 0.56 | 0.61 / 0.54 | 0.61 / 0.56 |
| 36 | 0.65 / 0.56 | 0.62 / 0.56 | 0.63 / 0.54 | 0.57 / 0.57 |
| 38 | 0.65 / 0.56 | 0.64 / 0.56 | 0.64 / 0.54 | 0.56 / 0.57 |
| 40 | 0.63 / 0.55 | 0.63 / 0.55 | 0.64 / 0.54 | 0.55 / 0.58 |

## 2. Is belief readable in each role? (probe, believed vs never-reached wrong answers)

| role | layer (role's best right-vs-wrong) | probe AUROC | cosine(belief dir, own correctness dir) | cosine(belief dir, judge correctness dir) |
|---|---|---|---|---|
| J judge (VERDICT:) | 24 | 0.81 | +0.77 | +0.77 |
| G generate (end of answer) | 6 | 0.74 | +0.60 | -0.04 |
| S self-check (VERDICT:) | 26 | 0.80 | +0.74 | +0.43 |
| N neutral (FINAL:) | 40 | 0.83 | +0.50 | +0.07 |

