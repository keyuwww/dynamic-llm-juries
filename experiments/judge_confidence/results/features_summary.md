# Which item features predict low confidence vs errors (real BFF answers)

459 answers with a unanimous expert label × 3 judges × condition; aspect codes cover 100% of rows (missing filled with the median). AUROC = logistic model on all features, 5-fold CV grouped by question. Coefficients are standardized (positive = more likely).

## No reference (n = 1377 judge × answer rows)

| Target | Positives | CV AUROC |
|---|---|---|
| error | 249 | 0.52 |
| unsure | 209 | 0.57 |
| conf_error | 161 | 0.58 |

| Feature | → error | → unsure (low confidence) | → confident error |
|---|---|---|---|
| knowledge | -0.08 | +0.03 | -0.15 |
| reasoning | +0.16 | +0.23 | +0.12 |
| constraints | -0.15 | +0.01 | -0.26 |
| open_endedness | +0.11 | +0.23 | +0.00 |
| context_load | +0.02 | +0.09 | -0.01 |
| risk | -0.04 | -0.10 | +0.01 |
| log_len | +0.28 | +0.11 | +0.42 |
| turn | -0.03 | +0.13 | -0.08 |
| model_gemma-2-2b | +0.13 | -0.13 | +0.24 |
| model_gpt-4o | -0.30 | -0.00 | -0.43 |
| model_llama-3.3-70b | +0.18 | +0.07 | +0.28 |
| model_phi-4 | -0.04 | -0.01 | -0.07 |
| model_qwen2.5-7b | +0.03 | +0.02 | +0.03 |
| model_yi1.5-34b-16k | +0.04 | +0.06 | +0.00 |

Rates by answer model (all judges pooled):

| Answer model | Error | Unsure | Confident error |
|---|---|---|---|
| gemma-2-2b | 0.25 | 0.12 | 0.20 |
| gpt-4o | 0.09 | 0.14 | 0.04 |
| llama-3.3-70b | 0.24 | 0.17 | 0.18 |
| phi-4 | 0.15 | 0.15 | 0.08 |
| qwen2.5-7b | 0.20 | 0.16 | 0.12 |
| yi1.5-34b-16k | 0.19 | 0.17 | 0.10 |

## With reference (n = 1368 judge × answer rows)

| Target | Positives | CV AUROC |
|---|---|---|
| error | 122 | 0.70 |
| unsure | 123 | 0.53 |
| conf_error | 75 | 0.71 |

| Feature | → error | → unsure (low confidence) | → confident error |
|---|---|---|---|
| knowledge | -0.21 | -0.00 | -0.18 |
| reasoning | +0.40 | +0.07 | +0.37 |
| constraints | -0.22 | +0.10 | -0.32 |
| open_endedness | +0.17 | +0.01 | +0.30 |
| context_load | -0.54 | -0.30 | -0.35 |
| risk | +0.11 | +0.09 | +0.14 |
| log_len | +0.63 | +0.32 | +0.65 |
| turn | +0.22 | +0.32 | +0.00 |
| model_gemma-2-2b | +0.36 | +0.03 | +0.42 |
| model_gpt-4o | -0.61 | -0.16 | -0.49 |
| model_llama-3.3-70b | +0.11 | +0.23 | +0.06 |
| model_phi-4 | -0.06 | +0.04 | -0.21 |
| model_qwen2.5-7b | +0.06 | -0.03 | +0.10 |
| model_yi1.5-34b-16k | +0.17 | -0.07 | +0.15 |

Rates by answer model (all judges pooled):

| Answer model | Error | Unsure | Confident error |
|---|---|---|---|
| gemma-2-2b | 0.21 | 0.11 | 0.15 |
| gpt-4o | 0.02 | 0.06 | 0.01 |
| llama-3.3-70b | 0.07 | 0.14 | 0.03 |
| phi-4 | 0.06 | 0.10 | 0.02 |
| qwen2.5-7b | 0.09 | 0.09 | 0.06 |
| yi1.5-34b-16k | 0.10 | 0.07 | 0.05 |

