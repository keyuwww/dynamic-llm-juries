# Stretching the judge direction at a rule-chosen layer: every judge × benchmark

Ranking = within-question AUROC (right answer scored above a wrong answer to the same question; 0.50 = coin flip). Gap = 100 × (best layer's direction ranking − verdict ranking). Gain = ranking change × 100 after stretching ×11 at the chosen layer [95% CI, questions resampled]. Same-model = only right-vs-wrong pairs written by the same answering model. Rule: out_allpairs/RULE.md.

| Benchmark | Judge | Gap | Layer (rule) | Accept −8 → +8 sd | Gain ×11, all | Not solved | Same-model, not solved | Same-model, solved | Random ×11 | Best of ×4/×11/×21 (all) |
|---|---|---|---|---|---|---|---|---|---|---|
| MMLU-Redux | Llama-3.1-8B | +12.6 | 16/32 (responds) | 79% → 97% | +6.8 [+5.0, +8.7] | +6.0 [+3.5, +8.7] | +0.4 [-4.4, +5.7] | +5.9 [+1.6, +10.3] | -0.2 | x21: +7.4 [+5.3, +9.5] |
| MMLU-Redux | Llama-3.2-3B | +11.6 | 12/None (none responds) | 93% → 91% | +4.0 [+2.1, +5.6] | +4.0 [+1.9, +6.3] | +3.3 [-0.9, +7.7] | +4.0 [-1.5, +9.8] | +0.3 | x11: +4.0 [+2.1, +5.6] |
| MMLU-Redux | Qwen3.5-9B | +0.8 | gap <= 5 (measured earlier) | | | | | | | |
| MMLU-Redux | Qwen3.5-4B | +1.2 | gap <= 5 (measured earlier) | | | | | | | |
| MMLU-Redux | Phi-4-mini | +7.2 | 16/32 (responds) | 69% → 96% | +3.8 [+2.2, +5.5] | +3.6 [+1.3, +6.1] | +0.3 [-3.6, +4.2] | +1.1 [-3.0, +5.4] | -0.2 | x21: +4.2 [+1.8, +6.4] |
| MMLU-Redux | Mistral-7B | +7.6 | 4/32 (none responds) | 99% → 99% | -0.5 [-1.2, +0.3] | – | – | – | -0.2 | x21: -0.4 [-1.4, +0.8] |
| MMLU-Redux | Granite-3.3-8B | – | not run / pending | | | | | | | |
| MATH | Llama-3.1-8B | +13.0 | 16/None (responds) | 43% → 98% | +8.2 [+6.0, +10.3] | +9.0 [+6.5, +11.6] | +2.7 [-2.0, +7.3] | -7.7 [-17.7, +1.7] | -0.6 | x11: +8.2 [+6.0, +10.3] |
| MATH | Llama-3.2-3B | – | not run / pending | | | | | | | |
| MATH | Qwen3.5-9B | +4.9 | gap <= 5 (measured earlier) | | | | | | | |
| MATH | Qwen3.5-4B | +2.0 | gap <= 5 | | | | | | | |
| MATH | Phi-4-mini | – | not run / pending | | | | | | | |
| MATH | Mistral-7B | – | not run / pending | | | | | | | |
| MATH | Granite-3.3-8B | – | not run / pending | | | | | | | |
| BBEH | Llama-3.1-8B | +11.2 | 14/32 (responds) | 47% → 73% | +11.8 [+4.5, +20.6] | +13.0 [+3.6, +24.0] | – | – | +2.2 | x11: +11.8 [+4.5, +20.6] |
| BBEH | Llama-3.2-3B | +10.3 | 14/28 (responds) | 29% → 43% | +3.8 [+0.7, +7.3] | – | – | – | +0.1 | x21: +4.5 [-0.2, +9.2] |
| BBEH | Qwen3.5-9B | -1.5 | gap <= 5 (measured earlier) | | | | | | | |
| BBEH | Qwen3.5-4B | +9.3 | 20/32 (responds) | 29% → 52% | – | – | – | – | +nan | x4: – |
| BBEH | Phi-4-mini | +10.8 | no final pass | | | | | | | |
| BBEH | Mistral-7B | – | not run / pending | | | | | | | |
| BBEH | Granite-3.3-8B | – | not run / pending | | | | | | | |

**Pooled over pairs** (inverse-variance weighted; pairs are not independent draws, so read as a summary):

| Pairs | k | Gain ×11, all | Not solved | Same-model, not solved | Same-model, solved |
|---|---|---|---|---|---|
| rule found a responding layer | 6 | +5.8 [+4.8, +6.8] | +6.3 [+4.8, +7.7] | +1.0 [-1.5, +3.6] | +2.4 [-0.5, +5.3] |
| all pairs with gap > 5 | 8 | +2.1 [+1.5, +2.7] | +5.6 [+4.4, +6.8] | +1.6 [-0.6, +3.8] | +2.7 [+0.2, +5.3] |

## Why a verdict does or doesn't respond (diagnostics)

corr = within-question correlation of the direction with the unedited verdict margin; src share = share of the direction's within-question spread explained by which model wrote the answer; push = accept rate at −8 → +8 sd, edit at the last token vs at every token.

### llama3.1-8b_math

| Layer | corr | src share | push, last token | push, every token |
|---|---|---|---|---|
| 2 | -0.50 | 0.84 | 95% → 94% | 97% → 94% |
| 4 | -0.29 | 0.85 | 94% → 94% | 96% → 95% |
| 6 | -0.24 | 0.85 | 94% → 96% | 96% → 89% |
| 8 | -0.18 | 0.81 | 94% → 95% | 98% → 88% |
| 10 | -0.16 | 0.83 | 96% → 94% | 87% → 96% |
| 12 | -0.03 | 0.84 | 96% → 94% | 90% → 98% |
| 14 | +0.31 | 0.77 | 95% → 96% | 83% → 99% |
| 16 | +0.67 | 0.85 | 44% → 99% | 44% → 100% |
| 18 | +0.74 | 0.85 | 46% → 98% | 46% → 98% |
| 20 | +0.78 | 0.87 | 46% → 98% | 45% → 98% |
| 22 | +0.81 | 0.87 | 46% → 99% | 48% → 99% |
| 24 | +0.83 | 0.88 | 46% → 100% | 46% → 100% |
| 26 | +0.86 | 0.88 | 44% → 100% | 46% → 100% |
| 28 | +0.88 | 0.87 | 36% → 100% | 40% → 100% |
| 30 | +0.90 | 0.86 | 29% → 100% | 33% → 100% |

### llama3.2-3b_mmlu

| Layer | corr | src share | push, last token | push, every token |
|---|---|---|---|---|
| 2 | -0.65 | 0.85 | 92% → 92% | 90% → 90% |
| 4 | -0.56 | 0.83 | 92% → 92% | 93% → 89% |
| 6 | -0.48 | 0.79 | 92% → 92% | 92% → 90% |
| 8 | -0.40 | 0.74 | 92% → 92% | 90% → 95% |
| 10 | -0.22 | 0.75 | 92% → 92% | 92% → 98% |
| 12 | -0.23 | 0.77 | 92% → 90% | 84% → 92% |
| 14 | -0.39 | 0.81 | 97% → 84% | 96% → 50% |
| 16 | -0.49 | 0.84 | 98% → 58% | 98% → 74% |
| 18 | -0.47 | 0.85 | 98% → 47% | 98% → 51% |
| 20 | -0.52 | 0.87 | 98% → 44% | 98% → 44% |
| 22 | -0.48 | 0.88 | 98% → 43% | 98% → 44% |
| 24 | -0.37 | 0.88 | 98% → 44% | 98% → 44% |
| 26 | -0.21 | 0.88 | 99% → 46% | 99% → 45% |

