# Pre-registered test: a gap without a responsive verdict (Llama-3.2-3B, Phi-4-mini, MMLU-Redux): outcome

Rule: verdict doesn't respond (RESPONDS < 0.10), so gain at ×11 < 3. Naive rule: gain ≈ 0.5 × GAP (±4).


## Llama-3.2-3B

Solves 3279 of 5330 questions (62%), one answer each.

### Gap rule (gain at ×11, judge direction)

| Group | Knows | Says | Rule predicts | Naive predicts | Measured gain [95% CI] | Rule holds (< 3) | Naive holds (±4) | Random direction gain | Same-model pairs gain [95% CI] |
|---|---|---|---|---|---|---|---|---|---|
| all | 0.632 | 0.518 | < 3 | +5.7 | +4.1 [+2.4, +5.9] | **no** | yes | +0.4 [+0.1, +0.7] | +3.0 [-0.5, +6.5] (612 q) |
| solved | 0.656 | 0.573 | < 3 | +4.2 | +3.7 [+0.7, +6.7] | **no** | yes | +0.5 [-0.1, +1.1] | +3.8 [-1.7, +9.3] (221 q) |
| not solved | 0.619 | 0.489 | < 3 | +6.5 | +4.4 [+2.1, +6.6] | **no** | yes | +0.3 [-0.1, +0.6] | +2.6 [-1.8, +7.1] (391 q) |

### Strength formula (all answers; formula predicts ×16)

| Strength | Ranking (judge) | Change vs unedited [95% CI] | Ranking (random) | Accept rate right / wrong (judge) |
|---|---|---|---|---|
| ×1 (none) | 0.518 | – | 0.518 | 92% / 95% |
| ×2 | 0.523 | +0.5 [-0.1, +1.0] | 0.519 | 92% / 95% |
| ×4 | 0.541 | +2.3 [+1.3, +3.3] | 0.519 | 92% / 95% |
| ×11 | 0.559 | +4.1 [+2.4, +5.9] | 0.522 | 89% / 92% |
| ×16 | 0.552 | +3.4 [+1.4, +5.4] | 0.521 | 88% / 92% |

Best tested: ×11 (55.9); formula ×16 = 55.2; ×11 = 55.9; none = 51.8. **Formula holds: yes.**


## Phi-4-mini

Solves 3889 of 5330 questions (73%), one answer each.

### Gap rule (gain at ×11, judge direction)

| Group | Knows | Says | Rule predicts | Naive predicts | Measured gain [95% CI] | Rule holds (< 3) | Naive holds (±4) | Random direction gain | Same-model pairs gain [95% CI] |
|---|---|---|---|---|---|---|---|---|---|
| all | 0.624 | 0.552 | < 3 | +3.6 | +1.2 [-0.2, +2.7] | **yes** | yes | -0.1 [-0.5, +0.3] | -1.0 [-3.7, +1.5] (612 q) |
| solved | 0.684 | 0.628 | < 3 | +2.8 | +1.5 [-0.7, +3.6] | **yes** | yes | -0.1 [-0.6, +0.5] | -0.5 [-4.2, +3.2] (266 q) |
| not solved | 0.578 | 0.494 | < 3 | +4.2 | +0.9 [-1.1, +3.0] | **yes** | yes | -0.1 [-0.6, +0.4] | -1.3 [-4.9, +2.2] (346 q) |

### Strength formula (all answers; formula predicts ×81)

| Strength | Ranking (judge) | Change vs unedited [95% CI] | Ranking (random) | Accept rate right / wrong (judge) |
|---|---|---|---|---|
| ×1 (none) | 0.552 | – | 0.552 | 91% / 91% |
| ×2 | 0.553 | +0.0 [-0.4, +0.4] | 0.552 | 91% / 91% |
| ×4 | 0.555 | +0.2 [-0.4, +0.9] | 0.550 | 91% / 90% |
| ×11 | 0.564 | +1.2 [-0.2, +2.7] | 0.551 | 89% / 84% |
| ×81 | 0.545 | -0.8 [-3.4, +2.0] | 0.552 | 74% / 72% |

Best tested: ×11 (56.4); formula ×81 = 54.5; ×11 = 56.4; none = 55.2. **Formula holds: no.**

