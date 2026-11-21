# Paper numbers (single source)

 (used everywhere unless a row says otherwise):
  approval   the verdict the judge states at the end of its transcript (spoken; agrees with the forced read at the
             transcript's end, acc_C, on 97-100% of rows); JudgeBench: picking the target response
  belief     share of the judge's 7 extra own answers (T=0.7) that reach the candidate's final answer
  labels     audited: a wrong-labelled answer is kept only if GLM-5.3 audits it as clearly wrong (LABEL_OK), on all three
             benchmarks (RB2 Math additionally had the value-match cleaning before); "released" = no audit
  intervals  95%, resampling whole questions (judge-independent question id), 2,000 draws
  effects    linear probability model, belief 0 -> 1 (= 0/7 -> 7/7), in points

  

## T1. Label audit by belief (Qwen rows, unique BFF + JudgeBench wrong-labelled answers, highest Qwen belief)

| belief | clearly wrong | actually correct | contested | no verdict | approval of 'actually correct' (judgments) |
|---|---|---|---|---|---|
| 0/7 | 155 | 1 | 4 | 2 | 80% (n=5) |
| 1-3 | 95 | 4 | 4 | 3 | 63% (n=19) |
| 4-6 | 49 | 11 | 16 | 0 | 61% (n=28) |
| 7/7 | 23 | 23 | 9 | 0 | 81% (n=47) |

## T2. Wrong answers approved by belief (stated verdict)

| judge | labels | 0/7 | 1-3 | 4-6 | 7/7 | gap 7/7 − 0/7 |
|---|---|---|---|---|---|---|
| 3 Qwens | audited | 17% (n=1689) | 30% (n=202) | 45% (n=88) | 59% (n=32) | +43 [+20, +62] |
| 3 Qwens | released | 18% (n=1741) | 35% (n=262) | 54% (n=156) | 74% (n=101) | +56 [+44, +66] |
| Nemotron-3-Super | audited | 25% (n=581) | 49% (n=61) | 59% (n=29) | 86% (n=14) | +61 [+40, +77] |
| Nemotron-3-Super | released | 25% (n=596) | 48% (n=80) | 58% (n=50) | 83% (n=42) | +58 [+44, +69] |
| DeepSeek-V4.1-Flash | audited | 13% (n=566) | 37% (n=38) | 38% (n=21) | 47% (n=15) | +34 [+9, +58] |
| DeepSeek-V4.1-Flash | released | 13% (n=580) | 45% (n=53) | 55% (n=31) | 68% (n=50) | +55 [+40, +68] |
| Kimi-K2.6 | audited | 1% (n=570) | 14% (n=28) | 33% (n=27) | 58% (n=12) | +57 [+23, +87] |
| Kimi-K2.6 | released | 2% (n=580) | 31% (n=45) | 48% (n=44) | 67% (n=43) | +66 [+50, +80] |
| Nemotron-3-Nano | audited | 37% (n=589) | 45% (n=231) | 46% (n=79) | 55% (n=11) | +18 [-11, +43] |
| Nemotron-3-Nano | released | 37% (n=613) | 45% (n=276) | 44% (n=104) | 58% (n=19) | +21 [-1, +41] |

## R1. Belief vs the one-sample 'matches my answer' label (audited wrong answers, judge FE)

| judge | belief alone | label alone | label, belief fixed | belief, label fixed | % believed-0/7 with label 'match' | % 7/7 with label 'differ' |
|---|---|---|---|---|---|---|
| 3 Qwens | +44 [+28, +56] | +21 [+10, +32] | +2 [-9, +12] | +43 [+26, +57] | 1% | 16% |
| Nemotron-3-Super | +57 [+40, +73] | +25 [+9, +39] | -5 [-23, +13] | +61 [+38, +86] | 2% | 7% |
| DeepSeek-V4.1-Flash | +38 [+17, +59] | +14 [-0, +29] | -15 [-37, +7] | +52 [+20, +82] | 1% | 0% |
| Kimi-K2.6 | +38 [+18, +58] | +25 [+10, +41] | +3 [-19, +24] | +35 [+5, +63] | 0% | 0% |
| Nemotron-3-Nano | +17 [+2, +31] | +1 [-8, +12] | -6 [-17, +7] | +21 [+4, +37] | 2% | 27% |

## R2. Same wrong answer, different Qwen judges (candidate + judge FE, audited)

Belief effect +17 [-2, +37]; candidates believed to different degrees by the three Qwens: 151.


## R3. Before any reasoning (A: 'VERDICT:' appended to the prompt) vs the stated verdict (Qwens, audited)

Belief effect at A +22 [+7, +37]; at the stated verdict +44 [+28, +56]; staircase at A 25% / 25% / 38% / 50%; stated 17% / 30% / 45% / 59%.

## R4. Per Qwen judge (audited)

| judge | 0/7 | 1-3 | 4-6 | 7/7 | gap |
|---|---|---|---|---|---|
| qwen3.5-4b | 26% (n=565) | 33% (n=103) | 49% (n=37) | 50% (n=10) | +24 [-10, +62] |
| qwen3.5-9b | 18% (n=554) | 34% (n=58) | 37% (n=35) | 75% (n=12) | +57 [+27, +82] |
| qwen3.6-35b-a3b | 6% (n=570) | 15% (n=41) | 56% (n=16) | 50% (n=10) | +44 [+10, +77] |

## R5. RIGHT answers approved by belief (labels as released for right answers)

| judge | 0/7 | 1-3 | 4-6 | 7/7 |
|---|---|---|---|---|
| 3 Qwens | 30% (n=102) | 71% (n=143) | 85% (n=469) | 91% (n=1723) |
| Nemotron-3-Super | 53% (n=34) | 72% (n=50) | 81% (n=155) | 90% (n=560) |
| DeepSeek-V4.1-Flash | 22% (n=32) | 56% (n=32) | 76% (n=107) | 90% (n=679) |
| Kimi-K2.6 | 23% (n=31) | 65% (n=20) | 77% (n=66) | 89% (n=728) |
| Nemotron-3-Nano | 50% (n=50) | 58% (n=114) | 66% (n=189) | 83% (n=214) |

## R6. Per benchmark, four families pooled (audited)

| benchmark | 0/7 | 1-3 | 4-6 | 7/7 | gap |
|---|---|---|---|---|---|
| rb2math | 18% (n=2831) | 50% (n=125) | 49% (n=39) | 75% (n=12) | +57 [-16, +81] |
| judgebench | 26% (n=367) | 36% (n=306) | 42% (n=118) | 69% (n=32) | +43 [+21, +61] |
| bff | 17% (n=797) | 33% (n=129) | 47% (n=87) | 50% (n=40) | +33 [+12, +53] |
| all three | 18% (n=3995) | 38% (n=560) | 45% (n=244) | 61% (n=84) | +42 [+28, +56] |

## C. Counts

- 3 Qwens: judgments with belief and a stated verdict 4697 (wrong 2260, audited wrong 2011); by bench rb2math 1885, judgebench 1508, bff 1304
- Nemotron-3-Super: judgments with belief and a stated verdict 1567 (wrong 768, audited wrong 685); by bench rb2math 630, judgebench 502, bff 435
- DeepSeek-V4.1-Flash: judgments with belief and a stated verdict 1564 (wrong 714, audited wrong 640); by bench rb2math 631, judgebench 499, bff 434
- Kimi-K2.6: judgments with belief and a stated verdict 1557 (wrong 712, audited wrong 637); by bench rb2math 631, judgebench 492, bff 434
- Nemotron-3-Nano: judgments with belief and a stated verdict 1579 (wrong 1012, audited wrong 910); by bench rb2math 630, judgebench 512, bff 437
