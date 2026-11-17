# Belief strength: acceptance vs how often the judge itself reaches the candidate's answer

belief = share of 7 fresh own answers (T=0.7, same prompt) that reach the candidate's final answer. Sample 0, which defined match/differ, is not part of it. Accepts at A = before reasoning; at C = at the verdict (readout). Effects in percentage points, 95% intervals resample whole questions.

Rows with a belief score: 1565 (of the main-set rows in rows.json).

Clean labels: 60 rows dropped, RB2-Math 'wrong' answers that reach the right value (GLM audit, clean_labels.py).

## 1. How stable is the judge's own answer? (wrong candidates)

| set | n | belief 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | old label 'match' among belief 0/7 | old 'differ' among all 7 |
|---|---|---|---|---|---|---|---|
| main | 714 | 580 | 53 | 31 | 50 | 2% | 2% |
| rb2math | 449 | 423 | 14 | 7 | 5 | 0% | 20% |
| judgebench | 86 | 32 | 24 | 14 | 16 | 12% | 0% |
| bff | 179 | 125 | 15 | 10 | 29 | 2% | 0% |

## 2a. Wrong candidates accepted at A, by belief

| set | 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | slope (all 7 vs 0/7, judge FE) |
|---|---|---|---|---|---|
| main | 22% (n=580) | 38% (n=53) | 42% (n=31) | 62% (n=50) | +41 [+28, +54] |
| rb2math | 25% (n=423) | 36% (n=14) | 57% (n=7) | 80% (n=5) | +51 [+18, +79] |
| judgebench | 28% (n=32) | 54% (n=24) | 43% (n=14) | 75% (n=16) | +39 [+14, +63] |
| bff | 12% (n=125) | 13% (n=15) | 30% (n=10) | 52% (n=29) | +38 [+18, +55] |

## 2b. Wrong candidates accepted at C, by belief

| set | 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | slope (all 7 vs 0/7, judge FE) |
|---|---|---|---|---|---|
| main | 13% (n=580) | 45% (n=53) | 55% (n=31) | 68% (n=50) | +57 [+43, +68] |
| rb2math | 13% (n=423) | 71% (n=14) | 57% (n=7) | 80% (n=5) | +74 [+42, +106] |
| judgebench | 16% (n=32) | 42% (n=24) | 57% (n=14) | 75% (n=16) | +60 [+35, +82] |
| bff | 14% (n=125) | 27% (n=15) | 50% (n=10) | 62% (n=29) | +49 [+27, +65] |

## 3. Which matters: belief, or the single answer that defined match/differ?

Wrong candidates, both in one model (judge FE). If anchoring is about what the judge believes, belief should carry the effect and the old single-sample label should add little once belief is known.

| set | checkpoint | old label alone | belief alone | old label, belief held fixed | belief, old label held fixed |
|---|---|---|---|---|---|
| main | A | +30 [+18, +40] | +41 [+28, +54] | +4 [-13, +22] | +37 [+14, +57] |
| main | C | +34 [+21, +45] | +57 [+43, +68] | -14 [-33, +5] | +69 [+46, +90] |
| rb2math | A | +24 [-12, +61] | +51 [+18, +79] | -17 [-71, +33] | +60 [+19, +97] |
| rb2math | C | +34 [-2, +71] | +74 [+42, +106] | -25 [-96, +26] | +88 [+49, +139] |
| judgebench | A | +29 [+9, +49] | +39 [+14, +63] | +15 [-15, +43] | +25 [-12, +62] |
| judgebench | C | +29 [+9, +48] | +60 [+35, +82] | -9 [-33, +18] | +68 [+32, +98] |
| bff | A | +31 [+15, +45] | +38 [+18, +55] | +8 [-14, +32] | +30 [-2, +63] |
| bff | C | +37 [+15, +53] | +49 [+27, +65] | -6 [-45, +30] | +55 [+10, +104] |

## 4. Same wrong candidate, different judges (candidate FE + judge FE)

Is it the judge's OWN belief, or a belief every Qwen shares? Only candidates the three Qwens believe to different degrees identify this.

| set | belief effect at A | at C | C minus A |
|---|---|---|---|
| main | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
| rb2math | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
| judgebench | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
| bff | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |

## 5. Correct candidates: does low belief make the judge reject a right answer?

| set | 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | slope at A | slope at C |
|---|---|---|---|---|---|---|
| main | 31%→22% (n=32) | 59%→56% (n=32) | 64%→76% (n=107) | 79%→90% (n=679) | +44 [+29, +58] | +64 [+50, +77] |
| rb2math | 47%→33% (n=15) | 33%→33% (n=3) | 69%→94% (n=16) | 91%→97% (n=148) | +46 [+21, +73] | +62 [+38, +84] |
| judgebench | 100%→0% (n=1) | 68%→74% (n=19) | 61%→75% (n=77) | 70%→87% (n=316) | +5 [-21, +34] | +34 [+8, +62] |
| bff | 12%→12% (n=16) | 50%→30% (n=10) | 79%→57% (n=14) | 84%→91% (n=215) | +65 [+46, +81] | +82 [+62, +100] |
