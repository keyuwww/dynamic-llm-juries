# Rigor checks (Nov 16), audited labels (Nov 18)

95% intervals resample whole questions (2,000 draws).

## 1. Commit first vs the usual prompt (same items; three Qwens; RB2 Math + BFF)

| answers | belief | n | usual prompt | own answer first | difference (points) |
|---|---|---|---|---|---|
| wrong (approved) | 0/7 | 1504 | 17% [14, 20] | 1% [0, 1] | -17 [-20, -14] |
| wrong (approved) | 1-3 | 108 | 32% [22, 42] | 14% [8, 21] | -19 [-30, -7] |
| wrong (approved) | 4-6 | 44 | 48% [31, 62] | 45% [23, 65] | -2 [-20, +13] |
| wrong (approved) | 7/7 | 16 | 50% [20, 79] | 56% [25, 82] | +6 [-14, +25] |
| right (approved) | 0/7 | 87 | 31% [19, 45] | 14% [4, 29] | -17 [-30, -6] |
| right (approved) | 1-3 | 73 | 73% [61, 82] | 36% [24, 48] | -37 [-51, -21] |
| right (approved) | 4-6 | 203 | 84% [77, 90] | 71% [63, 78] | -13 [-20, -6] |
| right (approved) | 7/7 | 919 | 88% [85, 92] | 86% [83, 90] | -2 [-4, -0] |

Balanced accuracy (mean of right-approved and wrong-rejected), all 2954 items: usual 82% [79, 84], own answer first 86% [84, 89], difference +5 [+3, +7] points.

## 2. Shown the answer, asked to solve: share landing on the candidate's answer

Expected = the average belief in the group (what landing would be with no candidate shown).

| candidate | belief | n | lands on it | expected | difference (points) |
|---|---|---|---|---|---|
| wrong | 0/7 | 1538 | 2% [1, 3] | 0% | +2 [+1, +3] |
| wrong | 1-3 | 116 | 27% [19, 35] | 22% | +5 [-3, +11] |
| wrong | 4-6 | 44 | 48% [27, 69] | 70% | -22 [-44, -2] |
| wrong | 7/7 | 16 | 56% [31, 81] | 100% | -44 [-71, -19] |
| right | 0/7 | 95 | 18% [6, 33] | 0% | +18 [+6, +32] |
| right | 1-3 | 76 | 62% [45, 76] | 27% | +35 [+20, +47] |
| right | 4-6 | 209 | 83% [77, 89] | 78% | +5 [-1, +11] |
| right | 7/7 | 925 | 97% [95, 98] | 100% | -3 [-5, -2] |

## 3. "Don't re-solve" (verify) vs normal, wrong BFF answers approved

| judges | belief | normal | verify |
|---|---|---|---|
| Qwens | 0/7 (n=343) | 15% [10, 19] | 3% [1, 5] |
| Qwens | 1-3 (n=89) | 43% [34, 52] | 28% [18, 39] |
| Qwens | 4-6 (n=56) | 55% [43, 67] | 45% [31, 59] |
| Qwens | 7/7 (n=52) | 74% [61, 85] | 69% [52, 84] |
| Nemotron | 0/7 (n=124) | 35% [28, 42] | 15% [10, 23] |
| Nemotron | 1-3 (n=16) | 62% [42, 81] | 50% [25, 75] |
| Nemotron | 4-6 (n=16) | 83% [67, 98] | 56% [31, 81] |
| Nemotron | 7/7 (n=24) | 85% [72, 94] | 83% [67, 96] |

## 4. Different-belief juror: route a Qwen's believed items (>= 4/7) to Nemotron-3-Super

Same items for all three columns (main set; verdicts at C). Wrong answers: share REJECTED; right answers: share APPROVED; balanced = their mean.

| Qwen judge | items | routed | Qwen alone (balanced) | Nemotron alone | Qwen + route | wrong & believed by the Qwen: rejected (Qwen → routed) |
|---|---|---|---|---|---|---|
| qwen3.5-4b | 1322 | 647 | 78% [75, 80] | 76% [74, 79] | 75% [73, 78] | 45% [29, 62] → 29% [13, 48] (n=31) |
| qwen3.5-9b | 1362 | 705 | 82% [80, 85] | 76% [73, 78] | 79% [77, 81] | 45% [29, 63] → 18% [6, 33] (n=33) |
| qwen3.6-35b-a3b | 1375 | 734 | 89% [87, 91] | 76% [73, 78] | 86% [83, 88] | 50% [27, 74] → 27% [10, 48] (n=22) |
