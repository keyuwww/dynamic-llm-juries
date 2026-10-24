# Hidden-state probes on Modal (all models)

Probe = logistic regression on one layer, 5-fold CV grouped by question; best layer chosen on the same folds (slightly optimistic). Verdict = the model's own P(INCORRECT) after a forced "VERDICT:" with no reasoning.

## jeff

**Real BFF answers, no reference**

Within model = AUROC computed inside each answer model and averaged, which removes the 'who wrote it' signal; baseline = answer model + length alone.

| Read-out | n | Verdict AUROC | Probe AUROC (best layer) | Verdict, within model | Probe, within model | Baseline |
|---|---|---|---|---|---|---|
| answer is wrong, end | 459 | 0.65 | 0.83 (L16) | 0.67 | 0.81 | 0.80 |
| answer is wrong, verdict | 459 | 0.65 | 0.88 (L14) | 0.67 | 0.87 | 0.80 |
| experts split (501 of 960) | 960 | 0.46 (verdict near 50%) | 0.60 (L18) | | | |

Shared blind spot: among answers all experts marked wrong, do the ones a strong judge confidently ACCEPTED also look more correct to this small model? AUROC of the small model's 'looks correct' score (probe or verdict) for accepted vs caught; 0.5 = no relation, above 0.5 = the small model shares the blind spot.

| Strong judge | Wrong answers | Confidently accepted | Probe | Small model's verdict |
|---|---|---|---|---|
| gpt-oss-120b | 203 | 18 | 0.69 | 0.66 |
| qwen3.6-35b-a3b | 203 | 17 | 0.58 | 0.67 |
| deepseek-v3.1 | 203 | 38 | 0.65 | 0.64 |

**Real BFF answers, with reference**

Within model = AUROC computed inside each answer model and averaged, which removes the 'who wrote it' signal; baseline = answer model + length alone.

| Read-out | n | Verdict AUROC | Probe AUROC (best layer) | Verdict, within model | Probe, within model | Baseline |
|---|---|---|---|---|---|---|
| answer is wrong, end | 456 | 0.80 | 0.83 (L18) | 0.79 | 0.80 | 0.82 |
| answer is wrong, verdict | 456 | 0.80 | 0.98 (L14) | 0.79 | 0.98 | 0.82 |

**Planted errors, no reference**

| Position | n | Verdict AUROC | Probe AUROC |
|---|---|---|---|
| target | 944 | 0.60 | 0.94 (L24) |
| end | 944 | 0.60 | 0.82 (L24) |
| verdict | 944 | 0.60 | 0.90 (L16) |

| Type vs ORIG at verdict | n | Verdict | Probe |
|---|---|---|---|
| C1 | 52 | 0.45 | 0.66 |
| C2 | 223 | 0.51 | 0.48 |
| V1 | 125 | 0.57 | 0.84 |
| V2-1 | 86 | 0.63 | 0.93 |
| V2-10 | 84 | 0.63 | 0.94 |
| V2-lead | 76 | 0.58 | 0.93 |
| V2-x10 | 50 | 0.59 | 0.90 |

**Planted errors, with reference**

| Position | n | Verdict AUROC | Probe AUROC |
|---|---|---|---|
| target | 944 | 0.58 | 0.94 (L24) |
| end | 944 | 0.58 | 0.82 (L24) |
| verdict | 944 | 0.58 | 0.92 (L16) |

| Type vs ORIG at verdict | n | Verdict | Probe |
|---|---|---|---|
| C1 | 52 | 0.43 | 0.73 |
| C2 | 223 | 0.51 | 0.48 |
| V1 | 125 | 0.55 | 0.91 |
| V2-1 | 86 | 0.54 | 0.92 |
| V2-10 | 84 | 0.63 | 0.95 |
| V2-lead | 76 | 0.59 | 0.94 |
| V2-x10 | 50 | 0.55 | 0.91 |

## qwen3.5-0.8b

**Real BFF answers, no reference**

Within model = AUROC computed inside each answer model and averaged, which removes the 'who wrote it' signal; baseline = answer model + length alone.

| Read-out | n | Verdict AUROC | Probe AUROC (best layer) | Verdict, within model | Probe, within model | Baseline |
|---|---|---|---|---|---|---|
| answer is wrong, end | 459 | 0.63 | 0.81 (L14) | 0.64 | 0.78 | 0.80 |
| answer is wrong, verdict | 459 | 0.63 | 0.88 (L16) | 0.64 | 0.87 | 0.80 |
| experts split (501 of 960) | 960 | 0.49 (verdict near 50%) | 0.61 (L22) | | | |

Shared blind spot: among answers all experts marked wrong, do the ones a strong judge confidently ACCEPTED also look more correct to this small model? AUROC of the small model's 'looks correct' score (probe or verdict) for accepted vs caught; 0.5 = no relation, above 0.5 = the small model shares the blind spot.

| Strong judge | Wrong answers | Confidently accepted | Probe | Small model's verdict |
|---|---|---|---|---|
| gpt-oss-120b | 203 | 18 | 0.72 | 0.61 |
| qwen3.6-35b-a3b | 203 | 17 | 0.57 | 0.55 |
| deepseek-v3.1 | 203 | 38 | 0.66 | 0.68 |

**Real BFF answers, with reference**

Within model = AUROC computed inside each answer model and averaged, which removes the 'who wrote it' signal; baseline = answer model + length alone.

| Read-out | n | Verdict AUROC | Probe AUROC (best layer) | Verdict, within model | Probe, within model | Baseline |
|---|---|---|---|---|---|---|
| answer is wrong, end | 456 | 0.81 | 0.82 (L14) | 0.81 | 0.78 | 0.82 |
| answer is wrong, verdict | 456 | 0.81 | 0.98 (L16) | 0.81 | 0.97 | 0.82 |

**Planted errors, no reference**

| Position | n | Verdict AUROC | Probe AUROC |
|---|---|---|---|
| target | 944 | 0.61 | 0.94 (L24) |
| end | 944 | 0.61 | 0.77 (L14) |
| verdict | 944 | 0.61 | 0.85 (L18) |

| Type vs ORIG at verdict | n | Verdict | Probe |
|---|---|---|---|
| C1 | 52 | 0.37 | 0.64 |
| C2 | 223 | 0.51 | 0.47 |
| V1 | 125 | 0.55 | 0.76 |
| V2-1 | 86 | 0.60 | 0.88 |
| V2-10 | 84 | 0.60 | 0.89 |
| V2-lead | 76 | 0.63 | 0.87 |
| V2-x10 | 50 | 0.69 | 0.91 |

**Planted errors, with reference**

| Position | n | Verdict AUROC | Probe AUROC |
|---|---|---|---|
| target | 944 | 0.63 | 0.94 (L24) |
| end | 944 | 0.63 | 0.77 (L14) |
| verdict | 944 | 0.63 | 0.91 (L20) |

| Type vs ORIG at verdict | n | Verdict | Probe |
|---|---|---|---|
| C1 | 52 | 0.35 | 0.66 |
| C2 | 223 | 0.51 | 0.49 |
| V1 | 125 | 0.62 | 0.89 |
| V2-1 | 86 | 0.57 | 0.90 |
| V2-10 | 84 | 0.67 | 0.94 |
| V2-lead | 76 | 0.63 | 0.92 |
| V2-x10 | 50 | 0.60 | 0.90 |

## qwen3.5-4b

**Real BFF answers, no reference**

Within model = AUROC computed inside each answer model and averaged, which removes the 'who wrote it' signal; baseline = answer model + length alone.

| Read-out | n | Verdict AUROC | Probe AUROC (best layer) | Verdict, within model | Probe, within model | Baseline |
|---|---|---|---|---|---|---|
| answer is wrong, end | 459 | 0.84 | 0.85 (L16) | 0.82 | 0.83 | 0.80 |
| answer is wrong, verdict | 459 | 0.84 | 0.88 (L32) | 0.82 | 0.86 | 0.80 |
| experts split (501 of 960) | 960 | 0.50 (verdict near 50%) | 0.59 (L22) | | | |

Shared blind spot: among answers all experts marked wrong, do the ones a strong judge confidently ACCEPTED also look more correct to this small model? AUROC of the small model's 'looks correct' score (probe or verdict) for accepted vs caught; 0.5 = no relation, above 0.5 = the small model shares the blind spot.

| Strong judge | Wrong answers | Confidently accepted | Probe | Small model's verdict |
|---|---|---|---|---|
| gpt-oss-120b | 203 | 18 | 0.75 | 0.82 |
| qwen3.6-35b-a3b | 203 | 17 | 0.73 | 0.82 |
| deepseek-v3.1 | 203 | 38 | 0.71 | 0.85 |

**Real BFF answers, with reference**

Within model = AUROC computed inside each answer model and averaged, which removes the 'who wrote it' signal; baseline = answer model + length alone.

| Read-out | n | Verdict AUROC | Probe AUROC (best layer) | Verdict, within model | Probe, within model | Baseline |
|---|---|---|---|---|---|---|
| answer is wrong, end | 456 | 0.97 | 0.85 (L16) | 0.96 | 0.83 | 0.82 |
| answer is wrong, verdict | 456 | 0.97 | 0.99 (L16) | 0.96 | 0.99 | 0.82 |

**Question only (before any answer is shown)**

| Predicts | n | Positives | Probe AUROC |
|---|---|---|---|
| own verdict error | 459 | 116 | 0.66 (L6) |
| gptoss error | 459 | 64 | 0.60 (L20) |

**Planted errors, no reference**

| Position | n | Verdict AUROC | Probe AUROC |
|---|---|---|---|
| target | 944 | 0.88 | 0.96 (L32) |
| end | 944 | 0.88 | 0.88 (L18) |
| verdict | 944 | 0.88 | 0.93 (L20) |

| Type vs ORIG at verdict | n | Verdict | Probe |
|---|---|---|---|
| C1 | 52 | 0.59 | 0.69 |
| C2 | 223 | 0.50 | 0.48 |
| V1 | 125 | 0.79 | 0.85 |
| V2-1 | 86 | 0.90 | 0.96 |
| V2-10 | 84 | 0.94 | 0.98 |
| V2-lead | 76 | 0.89 | 0.96 |
| V2-x10 | 50 | 0.94 | 0.97 |

**Planted errors, with reference**

| Position | n | Verdict AUROC | Probe AUROC |
|---|---|---|---|
| target | 944 | 0.93 | 0.96 (L32) |
| end | 944 | 0.93 | 0.88 (L18) |
| verdict | 944 | 0.93 | 0.97 (L20) |

| Type vs ORIG at verdict | n | Verdict | Probe |
|---|---|---|---|
| C1 | 52 | 0.57 | 0.71 |
| C2 | 223 | 0.50 | 0.49 |
| V1 | 125 | 0.92 | 0.98 |
| V2-1 | 86 | 0.90 | 0.96 |
| V2-10 | 84 | 0.96 | 0.99 |
| V2-lead | 76 | 0.93 | 0.97 |
| V2-x10 | 50 | 0.94 | 0.98 |

## qwen3.5-9b

**Real BFF answers, no reference**

Within model = AUROC computed inside each answer model and averaged, which removes the 'who wrote it' signal; baseline = answer model + length alone.

| Read-out | n | Verdict AUROC | Probe AUROC (best layer) | Verdict, within model | Probe, within model | Baseline |
|---|---|---|---|---|---|---|
| answer is wrong, end | 459 | 0.84 | 0.87 (L18) | 0.83 | 0.85 | 0.80 |
| answer is wrong, verdict | 459 | 0.84 | 0.89 (L30) | 0.83 | 0.88 | 0.80 |
| experts split (501 of 960) | 960 | 0.52 (verdict near 50%) | 0.59 (L26) | | | |

Shared blind spot: among answers all experts marked wrong, do the ones a strong judge confidently ACCEPTED also look more correct to this small model? AUROC of the small model's 'looks correct' score (probe or verdict) for accepted vs caught; 0.5 = no relation, above 0.5 = the small model shares the blind spot.

| Strong judge | Wrong answers | Confidently accepted | Probe | Small model's verdict |
|---|---|---|---|---|
| gpt-oss-120b | 203 | 18 | 0.84 | 0.87 |
| qwen3.6-35b-a3b | 203 | 17 | 0.79 | 0.84 |
| deepseek-v3.1 | 203 | 38 | 0.78 | 0.91 |

**Real BFF answers, with reference**

Within model = AUROC computed inside each answer model and averaged, which removes the 'who wrote it' signal; baseline = answer model + length alone.

| Read-out | n | Verdict AUROC | Probe AUROC (best layer) | Verdict, within model | Probe, within model | Baseline |
|---|---|---|---|---|---|---|
| answer is wrong, end | 456 | 0.97 | 0.87 (L18) | 0.96 | 0.85 | 0.82 |
| answer is wrong, verdict | 456 | 0.97 | 0.99 (L18) | 0.96 | 0.99 | 0.82 |

**Question only (before any answer is shown)**

| Predicts | n | Positives | Probe AUROC |
|---|---|---|---|
| own verdict error | 459 | 113 | 0.64 (L12) |
| gptoss error | 459 | 64 | 0.62 (L18) |

**Planted errors, no reference**

| Position | n | Verdict AUROC | Probe AUROC |
|---|---|---|---|
| target | 944 | 0.86 | 0.97 (L32) |
| end | 944 | 0.86 | 0.90 (L18) |
| verdict | 944 | 0.86 | 0.94 (L32) |

| Type vs ORIG at verdict | n | Verdict | Probe |
|---|---|---|---|
| C1 | 52 | 0.60 | 0.69 |
| C2 | 223 | 0.50 | 0.49 |
| V1 | 125 | 0.78 | 0.88 |
| V2-1 | 86 | 0.88 | 0.97 |
| V2-10 | 84 | 0.93 | 0.99 |
| V2-lead | 76 | 0.87 | 0.97 |
| V2-x10 | 50 | 0.94 | 0.98 |

**Planted errors, with reference**

| Position | n | Verdict AUROC | Probe AUROC |
|---|---|---|---|
| target | 944 | 0.92 | 0.97 (L32) |
| end | 944 | 0.92 | 0.90 (L18) |
| verdict | 944 | 0.92 | 0.98 (L22) |

| Type vs ORIG at verdict | n | Verdict | Probe |
|---|---|---|---|
| C1 | 52 | 0.59 | 0.66 |
| C2 | 223 | 0.50 | 0.49 |
| V1 | 125 | 0.92 | 0.97 |
| V2-1 | 86 | 0.90 | 0.97 |
| V2-10 | 84 | 0.94 | 0.99 |
| V2-lead | 76 | 0.92 | 0.99 |
| V2-x10 | 50 | 0.92 | 0.98 |

