
# Roles J, N, JX

# Belief vs correctness axes: qwen3.5-9b, bbeh

1860 answers (952 right). Wrong answers with a belief score: 908; believed (>= 0.50): 122, never reached (0): 575.

## 1. Does each role's correctness axis score believed WRONG answers as more 'right'?

AUROC of the projection on the role's own right-minus-wrong direction (learned on the other half of the questions), believed vs never-reached wrong answers. 0.5 = ignores belief; > 0.5 = treats belief as rightness. Same axis, right vs wrong answers (all), for reference.

| layer | J: belief / right-vs-wrong | N: belief / right-vs-wrong | JX: belief / right-vs-wrong |
|---|---|---|---|
| 0 | 0.50 / 0.50 | 0.50 / 0.50 | 0.50 / 0.50 |
| 2 | 0.53 / 0.56 | 0.51 / 0.55 | 0.52 / 0.52 |
| 4 | 0.57 / 0.57 | 0.53 / 0.56 | 0.56 / 0.55 |
| 6 | 0.52 / 0.56 | 0.53 / 0.55 | 0.57 / 0.55 |
| 8 | 0.54 / 0.55 | 0.54 / 0.55 | 0.59 / 0.57 |
| 10 | 0.54 / 0.55 | 0.58 / 0.55 | 0.60 / 0.57 |
| 12 | 0.60 / 0.55 | 0.59 / 0.58 | 0.63 / 0.57 |
| 14 | 0.62 / 0.56 | 0.62 / 0.59 | 0.64 / 0.59 |
| 16 | 0.61 / 0.57 | 0.62 / 0.58 | 0.67 / 0.60 |
| 18 | 0.65 / 0.57 | 0.63 / 0.58 | 0.68 / 0.61 |
| 20 | 0.68 / 0.57 | 0.65 / 0.59 | 0.67 / 0.61 |
| 22 | 0.66 / 0.57 | 0.65 / 0.59 | 0.67 / 0.62 |
| 24 | 0.66 / 0.58 | 0.63 / 0.59 | 0.66 / 0.61 |
| 26 | 0.66 / 0.58 | 0.62 / 0.59 | 0.66 / 0.61 |
| 28 | 0.67 / 0.58 | 0.59 / 0.60 | 0.66 / 0.61 |
| 30 | 0.66 / 0.57 | 0.59 / 0.60 | 0.65 / 0.61 |
| 32 | 0.66 / 0.58 | 0.59 / 0.60 | 0.66 / 0.61 |

## 2. Is belief readable in each role? (probe, believed vs never-reached wrong answers)

| role | layer (role's best right-vs-wrong) | probe AUROC | cosine(belief dir, own correctness dir) | cosine(belief dir, judge correctness dir) |
|---|---|---|---|---|
| J judge (VERDICT:) | 32 | 0.77 | +0.82 | +0.82 |
| N neutral (FINAL:) | 28 | 0.77 | +0.47 | +0.11 |
| JX judge after its written explanation (VERDICT:) | 22 | 0.79 | +0.96 | +0.43 |

## 3. Ceilings and the verdict-lean control (each role's best layer)

Ceiling = cosine of the same direction built on two random halves of the questions. Lean = the model's own verdict lean (CORRECT minus INCORRECT by its margin); only roles that give a verdict have one.

Disjoint = belief direction from one half of the questions vs correctness direction from the other half (and the reverse, averaged): no answers shared, so shared never-reached answers cannot inflate it.

| role | cos(belief, correctness) | **disjoint halves** | ceiling belief | ceiling correctness | cos(belief, lean) | cos(correctness, lean) | cos(belief, correctness) with lean removed |
|---|---|---|---|---|---|---|---|
| J judge (VERDICT:) | +0.82 | **+0.69** | 0.86 | 0.61 | +0.59 | +0.31 | +0.83 |
| N neutral (FINAL:) | +0.47 | **+0.36** | 0.48 | 0.75 | – | – | – |
| JX judge after its written explanation (VERDICT:) | +0.96 | **+0.88** | 0.93 | 0.92 | +0.88 | +0.94 | +0.79 |


# Roles J, N, JT

# Belief vs correctness axes: qwen3.5-9b, bbeh

533 answers (304 right). Wrong answers with a belief score: 229; believed (>= 0.50): 34, never reached (0): 145.

## 1. Does each role's correctness axis score believed WRONG answers as more 'right'?

AUROC of the projection on the role's own right-minus-wrong direction (learned on the other half of the questions), believed vs never-reached wrong answers. 0.5 = ignores belief; > 0.5 = treats belief as rightness. Same axis, right vs wrong answers (all), for reference.

| layer | J: belief / right-vs-wrong | N: belief / right-vs-wrong | JT: belief / right-vs-wrong |
|---|---|---|---|
| 0 | 0.50 / 0.50 | 0.50 / 0.50 | 0.50 / 0.50 |
| 2 | 0.52 / 0.53 | 0.46 / 0.52 | 0.59 / 0.53 |
| 4 | 0.59 / 0.50 | 0.53 / 0.46 | 0.62 / 0.55 |
| 6 | 0.57 / 0.51 | 0.56 / 0.52 | 0.68 / 0.58 |
| 8 | 0.53 / 0.51 | 0.63 / 0.55 | 0.68 / 0.61 |
| 10 | 0.53 / 0.53 | 0.60 / 0.54 | 0.64 / 0.63 |
| 12 | 0.57 / 0.51 | 0.58 / 0.58 | 0.64 / 0.66 |
| 14 | 0.56 / 0.50 | 0.60 / 0.58 | 0.65 / 0.67 |
| 16 | 0.59 / 0.50 | 0.65 / 0.57 | 0.65 / 0.67 |
| 18 | 0.59 / 0.54 | 0.64 / 0.59 | 0.65 / 0.67 |
| 20 | 0.59 / 0.54 | 0.67 / 0.60 | 0.66 / 0.66 |
| 22 | 0.56 / 0.54 | 0.67 / 0.61 | 0.66 / 0.65 |
| 24 | 0.55 / 0.57 | 0.61 / 0.60 | 0.63 / 0.65 |
| 26 | 0.57 / 0.58 | 0.61 / 0.59 | 0.62 / 0.66 |
| 28 | 0.58 / 0.57 | 0.57 / 0.60 | 0.63 / 0.66 |
| 30 | 0.57 / 0.58 | 0.57 / 0.59 | 0.63 / 0.66 |
| 32 | 0.56 / 0.57 | 0.66 / 0.57 | 0.64 / 0.68 |

## 2. Is belief readable in each role? (probe, believed vs never-reached wrong answers)

| role | layer (role's best right-vs-wrong) | probe AUROC | cosine(belief dir, own correctness dir) | cosine(belief dir, judge correctness dir) |
|---|---|---|---|---|
| J judge (VERDICT:) | 26 | 0.85 | +0.59 | +0.59 |
| N neutral (FINAL:) | 22 | 0.82 | +0.65 | +0.10 |
| JT judge after thinking (VERDICT:) | 32 | 0.82 | +0.99 | +0.32 |

## 3. Ceilings and the verdict-lean control (each role's best layer)

Ceiling = cosine of the same direction built on two random halves of the questions. Lean = the model's own verdict lean (CORRECT minus INCORRECT by its margin); only roles that give a verdict have one.

Disjoint = belief direction from one half of the questions vs correctness direction from the other half (and the reverse, averaged): no answers shared, so shared never-reached answers cannot inflate it.

| role | cos(belief, correctness) | **disjoint halves** | ceiling belief | ceiling correctness | cos(belief, lean) | cos(correctness, lean) | cos(belief, correctness) with lean removed |
|---|---|---|---|---|---|---|---|
| J judge (VERDICT:) | +0.59 | **+0.12** | -0.15 | 0.40 | +0.36 | +0.32 | +0.53 |
| N neutral (FINAL:) | +0.65 | **+0.29** | 0.46 | 0.49 | – | – | – |
| JT judge after thinking (VERDICT:) | +0.99 | **+0.91** | 0.81 | 0.98 | +0.99 | +1.00 | +0.23 |

