# Solve vs judge directions — qwen3.5-9b

9558 rows; layers kept: [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32]


## BBEH: 2018 answers, 446 questions (51% of answers on questions the model solved)

### 1. Does each role's hidden state separate right from wrong answers? (within-question AUROC of a cross-validated probe)

| Layer | judge (someone else's answer) | generate (as its own answer) | self-check (own answer + 'is it correct?') |
|---|---|---|---|
| 2 | 0.64 | 0.65 | 0.60 |
| 4 | 0.63 | 0.65 | 0.67 |
| 6 | 0.60 | 0.69 | 0.67 |
| 8 | 0.65 | 0.67 | 0.69 |
| 10 | 0.66 | 0.70 | 0.70 |
| 12 | 0.65 | 0.66 | 0.68 |
| 14 | 0.65 | 0.64 | 0.72 |
| 16 | 0.64 | 0.67 | 0.68 |
| 18 | 0.62 | 0.69 | 0.69 |
| 20 | 0.61 | 0.69 | 0.66 |
| 22 | 0.60 | 0.71 | 0.66 |
| 24 | 0.61 | 0.69 | 0.68 |
| 26 | 0.60 | 0.68 | 0.69 |
| 28 | 0.62 | 0.70 | 0.72 |
| 30 | 0.60 | 0.73 | 0.71 |
| 32 | 0.62 | 0.72 | 0.70 |

Best layer per role, and the model's own spoken readout (log-odds of CORRECT at the verdict position):

| Role | best layer | probe: all questions | probe: solved | probe: **not solved** | spoken: all | spoken: solved | spoken: **not solved** |
|---|---|---|---|---|---|---|---|
| judge (someone else's answer) | 10 | 0.66 | 0.68 | 0.63 | 0.62 | 0.68 | 0.50 |
| generate (as its own answer) | 30 | 0.73 | 0.77 | 0.64 | – | – | – |
| self-check (own answer + 'is it correct?') | 14 | 0.72 | 0.75 | 0.67 | 0.58 | 0.62 | 0.51 |

### 2. Is it the same direction? (layer 10, the judge role's best)

Cosine between the difference-of-means directions (right minus wrong answers), computed on question-centred states (each answer minus its question's mean) so only within-question differences count. Noise ceiling = cosine between the same role's direction from two random halves of the questions.

| | judge | generate | self-check |
|---|---|---|---|
| judge (someone else's answer) (ceiling 0.94) | 1.00 | -0.05 | 0.76 |
| generate (as its own answer) (ceiling 0.64) | -0.05 | 1.00 | -0.04 |
| self-check (own answer + 'is it correct?') (ceiling 0.93) | 0.76 | -0.04 | 1.00 |

(Two random directions in 4096 dimensions: cosine ≈ ±0.016.)

Cross-transfer: a probe trained in one role (rows), tested in another (columns), on held-out questions. Within-question AUROC, all / **not solved**.

| trained on \ tested on | judge | generate | self-check |
|---|---|---|---|
| judge (someone else's answer) | 0.66 / **0.63** | 0.51 / **0.48** | 0.54 / **0.49** |
| generate (as its own answer) | 0.56 / **0.51** | 0.70 / **0.63** | 0.54 / **0.54** |
| self-check (own answer + 'is it correct?') | 0.60 / **0.57** | 0.49 / **0.51** | 0.70 / **0.60** |

Cosine judge-vs-generate and judge-vs-self-check at every layer, question-centred (ceilings: judge / generate split-half):

| Layer | judge·generate | judge·self-check | ceiling judge | ceiling generate |
|---|---|---|---|---|
| 2 | 0.10 | 0.95 | 0.95 | 0.49 |
| 4 | 0.07 | 0.86 | 0.96 | 0.55 |
| 6 | 0.05 | 0.82 | 0.95 | 0.51 |
| 8 | 0.02 | 0.72 | 0.96 | 0.58 |
| 10 | -0.05 | 0.76 | 0.94 | 0.64 |
| 12 | -0.05 | 0.76 | 0.92 | 0.66 |
| 14 | -0.03 | 0.73 | 0.89 | 0.70 |
| 16 | 0.01 | 0.70 | 0.78 | 0.70 |
| 18 | 0.05 | 0.69 | 0.75 | 0.76 |
| 20 | 0.01 | 0.67 | 0.72 | 0.80 |
| 22 | 0.01 | 0.67 | 0.74 | 0.83 |
| 24 | -0.02 | 0.70 | 0.74 | 0.83 |
| 26 | -0.00 | 0.70 | 0.77 | 0.82 |
| 28 | -0.00 | 0.74 | 0.79 | 0.80 |
| 30 | 0.04 | 0.76 | 0.77 | 0.77 |
| 32 | -0.01 | 0.74 | 0.74 | 0.76 |

### 4. 'Will I solve this?' before answering (layer 10)

Probe AUROC (questions held out): **0.72** over 447 questions (47% solved).

Cosines: pre-solve 'will I solve it' vs judge 'is this answer right': 0.04; judge 'is this answer right' vs judge 'is this a question I solve' (judge rows, solved minus not solved): -0.09; pre-solve vs that judge-role solved direction: 0.04.


## RB2 Math: 732 answers, 183 questions (84% of answers on questions the model solved)

### 1. Does each role's hidden state separate right from wrong answers? (within-question AUROC of a cross-validated probe)

| Layer | judge (someone else's answer) | generate (as its own answer) | self-check (own answer + 'is it correct?') |
|---|---|---|---|
| 2 | 0.73 | 0.67 | 0.76 |
| 4 | 0.75 | 0.70 | 0.75 |
| 6 | 0.74 | 0.70 | 0.76 |
| 8 | 0.78 | 0.66 | 0.73 |
| 10 | 0.80 | 0.71 | 0.76 |
| 12 | 0.81 | 0.73 | 0.79 |
| 14 | 0.81 | 0.79 | 0.82 |
| 16 | 0.81 | 0.79 | 0.84 |
| 18 | 0.83 | 0.81 | 0.86 |
| 20 | 0.83 | 0.79 | 0.85 |
| 22 | 0.83 | 0.81 | 0.85 |
| 24 | 0.84 | 0.82 | 0.83 |
| 26 | 0.84 | 0.82 | 0.83 |
| 28 | 0.83 | 0.82 | 0.85 |
| 30 | 0.84 | 0.82 | 0.85 |
| 32 | 0.84 | 0.83 | 0.85 |

Best layer per role, and the model's own spoken readout (log-odds of CORRECT at the verdict position):

| Role | best layer | probe: all questions | probe: solved | probe: **not solved** | spoken: all | spoken: solved | spoken: **not solved** |
|---|---|---|---|---|---|---|---|
| judge (someone else's answer) | 32 | 0.85 | 0.85 | 0.82 | 0.84 | 0.85 | 0.78 |
| generate (as its own answer) | 32 | 0.83 | 0.85 | 0.74 | – | – | – |
| self-check (own answer + 'is it correct?') | 18 | 0.86 | 0.88 | 0.75 | 0.83 | 0.84 | 0.74 |

### 2. Is it the same direction? (layer 32, the judge role's best)

Cosine between the difference-of-means directions (right minus wrong answers), computed on question-centred states (each answer minus its question's mean) so only within-question differences count. Noise ceiling = cosine between the same role's direction from two random halves of the questions.

| | judge | generate | self-check |
|---|---|---|---|
| judge (someone else's answer) (ceiling 0.99) | 1.00 | 0.05 | 0.93 |
| generate (as its own answer) (ceiling 0.82) | 0.05 | 1.00 | 0.05 |
| self-check (own answer + 'is it correct?') (ceiling 0.99) | 0.93 | 0.05 | 1.00 |

(Two random directions in 4096 dimensions: cosine ≈ ±0.016.)

Cross-transfer: a probe trained in one role (rows), tested in another (columns), on held-out questions. Within-question AUROC, all / **not solved**.

| trained on \ tested on | judge | generate | self-check |
|---|---|---|---|
| judge (someone else's answer) | 0.84 / **0.82** | 0.62 / **0.67** | 0.83 / **0.75** |
| generate (as its own answer) | 0.38 / **0.39** | 0.83 / **0.74** | 0.43 / **0.38** |
| self-check (own answer + 'is it correct?') | 0.68 / **0.72** | 0.53 / **0.59** | 0.85 / **0.82** |

Cosine judge-vs-generate and judge-vs-self-check at every layer, question-centred (ceilings: judge / generate split-half):

| Layer | judge·generate | judge·self-check | ceiling judge | ceiling generate |
|---|---|---|---|---|
| 2 | -0.04 | 0.94 | 0.80 | 0.59 |
| 4 | 0.05 | 0.83 | 0.63 | 0.51 |
| 6 | -0.03 | 0.79 | 0.68 | 0.64 |
| 8 | -0.04 | 0.74 | 0.80 | 0.63 |
| 10 | 0.05 | 0.73 | 0.88 | 0.65 |
| 12 | 0.09 | 0.55 | 0.85 | 0.67 |
| 14 | 0.08 | 0.61 | 0.89 | 0.75 |
| 16 | 0.07 | 0.69 | 0.92 | 0.77 |
| 18 | 0.03 | 0.71 | 0.92 | 0.83 |
| 20 | 0.02 | 0.83 | 0.96 | 0.86 |
| 22 | 0.04 | 0.83 | 0.96 | 0.89 |
| 24 | 0.02 | 0.89 | 0.98 | 0.87 |
| 26 | 0.05 | 0.89 | 0.99 | 0.87 |
| 28 | 0.05 | 0.93 | 0.99 | 0.85 |
| 30 | 0.03 | 0.94 | 0.99 | 0.83 |
| 32 | 0.05 | 0.93 | 0.99 | 0.82 |

### 4. 'Will I solve this?' before answering (layer 32)

Probe AUROC (questions held out): **0.33** over 182 questions (84% solved).

Cosines: pre-solve 'will I solve it' vs judge 'is this answer right': -0.01; judge 'is this answer right' vs judge 'is this a question I solve' (judge rows, solved minus not solved): 0.83; pre-solve vs that judge-role solved direction: 0.07.


## Its own answers (BBEH, 5 thinking-off answers per question)

Does the model's state after writing its OWN answer know whether that answer is right? Within-question AUROC compares its right and wrong answers to the same question.

| Role | best layer | probe | spoken (self-check) | judge-role probe transferred here |
|---|---|---|---|---|
| generate (as its own answer) | 16 | 0.68 | nan | 0.54 |
| self-check (own answer + 'is it correct?') | 18 | 0.69 | 0.61 | 0.58 |

(460 questions; pairs only exist where the model's 5 answers include both right and wrong ones.)

