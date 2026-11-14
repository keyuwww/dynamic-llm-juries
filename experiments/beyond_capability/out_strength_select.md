| Benchmark | Judge | Strength picked on half 1 / half 2 | Ranking x1 | Ranking at picked strength | Gain, picked [95% CI] | Gain, fixed x11 [95% CI] |
|---|---|---|---|---|---|---|
| MMLU-Redux | Qwen-9B | ×11 / ×4 | 0.673 | 0.677 | +0.4 [-0.7, +1.4] | +0.5 [-0.6, +1.7] |
| MMLU-Redux | Llama-8B | ×21 / ×51 | 0.511 | 0.567 | +5.5 [+3.2, +8.0] | +7.0 [+5.1, +8.9] |
| MATH | Qwen-9B | ×11 / ×4 | 0.663 | 0.683 | +2.1 [+0.3, +3.7] | +2.2 [+0.2, +4.1] |
| MATH | Llama-8B | ×1 / ×11 | 0.541 | 0.527 | -1.4 [-2.7, -0.1] | +1.4 [-0.4, +3.3] |
| BBEH | Qwen-9B | ×2 / ×11 | 0.616 | 0.602 | -1.4 [-3.7, +0.9] | +1.2 [-2.1, +4.7] |
| BBEH | Llama-8B | ×11 / ×11 | 0.557 | 0.620 | +6.3 [+3.2, +9.6] | +6.3 [+3.2, +9.6] |
| RB2 Safety | Qwen-9B | ×4 / ×11 | 0.964 | 0.963 | -0.1 [-0.4, +0.1] | +0.1 [-0.3, +0.4] |
| RB2 Safety | Llama-8B | ×4 / ×4 | 0.959 | 0.969 | +1.0 [+0.1, +1.8] | -6.3 [-8.2, -4.6] |

| Benchmark | Judge | Sensitivity | Formula strength | Nearest tested | Gain there [95% CI] | Best tested (gain) |
|---|---|---|---|---|---|---|
| MMLU-Redux | Qwen-9B | 0.26 | ×5 | ×4 | +0.5 [-0.3, +1.4] | ×4 (+0.5) |
| MMLU-Redux | Llama-8B | 0.13 | ×9 | ×11 | +7.0 [+5.1, +8.9] | ×21 (+7.5) |
| MATH | Qwen-9B | 0.43 | ×3 | ×4 | +3.5 [+2.1, +4.8] | ×4 (+3.5) |
| MATH | Llama-8B | -0.04 | none (verdict doesn't respond) | ×1 | +0.0 [+0.0, +0.0] | ×11 (+1.4) |
| BBEH | Qwen-9B | 0.15 | ×8 | ×11 | +1.2 [-2.0, +4.7] | ×4 (+1.6) |
| BBEH | Llama-8B | 0.02 | ×48 | ×11 | +6.3 [+3.3, +9.5] | ×11 (+6.3) |
| RB2 Safety | Qwen-9B | -0.01 | none (verdict doesn't respond) | ×1 | +0.0 [+0.0, +0.0] | ×11 (+0.1) |
| RB2 Safety | Llama-8B | 0.21 | ×6 | ×4 | +1.0 [+0.1, +1.8] | ×4 (+1.0) |
