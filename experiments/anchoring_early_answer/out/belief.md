# Belief strength: acceptance vs how often the judge itself reaches the candidate's answer

belief = share of 7 fresh own answers (T=0.7, same prompt) that reach the candidate's final answer. Sample 0, which defined match/differ, is not part of it. Accepts at A = before reasoning; at C = at the verdict (readout). Effects in percentage points, 95% intervals resample whole questions.

Rows with a belief score: 4877 (of the main-set rows in rows.json).

## 1. How stable is the judge's own answer? (wrong candidates)

| set | n | belief 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | old label 'match' among belief 0/7 | old 'differ' among all 7 |
|---|---|---|---|---|---|---|---|
| main | 2440 | 1758 | 274 | 197 | 211 | 1% | 4% |
| rb2math | 1519 | 1262 | 78 | 59 | 120 | 0% | 1% |
| judgebench | 381 | 153 | 107 | 82 | 39 | 8% | 13% |
| bff | 540 | 343 | 89 | 56 | 52 | 1% | 6% |

## 2a. Wrong candidates accepted at A, by belief

| set | 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | slope (all 7 vs 0/7, judge FE) |
|---|---|---|---|---|---|
| main | 25% (n=1758) | 29% (n=274) | 41% (n=197) | 56% (n=211) | +28 [+19, +36] |
| rb2math | 26% (n=1262) | 28% (n=78) | 36% (n=59) | 51% (n=120) | +22 [+9, +34] |
| judgebench | 33% (n=153) | 37% (n=107) | 52% (n=82) | 77% (n=39) | +38 [+23, +53] |
| bff | 17% (n=343) | 19% (n=89) | 29% (n=56) | 54% (n=52) | +33 [+16, +44] |

## 2b. Wrong candidates accepted at C, by belief

| set | 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | slope (all 7 vs 0/7, judge FE) |
|---|---|---|---|---|---|
| main | 18% (n=1758) | 36% (n=274) | 54% (n=197) | 71% (n=211) | +52 [+44, +59] |
| rb2math | 18% (n=1262) | 38% (n=78) | 58% (n=59) | 70% (n=120) | +52 [+40, +63] |
| judgebench | 25% (n=153) | 34% (n=107) | 51% (n=82) | 74% (n=39) | +44 [+29, +59] |
| bff | 15% (n=343) | 36% (n=89) | 54% (n=56) | 71% (n=52) | +56 [+41, +67] |

## 3. Which matters: belief, or the single answer that defined match/differ?

Wrong candidates, both in one model (judge FE). If anchoring is about what the judge believes, belief should carry the effect and the old single-sample label should add little once belief is known.

| set | checkpoint | old label alone | belief alone | old label, belief held fixed | belief, old label held fixed |
|---|---|---|---|---|---|
| main | A | +21 [+14, +28] | +28 [+19, +36] | +5 [-4, +13] | +24 [+12, +35] |
| main | C | +37 [+30, +43] | +52 [+44, +59] | +1 [-7, +10] | +50 [+39, +61] |
| rb2math | A | +18 [+6, +29] | +22 [+9, +34] | -7 [-25, +14] | +29 [+7, +50] |
| rb2math | C | +43 [+33, +52] | +52 [+40, +63] | -6 [-23, +12] | +58 [+36, +78] |
| judgebench | A | +23 [+11, +34] | +38 [+23, +53] | +9 [-5, +22] | +31 [+12, +50] |
| judgebench | C | +20 [+9, +31] | +44 [+29, +59] | +1 [-11, +12] | +44 [+27, +61] |
| bff | A | +27 [+13, +38] | +33 [+16, +44] | +11 [-2, +25] | +23 [+5, +39] |
| bff | C | +42 [+29, +53] | +56 [+41, +67] | +8 [-9, +25] | +49 [+28, +69] |

## 4. Same wrong candidate, different judges (candidate FE + judge FE)

Is it the judge's OWN belief, or a belief every Qwen shares? Only candidates the three Qwens believe to different degrees identify this.

| set | belief effect at A | at C | C minus A |
|---|---|---|---|
| main | +14 [+1, +27] | +22 [+6, +38] | +8 [-10, +25] |
| rb2math | -8 [-30, +13] | +16 [-23, +53] | +24 [-15, +62] |
| judgebench | +31 [+7, +54] | +16 [-8, +41] | -15 [-45, +17] |
| bff | +11 [-10, +30] | +30 [+5, +52] | +19 [-6, +44] |

## 5. Correct candidates: does low belief make the judge reject a right answer?

| set | 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | slope at A | slope at C |
|---|---|---|---|---|---|---|
| main | 25%→30% (n=102) | 55%→71% (n=143) | 65%→85% (n=469) | 75%→91% (n=1723) | +41 [+30, +50] | +46 [+36, +55] |
| rb2math | 37%→44% (n=41) | 74%→81% (n=31) | 69%→93% (n=85) | 81%→93% (n=389) | +34 [+14, +52] | +38 [+21, +55] |
| judgebench | 20%→40% (n=5) | 61%→70% (n=66) | 67%→86% (n=259) | 70%→95% (n=797) | +14 [-3, +30] | +35 [+22, +50] |
| bff | 18%→20% (n=56) | 33%→65% (n=46) | 58%→75% (n=125) | 78%→85% (n=537) | +60 [+47, +72] | +57 [+41, +71] |
