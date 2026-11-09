# Solve vs judge directions — llama3.1-8b

9558 rows; layers kept: [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32]


## BBEH: 2244 answers, 447 questions (12% of answers on questions the model solved)

### 1. Does each role's hidden state separate right from wrong answers? (within-question AUROC of a cross-validated probe)

| Layer | judge (someone else's answer) | generate (as its own answer) | self-check (own answer + 'is it correct?') |
|---|---|---|---|
| 2 | 0.61 | 0.67 | 0.62 |
| 4 | 0.64 | 0.68 | 0.65 |
| 6 | 0.65 | 0.66 | 0.61 |
| 8 | 0.67 | 0.64 | 0.62 |
| 10 | 0.63 | 0.66 | 0.67 |
| 12 | 0.68 | 0.68 | 0.68 |
| 14 | 0.67 | 0.66 | 0.63 |
| 16 | 0.66 | 0.64 | 0.63 |
| 18 | 0.65 | 0.66 | 0.65 |
| 20 | 0.64 | 0.64 | 0.68 |
| 22 | 0.67 | 0.63 | 0.67 |
| 24 | 0.68 | 0.64 | 0.66 |
| 26 | 0.68 | 0.67 | 0.67 |
| 28 | 0.68 | 0.68 | 0.69 |
| 30 | 0.70 | 0.68 | 0.70 |
| 32 | 0.69 | 0.67 | 0.71 |

Best layer per role, and the model's own spoken readout (log-odds of CORRECT at the verdict position):

| Role | best layer | probe: all questions | probe: solved | probe: **not solved** | spoken: all | spoken: solved | spoken: **not solved** |
|---|---|---|---|---|---|---|---|
| judge (someone else's answer) | 30 | 0.69 | 0.71 | 0.69 | 0.56 | 0.68 | 0.53 |
| generate (as its own answer) | 4 | 0.68 | 0.70 | 0.67 | – | – | – |
| self-check (own answer + 'is it correct?') | 32 | 0.71 | 0.74 | 0.70 | 0.52 | 0.64 | 0.50 |

### 2. Is it the same direction? (layer 30, the judge role's best)

Cosine between the difference-of-means directions (right minus wrong answers), computed on question-centred states (each answer minus its question's mean) so only within-question differences count. Noise ceiling = cosine between the same role's direction from two random halves of the questions.

| | judge | generate | self-check |
|---|---|---|---|
| judge (someone else's answer) (ceiling 0.82) | 1.00 | 0.04 | 0.67 |
| generate (as its own answer) (ceiling 0.80) | 0.04 | 1.00 | 0.06 |
| self-check (own answer + 'is it correct?') (ceiling 0.72) | 0.67 | 0.06 | 1.00 |

(Two random directions in 4096 dimensions: cosine ≈ ±0.016.)

Cross-transfer: a probe trained in one role (rows), tested in another (columns), on held-out questions. Within-question AUROC, all / **not solved**.

| trained on \ tested on | judge | generate | self-check |
|---|---|---|---|
| judge (someone else's answer) | 0.70 / **0.69** | 0.46 / **0.44** | 0.66 / **0.67** |
| generate (as its own answer) | 0.55 / **0.54** | 0.68 / **0.67** | 0.54 / **0.52** |
| self-check (own answer + 'is it correct?') | 0.66 / **0.66** | 0.53 / **0.52** | 0.70 / **0.69** |

Cosine judge-vs-generate and judge-vs-self-check at every layer, question-centred (ceilings: judge / generate split-half):

| Layer | judge·generate | judge·self-check | ceiling judge | ceiling generate |
|---|---|---|---|---|
| 2 | 0.09 | 0.99 | 0.92 | 0.42 |
| 4 | 0.08 | 0.92 | 0.89 | 0.54 |
| 6 | 0.03 | 0.80 | 0.91 | 0.57 |
| 8 | -0.01 | 0.82 | 0.92 | 0.57 |
| 10 | -0.03 | 0.75 | 0.93 | 0.59 |
| 12 | -0.01 | 0.72 | 0.89 | 0.60 |
| 14 | 0.04 | 0.72 | 0.83 | 0.66 |
| 16 | 0.02 | 0.64 | 0.81 | 0.65 |
| 18 | 0.02 | 0.64 | 0.84 | 0.71 |
| 20 | 0.02 | 0.64 | 0.85 | 0.73 |
| 22 | 0.02 | 0.65 | 0.84 | 0.72 |
| 24 | 0.01 | 0.65 | 0.83 | 0.72 |
| 26 | 0.01 | 0.66 | 0.83 | 0.78 |
| 28 | 0.01 | 0.66 | 0.82 | 0.79 |
| 30 | 0.04 | 0.67 | 0.82 | 0.80 |
| 32 | 0.11 | 0.67 | 0.73 | 0.81 |

### 4. 'Will I solve this?' before answering (layer 30)

Probe AUROC (questions held out): **0.74** over 410 questions (10% solved).

Cosines: pre-solve 'will I solve it' vs judge 'is this answer right': 0.02; judge 'is this answer right' vs judge 'is this a question I solve' (judge rows, solved minus not solved): 0.28; pre-solve vs that judge-role solved direction: 0.22.


## RB2 Math: 732 answers, 183 questions (33% of answers on questions the model solved)

### 1. Does each role's hidden state separate right from wrong answers? (within-question AUROC of a cross-validated probe)

| Layer | judge (someone else's answer) | generate (as its own answer) | self-check (own answer + 'is it correct?') |
|---|---|---|---|
| 2 | 0.72 | 0.63 | 0.74 |
| 4 | 0.72 | 0.69 | 0.74 |
| 6 | 0.71 | 0.66 | 0.75 |
| 8 | 0.75 | 0.71 | 0.75 |
| 10 | 0.74 | 0.72 | 0.75 |
| 12 | 0.76 | 0.73 | 0.77 |
| 14 | 0.77 | 0.74 | 0.78 |
| 16 | 0.79 | 0.73 | 0.79 |
| 18 | 0.79 | 0.74 | 0.77 |
| 20 | 0.79 | 0.73 | 0.79 |
| 22 | 0.78 | 0.71 | 0.77 |
| 24 | 0.78 | 0.72 | 0.79 |
| 26 | 0.78 | 0.72 | 0.79 |
| 28 | 0.78 | 0.72 | 0.80 |
| 30 | 0.77 | 0.70 | 0.79 |
| 32 | 0.79 | 0.73 | 0.82 |

Best layer per role, and the model's own spoken readout (log-odds of CORRECT at the verdict position):

| Role | best layer | probe: all questions | probe: solved | probe: **not solved** | spoken: all | spoken: solved | spoken: **not solved** |
|---|---|---|---|---|---|---|---|
| judge (someone else's answer) | 20 | 0.79 | 0.87 | 0.75 | 0.73 | 0.76 | 0.72 |
| generate (as its own answer) | 18 | 0.74 | 0.74 | 0.74 | – | – | – |
| self-check (own answer + 'is it correct?') | 32 | 0.82 | 0.84 | 0.81 | 0.65 | 0.63 | 0.66 |

### 2. Is it the same direction? (layer 20, the judge role's best)

Cosine between the difference-of-means directions (right minus wrong answers), computed on question-centred states (each answer minus its question's mean) so only within-question differences count. Noise ceiling = cosine between the same role's direction from two random halves of the questions.

| | judge | generate | self-check |
|---|---|---|---|
| judge (someone else's answer) (ceiling 0.98) | 1.00 | 0.11 | 0.64 |
| generate (as its own answer) (ceiling 0.70) | 0.11 | 1.00 | 0.11 |
| self-check (own answer + 'is it correct?') (ceiling 0.90) | 0.64 | 0.11 | 1.00 |

(Two random directions in 4096 dimensions: cosine ≈ ±0.016.)

Cross-transfer: a probe trained in one role (rows), tested in another (columns), on held-out questions. Within-question AUROC, all / **not solved**.

| trained on \ tested on | judge | generate | self-check |
|---|---|---|---|
| judge (someone else's answer) | 0.79 / **0.75** | 0.54 / **0.56** | 0.73 / **0.70** |
| generate (as its own answer) | 0.68 / **0.65** | 0.73 / **0.75** | 0.62 / **0.61** |
| self-check (own answer + 'is it correct?') | 0.64 / **0.60** | 0.57 / **0.57** | 0.79 / **0.77** |

Cosine judge-vs-generate and judge-vs-self-check at every layer, question-centred (ceilings: judge / generate split-half):

| Layer | judge·generate | judge·self-check | ceiling judge | ceiling generate |
|---|---|---|---|---|
| 2 | 0.07 | 0.97 | 0.74 | 0.56 |
| 4 | 0.09 | 0.92 | 0.74 | 0.50 |
| 6 | 0.16 | 0.83 | 0.74 | 0.56 |
| 8 | 0.10 | 0.76 | 0.73 | 0.60 |
| 10 | -0.02 | 0.71 | 0.65 | 0.55 |
| 12 | 0.04 | 0.58 | 0.63 | 0.57 |
| 14 | 0.09 | 0.65 | 0.88 | 0.58 |
| 16 | 0.12 | 0.51 | 0.94 | 0.64 |
| 18 | 0.11 | 0.56 | 0.97 | 0.70 |
| 20 | 0.11 | 0.64 | 0.98 | 0.70 |
| 22 | 0.11 | 0.68 | 0.98 | 0.70 |
| 24 | 0.09 | 0.65 | 0.98 | 0.70 |
| 26 | 0.06 | 0.68 | 0.99 | 0.76 |
| 28 | 0.03 | 0.69 | 0.99 | 0.77 |
| 30 | 0.03 | 0.66 | 0.98 | 0.77 |
| 32 | 0.06 | 0.57 | 0.97 | 0.75 |

### 4. 'Will I solve this?' before answering (layer 20)

Probe AUROC (questions held out): **0.73** over 178 questions (34% solved).

Cosines: pre-solve 'will I solve it' vs judge 'is this answer right': -0.01; judge 'is this answer right' vs judge 'is this a question I solve' (judge rows, solved minus not solved): -0.22; pre-solve vs that judge-role solved direction: 0.07.

