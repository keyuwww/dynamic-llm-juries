# Belief vs correctness axes: qwen3.6-35b-a3b, rb2math

671 answers (183 right). Wrong answers with a belief score: 446; believed (>= 0.57): 9, never reached (0): 422.

## 1. Does each role's correctness axis score believed WRONG answers as more 'right'?

AUROC of the projection on the role's own right-minus-wrong direction (learned on the other half of the questions), believed vs never-reached wrong answers. 0.5 = ignores belief; > 0.5 = treats belief as rightness. Same axis, right vs wrong answers (all), for reference.

| layer | J: belief / right-vs-wrong | G: belief / right-vs-wrong | S: belief / right-vs-wrong | N: belief / right-vs-wrong |
|---|---|---|---|---|
| 0 | 0.50 / 0.50 | 0.55 / 0.57 | 0.50 / 0.50 | 0.50 / 0.50 |
| 2 | 0.64 / 0.69 | 0.60 / 0.60 | 0.60 / 0.69 | 0.58 / 0.73 |
| 4 | 0.59 / 0.70 | 0.62 / 0.61 | 0.60 / 0.72 | 0.64 / 0.75 |
| 6 | 0.57 / 0.72 | 0.62 / 0.61 | 0.57 / 0.76 | 0.69 / 0.75 |
| 8 | 0.53 / 0.74 | 0.58 / 0.62 | 0.58 / 0.77 | 0.58 / 0.68 |
| 10 | 0.57 / 0.76 | 0.61 / 0.65 | 0.55 / 0.77 | 0.45 / 0.77 |
| 12 | 0.53 / 0.67 | 0.63 / 0.65 | 0.47 / 0.78 | 0.41 / 0.74 |
| 14 | 0.56 / 0.69 | 0.62 / 0.66 | 0.47 / 0.78 | 0.45 / 0.76 |
| 16 | 0.54 / 0.78 | 0.59 / 0.68 | 0.48 / 0.82 | 0.51 / 0.80 |
| 18 | 0.52 / 0.81 | 0.58 / 0.72 | 0.42 / 0.83 | 0.45 / 0.80 |
| 20 | 0.48 / 0.85 | 0.57 / 0.76 | 0.43 / 0.85 | 0.46 / 0.83 |
| 22 | 0.49 / 0.85 | 0.57 / 0.77 | 0.47 / 0.85 | 0.44 / 0.82 |
| 24 | 0.54 / 0.86 | 0.55 / 0.77 | 0.52 / 0.88 | 0.44 / 0.83 |
| 26 | 0.53 / 0.85 | 0.54 / 0.80 | 0.50 / 0.89 | 0.47 / 0.84 |
| 28 | 0.52 / 0.87 | 0.55 / 0.81 | 0.50 / 0.87 | 0.50 / 0.86 |
| 30 | 0.50 / 0.87 | 0.55 / 0.83 | 0.54 / 0.87 | 0.53 / 0.87 |
| 32 | 0.47 / 0.88 | 0.55 / 0.84 | 0.57 / 0.89 | 0.54 / 0.86 |
| 34 | 0.57 / 0.91 | 0.54 / 0.84 | 0.62 / 0.90 | 0.53 / 0.86 |
| 36 | 0.60 / 0.91 | 0.55 / 0.83 | 0.62 / 0.90 | 0.53 / 0.85 |
| 38 | 0.63 / 0.90 | 0.56 / 0.82 | 0.68 / 0.88 | 0.52 / 0.85 |
| 40 | 0.64 / 0.89 | 0.55 / 0.80 | 0.69 / 0.87 | 0.55 / 0.85 |

## 2. Is belief readable in each role? (probe, believed vs never-reached wrong answers)

| role | layer (role's best right-vs-wrong) | probe AUROC | cosine(belief dir, own correctness dir) | cosine(belief dir, judge correctness dir) |
|---|---|---|---|---|
| J judge (VERDICT:) | 36 | 0.56 | +0.31 | +0.31 |
| G generate (end of answer) | 34 | 0.30 | +0.09 | -0.02 |
| S self-check (VERDICT:) | 34 | 0.38 | +0.47 | +0.37 |
| N neutral (FINAL:) | 30 | 0.35 | +0.15 | -0.03 |

## 3. Ceilings and the verdict-lean control (each role's best layer)

Ceiling = cosine of the same direction built on two random halves of the questions. Lean = the model's own verdict lean (CORRECT minus INCORRECT by its margin); only roles that give a verdict have one.

Disjoint = belief direction from one half of the questions vs correctness direction from the other half (and the reverse, averaged): no answers shared, so shared never-reached answers cannot inflate it.

| role | cos(belief, correctness) | **disjoint halves** | ceiling belief | ceiling correctness | cos(belief, lean) | cos(correctness, lean) | cos(belief, correctness) with lean removed |
|---|---|---|---|---|---|---|---|
| J judge (VERDICT:) | +0.31 | **+0.23** | -0.01 | 0.99 | +0.34 | +0.99 | -0.24 |
| G generate (end of answer) | +0.09 | **+0.08** | -0.07 | 0.84 | – | – | – |
| S self-check (VERDICT:) | +0.47 | **+0.31** | 0.27 | 0.96 | +0.51 | +0.99 | -0.25 |
| N neutral (FINAL:) | +0.15 | **+0.10** | 0.11 | 0.93 | – | – | – |

# Belief vs correctness axes: qwen3.6-35b-a3b, bff

431 answers (256 right). Wrong answers with a belief score: 154; believed (>= 0.57): 12, never reached (0): 126.

## 1. Does each role's correctness axis score believed WRONG answers as more 'right'?

AUROC of the projection on the role's own right-minus-wrong direction (learned on the other half of the questions), believed vs never-reached wrong answers. 0.5 = ignores belief; > 0.5 = treats belief as rightness. Same axis, right vs wrong answers (all), for reference.

| layer | J: belief / right-vs-wrong | G: belief / right-vs-wrong | S: belief / right-vs-wrong | N: belief / right-vs-wrong |
|---|---|---|---|---|
| 0 | 0.50 / 0.50 | 0.43 / 0.47 | 0.50 / 0.50 | 0.50 / 0.50 |
| 2 | 0.52 / 0.50 | 0.50 / 0.49 | 0.48 / 0.46 | 0.45 / 0.49 |
| 4 | 0.42 / 0.47 | 0.46 / 0.47 | 0.45 / 0.48 | 0.45 / 0.54 |
| 6 | 0.40 / 0.47 | 0.45 / 0.46 | 0.52 / 0.50 | 0.43 / 0.49 |
| 8 | 0.47 / 0.46 | 0.46 / 0.48 | 0.48 / 0.49 | 0.43 / 0.53 |
| 10 | 0.41 / 0.47 | 0.46 / 0.47 | 0.51 / 0.50 | 0.45 / 0.48 |
| 12 | 0.40 / 0.48 | 0.46 / 0.48 | 0.47 / 0.49 | 0.44 / 0.49 |
| 14 | 0.41 / 0.48 | 0.43 / 0.47 | 0.55 / 0.51 | 0.45 / 0.48 |
| 16 | 0.49 / 0.51 | 0.42 / 0.48 | 0.60 / 0.50 | 0.44 / 0.49 |
| 18 | 0.48 / 0.51 | 0.42 / 0.48 | 0.51 / 0.50 | 0.50 / 0.51 |
| 20 | 0.50 / 0.53 | 0.42 / 0.47 | 0.41 / 0.47 | 0.46 / 0.49 |
| 22 | 0.49 / 0.52 | 0.43 / 0.49 | 0.40 / 0.47 | 0.45 / 0.49 |
| 24 | 0.45 / 0.50 | 0.42 / 0.49 | 0.40 / 0.49 | 0.47 / 0.49 |
| 26 | 0.53 / 0.51 | 0.43 / 0.50 | 0.42 / 0.52 | 0.46 / 0.51 |
| 28 | 0.50 / 0.55 | 0.42 / 0.50 | 0.47 / 0.56 | 0.55 / 0.53 |
| 30 | 0.58 / 0.54 | 0.40 / 0.50 | 0.44 / 0.55 | 0.54 / 0.53 |
| 32 | 0.59 / 0.54 | 0.40 / 0.50 | 0.46 / 0.57 | 0.48 / 0.54 |
| 34 | 0.58 / 0.55 | 0.41 / 0.51 | 0.59 / 0.57 | 0.49 / 0.56 |
| 36 | 0.56 / 0.53 | 0.42 / 0.51 | 0.61 / 0.56 | 0.49 / 0.57 |
| 38 | 0.54 / 0.55 | 0.41 / 0.50 | 0.61 / 0.56 | 0.51 / 0.57 |
| 40 | 0.55 / 0.56 | 0.41 / 0.50 | 0.60 / 0.57 | 0.50 / 0.57 |

## 2. Is belief readable in each role? (probe, believed vs never-reached wrong answers)

| role | layer (role's best right-vs-wrong) | probe AUROC | cosine(belief dir, own correctness dir) | cosine(belief dir, judge correctness dir) |
|---|---|---|---|---|
| J judge (VERDICT:) | 40 | 0.74 | +0.79 | +0.79 |
| G generate (end of answer) | 36 | 0.47 | +0.22 | +0.03 |
| S self-check (VERDICT:) | 40 | 0.73 | +0.94 | +0.87 |
| N neutral (FINAL:) | 38 | 0.44 | +0.12 | -0.04 |

## 3. Ceilings and the verdict-lean control (each role's best layer)

Ceiling = cosine of the same direction built on two random halves of the questions. Lean = the model's own verdict lean (CORRECT minus INCORRECT by its margin); only roles that give a verdict have one.

Disjoint = belief direction from one half of the questions vs correctness direction from the other half (and the reverse, averaged): no answers shared, so shared never-reached answers cannot inflate it.

| role | cos(belief, correctness) | **disjoint halves** | ceiling belief | ceiling correctness | cos(belief, lean) | cos(correctness, lean) | cos(belief, correctness) with lean removed |
|---|---|---|---|---|---|---|---|
| J judge (VERDICT:) | +0.79 | **+0.11** | 0.63 | 0.88 | +0.87 | +0.90 | +0.03 |
| G generate (end of answer) | +0.22 | **-0.03** | -0.33 | 0.35 | – | – | – |
| S self-check (VERDICT:) | +0.94 | **+0.30** | 0.89 | 0.90 | +0.84 | +0.87 | +0.78 |
| N neutral (FINAL:) | +0.12 | **-0.15** | 0.03 | 0.50 | – | – | – |

# Belief vs correctness axes: qwen3.6-35b-a3b, bbeh

1854 answers (959 right). Wrong answers with a belief score: 895; believed (>= 0.50): 122, never reached (0): 597.

## 1. Does each role's correctness axis score believed WRONG answers as more 'right'?

AUROC of the projection on the role's own right-minus-wrong direction (learned on the other half of the questions), believed vs never-reached wrong answers. 0.5 = ignores belief; > 0.5 = treats belief as rightness. Same axis, right vs wrong answers (all), for reference.

| layer | J: belief / right-vs-wrong | G: belief / right-vs-wrong | S: belief / right-vs-wrong | N: belief / right-vs-wrong |
|---|---|---|---|---|
| 0 | 0.50 / 0.50 | 0.53 / 0.56 | 0.50 / 0.50 | 0.50 / 0.50 |
| 2 | 0.55 / 0.56 | 0.55 / 0.56 | 0.52 / 0.57 | 0.52 / 0.57 |
| 4 | 0.50 / 0.55 | 0.57 / 0.58 | 0.52 / 0.56 | 0.52 / 0.57 |
| 6 | 0.47 / 0.55 | 0.58 / 0.59 | 0.51 / 0.57 | 0.52 / 0.58 |
| 8 | 0.49 / 0.55 | 0.59 / 0.59 | 0.54 / 0.55 | 0.54 / 0.57 |
| 10 | 0.51 / 0.56 | 0.59 / 0.59 | 0.57 / 0.55 | 0.53 / 0.56 |
| 12 | 0.54 / 0.57 | 0.59 / 0.59 | 0.56 / 0.54 | 0.57 / 0.54 |
| 14 | 0.50 / 0.56 | 0.59 / 0.58 | 0.56 / 0.53 | 0.54 / 0.54 |
| 16 | 0.51 / 0.54 | 0.60 / 0.58 | 0.60 / 0.54 | 0.57 / 0.53 |
| 18 | 0.56 / 0.55 | 0.61 / 0.57 | 0.62 / 0.55 | 0.57 / 0.53 |
| 20 | 0.59 / 0.56 | 0.60 / 0.56 | 0.62 / 0.56 | 0.57 / 0.55 |
| 22 | 0.58 / 0.56 | 0.62 / 0.56 | 0.62 / 0.56 | 0.57 / 0.54 |
| 24 | 0.58 / 0.56 | 0.61 / 0.56 | 0.60 / 0.55 | 0.59 / 0.55 |
| 26 | 0.60 / 0.57 | 0.61 / 0.56 | 0.58 / 0.57 | 0.60 / 0.56 |
| 28 | 0.59 / 0.56 | 0.62 / 0.56 | 0.60 / 0.56 | 0.61 / 0.56 |
| 30 | 0.60 / 0.55 | 0.61 / 0.56 | 0.59 / 0.57 | 0.64 / 0.56 |
| 32 | 0.58 / 0.54 | 0.62 / 0.56 | 0.59 / 0.56 | 0.64 / 0.56 |
| 34 | 0.60 / 0.55 | 0.62 / 0.56 | 0.62 / 0.56 | 0.62 / 0.56 |
| 36 | 0.60 / 0.54 | 0.64 / 0.56 | 0.63 / 0.55 | 0.60 / 0.58 |
| 38 | 0.59 / 0.53 | 0.67 / 0.57 | 0.62 / 0.54 | 0.58 / 0.59 |
| 40 | 0.60 / 0.52 | 0.67 / 0.56 | 0.63 / 0.54 | 0.57 / 0.60 |

## 2. Is belief readable in each role? (probe, believed vs never-reached wrong answers)

| role | layer (role's best right-vs-wrong) | probe AUROC | cosine(belief dir, own correctness dir) | cosine(belief dir, judge correctness dir) |
|---|---|---|---|---|
| J judge (VERDICT:) | 12 | 0.64 | +0.92 | +0.92 |
| G generate (end of answer) | 6 | 0.69 | +0.42 | +0.05 |
| S self-check (VERDICT:) | 6 | 0.71 | +0.94 | +0.53 |
| N neutral (FINAL:) | 40 | 0.80 | +0.33 | +0.27 |

## 3. Ceilings and the verdict-lean control (each role's best layer)

Ceiling = cosine of the same direction built on two random halves of the questions. Lean = the model's own verdict lean (CORRECT minus INCORRECT by its margin); only roles that give a verdict have one.

Disjoint = belief direction from one half of the questions vs correctness direction from the other half (and the reverse, averaged): no answers shared, so shared never-reached answers cannot inflate it.

| role | cos(belief, correctness) | **disjoint halves** | ceiling belief | ceiling correctness | cos(belief, lean) | cos(correctness, lean) | cos(belief, correctness) with lean removed |
|---|---|---|---|---|---|---|---|
| J judge (VERDICT:) | +0.92 | **+0.80** | 0.75 | 0.86 | -0.27 | -0.43 | +0.93 |
| G generate (end of answer) | +0.42 | **+0.31** | 0.52 | 0.68 | – | – | – |
| S self-check (VERDICT:) | +0.94 | **+0.88** | 0.82 | 0.91 | -0.33 | -0.45 | +0.94 |
| N neutral (FINAL:) | +0.33 | **+0.25** | 0.42 | 0.64 | – | – | – |

