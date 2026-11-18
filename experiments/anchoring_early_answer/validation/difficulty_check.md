# Is belief just difficulty?

Belief = how often the judge's 7 own answers reach this wrong answer. Difficulty = how often they reach the RIGHT answer to the same question (the judge's own accuracy there). Audited wrong answers, thinking off. Effects in points for belief 0/7 → 7/7 (a linear probability model), 95% intervals resampling questions.

| judge | wrong answers | 1. within the same question (judge × question FE) | questions that contribute | 2. belief, holding accuracy fixed | accuracy, holding belief fixed |
|---|---|---|---|---|---|
| 3 Qwens | 2011 | +61 [+31, +108] | 58 | +62 [-1, +86] | +1 [-8, +10] |
| Nemotron-3-Super | 685 | +73 [+22, +175] | 17 | +64 [-7, +95] | -3 [-21, +12] |
| DeepSeek-V4.1-Flash | 640 | +45 [-9, +86] | 14 | +60 [-6, +120] | -3 [-16, +10] |
| Kimi-K2.6 | 637 | -13 [-69, +24] | 11 | +36 [-10, +74] | -13 [-23, -3] |
| Nemotron-3-Nano | 910 | +47 [+8, +85] | 58 | +43 [+22, +69] | +15 [+0, +30] |
| **all four families** | 4883 | **+47 [+27, +71]** | 158 | **+48 [+15, +72]** | +1 [-7, +8] |

## 3. The staircase within difficulty strata (all four families pooled)

Strata by the judge's own accuracy on the question (its 7 answers reaching the right answer).

| judge's accuracy on the question | 0/7 | 1-3 | 4-6 | 7/7 | gap 7/7 − 0/7 |
|---|---|---|---|---|---|
| never right (0/7): hardest | 17% (n=218) | 35% (n=31) | 33% (n=9) | 86% (n=14) | +68 [+36, +86] |
| 1–3 of 7 | 21% (n=161) | 46% (n=24) | 70% (n=20) | nan% (n=0) | +nan [+nan, +nan] |
| 4–7 of 7: easiest | 18% (n=2615) | 51% (n=91) | 33% (n=12) | 0% (n=1) | -18 [-21, -15] |
