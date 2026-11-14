# Interior-layer gain: better ranking or just a better cutoff?

## Summary (plain English)

- Of the 41 main cells with usable scores (7 judges x BFF/BiGGen/HealthBench x rubric/no rubric, minus 1 skipped), 15 show a real held-out gain from reading an interior layer; 26 show none.
- **Mostly cutoff** (just moving the final layer's yes/no threshold, fitted on the other half, recovers >= 70% of the gain): 8 cells -- qwen3.5-4b (4), nemotron3-nano-30b (2), gpt-oss-120b (1), qwen3.6-35b-a3b (1).
- **Mostly ranking** (re-thresholding the final layer recovers < 30%; the interior layer orders items better): 2 cells -- gpt-oss-120b (1), nemotron3-nano-30b (1).
- **Mixed** (30-70% recovered): 4 cells -- gpt-oss-120b (3), qwen3.5-4b (1); **neither** (< 30% recovered but no AUROC gain either): 1 -- nemotron3-super-120b (1).
- AUROC (how well a score sorts good answers above bad ones, ignoring any threshold; 0.5 = chance, 1 = perfect) agrees: mean AUROC gain of the chosen layer over the final layer is -0.012 in 'mostly cutoff' cells, +0.034 in 'mixed' cells and +0.121 in 'mostly ranking' cells. Caveat for qwen3.5-4b: part of its 'gain' is already there in the final layer's own logit-lens readout at 0.5 (column a' vs a; bff_rubric 30%, bff_standard 85%, biggen_rubric 67%, biggen_standard 24%, healthbench_standard 79% of the gain), i.e. the lens and the recorded verdict disagree; the rest is the cutoff. Either way the interior layer adds no ranking there.

## What was done

Same split protocol as `experiments/interp/held_out_significance.py` (seed 0, 200 random half/half splits, layer chosen on half A by Cohen's kappa of the argmax verdict, scored on half B). Reproduction check: (c)-(a) matches the saved per-split gaps in `significance_results/*.json` to within 0.0e+00 (max abs difference over all splits of all 44 cells that have a saved file).

On half A we also fit a single cutoff on the final layer's P(positive label) (two-way renormalised logit-lens probability at the verdict position; monotone in the logit margin) to maximise kappa. On half B:

- **(a) final** = the final verdict exactly as the original analysis used it (the run's recorded argmax prediction);
- **(b) recal. final** = final-layer score with the cutoff fitted on A;
- **(c) layer** = layer chosen on A, argmax verdict (P >= 0.5) -- the original 'interior layer';
- **AUROC final / layer** = threshold-free ranking quality of the final-layer score / the chosen layer's score on B.

Cohen's kappa = agreement with the human label corrected for chance (0 = no better than guessing from base rates, 1 = perfect). 'gain' = (c) - (a). 'recovered by recal.' = mean((b) - (a)) / mean((c) - (a)) -- the share of the interior-layer gain you also get by keeping the final layer and only moving its threshold. Brackets = 2.5-97.5 percentiles of the per-split values over the 200 splits (spread you would see on a fresh half-size test set). A cell counts as 'gain' only if the mean gain >= 0.02 kappa and the original script's bootstrap CI on the mean gap excludes 0. 'layer (depth)' = modal chosen layer index / last index (index 0 = embeddings, last = final hidden state). Mean (a)/(b)/(c) are averages over the 200 B halves.

‡ = the recorded final verdict and the final-layer lens score at 0.5 disagree on > 5% of items (seen only for Qwen models; a likely but unverified cause is the lens applying the final norm to a last hidden state that is already normed, so for these cells the 'final-layer score' used for (a'), (b) and AUROC is a close but not identical proxy for the model's own output logits, which were not saved). Per-cell agreement is in results.json (`final_pred_vs_lens_agree`). (a') = final-layer lens score thresholded at 0.5.

## Main cells (41)

| cell | n | layer (depth) | (a) final | (a') lens final @0.5 | (b) recal. final | (c) layer | gain (c-a) [95% over splits] | recovered by recal. | AUROC final | AUROC layer | AUROC gain [95% over splits] | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bff_rubric / gpt-oss-120b | 459 | 32/36 (89%) | 0.040 | 0.051 | 0.095 | 0.208 | +0.167 [+0.04, +0.26] | 33% | 0.583 | 0.638 | +0.055 [+0.02, +0.10] | **mixed** |
| bff_standard / gpt-oss-120b | 459 | 10/36 (28%) | -0.050 | -0.006 | -0.024 | 0.111 | +0.161 [+0.00, +0.29] | 16% | 0.478 | 0.599 | +0.121 [-0.00, +0.19] | **mostly ranking** |
| biggen_rubric / gpt-oss-120b | 459 | 4/36 (11%) | 0.001 | -0.004 | 0.041 | 0.106 | +0.105 [-0.04, +0.19] | 38% | 0.526 | 0.582 | +0.056 [-0.06, +0.13] | **mixed** |
| biggen_standard / gpt-oss-120b | 459 | 30/36 (83%) | 0.001 | 0.010 | 0.060 | 0.112 | +0.111 [-0.02, +0.20] | 53% | 0.534 | 0.583 | +0.049 [-0.03, +0.11] | **mixed** |
| healthbench_rubric / gpt-oss-120b | 2500 | 34/36 (94%) | 0.000 | 0.000 | 0.019 | 0.025 | +0.025 [-0.01, +0.05] | 77% | 0.520 | 0.530 | +0.011 [-0.05, +0.04] | **mostly cutoff** |
| healthbench_standard / gpt-oss-120b | 2500 | 36/36 (100%) | 0.054 | 0.056 | 0.074 | 0.043 | -0.011 [-0.06, +0.01] | -- | 0.573 | 0.563 | -0.011 [-0.06, +0.00] | **no gain** |
| bff_standard / gpt-oss-20b | 459 | 0/24 (0%) | 0.006 | 0.006 | 0.133 | 0.000 | -0.006 [-0.01, +0.00] | -- | 0.591 | 0.541 | -0.050 [-0.14, +0.00] | **no gain** |
| biggen_rubric / gpt-oss-20b | 459 | 0/24 (0%) | 0.006 | 0.000 | 0.162 | 0.000 | -0.006 [-0.01, +0.00] | -- | 0.633 | 0.500 | -0.133 [-0.18, -0.09] | **no gain** |
| biggen_standard / gpt-oss-20b | 459 | 24/24 (100%) | 0.005 | 0.005 | 0.248 | 0.000 | -0.005 [-0.01, +0.00] | -- | 0.654 | 0.581 | -0.074 [-0.20, +0.00] | **no gain** |
| healthbench_rubric / gpt-oss-20b | 2500 | 24/24 (100%) | 0.044 | 0.044 | 0.091 | 0.041 | -0.003 [-0.08, +0.02] | -- | 0.611 | 0.606 | -0.004 [-0.11, +0.00] | **no gain** |
| healthbench_standard / gpt-oss-20b | 2500 | 0/24 (0%) | 0.000 | 0.000 | 0.058 | 0.000 | +0.000 [+0.00, +0.00] | -- | 0.599 | 0.500 | -0.099 [-0.13, -0.07] | **no gain** |
| bff_rubric / nemotron3-nano-30b | 459 | 52/52 (100%) | 0.282 | 0.282 | 0.293 | 0.282 | +0.000 [+0.00, +0.00] | -- | 0.693 | 0.693 | +0.000 [+0.00, +0.00] | **no gain** |
| bff_standard / nemotron3-nano-30b | 459 | 41/52 (79%) | 0.100 | 0.100 | 0.125 | 0.329 | +0.229 [+0.14, +0.30] | 11% | 0.579 | 0.699 | +0.120 [+0.07, +0.17] | **mostly ranking** |
| biggen_rubric / nemotron3-nano-30b | 459 | 44/52 (85%) | 0.016 | 0.016 | 0.193 | 0.243 | +0.226 [+0.13, +0.32] | 78% | 0.666 | 0.647 | -0.019 [-0.08, +0.02] | **mostly cutoff** |
| biggen_standard / nemotron3-nano-30b | 459 | 37/52 (71%) | 0.207 | 0.207 | 0.172 | 0.190 | -0.016 [-0.11, +0.01] | -- | 0.650 | 0.645 | -0.004 [-0.04, +0.03] | **no gain** |
| healthbench_rubric / nemotron3-nano-30b | 2500 | 52/52 (100%) | 0.092 | 0.092 | 0.097 | 0.086 | -0.006 [-0.08, +0.00] | -- | 0.579 | 0.576 | -0.003 [-0.04, +0.00] | **no gain** |
| healthbench_standard / nemotron3-nano-30b | 2500 | 34/52 (65%) | 0.177 | 0.177 | 0.287 | 0.273 | +0.096 [+0.05, +0.14] | 114% | 0.712 | 0.696 | -0.016 [-0.04, +0.01] | **mostly cutoff** |
| bff_rubric / nemotron3-super-120b | 459 | 88/88 (100%) | 0.489 | 0.489 | 0.462 | 0.466 | -0.023 [-0.13, +0.00] | -- | 0.826 | 0.824 | -0.001 [-0.03, +0.01] | **no gain** |
| bff_standard / nemotron3-super-120b | 459 | 82/88 (93%) | 0.446 | 0.446 | 0.427 | 0.471 | +0.025 [-0.06, +0.08] | -74% | 0.810 | 0.811 | +0.001 [-0.02, +0.02] | **neither** |
| biggen_rubric / nemotron3-super-120b | 459 | 83/88 (94%) | 0.469 | 0.469 | 0.506 | 0.448 | -0.021 [-0.08, +0.00] | -- | 0.821 | 0.819 | -0.002 [-0.01, +0.01] | **no gain** |
| biggen_standard / nemotron3-super-120b | 459 | 83/88 (94%) | 0.342 | 0.342 | 0.338 | 0.339 | -0.003 [-0.07, +0.03] | -- | 0.736 | 0.728 | -0.008 [-0.03, +0.01] | **no gain** |
| healthbench_rubric / nemotron3-super-120b | 2500 | 88/88 (100%) | 0.247 | 0.247 | 0.514 | 0.247 | +0.000 [+0.00, +0.00] | -- | 0.830 | 0.830 | +0.000 [+0.00, +0.00] | **no gain** |
| healthbench_standard / nemotron3-super-120b | 2500 | 88/88 (100%) | 0.376 | 0.376 | 0.370 | 0.369 | -0.007 [-0.03, +0.00] | -- | 0.746 | 0.748 | +0.002 [-0.00, +0.01] | **no gain** |
| bff_rubric / qwen3.5-4b ‡ | 459 | 25/32 (78%) | 0.005 | 0.108 | 0.414 | 0.352 | +0.347 [+0.26, +0.43] | 118% | 0.793 | 0.756 | -0.037 [-0.08, +0.02] | **mostly cutoff** |
| bff_standard / qwen3.5-4b ‡ | 459 | 26/32 (81%) | 0.297 | 0.443 | 0.480 | 0.469 | +0.172 [+0.08, +0.26] | 107% | 0.824 | 0.830 | +0.006 [-0.02, +0.03] | **mostly cutoff** |
| biggen_rubric / qwen3.5-4b ‡ | 459 | 31/32 (97%) | 0.285 | 0.375 | 0.432 | 0.419 | +0.134 [+0.06, +0.22] | 110% | 0.798 | 0.782 | -0.016 [-0.04, -0.00] | **mostly cutoff** |
| biggen_standard / qwen3.5-4b | 459 | 25/32 (78%) | 0.199 | 0.232 | 0.386 | 0.339 | +0.140 [+0.06, +0.22] | 133% | 0.748 | 0.723 | -0.025 [-0.05, -0.00] | **mostly cutoff** |
| healthbench_rubric / qwen3.5-4b ‡ | 2500 | 29/32 (91%) | 0.199 | 0.194 | 0.269 | 0.199 | -0.001 [-0.04, +0.04] | -- | 0.720 | 0.711 | -0.009 [-0.02, +0.00] | **no gain** |
| healthbench_standard / qwen3.5-4b | 2500 | 26/32 (81%) | 0.233 | 0.261 | 0.257 | 0.268 | +0.036 [-0.00, +0.07] | 68% | 0.686 | 0.664 | -0.022 [-0.06, +0.00] | **mixed** |
| bff_rubric / qwen3.5-9b ‡ | 459 | 32/32 (100%) | 0.502 | 0.470 | 0.458 | 0.470 | -0.032 [-0.08, +0.02] | -- | 0.820 | 0.820 | +0.000 [+0.00, +0.00] | **no gain** |
| bff_standard / qwen3.5-9b | 459 | 32/32 (100%) | 0.264 | 0.184 | 0.492 | 0.169 | -0.095 [-0.26, -0.05] | -- | 0.835 | 0.806 | -0.029 [-0.35, +0.00] | **no gain** |
| biggen_rubric / qwen3.5-9b ‡ | 459 | 32/32 (100%) | 0.384 | 0.253 | 0.419 | 0.253 | -0.131 [-0.18, -0.08] | -- | 0.803 | 0.803 | +0.000 [+0.00, +0.00] | **no gain** |
| biggen_standard / qwen3.5-9b | 459 | 26/32 (81%) | 0.333 | 0.331 | 0.313 | 0.330 | -0.002 [-0.09, +0.05] | -- | 0.726 | 0.724 | -0.002 [-0.02, +0.01] | **no gain** |
| healthbench_rubric / qwen3.5-9b ‡ | 2500 | 32/32 (100%) | 0.281 | 0.214 | 0.398 | 0.214 | -0.067 [-0.08, -0.05] | -- | 0.806 | 0.806 | +0.000 [+0.00, +0.00] | **no gain** |
| healthbench_standard / qwen3.5-9b | 2500 | 32/32 (100%) | 0.342 | 0.327 | 0.338 | 0.327 | -0.015 [-0.05, +0.01] | -- | 0.741 | 0.741 | +0.000 [+0.00, +0.00] | **no gain** |
| bff_rubric / qwen3.6-35b-a3b ‡ | 459 | 40/40 (100%) | 0.493 | 0.522 | 0.494 | 0.510 | +0.017 [-0.10, +0.07] | -- | 0.845 | 0.845 | -0.001 [-0.01, +0.00] | **no gain** |
| bff_standard / qwen3.6-35b-a3b | 459 | 39/40 (98%) | 0.235 | 0.173 | 0.439 | 0.463 | +0.228 [+0.15, +0.31] | 89% | 0.798 | 0.800 | +0.002 [-0.01, +0.01] | **mostly cutoff** |
| biggen_rubric / qwen3.6-35b-a3b | 459 | 39/40 (98%) | 0.502 | 0.454 | 0.521 | 0.516 | +0.014 [-0.03, +0.06] | -- | 0.837 | 0.828 | -0.009 [-0.02, -0.00] | **no gain** |
| biggen_standard / qwen3.6-35b-a3b | 459 | 40/40 (100%) | 0.370 | 0.358 | 0.344 | 0.346 | -0.024 [-0.07, +0.01] | -- | 0.741 | 0.742 | +0.001 [-0.00, +0.01] | **no gain** |
| healthbench_rubric / qwen3.6-35b-a3b | 2500 | 40/40 (100%) | 0.348 | 0.358 | 0.441 | 0.358 | +0.011 [-0.00, +0.02] | -- | 0.833 | 0.833 | +0.000 [+0.00, +0.00] | **no gain** |
| healthbench_standard / qwen3.6-35b-a3b | 2500 | 40/40 (100%) | 0.380 | 0.381 | 0.381 | 0.377 | -0.003 [-0.05, +0.01] | -- | 0.760 | 0.759 | -0.001 [-0.01, +0.00] | **no gain** |

## Supplementary: RB2-Safety and JudgeBench runs on disk (not part of the 42)

These have per-item per-layer scores locally but are outside the 42-cell grid (only gpt-oss-120b has a saved significance file for them). Same protocol.

Counts: mixed: 3, mostly cutoff: 4, no gain: 10

| cell | n | layer (depth) | (a) final | (a') lens final @0.5 | (b) recal. final | (c) layer | gain (c-a) [95% over splits] | recovered by recal. | AUROC final | AUROC layer | AUROC gain [95% over splits] | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rb2safety_rubric / gpt-oss-120b | 459 | 18/36 (50%) | 0.003 | 0.003 | 0.476 | 0.200 | +0.197 [+0.09, +0.30] | 240% | 0.879 | 0.649 | -0.230 [-0.29, -0.17] | **mostly cutoff** |
| rb2safety_standard / gpt-oss-120b | 459 | 28/36 (78%) | 0.017 | 0.017 | 0.130 | 0.226 | +0.209 [+0.10, +0.30] | 54% | 0.626 | 0.702 | +0.077 [+0.00, +0.13] | **mixed** |
| judgebench / gpt-oss-120b | 459 | 35/36 (97%) | 0.044 | 0.054 | 0.074 | 0.096 | +0.052 [-0.17, +0.13] | 58% | 0.560 | 0.562 | +0.001 [-0.13, +0.03] | **mixed** |
| rb2safety_standard / gpt-oss-20b | 459 | 0/24 (0%) | 0.000 | 0.000 | 0.489 | 0.000 | +0.000 [+0.00, +0.00] | -- | 0.836 | 0.500 | -0.336 [-0.38, -0.29] | **no gain** |
| judgebench / gpt-oss-20b | 459 | 11/24 (46%) | 0.000 | 0.000 | 0.069 | 0.016 | +0.016 [-0.05, +0.06] | -- | 0.560 | 0.509 | -0.051 [-0.12, +0.01] | **no gain** |
| rb2safety_standard / nemotron3-nano-30b | 459 | 34/52 (65%) | 0.138 | 0.138 | 0.261 | 0.325 | +0.187 [+0.08, +0.28] | 66% | 0.715 | 0.774 | +0.059 [-0.03, +0.11] | **mixed** |
| judgebench / nemotron3-nano-30b | 459 | 51/52 (98%) | 0.082 | 0.082 | 0.130 | 0.094 | +0.012 [-0.10, +0.07] | -- | 0.605 | 0.597 | -0.007 [-0.12, +0.02] | **no gain** |
| rb2safety_standard / nemotron3-super-120b | 459 | 86/88 (98%) | 0.912 | 0.912 | 0.901 | 0.912 | -0.000 [-0.04, +0.03] | -- | 0.996 | 0.996 | +0.000 [-0.00, +0.00] | **no gain** |
| judgebench / nemotron3-super-120b | 459 | 64/88 (73%) | 0.268 | 0.268 | 0.290 | 0.245 | -0.023 [-0.13, +0.02] | -- | 0.716 | 0.687 | -0.029 [-0.10, +0.00] | **no gain** |
| rb2safety_rubric / qwen3.5-4b ‡ | 459 | 27/32 (84%) | 0.122 | 0.339 | 0.885 | 0.822 | +0.700 [+0.62, +0.76] | 109% | 0.987 | 0.976 | -0.011 [-0.02, -0.00] | **mostly cutoff** |
| rb2safety_standard / qwen3.5-4b ‡ | 459 | 30/32 (94%) | 0.132 | 0.342 | 0.739 | 0.771 | +0.639 [+0.55, +0.70] | 95% | 0.953 | 0.963 | +0.010 [-0.00, +0.02] | **mostly cutoff** |
| judgebench / qwen3.5-4b ‡ | 459 | 30/32 (94%) | 0.218 | 0.200 | 0.196 | 0.196 | -0.022 [-0.11, +0.05] | -- | 0.673 | 0.665 | -0.008 [-0.09, +0.01] | **no gain** |
| rb2safety_rubric / qwen3.5-9b | 459 | 27/32 (84%) | 0.867 | 0.888 | 0.905 | 0.881 | +0.014 [-0.05, +0.06] | -- | 0.995 | 0.994 | -0.001 [-0.00, +0.00] | **no gain** |
| rb2safety_standard / qwen3.5-9b | 459 | 32/32 (100%) | 0.849 | 0.853 | 0.848 | 0.851 | +0.002 [-0.04, +0.05] | -- | 0.983 | 0.983 | -0.000 [+0.00, +0.00] | **no gain** |
| judgebench / qwen3.5-9b ‡ | 459 | 29/32 (91%) | 0.222 | 0.215 | 0.210 | 0.223 | +0.002 [-0.07, +0.07] | -- | 0.688 | 0.689 | +0.001 [-0.01, +0.02] | **no gain** |
| rb2safety_standard / qwen3.6-35b-a3b | 459 | 39/40 (98%) | 0.825 | 0.797 | 0.922 | 0.918 | +0.092 [+0.04, +0.15] | 105% | 0.989 | 0.989 | +0.000 [-0.00, +0.00] | **mostly cutoff** |
| judgebench / qwen3.6-35b-a3b | 459 | 36/40 (90%) | 0.333 | 0.315 | 0.331 | 0.333 | -0.000 [-0.06, +0.05] | -- | 0.756 | 0.748 | -0.008 [-0.02, +0.00] | **no gain** |

## Skipped cells (no continuous per-layer score on disk)

- `bff_rubric_gpt-oss-20b` (main): no `pcn_rules` field in logit_lens_results/gpt-oss-20b_rules2/pilot_results.json (only ['critical_layer', 'ds_rules', 'ds_standard', 'gold', 'id', 'kl_at_critical', 'kl_per_layer', 'pred_rules', 'pred_standard']). Its saved held-out significance result used the saturated legacy `decision_score` (ds) field as a stand-in, which is a valid 0/1 verdict but only keeps the margin for items favouring CORRECT (it is exactly 0 for every item favouring INCORRECT), so neither a cutoff nor an AUROC can be computed faithfully. The original held-out gain there was 0.000, so it would be 'no gain' regardless.

## Caveats

- The 95% brackets are split-to-split spread, not a formal CI on the population effect; splits share items, so a bootstrap-over-splits CI (used only for the gain/no-gain call, as in the original) is optimistic.
- Both (b) and (c) get one 'free choice' on half A (a cutoff vs a layer out of ~25-89), so neither side is favoured by over-fitting; the comparison is like-for-like.
- 'Recovered' can exceed 100% (recalibrated final beats the interior layer) or be negative (re-thresholding the final layer overfits A and hurts on B).
