# Pre-registered test, Qwen3.5-4B on MMLU-Redux: outcome

Stretch run: job 59930641 (gpu_test, A100 MIG slice). 3496 answers per direction. Unedited verdict vs the earlier shift-only run (different GPU): same within 0.25 for 99.4%, same accept/reject for 99.1%.

## 1. Gap rule (gain at x11, judge direction)

| Group | Predicted | Measured gain [95% CI] | In range? | CI includes 0? | Rule holds | Random direction gain | Same-model pairs: gain [95% CI] |
|---|---|---|---|---|---|---|---|
| with own answers, all | +0.6 | -0.4 [-1.5, +0.8] | yes | yes | **yes** | -0.1 [-0.4, +0.2] | -1.3 [-3.1, +0.5] (612 q, 674 pairs) |
| with own answers, solved | +0.6 | -0.4 [-1.9, +1.2] | yes | yes | **yes** | +0.0 [-0.5, +0.5] | +0.0 [-2.5, +2.5] (363 q, 363 pairs) |
| with own answers, not solved | +0.6 | -0.4 [-2.1, +1.2] | yes | yes | **yes** | -0.2 [-0.7, +0.2] | -2.7 [-5.7, +0.0] (249 q, 311 pairs) |
| without own answers, all | -1.3 | -2.5 [-5.6, +0.5] | yes | yes | **yes** | -0.2 [-0.8, +0.3] | – (0 questions with a same-model pair) |
| without own answers, solved | -1.7 | -3.1 [-7.5, +1.2] | yes | yes | **yes** | +0.0 [+0.0, +0.0] | – (0 questions with a same-model pair) |
| without own answers, not solved | -0.6 | -1.7 [-6.2, +2.8] | yes | yes | **yes** | -0.3 [-1.4, +0.7] | – (0 questions with a same-model pair) |

Gap rule holds in 6 of 6 groups.

## 2. Strength formula (all answers, with own answers; formula predicts x9)

| Strength | Ranking (judge) | Change vs unedited [95% CI] | Ranking (random) | Accept rate right / wrong (judge) |
|---|---|---|---|---|
| x1 (none) | 0.610 | – | 0.610 | 84% / 74% |
| x2 | 0.611 | +0.1 [-0.4, +0.5] | 0.608 | 82% / 71% |
| x4 | 0.613 | +0.3 [-0.4, +1.0] | 0.609 | 78% / 66% |
| x9 | 0.606 | -0.4 [-1.5, +0.7] | 0.609 | 73% / 59% |
| x11 | 0.607 | -0.4 [-1.5, +0.8] | 0.609 | 71% / 57% |

Best tested strength: x4 (61.3). x9 = 60.6: within 1 point of best: yes; at least as good as x11 (within 1): yes. **Formula holds: yes.** No stretch (x1) = 61.0.

