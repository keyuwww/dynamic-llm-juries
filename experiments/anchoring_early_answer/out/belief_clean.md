# Belief strength: acceptance vs how often the judge itself reaches the candidate's answer

belief = share of 7 fresh own answers (T=0.7, same prompt) that reach the candidate's final answer. Sample 0, which defined match/differ, is not part of it. Accepts at A = before reasoning; at C = at the verdict (readout). Effects in percentage points, 95% intervals resample whole questions.

Rows with a belief score: 4697 (of the main-set rows in rows.json).

Clean labels: 180 rows dropped, RB2-Math 'wrong' answers that reach the right value (GLM audit, clean_labels.py).

## 1. How stable is the judge's own answer? (wrong candidates)

| set | n | belief 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | old label 'match' among belief 0/7 | old 'differ' among all 7 |
|---|---|---|---|---|---|---|---|
| main | 2260 | 1741 | 262 | 156 | 101 | 1% | 8% |
| rb2math | 1339 | 1245 | 66 | 18 | 10 | 0% | 0% |
| judgebench | 381 | 153 | 107 | 82 | 39 | 8% | 13% |
| bff | 540 | 343 | 89 | 56 | 52 | 1% | 6% |

## 2a. Wrong candidates accepted at A, by belief

| set | 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | slope (all 7 vs 0/7, judge FE) |
|---|---|---|---|---|---|
| main | 25% (n=1741) | 28% (n=262) | 42% (n=156) | 65% (n=101) | +35 [+25, +43] |
| rb2math | 26% (n=1245) | 24% (n=66) | 39% (n=18) | 80% (n=10) | +32 [+1, +57] |
| judgebench | 33% (n=153) | 37% (n=107) | 52% (n=82) | 77% (n=39) | +38 [+23, +53] |
| bff | 17% (n=343) | 19% (n=89) | 29% (n=56) | 54% (n=52) | +33 [+16, +44] |

## 2b. Wrong candidates accepted at C, by belief

| set | 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | slope (all 7 vs 0/7, judge FE) |
|---|---|---|---|---|---|
| main | 18% (n=1741) | 35% (n=262) | 54% (n=156) | 74% (n=101) | +54 [+45, +63] |
| rb2math | 18% (n=1245) | 36% (n=66) | 72% (n=18) | 90% (n=10) | +71 [+51, +85] |
| judgebench | 25% (n=153) | 34% (n=107) | 51% (n=82) | 74% (n=39) | +44 [+29, +59] |
| bff | 15% (n=343) | 36% (n=89) | 54% (n=56) | 71% (n=52) | +56 [+41, +67] |

## 3. Which matters: belief, or the single answer that defined match/differ?

Wrong candidates, both in one model (judge FE). If anchoring is about what the judge believes, belief should carry the effect and the old single-sample label should add little once belief is known.

| set | checkpoint | old label alone | belief alone | old label, belief held fixed | belief, old label held fixed |
|---|---|---|---|---|---|
| main | A | +23 [+16, +31] | +35 [+25, +43] | +7 [-1, +17] | +28 [+16, +39] |
| main | C | +32 [+25, +40] | +54 [+45, +63] | +3 [-6, +12] | +52 [+39, +63] |
| rb2math | A | +18 [-4, +41] | +32 [+1, +57] | -3 [-24, +23] | +35 [-1, +67] |
| rb2math | C | +41 [+20, +58] | +71 [+51, +85] | -4 [-25, +19] | +75 [+44, +100] |
| judgebench | A | +23 [+11, +34] | +38 [+23, +53] | +9 [-5, +22] | +31 [+12, +50] |
| judgebench | C | +20 [+9, +31] | +44 [+29, +59] | +1 [-11, +12] | +44 [+27, +61] |
| bff | A | +27 [+13, +38] | +33 [+16, +44] | +11 [-2, +25] | +23 [+5, +39] |
| bff | C | +42 [+29, +53] | +56 [+41, +67] | +8 [-9, +25] | +49 [+28, +69] |

## 4. Same wrong candidate, different judges (candidate FE + judge FE)

Is it the judge's OWN belief, or a belief every Qwen shares? Only candidates the three Qwens believe to different degrees identify this.

| set | belief effect at A | at C | C minus A |
|---|---|---|---|
| main | +17 [+3, +31] | +23 [+6, +38] | +5 [-13, +23] |
| rb2math | -2 [-28, +23] | +12 [-34, +56] | +14 [-36, +61] |
| judgebench | +31 [+7, +54] | +16 [-8, +41] | -15 [-45, +17] |
| bff | +11 [-10, +30] | +30 [+5, +52] | +19 [-6, +44] |

## 5. Correct candidates: does low belief make the judge reject a right answer?

| set | 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | slope at A | slope at C |
|---|---|---|---|---|---|---|
| main | 25%→30% (n=102) | 55%→71% (n=143) | 65%→85% (n=469) | 75%→91% (n=1723) | +41 [+30, +50] | +46 [+36, +55] |
| rb2math | 37%→44% (n=41) | 74%→81% (n=31) | 69%→93% (n=85) | 81%→93% (n=389) | +34 [+14, +52] | +38 [+21, +55] |
| judgebench | 20%→40% (n=5) | 61%→70% (n=66) | 67%→86% (n=259) | 70%→95% (n=797) | +14 [-3, +30] | +35 [+22, +50] |
| bff | 18%→20% (n=56) | 33%→65% (n=46) | 58%→75% (n=125) | 78%→85% (n=537) | +60 [+47, +72] | +57 [+41, +71] |
