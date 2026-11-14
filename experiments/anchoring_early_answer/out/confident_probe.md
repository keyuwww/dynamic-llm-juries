# Can the judge tell its wrong confident beliefs from its right ones?

Candidates with belief >= 4/7 (the judge itself gives this answer in at least 4 of 7 tries). AUROC for right vs wrong on held-out questions (0.5 = chance). 95% intervals resample questions. 'Probe minus verdict' is paired on the same candidates.


## qwen3.5-9b, rb2math: 216 confident candidates (157 right, 59 wrong) on 161 questions; 36 questions have both

| signal | AUROC right vs wrong | minus the verdict at C (paired) |
|---|---|---|
| probe on this answer's state | 0.73 [0.63, 0.82] | +0.03 [-0.07, +0.13] |
| question-only probe (no answer-specific information) | 0.71 [0.64, 0.78] | +0.01 [-0.10, +0.12] |
| judge's verdict at A (before reasoning) | 0.71 [0.63, 0.79] | +0.00 [-0.06, +0.06] |
| judge's verdict at C (at the verdict) | 0.70 [0.62, 0.79] | – |
| belief (4/7 .. 7/7) | 0.57 [0.50, 0.65] | -0.13 [-0.23, -0.03] |

Cells chosen (answer probe): A/L32, A/L20, A/L26, A/L30, A/L24; (question-only): C/L30, 75/L22, 75/L20, 75/L22, 75/L22

Flag the 20% the probe rates least likely right: catches 17 of 42 wrong answers the judge accepted, and flags 9 of 144 right answers it accepted.

Same rule on the judge's own verdict log-odds at C: catches 6 of 42 and flags 8 of 144.

Among the 186 confident answers the judge accepted (42 wrong): AUROC right vs wrong

| signal | AUROC among accepted | minus the verdict at C (paired) |
|---|---|---|
| probe on this answer's state | 0.69 [0.56, 0.81] | +0.03 [-0.09, +0.16] |
| question-only probe | 0.73 [0.65, 0.82] | +0.08 [-0.05, +0.20] |
| judge's verdict at A | 0.66 [0.57, 0.76] | +0.01 [-0.07, +0.10] |
| judge's verdict at C | 0.65 [0.55, 0.76] | – |


## qwen3.5-9b, bff: 261 confident candidates (222 right, 39 wrong) on 70 questions; 15 questions have both

| signal | AUROC right vs wrong | minus the verdict at C (paired) |
|---|---|---|
| probe on this answer's state | 0.82 [0.74, 0.89] | +0.11 [-0.03, +0.24] |
| question-only probe (no answer-specific information) | 0.65 [0.51, 0.77] | -0.06 [-0.26, +0.09] |
| judge's verdict at A (before reasoning) | 0.75 [0.67, 0.83] | +0.04 [-0.06, +0.14] |
| judge's verdict at C (at the verdict) | 0.71 [0.62, 0.82] | – |
| belief (4/7 .. 7/7) | 0.74 [0.65, 0.85] | +0.03 [-0.06, +0.14] |

Cells chosen (answer probe): A/L24, A/L20, A/L18, A/L18, A/L20; (question-only): A/L14, A/L28, 50/L32, 50/L2, A/L28

Flag the 20% the probe rates least likely right: catches 13 of 25 wrong answers the judge accepted, and flags 24 of 191 right answers it accepted.

Same rule on the judge's own verdict log-odds at C: catches 3 of 25 and flags 5 of 191.

Among the 216 confident answers the judge accepted (25 wrong): AUROC right vs wrong

| signal | AUROC among accepted | minus the verdict at C (paired) |
|---|---|---|
| probe on this answer's state | 0.84 [0.74, 0.91] | +0.18 [-0.00, +0.34] |
| question-only probe | 0.72 [0.56, 0.86] | +0.06 [-0.14, +0.23] |
| judge's verdict at A | 0.74 [0.64, 0.84] | +0.08 [-0.09, +0.25] |
| judge's verdict at C | 0.66 [0.51, 0.80] | – |


## qwen3.5-4b, rb2math: 218 confident candidates (157 right, 61 wrong) on 161 questions; 39 questions have both

| signal | AUROC right vs wrong | minus the verdict at C (paired) |
|---|---|---|
| probe on this answer's state | 0.68 [0.57, 0.78] | -0.01 [-0.11, +0.08] |
| question-only probe (no answer-specific information) | 0.63 [0.55, 0.71] | -0.07 [-0.21, +0.07] |
| judge's verdict at A (before reasoning) | 0.72 [0.64, 0.80] | +0.02 [-0.04, +0.09] |
| judge's verdict at C (at the verdict) | 0.69 [0.60, 0.79] | – |
| belief (4/7 .. 7/7) | 0.57 [0.50, 0.65] | -0.12 [-0.24, -0.01] |

Cells chosen (answer probe): A/L20, 75/L32, 75/L20, A/L20, 25/L20; (question-only): 25/L18, 75/L24, 25/L10, C/L20, 75/L24

Flag the 20% the probe rates least likely right: catches 8 of 43 wrong answers the judge accepted, and flags 16 of 145 right answers it accepted.

Same rule on the judge's own verdict log-odds at C: catches 4 of 43 and flags 10 of 145.

Among the 188 confident answers the judge accepted (43 wrong): AUROC right vs wrong

| signal | AUROC among accepted | minus the verdict at C (paired) |
|---|---|---|
| probe on this answer's state | 0.62 [0.50, 0.74] | -0.01 [-0.13, +0.13] |
| question-only probe | 0.69 [0.58, 0.78] | +0.07 [-0.09, +0.20] |
| judge's verdict at A | 0.67 [0.59, 0.75] | +0.04 [-0.05, +0.13] |
| judge's verdict at C | 0.63 [0.52, 0.74] | – |


## qwen3.5-4b, bff: 250 confident candidates (213 right, 37 wrong) on 69 questions; 11 questions have both

| signal | AUROC right vs wrong | minus the verdict at C (paired) |
|---|---|---|
| probe on this answer's state | 0.85 [0.76, 0.92] | +0.09 [-0.02, +0.17] |
| question-only probe (no answer-specific information) | 0.82 [0.70, 0.90] | +0.06 [-0.11, +0.18] |
| judge's verdict at A (before reasoning) | 0.81 [0.73, 0.87] | +0.04 [-0.04, +0.12] |
| judge's verdict at C (at the verdict) | 0.76 [0.68, 0.86] | – |
| belief (4/7 .. 7/7) | 0.68 [0.59, 0.76] | -0.08 [-0.20, +0.03] |

Cells chosen (answer probe): A/L24, A/L20, A/L16, A/L22, A/L18; (question-only): A/L26, A/L20, A/L20, A/L10, A/L18

Flag the 20% the probe rates least likely right: catches 12 of 23 wrong answers the judge accepted, and flags 22 of 184 right answers it accepted.

Same rule on the judge's own verdict log-odds at C: catches 3 of 23 and flags 4 of 184.

Among the 207 confident answers the judge accepted (23 wrong): AUROC right vs wrong

| signal | AUROC among accepted | minus the verdict at C (paired) |
|---|---|---|
| probe on this answer's state | 0.81 [0.69, 0.91] | +0.07 [-0.11, +0.19] |
| question-only probe | 0.82 [0.68, 0.90] | +0.08 [-0.12, +0.22] |
| judge's verdict at A | 0.83 [0.75, 0.89] | +0.09 [-0.03, +0.18] |
| judge's verdict at C | 0.74 [0.64, 0.88] | – |

