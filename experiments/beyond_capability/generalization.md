| Benchmark | Judge | Knows | Says | Gap | Verdict responds (sensitivity) | Gain at ×11 [95% CI] | Why |
|---|---|---|---|---|---|---|---|
| MMLU-Redux | Llama-3.1-8B | 0.64 | 0.51 | +12 | 0.13 | +7.0 [+5.1, +8.9] | gap, verdict responds* |
| MMLU-Redux | Qwen3.5-9B | 0.68 | 0.67 | +1 | 0.26 | +0.5 [-0.6, +1.7] | no gap |
| MMLU-Redux | Qwen3.5-4B (preregistered) | 0.62 | 0.61 | +1 | 0.13 | -0.4 [-1.5, +0.8] | no gap |
| BBEH | Llama-3.1-8B | 0.63 | 0.56 | +8 | 0.02 | +6.3 [+3.2, +9.6] | gap, verdict responds weakly† |
| BBEH | Qwen3.5-9B | 0.60 | 0.62 | -2 | 0.15 | +1.2 [-2.1, +4.7] | no gap |
| MATH | Llama-3.1-8B | 0.68 | 0.54 | +14 | -0.04 | +1.4 [-0.4, +3.3] | gap, but verdict doesn't respond |
| MATH | Qwen3.5-9B | 0.71 | 0.66 | +5 | 0.43 | +2.2 [+0.2, +4.1] | small gap, small gain |
| RB2 Safety | Llama-3.1-8B | 0.99 | 0.96 | +3 | 0.21 | -6.3 [-8.2, -4.6] | ×11 overshoots (×4: +1.0) |
| RB2 Safety | Qwen3.5-9B | 0.98 | 0.96 | +1 | -0.01 | +0.1 [-0.3, +0.4] | no gap, doesn't respond |
