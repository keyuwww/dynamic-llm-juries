# Belief vs correctness axes: qwen3.5-9b, rb2math

671 answers (183 right). Wrong answers with a belief score: 447; believed (>= 0.57): 9, never reached (0): 421.

## 1. Does each role's correctness axis score believed WRONG answers as more 'right'?

AUROC of the projection on the role's own right-minus-wrong direction (learned on the other half of the questions), believed vs never-reached wrong answers. 0.5 = ignores belief; > 0.5 = treats belief as rightness. Same axis, right vs wrong answers (all), for reference.

| layer | J: belief / right-vs-wrong | G: belief / right-vs-wrong | S: belief / right-vs-wrong | N: belief / right-vs-wrong |
|---|---|---|---|---|
| 0 | 0.50 / 0.50 | 0.59 / 0.59 | 0.50 / 0.50 | 0.50 / 0.50 |
| 2 | 0.47 / 0.74 | 0.57 / 0.59 | 0.48 / 0.75 | 0.51 / 0.73 |
| 4 | 0.43 / 0.71 | 0.63 / 0.61 | 0.54 / 0.79 | 0.57 / 0.77 |
| 6 | 0.49 / 0.75 | 0.65 / 0.65 | 0.63 / 0.78 | 0.60 / 0.80 |
| 8 | 0.60 / 0.76 | 0.62 / 0.65 | 0.66 / 0.77 | 0.56 / 0.79 |
| 10 | 0.61 / 0.76 | 0.60 / 0.66 | 0.62 / 0.72 | 0.55 / 0.79 |
| 12 | 0.61 / 0.76 | 0.60 / 0.66 | 0.57 / 0.72 | 0.47 / 0.78 |
| 14 | 0.64 / 0.81 | 0.63 / 0.72 | 0.55 / 0.79 | 0.47 / 0.80 |
| 16 | 0.68 / 0.84 | 0.60 / 0.75 | 0.62 / 0.85 | 0.53 / 0.84 |
| 18 | 0.72 / 0.86 | 0.63 / 0.82 | 0.67 / 0.87 | 0.56 / 0.86 |
| 20 | 0.72 / 0.88 | 0.61 / 0.85 | 0.71 / 0.88 | 0.60 / 0.87 |
| 22 | 0.72 / 0.88 | 0.60 / 0.86 | 0.73 / 0.89 | 0.63 / 0.86 |
| 24 | 0.73 / 0.88 | 0.58 / 0.86 | 0.72 / 0.88 | 0.61 / 0.86 |
| 26 | 0.73 / 0.88 | 0.58 / 0.85 | 0.72 / 0.88 | 0.63 / 0.86 |
| 28 | 0.74 / 0.88 | 0.58 / 0.85 | 0.73 / 0.89 | 0.63 / 0.86 |
| 30 | 0.75 / 0.88 | 0.62 / 0.85 | 0.73 / 0.88 | 0.62 / 0.86 |
| 32 | 0.72 / 0.87 | 0.58 / 0.83 | 0.70 / 0.88 | 0.64 / 0.86 |

## 2. Is belief readable in each role? (probe, believed vs never-reached wrong answers)

| role | layer (role's best right-vs-wrong) | probe AUROC | cosine(belief dir, own correctness dir) | cosine(belief dir, judge correctness dir) |
|---|---|---|---|---|
| J judge (VERDICT:) | 28 | 0.67 | +0.88 | +0.88 |
| G generate (end of answer) | 22 | 0.33 | +0.31 | -0.01 |
| S self-check (VERDICT:) | 28 | 0.71 | +0.95 | +0.90 |
| N neutral (FINAL:) | 20 | 0.63 | +0.42 | -0.00 |

## 3. Ceilings and the verdict-lean control (each role's best layer)

Ceiling = cosine of the same direction built on two random halves of the questions. Lean = the model's own verdict lean (CORRECT minus INCORRECT by its margin); only roles that give a verdict have one.

Disjoint = belief direction from one half of the questions vs correctness direction from the other half (and the reverse, averaged): no answers shared, so shared never-reached answers cannot inflate it.

| role | cos(belief, correctness) | **disjoint halves** | ceiling belief | ceiling correctness | cos(belief, lean) | cos(correctness, lean) | cos(belief, correctness) with lean removed |
|---|---|---|---|---|---|---|---|
| J judge (VERDICT:) | +0.88 | **+0.69** | 0.43 | 0.98 | +0.88 | +1.00 | +0.06 |
| G generate (end of answer) | +0.31 | **+0.17** | 0.06 | 0.88 | – | – | – |
| S self-check (VERDICT:) | +0.95 | **+0.72** | -0.13 | 0.99 | +0.94 | +0.99 | +0.27 |
| N neutral (FINAL:) | +0.42 | **+0.24** | 0.11 | 0.94 | – | – | – |

# Belief vs correctness axes: qwen3.5-9b, bff

431 answers (256 right). Wrong answers with a belief score: 151; believed (>= 0.57): 20, never reached (0): 110.

## 1. Does each role's correctness axis score believed WRONG answers as more 'right'?

AUROC of the projection on the role's own right-minus-wrong direction (learned on the other half of the questions), believed vs never-reached wrong answers. 0.5 = ignores belief; > 0.5 = treats belief as rightness. Same axis, right vs wrong answers (all), for reference.

| layer | J: belief / right-vs-wrong | G: belief / right-vs-wrong | S: belief / right-vs-wrong | N: belief / right-vs-wrong |
|---|---|---|---|---|
| 0 | 0.50 / 0.50 | 0.47 / 0.45 | 0.50 / 0.50 | 0.50 / 0.50 |
| 2 | 0.51 / 0.49 | 0.47 / 0.48 | 0.52 / 0.51 | 0.53 / 0.49 |
| 4 | 0.53 / 0.49 | 0.50 / 0.47 | 0.50 / 0.49 | 0.50 / 0.48 |
| 6 | 0.52 / 0.47 | 0.47 / 0.47 | 0.51 / 0.47 | 0.52 / 0.46 |
| 8 | 0.49 / 0.46 | 0.49 / 0.46 | 0.51 / 0.47 | 0.50 / 0.46 |
| 10 | 0.49 / 0.45 | 0.48 / 0.46 | 0.49 / 0.46 | 0.52 / 0.48 |
| 12 | 0.48 / 0.46 | 0.51 / 0.47 | 0.49 / 0.48 | 0.48 / 0.49 |
| 14 | 0.50 / 0.47 | 0.51 / 0.47 | 0.50 / 0.49 | 0.47 / 0.47 |
| 16 | 0.53 / 0.50 | 0.49 / 0.46 | 0.53 / 0.51 | 0.49 / 0.46 |
| 18 | 0.55 / 0.52 | 0.45 / 0.47 | 0.55 / 0.53 | 0.56 / 0.55 |
| 20 | 0.55 / 0.55 | 0.46 / 0.47 | 0.57 / 0.58 | 0.55 / 0.58 |
| 22 | 0.53 / 0.56 | 0.48 / 0.48 | 0.54 / 0.57 | 0.55 / 0.59 |
| 24 | 0.55 / 0.57 | 0.47 / 0.48 | 0.57 / 0.59 | 0.55 / 0.59 |
| 26 | 0.55 / 0.57 | 0.47 / 0.49 | 0.58 / 0.59 | 0.54 / 0.58 |
| 28 | 0.55 / 0.57 | 0.47 / 0.48 | 0.56 / 0.59 | 0.55 / 0.57 |
| 30 | 0.56 / 0.57 | 0.46 / 0.48 | 0.56 / 0.57 | 0.54 / 0.57 |
| 32 | 0.52 / 0.55 | 0.45 / 0.50 | 0.54 / 0.56 | 0.54 / 0.58 |

## 2. Is belief readable in each role? (probe, believed vs never-reached wrong answers)

| role | layer (role's best right-vs-wrong) | probe AUROC | cosine(belief dir, own correctness dir) | cosine(belief dir, judge correctness dir) |
|---|---|---|---|---|
| J judge (VERDICT:) | 24 | 0.77 | +0.92 | +0.92 |
| G generate (end of answer) | 32 | 0.67 | +0.59 | +0.01 |
| S self-check (VERDICT:) | 28 | 0.84 | +0.94 | +0.60 |
| N neutral (FINAL:) | 24 | 0.80 | +0.51 | +0.04 |

## 3. Ceilings and the verdict-lean control (each role's best layer)

Ceiling = cosine of the same direction built on two random halves of the questions. Lean = the model's own verdict lean (CORRECT minus INCORRECT by its margin); only roles that give a verdict have one.

Disjoint = belief direction from one half of the questions vs correctness direction from the other half (and the reverse, averaged): no answers shared, so shared never-reached answers cannot inflate it.

| role | cos(belief, correctness) | **disjoint halves** | ceiling belief | ceiling correctness | cos(belief, lean) | cos(correctness, lean) | cos(belief, correctness) with lean removed |
|---|---|---|---|---|---|---|---|
| J judge (VERDICT:) | +0.92 | **+0.43** | 0.78 | 0.68 | +0.78 | +0.68 | +0.85 |
| G generate (end of answer) | +0.59 | **+0.07** | 0.07 | 0.30 | – | – | – |
| S self-check (VERDICT:) | +0.94 | **+0.65** | 0.90 | 0.85 | +0.95 | +0.93 | +0.53 |
| N neutral (FINAL:) | +0.51 | **+0.10** | 0.25 | 0.54 | – | – | – |

# Belief vs correctness axes: qwen3.5-9b, bbeh

1862 answers (952 right). Wrong answers with a belief score: 910; believed (>= 0.50): 122, never reached (0): 576.

## 1. Does each role's correctness axis score believed WRONG answers as more 'right'?

AUROC of the projection on the role's own right-minus-wrong direction (learned on the other half of the questions), believed vs never-reached wrong answers. 0.5 = ignores belief; > 0.5 = treats belief as rightness. Same axis, right vs wrong answers (all), for reference.

| layer | J: belief / right-vs-wrong | G: belief / right-vs-wrong | S: belief / right-vs-wrong | N: belief / right-vs-wrong |
|---|---|---|---|---|
| 0 | 0.50 / 0.50 | 0.58 / 0.58 | 0.50 / 0.50 | 0.50 / 0.50 |
| 2 | 0.53 / 0.56 | 0.58 / 0.56 | 0.53 / 0.56 | 0.51 / 0.56 |
| 4 | 0.57 / 0.57 | 0.63 / 0.58 | 0.55 / 0.58 | 0.53 / 0.56 |
| 6 | 0.52 / 0.56 | 0.66 / 0.59 | 0.55 / 0.57 | 0.53 / 0.56 |
| 8 | 0.54 / 0.56 | 0.66 / 0.60 | 0.53 / 0.56 | 0.54 / 0.55 |
| 10 | 0.54 / 0.55 | 0.68 / 0.61 | 0.55 / 0.55 | 0.58 / 0.56 |
| 12 | 0.60 / 0.55 | 0.67 / 0.60 | 0.59 / 0.56 | 0.58 / 0.58 |
| 14 | 0.62 / 0.56 | 0.66 / 0.60 | 0.61 / 0.56 | 0.62 / 0.59 |
| 16 | 0.61 / 0.57 | 0.66 / 0.59 | 0.62 / 0.59 | 0.62 / 0.58 |
| 18 | 0.65 / 0.57 | 0.66 / 0.59 | 0.63 / 0.58 | 0.64 / 0.58 |
| 20 | 0.68 / 0.57 | 0.64 / 0.58 | 0.66 / 0.59 | 0.65 / 0.59 |
| 22 | 0.66 / 0.57 | 0.65 / 0.58 | 0.67 / 0.59 | 0.65 / 0.59 |
| 24 | 0.66 / 0.58 | 0.64 / 0.58 | 0.67 / 0.57 | 0.63 / 0.59 |
| 26 | 0.66 / 0.58 | 0.65 / 0.58 | 0.68 / 0.57 | 0.62 / 0.59 |
| 28 | 0.67 / 0.58 | 0.65 / 0.58 | 0.66 / 0.55 | 0.60 / 0.60 |
| 30 | 0.66 / 0.58 | 0.65 / 0.58 | 0.65 / 0.55 | 0.59 / 0.60 |
| 32 | 0.66 / 0.58 | 0.66 / 0.58 | 0.64 / 0.54 | 0.59 / 0.60 |

## 2. Is belief readable in each role? (probe, believed vs never-reached wrong answers)

| role | layer (role's best right-vs-wrong) | probe AUROC | cosine(belief dir, own correctness dir) | cosine(belief dir, judge correctness dir) |
|---|---|---|---|---|
| J judge (VERDICT:) | 32 | 0.78 | +0.82 | +0.82 |
| G generate (end of answer) | 10 | 0.75 | +0.62 | -0.00 |
| S self-check (VERDICT:) | 20 | 0.82 | +0.67 | +0.53 |
| N neutral (FINAL:) | 28 | 0.78 | +0.47 | +0.10 |

## 3. Ceilings and the verdict-lean control (each role's best layer)

Ceiling = cosine of the same direction built on two random halves of the questions. Lean = the model's own verdict lean (CORRECT minus INCORRECT by its margin); only roles that give a verdict have one.

Disjoint = belief direction from one half of the questions vs correctness direction from the other half (and the reverse, averaged): no answers shared, so shared never-reached answers cannot inflate it.

| role | cos(belief, correctness) | **disjoint halves** | ceiling belief | ceiling correctness | cos(belief, lean) | cos(correctness, lean) | cos(belief, correctness) with lean removed |
|---|---|---|---|---|---|---|---|
| J judge (VERDICT:) | +0.82 | **+0.70** | 0.83 | 0.65 | +0.58 | +0.29 | +0.84 |
| G generate (end of answer) | +0.62 | **+0.52** | 0.59 | 0.69 | – | – | – |
| S self-check (VERDICT:) | +0.67 | **+0.60** | 0.66 | 0.72 | +0.19 | +0.20 | +0.66 |
| N neutral (FINAL:) | +0.47 | **+0.36** | 0.51 | 0.75 | – | – | – |

