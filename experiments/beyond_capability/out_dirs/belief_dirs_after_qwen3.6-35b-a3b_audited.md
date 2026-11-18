
# Roles J, N, JX

# Belief vs correctness axes: qwen3.6-35b-a3b, bbeh

1851 answers (956 right). Wrong answers with a belief score: 895; believed (>= 0.50): 122, never reached (0): 597.

## 1. Does each role's correctness axis score believed WRONG answers as more 'right'?

AUROC of the projection on the role's own right-minus-wrong direction (learned on the other half of the questions), believed vs never-reached wrong answers. 0.5 = ignores belief; > 0.5 = treats belief as rightness. Same axis, right vs wrong answers (all), for reference.

| layer | J: belief / right-vs-wrong | N: belief / right-vs-wrong | JX: belief / right-vs-wrong |
|---|---|---|---|
| 0 | 0.50 / 0.50 | 0.50 / 0.50 | 0.50 / 0.50 |
| 2 | 0.55 / 0.55 | 0.53 / 0.56 | 0.62 / 0.58 |
| 4 | 0.51 / 0.54 | 0.53 / 0.55 | 0.60 / 0.57 |
| 6 | 0.48 / 0.54 | 0.52 / 0.57 | 0.62 / 0.60 |
| 8 | 0.49 / 0.55 | 0.55 / 0.57 | 0.65 / 0.62 |
| 10 | 0.51 / 0.55 | 0.53 / 0.56 | 0.67 / 0.62 |
| 12 | 0.53 / 0.57 | 0.57 / 0.55 | 0.67 / 0.61 |
| 14 | 0.50 / 0.56 | 0.53 / 0.55 | 0.70 / 0.64 |
| 16 | 0.52 / 0.54 | 0.57 / 0.53 | 0.71 / 0.64 |
| 18 | 0.55 / 0.55 | 0.56 / 0.54 | 0.73 / 0.65 |
| 20 | 0.61 / 0.57 | 0.59 / 0.56 | 0.73 / 0.65 |
| 22 | 0.61 / 0.58 | 0.59 / 0.56 | 0.73 / 0.65 |
| 24 | 0.61 / 0.58 | 0.59 / 0.56 | 0.73 / 0.65 |
| 26 | 0.63 / 0.58 | 0.61 / 0.56 | 0.72 / 0.65 |
| 28 | 0.62 / 0.58 | 0.61 / 0.57 | 0.73 / 0.65 |
| 30 | 0.63 / 0.57 | 0.64 / 0.57 | 0.72 / 0.65 |
| 32 | 0.62 / 0.57 | 0.64 / 0.56 | 0.73 / 0.65 |
| 34 | 0.63 / 0.57 | 0.63 / 0.56 | 0.73 / 0.64 |
| 36 | 0.64 / 0.56 | 0.61 / 0.56 | 0.73 / 0.64 |
| 38 | 0.63 / 0.55 | 0.60 / 0.57 | 0.73 / 0.64 |
| 40 | 0.63 / 0.54 | 0.58 / 0.58 | 0.74 / 0.65 |

## 2. Is belief readable in each role? (probe, believed vs never-reached wrong answers)

| role | layer (role's best right-vs-wrong) | probe AUROC | cosine(belief dir, own correctness dir) | cosine(belief dir, judge correctness dir) |
|---|---|---|---|---|
| J judge (VERDICT:) | 24 | 0.75 | +0.60 | +0.60 |
| N neutral (FINAL:) | 40 | 0.80 | +0.32 | +0.03 |
| JX judge after its written explanation (VERDICT:) | 28 | 0.88 | +0.96 | +0.20 |

## 3. Ceilings and the verdict-lean control (each role's best layer)

Ceiling = cosine of the same direction built on two random halves of the questions. Lean = the model's own verdict lean (CORRECT minus INCORRECT by its margin); only roles that give a verdict have one.

Disjoint = belief direction from one half of the questions vs correctness direction from the other half (and the reverse, averaged): no answers shared, so shared never-reached answers cannot inflate it.

| role | cos(belief, correctness) | **disjoint halves** | ceiling belief | ceiling correctness | cos(belief, lean) | cos(correctness, lean) | cos(belief, correctness) with lean removed |
|---|---|---|---|---|---|---|---|
| J judge (VERDICT:) | +0.60 | **+0.41** | 0.54 | 0.59 | +0.18 | +0.21 | +0.59 |
| N neutral (FINAL:) | +0.32 | **+0.25** | 0.42 | 0.51 | – | – | – |
| JX judge after its written explanation (VERDICT:) | +0.96 | **+0.91** | 0.89 | 0.94 | +0.95 | +0.94 | +0.61 |


# Roles J, N, JT

# Belief vs correctness axes: qwen3.6-35b-a3b, bbeh

520 answers (288 right). Wrong answers with a belief score: 232; believed (>= 0.50): 34, never reached (0): 154.

## 1. Does each role's correctness axis score believed WRONG answers as more 'right'?

AUROC of the projection on the role's own right-minus-wrong direction (learned on the other half of the questions), believed vs never-reached wrong answers. 0.5 = ignores belief; > 0.5 = treats belief as rightness. Same axis, right vs wrong answers (all), for reference.

| layer | J: belief / right-vs-wrong | N: belief / right-vs-wrong | JT: belief / right-vs-wrong |
|---|---|---|---|
| 0 | 0.50 / 0.50 | 0.50 / 0.50 | 0.50 / 0.50 |
| 2 | 0.51 / 0.50 | 0.56 / 0.51 | 0.63 / 0.55 |
| 4 | 0.51 / 0.53 | 0.53 / 0.52 | 0.66 / 0.57 |
| 6 | 0.51 / 0.51 | 0.53 / 0.53 | 0.66 / 0.59 |
| 8 | 0.55 / 0.52 | 0.63 / 0.55 | 0.71 / 0.68 |
| 10 | 0.59 / 0.53 | 0.59 / 0.53 | 0.68 / 0.66 |
| 12 | 0.51 / 0.49 | 0.64 / 0.50 | 0.67 / 0.66 |
| 14 | 0.51 / 0.50 | 0.60 / 0.51 | 0.66 / 0.67 |
| 16 | 0.50 / 0.50 | 0.63 / 0.52 | 0.66 / 0.68 |
| 18 | 0.50 / 0.51 | 0.60 / 0.50 | 0.64 / 0.66 |
| 20 | 0.61 / 0.54 | 0.58 / 0.52 | 0.66 / 0.69 |
| 22 | 0.61 / 0.53 | 0.62 / 0.56 | 0.65 / 0.65 |
| 24 | 0.62 / 0.54 | 0.59 / 0.55 | 0.62 / 0.62 |
| 26 | 0.61 / 0.55 | 0.57 / 0.57 | 0.63 / 0.61 |
| 28 | 0.64 / 0.56 | 0.60 / 0.58 | 0.64 / 0.62 |
| 30 | 0.67 / 0.58 | 0.64 / 0.60 | 0.65 / 0.65 |
| 32 | 0.70 / 0.61 | 0.63 / 0.61 | 0.70 / 0.70 |
| 34 | 0.70 / 0.65 | 0.66 / 0.62 | 0.73 / 0.70 |
| 36 | 0.71 / 0.65 | 0.60 / 0.57 | 0.71 / 0.68 |
| 38 | 0.70 / 0.64 | 0.60 / 0.58 | 0.72 / 0.69 |
| 40 | 0.69 / 0.63 | 0.59 / 0.54 | 0.75 / 0.71 |

## 2. Is belief readable in each role? (probe, believed vs never-reached wrong answers)

| role | layer (role's best right-vs-wrong) | probe AUROC | cosine(belief dir, own correctness dir) | cosine(belief dir, judge correctness dir) |
|---|---|---|---|---|
| J judge (VERDICT:) | 34 | 0.79 | +0.55 | +0.55 |
| N neutral (FINAL:) | 34 | 0.80 | +0.36 | +0.08 |
| JT judge after thinking (VERDICT:) | 40 | 0.87 | +0.99 | +0.45 |

## 3. Ceilings and the verdict-lean control (each role's best layer)

Ceiling = cosine of the same direction built on two random halves of the questions. Lean = the model's own verdict lean (CORRECT minus INCORRECT by its margin); only roles that give a verdict have one.

Disjoint = belief direction from one half of the questions vs correctness direction from the other half (and the reverse, averaged): no answers shared, so shared never-reached answers cannot inflate it.

| role | cos(belief, correctness) | **disjoint halves** | ceiling belief | ceiling correctness | cos(belief, lean) | cos(correctness, lean) | cos(belief, correctness) with lean removed |
|---|---|---|---|---|---|---|---|
| J judge (VERDICT:) | +0.55 | **+0.41** | 0.28 | 0.67 | +0.82 | +0.66 | +0.02 |
| N neutral (FINAL:) | +0.36 | **+0.28** | 0.23 | 0.34 | – | – | – |
| JT judge after thinking (VERDICT:) | +0.99 | **+0.99** | 0.97 | 0.99 | +1.00 | +1.00 | -0.20 |

