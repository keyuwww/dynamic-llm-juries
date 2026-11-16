# Rigor checks (Nov 16)

95% intervals resample whole questions (2,000 draws).

## 1. Commit first vs the usual prompt (same items; three Qwens; RB2 Math + BFF)

| answers | belief | n | usual prompt | own answer first | difference (points) |
|---|---|---|---|---|---|
| wrong (approved) | 0/7 | 1528 | 18% [15, 21] | 1% [0, 1] | -17 [-20, -14] |
| wrong (approved) | 1-3 | 144 | 38% [29, 46] | 22% [14, 28] | -16 [-26, -7] |
| wrong (approved) | 4-6 | 72 | 58% [45, 70] | 51% [35, 65] | -7 [-17, +4] |
| wrong (approved) | 7/7 | 61 | 74% [55, 84] | 69% [56, 83] | -5 [-19, +13] |
| right (approved) | 0/7 | 87 | 31% [18, 44] | 14% [4, 28] | -17 [-31, -5] |
| right (approved) | 1-3 | 73 | 73% [61, 82] | 36% [22, 48] | -37 [-51, -21] |
| right (approved) | 4-6 | 203 | 84% [77, 90] | 71% [63, 78] | -13 [-19, -6] |
| right (approved) | 7/7 | 919 | 88% [85, 92] | 86% [82, 90] | -2 [-4, -0] |

Balanced accuracy (mean of right-approved and wrong-rejected), all 3087 items: usual 80% [78, 82], own answer first 85% [82, 87], difference +5 [+3, +6] points.

## 2. Shown the answer, asked to solve: share landing on the candidate's answer

Expected = the average belief in the group (what landing would be with no candidate shown).

| candidate | belief | n | lands on it | expected | difference (points) |
|---|---|---|---|---|---|
| wrong | 0/7 | 1568 | 2% [2, 3] | 0% | +2 [+2, +3] |
| wrong | 1-3 | 150 | 35% [27, 43] | 24% | +12 [+4, +19] |
| wrong | 4-6 | 73 | 63% [46, 78] | 72% | -9 [-24, +6] |
| wrong | 7/7 | 62 | 89% [75, 96] | 100% | -11 [-24, -4] |
| right | 0/7 | 95 | 18% [6, 32] | 0% | +18 [+5, +33] |
| right | 1-3 | 76 | 62% [47, 77] | 27% | +35 [+20, +47] |
| right | 4-6 | 209 | 83% [77, 89] | 78% | +5 [-1, +11] |
| right | 7/7 | 925 | 97% [95, 98] | 100% | -3 [-5, -2] |

## 3. "Don't re-solve" (verify) vs normal, wrong BFF answers approved

| judges | belief | normal | verify |
|---|---|---|---|
| Qwens | 0/7 (n=343) | 15% [11, 19] | 3% [1, 5] |
| Qwens | 1-3 (n=89) | 43% [34, 52] | 28% [18, 39] |
| Qwens | 4-6 (n=56) | 55% [43, 67] | 45% [30, 59] |
| Qwens | 7/7 (n=52) | 74% [61, 85] | 69% [53, 83] |
| Nemotron | 0/7 (n=124) | 35% [28, 42] | 15% [9, 22] |
| Nemotron | 1-3 (n=16) | 62% [42, 83] | 50% [25, 75] |
| Nemotron | 4-6 (n=16) | 83% [65, 98] | 56% [31, 81] |
| Nemotron | 7/7 (n=24) | 85% [71, 94] | 83% [67, 96] |

## 4. Different-belief juror: route a Qwen's believed items (>= 4/7) to Nemotron-3-Super

Same items for all three columns (main set; verdicts at C). Wrong answers: share REJECTED; right answers: share APPROVED; balanced = their mean.

| Qwen judge | items | routed | Qwen alone (balanced) | Nemotron alone | Qwen + route | wrong & believed by the Qwen: rejected (Qwen → routed) |
|---|---|---|---|---|---|---|
| qwen3.5-4b | 1399 | 689 | 76% [73, 78] | 75% [72, 77] | 74% [71, 76] | 36% [25, 48] → 30% [19, 44] (n=73) |
| qwen3.5-9b | 1431 | 744 | 80% [78, 83] | 74% [71, 77] | 77% [75, 80] | 32% [22, 43] → 22% [13, 33] (n=72) |
| qwen3.6-35b-a3b | 1450 | 774 | 86% [84, 88] | 74% [71, 77] | 82% [80, 85] | 32% [21, 46] → 26% [15, 39] (n=62) |
