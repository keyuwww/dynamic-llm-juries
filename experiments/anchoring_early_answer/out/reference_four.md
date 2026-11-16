# Four prompts on the same BFF items (three Qwens, thinking off)

1294 items judged under all four prompts. 95% intervals resample questions.

## Wrong answers approved

| prompt | 0/7 | 1-3 | 4-6 | 7/7 | strong belief (4/7+) |
|---|---|---|---|---|---|
| usual judge prompt | 15% (n=336) | 36% (n=89) | 54% (n=56) | 71% (n=52) | 62% (n=108) |
| commit first | 1% (n=336) | 27% (n=89) | 48% (n=56) | 63% (n=52) | 56% (n=108) |
| + expert reference | 1% (n=336) | 1% (n=89) | 5% (n=56) | 19% (n=52) | 12% (n=108) |
| commit first + reference | 1% (n=336) | 1% (n=89) | 5% (n=56) | 31% (n=52) | 18% (n=108) |

## Right answers approved

| prompt | 0/7 | 1-3 | 4-6 | 7/7 |
|---|---|---|---|---|
| usual judge prompt | 20% | 65% | 75% | 85% |
| commit first | 12% | 33% | 64% | 83% |
| + expert reference | 41% | 76% | 80% | 88% |
| commit first + reference | 30% | 65% | 72% | 86% |

## Balanced accuracy (change vs usual, 95% interval)

| prompt | all three | 4B | 9B | 35B |
|---|---|---|---|---|
| usual judge prompt | 74.6% | 70.9% | 76.1% | 76.7% |
| commit first | 77.8% (+3.2 [+0.5, +6.0]) | 75.7% (+4.7 [+0.2, +9.3]) | 78.8% (+2.7 [-1.3, +6.6]) | 78.9% (+2.2 [-1.6, +5.8]) |
| + expert reference | 89.6% (+15.0 [+11.9, +18.2]) | 89.3% (+18.4 [+14.1, +22.7]) | 90.4% (+14.3 [+9.7, +18.8]) | 89.1% (+12.4 [+8.4, +16.3]) |
| commit first + reference | 87.0% (+12.4 [+9.2, +15.7]) | 86.8% (+15.8 [+11.2, +20.5]) | 89.0% (+12.8 [+8.4, +17.1]) | 85.3% (+8.6 [+5.0, +12.2]) |

Commit first + reference vs reference alone: -2.6 [-4.6, -0.7] balanced accuracy.
