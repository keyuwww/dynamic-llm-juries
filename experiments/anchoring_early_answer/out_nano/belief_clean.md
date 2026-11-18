# Belief strength: acceptance vs how often the judge itself reaches the candidate's answer

belief = share of 7 fresh own answers (T=0.7, same prompt) that reach the candidate's final answer. Sample 0, which defined match/differ, is not part of it. Accepts at A = before reasoning; at C = at the verdict (readout). Effects in percentage points, 95% intervals resample whole questions.

Rows with a belief score: 1579 (of the main-set rows in rows.json).

Clean labels: 60 rows dropped, RB2-Math 'wrong' answers that reach the right value (GLM audit, clean_labels.py).

## 1. How stable is the judge's own answer? (wrong candidates)

| set | n | belief 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | old label 'match' among belief 0/7 | old 'differ' among all 7 |
|---|---|---|---|---|---|---|---|
| main | 1012 | 613 | 276 | 104 | 19 | 2% | 16% |
| rb2math | 448 | 356 | 60 | 26 | 6 | 0% | 50% |
| judgebench | 382 | 156 | 174 | 51 | 1 | 6% | 0% |
| bff | 182 | 101 | 42 | 27 | 12 | 3% | 0% |

## 2a. Wrong candidates accepted at A, by belief

| set | 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | slope (all 7 vs 0/7, judge FE) |
|---|---|---|---|---|---|
| main | – (n=0) | – (n=0) | – (n=0) | – (n=0) | +nan [+nan, +nan] |
| rb2math | – (n=0) | – (n=0) | – (n=0) | – (n=0) | +nan [+nan, +nan] |
| judgebench | – (n=0) | – (n=0) | – (n=0) | – (n=0) | +nan [+nan, +nan] |
| bff | – (n=0) | – (n=0) | – (n=0) | – (n=0) | +nan [+nan, +nan] |

## 2b. Wrong candidates accepted at C, by belief

| set | 0/7 | 1-3 of 7 | 4-6 of 7 | all 7 | slope (all 7 vs 0/7, judge FE) |
|---|---|---|---|---|---|
| main | 37% (n=613) | 45% (n=276) | 44% (n=104) | 58% (n=19) | +18 [+6, +30] |
| rb2math | 36% (n=356) | 68% (n=60) | 58% (n=26) | 67% (n=6) | +41 [+19, +65] |
| judgebench | 42% (n=156) | 40% (n=174) | 39% (n=51) | 0% (n=1) | -6 [-27, +14] |
| bff | 33% (n=101) | 33% (n=42) | 41% (n=27) | 58% (n=12) | +21 [+1, +43] |

## 3. Which matters: belief, or the single answer that defined match/differ?

Wrong candidates, both in one model (judge FE). If anchoring is about what the judge believes, belief should carry the effect and the old single-sample label should add little once belief is known.

| set | checkpoint | old label alone | belief alone | old label, belief held fixed | belief, old label held fixed |
|---|---|---|---|---|---|
| main | A | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
| main | C | +6 [-2, +15] | +18 [+6, +30] | -1 [-11, +9] | +18 [+3, +33] |
| rb2math | A | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
| rb2math | C | +29 [+10, +45] | +41 [+19, +65] | +15 [-6, +35] | +32 [+6, +58] |
| judgebench | A | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
| judgebench | C | -4 [-16, +8] | -6 [-27, +14] | -3 [-17, +10] | -4 [-27, +21] |
| bff | A | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] | +nan [+nan, +nan] |
| bff | C | +9 [-6, +26] | +21 [+1, +43] | -6 [-30, +16] | +27 [-1, +57] |

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
| main | –→– (n=0) | –→– (n=0) | –→– (n=0) | –→– (n=0) | +nan [+nan, +nan] | +nan [+nan, +nan] |
| rb2math | –→– (n=0) | –→– (n=0) | –→– (n=0) | –→– (n=0) | +nan [+nan, +nan] | +nan [+nan, +nan] |
| judgebench | –→– (n=0) | –→– (n=0) | –→– (n=0) | –→– (n=0) | +nan [+nan, +nan] | +nan [+nan, +nan] |
| bff | –→– (n=0) | –→– (n=0) | –→– (n=0) | –→– (n=0) | +nan [+nan, +nan] | +nan [+nan, +nan] |
