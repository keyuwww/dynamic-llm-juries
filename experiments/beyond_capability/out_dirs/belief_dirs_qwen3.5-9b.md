# Belief vs correctness axes: qwen3.5-9b, rb2math

732 answers (183 right). Wrong answers with a belief score: 447; believed (>= 0.57): 9, never reached (0): 421.

## 1. Does each role's correctness axis score believed WRONG answers as more 'right'?

AUROC of the projection on the role's own right-minus-wrong direction (learned on the other half of the questions), believed vs never-reached wrong answers. 0.5 = ignores belief; > 0.5 = treats belief as rightness. Same axis, right vs wrong answers (all), for reference.

| layer | J: belief / right-vs-wrong | G: belief / right-vs-wrong | S: belief / right-vs-wrong | N: belief / right-vs-wrong |
|---|---|---|---|---|
| 0 | 0.50 / 0.50 | 0.62 / 0.59 | 0.50 / 0.50 | 0.50 / 0.50 |
| 2 | 0.50 / 0.74 | 0.54 / 0.58 | 0.56 / 0.74 | 0.59 / 0.71 |
| 4 | 0.48 / 0.71 | 0.63 / 0.60 | 0.55 / 0.77 | 0.62 / 0.76 |
| 6 | 0.52 / 0.74 | 0.64 / 0.64 | 0.63 / 0.77 | 0.65 / 0.78 |
| 8 | 0.63 / 0.75 | 0.62 / 0.64 | 0.67 / 0.76 | 0.61 / 0.78 |
| 10 | 0.60 / 0.75 | 0.60 / 0.65 | 0.62 / 0.71 | 0.58 / 0.77 |
| 12 | 0.61 / 0.76 | 0.59 / 0.66 | 0.56 / 0.72 | 0.51 / 0.77 |
| 14 | 0.64 / 0.81 | 0.60 / 0.71 | 0.53 / 0.78 | 0.49 / 0.79 |
| 16 | 0.70 / 0.84 | 0.56 / 0.73 | 0.62 / 0.85 | 0.55 / 0.83 |
| 18 | 0.73 / 0.85 | 0.57 / 0.81 | 0.67 / 0.86 | 0.58 / 0.85 |
| 20 | 0.74 / 0.88 | 0.57 / 0.84 | 0.70 / 0.87 | 0.60 / 0.85 |
| 22 | 0.75 / 0.88 | 0.57 / 0.85 | 0.71 / 0.87 | 0.62 / 0.85 |
| 24 | 0.77 / 0.87 | 0.56 / 0.84 | 0.70 / 0.87 | 0.61 / 0.85 |
| 26 | 0.77 / 0.87 | 0.57 / 0.84 | 0.71 / 0.87 | 0.63 / 0.84 |
| 28 | 0.78 / 0.87 | 0.55 / 0.84 | 0.71 / 0.87 | 0.62 / 0.84 |
| 30 | 0.79 / 0.88 | 0.59 / 0.84 | 0.72 / 0.87 | 0.62 / 0.85 |
| 32 | 0.76 / 0.87 | 0.55 / 0.81 | 0.70 / 0.88 | 0.65 / 0.85 |

## 2. Is belief readable in each role? (probe, believed vs never-reached wrong answers)

| role | layer (role's best right-vs-wrong) | probe AUROC | cosine(belief dir, own correctness dir) | cosine(belief dir, judge correctness dir) |
|---|---|---|---|---|
| J judge (VERDICT:) | 22 | 0.57 | +0.68 | +0.68 |
| G generate (end of answer) | 22 | 0.33 | +0.26 | -0.07 |
| S self-check (VERDICT:) | 32 | 0.71 | +0.94 | +0.76 |
| N neutral (FINAL:) | 20 | 0.63 | +0.45 | -0.00 |

## 3. Ceilings and the verdict-lean control (each role's best layer)

Ceiling = cosine of the same direction built on two random halves of the questions. Lean = the model's own verdict lean (CORRECT minus INCORRECT by its margin); only roles that give a verdict have one.

Disjoint = belief direction from one half of the questions vs correctness direction from the other half (and the reverse, averaged): no answers shared, so shared never-reached answers cannot inflate it.

| role | cos(belief, correctness) | **disjoint halves** | ceiling belief | ceiling correctness | cos(belief, lean) | cos(correctness, lean) | cos(belief, correctness) with lean removed |
|---|---|---|---|---|---|---|---|
| J judge (VERDICT:) | +0.68 | **+0.55** | 0.26 | 0.95 | +0.68 | +0.99 | +0.09 |
| G generate (end of answer) | +0.26 | **+0.12** | 0.04 | 0.87 | – | – | – |
| S self-check (VERDICT:) | +0.94 | **+0.63** | -0.18 | 0.99 | +0.93 | +0.99 | +0.33 |
| N neutral (FINAL:) | +0.45 | **+0.23** | 0.05 | 0.94 | – | – | – |

# Belief vs correctness axes: qwen3.5-9b, bff

459 answers (256 right). Wrong answers with a belief score: 179; believed (>= 0.57): 39, never reached (0): 112.

## 1. Does each role's correctness axis score believed WRONG answers as more 'right'?

AUROC of the projection on the role's own right-minus-wrong direction (learned on the other half of the questions), believed vs never-reached wrong answers. 0.5 = ignores belief; > 0.5 = treats belief as rightness. Same axis, right vs wrong answers (all), for reference.

| layer | J: belief / right-vs-wrong | G: belief / right-vs-wrong | S: belief / right-vs-wrong | N: belief / right-vs-wrong |
|---|---|---|---|---|
| 0 | 0.50 / 0.50 | 0.42 / 0.47 | 0.50 / 0.50 | 0.50 / 0.50 |
| 2 | 0.52 / 0.50 | 0.45 / 0.48 | 0.55 / 0.52 | 0.51 / 0.50 |
| 4 | 0.44 / 0.48 | 0.41 / 0.47 | 0.52 / 0.50 | 0.49 / 0.50 |
| 6 | 0.41 / 0.47 | 0.38 / 0.45 | 0.48 / 0.49 | 0.45 / 0.48 |
| 8 | 0.42 / 0.47 | 0.42 / 0.45 | 0.40 / 0.48 | 0.40 / 0.46 |
| 10 | 0.41 / 0.45 | 0.42 / 0.45 | 0.42 / 0.47 | 0.43 / 0.46 |
| 12 | 0.42 / 0.45 | 0.40 / 0.45 | 0.40 / 0.47 | 0.46 / 0.46 |
| 14 | 0.40 / 0.46 | 0.40 / 0.46 | 0.40 / 0.47 | 0.45 / 0.46 |
| 16 | 0.45 / 0.50 | 0.41 / 0.48 | 0.43 / 0.49 | 0.46 / 0.48 |
| 18 | 0.48 / 0.48 | 0.44 / 0.48 | 0.51 / 0.50 | 0.54 / 0.54 |
| 20 | 0.59 / 0.55 | 0.48 / 0.50 | 0.58 / 0.55 | 0.59 / 0.53 |
| 22 | 0.60 / 0.54 | 0.49 / 0.49 | 0.58 / 0.56 | 0.61 / 0.56 |
| 24 | 0.60 / 0.55 | 0.49 / 0.48 | 0.59 / 0.56 | 0.61 / 0.57 |
| 26 | 0.60 / 0.56 | 0.49 / 0.49 | 0.59 / 0.57 | 0.61 / 0.56 |
| 28 | 0.62 / 0.56 | 0.49 / 0.49 | 0.60 / 0.57 | 0.61 / 0.56 |
| 30 | 0.62 / 0.55 | 0.49 / 0.49 | 0.60 / 0.57 | 0.61 / 0.56 |
| 32 | 0.56 / 0.54 | 0.47 / 0.49 | 0.58 / 0.55 | 0.60 / 0.56 |

## 2. Is belief readable in each role? (probe, believed vs never-reached wrong answers)

| role | layer (role's best right-vs-wrong) | probe AUROC | cosine(belief dir, own correctness dir) | cosine(belief dir, judge correctness dir) |
|---|---|---|---|---|
| J judge (VERDICT:) | 28 | 0.77 | +0.93 | +0.93 |
| G generate (end of answer) | 20 | 0.60 | +0.58 | -0.02 |
| S self-check (VERDICT:) | 26 | 0.74 | +0.90 | +0.70 |
| N neutral (FINAL:) | 24 | 0.79 | +0.71 | +0.02 |

## 3. Ceilings and the verdict-lean control (each role's best layer)

Ceiling = cosine of the same direction built on two random halves of the questions. Lean = the model's own verdict lean (CORRECT minus INCORRECT by its margin); only roles that give a verdict have one.

Disjoint = belief direction from one half of the questions vs correctness direction from the other half (and the reverse, averaged): no answers shared, so shared never-reached answers cannot inflate it.

| role | cos(belief, correctness) | **disjoint halves** | ceiling belief | ceiling correctness | cos(belief, lean) | cos(correctness, lean) | cos(belief, correctness) with lean removed |
|---|---|---|---|---|---|---|---|
| J judge (VERDICT:) | +0.93 | **+0.80** | 0.86 | 0.74 | +0.81 | +0.70 | +0.86 |
| G generate (end of answer) | +0.58 | **+0.24** | -0.15 | 0.24 | – | – | – |
| S self-check (VERDICT:) | +0.90 | **+0.70** | 0.73 | 0.69 | +0.92 | +0.91 | +0.39 |
| N neutral (FINAL:) | +0.71 | **+0.46** | 0.37 | 0.61 | – | – | – |

# Belief vs correctness axes: qwen3.5-9b, bbeh

2018 answers (952 right). Wrong answers with a belief score: 1066; believed (>= 0.50): 255, never reached (0): 583.

## 1. Does each role's correctness axis score believed WRONG answers as more 'right'?

AUROC of the projection on the role's own right-minus-wrong direction (learned on the other half of the questions), believed vs never-reached wrong answers. 0.5 = ignores belief; > 0.5 = treats belief as rightness. Same axis, right vs wrong answers (all), for reference.

| layer | J: belief / right-vs-wrong | G: belief / right-vs-wrong | S: belief / right-vs-wrong | N: belief / right-vs-wrong |
|---|---|---|---|---|
| 0 | 0.50 / 0.50 | 0.56 / 0.55 | 0.50 / 0.50 | 0.50 / 0.50 |
| 2 | 0.53 / 0.57 | 0.57 / 0.58 | 0.54 / 0.56 | 0.53 / 0.56 |
| 4 | 0.57 / 0.57 | 0.61 / 0.59 | 0.55 / 0.58 | 0.55 / 0.56 |
| 6 | 0.54 / 0.56 | 0.63 / 0.58 | 0.54 / 0.57 | 0.55 / 0.56 |
| 8 | 0.53 / 0.56 | 0.63 / 0.59 | 0.53 / 0.56 | 0.56 / 0.56 |
| 10 | 0.54 / 0.55 | 0.65 / 0.60 | 0.51 / 0.56 | 0.58 / 0.56 |
| 12 | 0.56 / 0.56 | 0.64 / 0.60 | 0.57 / 0.56 | 0.56 / 0.58 |
| 14 | 0.58 / 0.56 | 0.63 / 0.59 | 0.58 / 0.57 | 0.58 / 0.58 |
| 16 | 0.58 / 0.57 | 0.63 / 0.59 | 0.61 / 0.59 | 0.61 / 0.58 |
| 18 | 0.61 / 0.57 | 0.62 / 0.58 | 0.63 / 0.59 | 0.62 / 0.57 |
| 20 | 0.62 / 0.58 | 0.61 / 0.58 | 0.65 / 0.59 | 0.64 / 0.58 |
| 22 | 0.61 / 0.58 | 0.61 / 0.58 | 0.66 / 0.59 | 0.64 / 0.58 |
| 24 | 0.62 / 0.57 | 0.60 / 0.58 | 0.65 / 0.57 | 0.61 / 0.58 |
| 26 | 0.61 / 0.57 | 0.61 / 0.58 | 0.65 / 0.57 | 0.61 / 0.58 |
| 28 | 0.62 / 0.57 | 0.61 / 0.57 | 0.63 / 0.55 | 0.59 / 0.59 |
| 30 | 0.61 / 0.57 | 0.61 / 0.57 | 0.62 / 0.55 | 0.59 / 0.58 |
| 32 | 0.60 / 0.57 | 0.62 / 0.58 | 0.61 / 0.54 | 0.59 / 0.59 |

## 2. Is belief readable in each role? (probe, believed vs never-reached wrong answers)

| role | layer (role's best right-vs-wrong) | probe AUROC | cosine(belief dir, own correctness dir) | cosine(belief dir, judge correctness dir) |
|---|---|---|---|---|
| J judge (VERDICT:) | 22 | 0.82 | +0.77 | +0.77 |
| G generate (end of answer) | 10 | 0.79 | +0.66 | +0.05 |
| S self-check (VERDICT:) | 16 | 0.79 | +0.76 | +0.58 |
| N neutral (FINAL:) | 32 | 0.83 | +0.65 | +0.07 |

## 3. Ceilings and the verdict-lean control (each role's best layer)

Ceiling = cosine of the same direction built on two random halves of the questions. Lean = the model's own verdict lean (CORRECT minus INCORRECT by its margin); only roles that give a verdict have one.

Disjoint = belief direction from one half of the questions vs correctness direction from the other half (and the reverse, averaged): no answers shared, so shared never-reached answers cannot inflate it.

| role | cos(belief, correctness) | **disjoint halves** | ceiling belief | ceiling correctness | cos(belief, lean) | cos(correctness, lean) | cos(belief, correctness) with lean removed |
|---|---|---|---|---|---|---|---|
| J judge (VERDICT:) | +0.77 | **+0.63** | 0.68 | 0.69 | +0.11 | +0.09 | +0.77 |
| G generate (end of answer) | +0.66 | **+0.51** | 0.59 | 0.62 | – | – | – |
| S self-check (VERDICT:) | +0.76 | **+0.63** | 0.75 | 0.75 | -0.13 | +0.01 | +0.76 |
| N neutral (FINAL:) | +0.65 | **+0.54** | 0.58 | 0.76 | – | – | – |

