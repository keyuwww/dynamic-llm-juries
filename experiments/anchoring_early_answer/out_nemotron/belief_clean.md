# Belief strength: acceptance vs how often the judge itself reaches the candidate's answer

belief = share of 7 fresh own answers (T=0.7, same prompt) that reach the candidate's final answer. Sample 0, which defined match/differ, is not part of it. Accepts at A = before reasoning; at C = at the verdict (readout). Effects in percentage points, 95% intervals resample whole questions.

Rows with a belief score: 1571 (of the main-set rows in rows.json).

Clean labels: 59 rows dropped, RB2-Math 'wrong' answers that reach the right value (GLM audit, clean_labels.py).

## 1. How stable is the judge's own answer? (wrong candidates)

| set | n | belief 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | old label 'match' among belief 0/7 | old 'differ' among all 7 |
|---|---|---|---|---|---|---|---|
| main | 768 | 596 | 80 | 50 | 42 | 2% | 2% |
| rb2math | 448 | 418 | 15 | 10 | 5 | 0% | 0% |
| judgebench | 140 | 54 | 49 | 24 | 13 | 15% | 0% |
| bff | 180 | 124 | 16 | 16 | 24 | 1% | 4% |

## 2a. Wrong candidates accepted at A, by belief

| set | 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | slope (all 7 vs 0/7, judge FE) |
|---|---|---|---|---|---|
| main | 33% (n=596) | 41% (n=80) | 58% (n=50) | 81% (n=42) | +42 [+30, +53] |
| rb2math | 33% (n=418) | 33% (n=15) | 50% (n=10) | 100% (n=5) | +42 [+12, +65] |
| judgebench | 35% (n=54) | 41% (n=49) | 46% (n=24) | 69% (n=13) | +23 [-1, +47] |
| bff | 31% (n=124) | 50% (n=16) | 81% (n=16) | 83% (n=24) | +55 [+38, +70] |

## 2b. Wrong candidates accepted at C, by belief

| set | 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | slope (all 7 vs 0/7, judge FE) |
|---|---|---|---|---|---|
| main | 26% (n=596) | 50% (n=80) | 58% (n=50) | 83% (n=42) | +51 [+39, +61] |
| rb2math | 24% (n=418) | 47% (n=15) | 80% (n=10) | 100% (n=5) | +77 [+57, +94] |
| judgebench | 26% (n=54) | 45% (n=49) | 33% (n=24) | 69% (n=13) | +27 [+5, +50] |
| bff | 34% (n=124) | 69% (n=16) | 81% (n=16) | 88% (n=24) | +55 [+39, +71] |

## 3. Which matters: belief, or the single answer that defined match/differ?

Wrong candidates, both in one model (judge FE). If anchoring is about what the judge believes, belief should carry the effect and the old single-sample label should add little once belief is known.

| set | checkpoint | old label alone | belief alone | old label, belief held fixed | belief, old label held fixed |
|---|---|---|---|---|---|
| main | A | +27 [+16, +38] | +42 [+30, +53] | +2 [-14, +19] | +40 [+21, +59] |
| main | C | +32 [+21, +42] | +51 [+39, +61] | +2 [-14, +18] | +48 [+30, +67] |
| rb2math | A | +30 [+3, +54] | +42 [+12, +65] | -2 [-43, +64] | +45 [-25, +97] |
| rb2math | C | +63 [+42, +78] | +77 [+57, +94] | +30 [-21, +82] | +46 [-12, +106] |
| judgebench | A | +13 [-4, +30] | +23 [-1, +47] | +5 [-15, +26] | +19 [-11, +48] |
| judgebench | C | +9 [-7, +26] | +27 [+5, +50] | -3 [-21, +17] | +30 [+2, +57] |
| bff | A | +42 [+24, +56] | +55 [+38, +70] | -10 [-44, +25] | +65 [+26, +104] |
| bff | C | +43 [+24, +59] | +55 [+39, +71] | -6 [-44, +32] | +60 [+21, +101] |

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
| main | 38%→53% (n=34) | 44%→64% (n=50) | 66%→75% (n=155) | 83%→87% (n=560) | +51 [+37, +66] | +36 [+23, +51] |
| rb2math | 33%→60% (n=15) | 75%→100% (n=4) | 74%→84% (n=19) | 90%→94% (n=144) | +53 [+29, +75] | +30 [+8, +53] |
| judgebench | –→– (n=0) | 37%→54% (n=35) | 57%→68% (n=106) | 71%→77% (n=221) | +53 [+29, +75] | +38 [+14, +60] |
| bff | 42%→47% (n=19) | 55%→82% (n=11) | 97%→97% (n=30) | 92%→94% (n=195) | +49 [+24, +73] | +39 [+15, +63] |
