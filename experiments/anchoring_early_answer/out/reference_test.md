# Expert reference answer vs strong-belief errors (BFF-Bench, three Qwens, thinking off)

1295 paired judgments (same item, usual prompt vs + expert reference). 95% intervals resample questions.

## Wrong answers approved, by belief

| condition | 0/7 | 1-3 | 4-6 | 7/7 |
|---|---|---|---|---|
| usual judge prompt | 15% (n=337) | 36% (n=89) | 54% (n=56) | 71% (n=52) |
| + expert reference answer | 1% (n=337) | 1% (n=89) | 5% (n=56) | 19% (n=52) |

| change (points) | 0/7 | 1-3 | 4-6 | 7/7 |
|---|---|---|---|---|
| wrong answers | -14 [-19, -9] | -35 [-45, -24] | -48 [-62, -34] | -52 [-67, -32] |

## Right answers approved, by belief

| condition | 0/7 | 1-3 | 4-6 | 7/7 |
|---|---|---|---|---|
| usual judge prompt | 20% (n=56) | 65% (n=46) | 75% (n=125) | 85% (n=534) |
| + expert reference answer | 41% (n=56) | 76% (n=46) | 80% (n=125) | 88% (n=534) |

## Balanced accuracy

| judge | usual | + reference | change |
|---|---|---|---|
| qwen3.5-4b | 70.9% | 89.3% | +18.4 [+14.1, +22.7] |
| qwen3.5-9b | 76.1% | 90.4% | +14.3 [+9.7, +18.8] |
| qwen3.6-35b-a3b | 76.7% | 89.1% | +12.3 [+8.5, +16.2] |
| all three | 74.6% | 89.6% | +15.0 [+11.8, +18.2] |

Strong-belief wrong answers (4/7 or more), n=108: approved 62% usually, 12% with the reference (-50 [-61, -37]).
