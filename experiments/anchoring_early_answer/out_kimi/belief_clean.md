# Belief strength: acceptance vs how often the judge itself reaches the candidate's answer

belief = share of 7 fresh own answers (T=0.7, same prompt) that reach the candidate's final answer. Sample 0, which defined match/differ, is not part of it. Accepts at A = before reasoning; at C = at the verdict (readout). Effects in percentage points, 95% intervals resample whole questions.

Rows with a belief score: 1564 (of the main-set rows in rows.json).

Clean labels: 60 rows dropped, RB2-Math 'wrong' answers that reach the right value (GLM audit, clean_labels.py).

## 1. How stable is the judge's own answer? (wrong candidates)

| set | n | belief 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | old label 'match' among belief 0/7 | old 'differ' among all 7 |
|---|---|---|---|---|---|---|---|
| main | 713 | 581 | 45 | 44 | 43 | 0% | 0% |
| rb2math | 450 | 426 | 11 | 5 | 8 | 0% | 0% |
| judgebench | 82 | 22 | 20 | 25 | 15 | 0% | 0% |
| bff | 181 | 133 | 14 | 14 | 20 | 1% | 0% |

## 2a. Wrong candidates accepted at A, by belief

| set | 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | slope (all 7 vs 0/7, judge FE) |
|---|---|---|---|---|---|
| main | 16% (n=581) | 31% (n=45) | 48% (n=44) | 53% (n=43) | +38 [+22, +52] |
| rb2math | 17% (n=426) | 27% (n=11) | 20% (n=5) | 50% (n=8) | +27 [-1, +57] |
| judgebench | 23% (n=22) | 30% (n=20) | 64% (n=25) | 47% (n=15) | +35 [+9, +62] |
| bff | 9% (n=133) | 36% (n=14) | 29% (n=14) | 60% (n=20) | +45 [+21, +63] |

## 2b. Wrong candidates accepted at C, by belief

| set | 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | slope (all 7 vs 0/7, judge FE) |
|---|---|---|---|---|---|
| main | 2% (n=580) | 31% (n=45) | 48% (n=44) | 67% (n=43) | +57 [+42, +68] |
| rb2math | 1% (n=425) | 27% (n=11) | 20% (n=5) | 75% (n=8) | +66 [+38, +90] |
| judgebench | 14% (n=22) | 25% (n=20) | 68% (n=25) | 80% (n=15) | +68 [+45, +90] |
| bff | 2% (n=133) | 43% (n=14) | 21% (n=14) | 55% (n=20) | +46 [+20, +62] |

## 3. Which matters: belief, or the single answer that defined match/differ?

Wrong candidates, both in one model (judge FE). If anchoring is about what the judge believes, belief should carry the effect and the old single-sample label should add little once belief is known.

| set | checkpoint | old label alone | belief alone | old label, belief held fixed | belief, old label held fixed |
|---|---|---|---|---|---|
| main | A | +27 [+14, +40] | +38 [+22, +52] | +3 [-18, +25] | +35 [+7, +61] |
| main | C | +39 [+25, +50] | +57 [+42, +68] | -0 [-21, +21] | +57 [+32, +81] |
| rb2math | A | +25 [-1, +53] | +27 [-1, +57] | +16 [-32, +60] | +13 [-37, +67] |
| rb2math | C | +56 [+28, +81] | +66 [+38, +90] | +24 [-20, +70] | +45 [-2, +92] |
| judgebench | A | +21 [-1, +42] | +35 [+9, +62] | +3 [-27, +37] | +32 [-11, +72] |
| judgebench | C | +27 [+5, +48] | +68 [+45, +90] | -20 [-42, +5] | +86 [+56, +114] |
| bff | A | +32 [+12, +51] | +45 [+21, +63] | -15 [-48, +21] | +62 [+16, +105] |
| bff | C | +39 [+16, +54] | +46 [+20, +62] | +25 [-24, +65] | +19 [-28, +74] |

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
| main | 23%→23% (n=31) | 45%→65% (n=20) | 56%→77% (n=66) | 75%→89% (n=728) | +52 [+37, +66] | +54 [+40, +69] |
| rb2math | 36%→36% (n=14) | 38%→50% (n=8) | 57%→86% (n=14) | 76%→92% (n=146) | +45 [+20, +67] | +54 [+30, +78] |
| judgebench | 33%→67% (n=3) | 75%→100% (n=4) | 56%→92% (n=36) | 73%→95% (n=367) | +38 [+2, +81] | +20 [-5, +54] |
| bff | 7%→0% (n=14) | 38%→62% (n=8) | 56%→38% (n=16) | 76%→76% (n=215) | +66 [+44, +84] | +69 [+47, +87] |
