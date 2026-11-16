# Belief strength: acceptance vs how often the judge itself reaches the candidate's answer

belief = share of 7 fresh own answers (T=0.7, same prompt) that reach the candidate's final answer. Sample 0, which defined match/differ, is not part of it. Accepts at A = before reasoning; at C = at the verdict (readout). Effects in percentage points, 95% intervals resample whole questions.

Rows with a belief score: 1510 (of the main-set rows in rows.json).

Clean labels: 59 rows dropped, RB2-Math 'wrong' answers that reach the right value (GLM audit, clean_labels.py).

## 1. How stable is the judge's own answer? (wrong candidates)

| set | n | belief 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | old label 'match' among belief 0/7 | old 'differ' among all 7 |
|---|---|---|---|---|---|---|---|
| main | 982 | 539 | 331 | 104 | 8 | 6% | 12% |
| rb2math | 431 | 278 | 110 | 42 | 1 | 5% | 0% |
| judgebench | 375 | 149 | 177 | 44 | 5 | 7% | 0% |
| bff | 176 | 112 | 44 | 18 | 2 | 5% | 50% |

## 2a. Wrong candidates accepted at A, by belief

| set | 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | slope (all 7 vs 0/7, judge FE) |
|---|---|---|---|---|---|
| main | 57% (n=427) | 56% (n=287) | 53% (n=86) | 17% (n=6) | -1 [-16, +13] |
| rb2math | 64% (n=278) | 65% (n=110) | 62% (n=42) | 100% (n=1) | +4 [-19, +25] |
| judgebench | 44% (n=149) | 50% (n=177) | 45% (n=44) | 0% (n=5) | -6 [-26, +14] |
| bff | – (n=0) | – (n=0) | – (n=0) | – (n=0) | +nan [+nan, +nan] |

## 2b. Wrong candidates accepted at C, by belief

| set | 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | slope (all 7 vs 0/7, judge FE) |
|---|---|---|---|---|---|
| main | 51% (n=537) | 50% (n=330) | 57% (n=104) | 71% (n=7) | +14 [+0, +27] |
| rb2math | 66% (n=276) | 64% (n=110) | 74% (n=42) | 100% (n=1) | +9 [-11, +28] |
| judgebench | 42% (n=149) | 47% (n=177) | 50% (n=44) | 100% (n=4) | +21 [+0, +41] |
| bff | 26% (n=112) | 26% (n=43) | 33% (n=18) | 0% (n=2) | +7 [-23, +40] |

## 3. Which matters: belief, or the single answer that defined match/differ?

Wrong candidates, both in one model (judge FE). If anchoring is about what the judge believes, belief should carry the effect and the old single-sample label should add little once belief is known.

| set | checkpoint | old label alone | belief alone | old label, belief held fixed | belief, old label held fixed |
|---|---|---|---|---|---|
| main | A | -6 [-15, +3] | -1 [-16, +13] | -7 [-17, +4] | +3 [-14, +19] |
| main | C | +5 [-3, +14] | +14 [+0, +27] | +2 [-7, +11] | +12 [-2, +26] |
| rb2math | A | -5 [-19, +9] | +4 [-19, +25] | -7 [-22, +8] | +8 [-16, +31] |
| rb2math | C | -5 [-20, +8] | +9 [-11, +28] | -9 [-24, +5] | +14 [-9, +36] |
| judgebench | A | -7 [-19, +6] | -6 [-26, +14] | -6 [-20, +8] | -2 [-24, +20] |
| judgebench | C | +9 [-3, +22] | +21 [+0, +41] | +5 [-9, +18] | +18 [-5, +40] |
| bff | A | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
| bff | C | +17 [-2, +35] | +7 [-23, +40] | +18 [-1, +36] | -3 [-31, +30] |

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
| main | 76%→74% (n=62) | 70%→72% (n=123) | 81%→75% (n=77) | 64%→82% (n=11) | +7 [-9, +24] | +9 [-7, +24] |
| rb2math | 78%→78% (n=54) | 79%→85% (n=68) | 85%→83% (n=47) | 75%→100% (n=8) | +5 [-13, +23] | +9 [-7, +26] |
| judgebench | 62%→50% (n=8) | 58%→55% (n=55) | 73%→63% (n=30) | 33%→33% (n=3) | +13 [-22, +52] | +8 [-30, +46] |
| bff | –→– (n=0) | –→– (n=0) | –→– (n=0) | –→– (n=0) | +nan [+nan, +nan] | +nan [+nan, +nan] |
