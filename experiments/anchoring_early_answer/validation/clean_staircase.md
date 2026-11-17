# Belief staircase after label cleaning (three Qwens, thinking off)

Wrong answers approved, by how often the judge reaches that answer itself (0/7 .. 7/7). Gap = 7/7 minus 0/7, 95% interval resampling answers. RB2 Math rows keep the earlier value-match cleaning in every version.

| labels | 0/7 | 1-3 | 4-6 | 7/7 | gap 7/7 − 0/7 |
|---|---|---|---|---|---|
| as released | 18% (n=1741) | 35% (n=262) | 54% (n=156) | 74% (n=101) | +56 [+45, +66] |
| drop GLM-5.3 'actually correct' | 18% (n=1736) | 33% (n=243) | 53% (n=128) | 69% (n=54) | +51 [+37, +63] |
| only GLM-5.3 'clearly wrong' | 17% (n=1709) | 30% (n=216) | 49% (n=100) | 65% (n=40) | +48 [+30, +64] |
| GLM-5.3 and Claude both 'clearly wrong' | 17% (n=1709) | 30% (n=216) | 49% (n=100) | 63% (n=35) | +46 [+27, +63] |

## By benchmark (only GLM-5.3 'clearly wrong')

| bench | 0/7 | 1-3 | 4-6 | 7/7 |
|---|---|---|---|---|
| rb2math | 18% (n=1245) | 36% (n=66) | 72% (n=18) | 90% (n=10) |
| bff | 15% (n=332) | 27% (n=67) | 45% (n=38) | 43% (n=14) |
| judgebench | 16% (n=132) | 28% (n=83) | 43% (n=44) | 69% (n=16) |

## By judge (only GLM-5.3 'clearly wrong')

| judge | 0/7 | 1-3 | 4-6 | 7/7 |
|---|---|---|---|---|
| qwen3.5-4b | 26% | 32% | 52% | 58% |
| qwen3.5-9b | 18% | 35% | 41% | 73% |
| qwen3.6-35b-a3b | 7% | 18% | 58% | 62% |

## How many 'wrong' answers are actually wrong, by belief level (GLM-5.3, unique answers, BFF + JudgeBench)

| belief | clearly wrong | actually correct | contested | approval if actually correct |
|---|---|---|---|---|
| 0/7 | 233 | 2 | 10 | 80% (n=5) |
| 1-3 | 120 | 15 | 18 | 63% (n=19) |
| 4-6 | 57 | 23 | 21 | 61% (n=28) |
| 7/7 | 23 | 23 | 9 | 81% (n=47) |

GLM-5.3 vs Claude on the 55 answers believed 7/7: same three-way verdict 80%, same 'clearly wrong or not' call 87%.

## Every judge family: as released vs only GLM-5.3 'clearly wrong'

Answers not in the audit are kept as released. Gap = 7/7 minus 0/7 with a 95% interval resampling answers.

| judge | labels | 0/7 | 1-3 | 4-6 | 7/7 | gap |
|---|---|---|---|---|---|---|
| Qwen3.5-4B / 9B / Qwen3.6-35B (Alibaba) | as released | 18% (n=1741) | 35% (n=262) | 54% (n=156) | 74% (n=101) | +56 [+46, +66] |
| Qwen3.5-4B / 9B / Qwen3.6-35B (Alibaba) | clean | 17% (n=1715) | 30% (n=216) | 49% (n=100) | 65% (n=40) | +48 [+30, +63] |
| Nemotron-3-Super-120B (NVIDIA) | as released | 26% (n=596) | 50% (n=80) | 58% (n=50) | 83% (n=42) | +57 [+45, +68] |
| Nemotron-3-Super-120B (NVIDIA) | clean | 26% (n=588) | 55% (n=66) | 62% (n=34) | 88% (n=17) | +62 [+45, +76] |
| DeepSeek-V4.1-Flash (DeepSeek) | as released | 13% (n=580) | 45% (n=53) | 55% (n=31) | 68% (n=50) | +55 [+41, +67] |
| DeepSeek-V4.1-Flash (DeepSeek) | clean | 13% (n=572) | 42% (n=45) | 43% (n=23) | 55% (n=20) | +42 [+20, +65] |
| Kimi-K2.6 (Moonshot) | as released | 2% (n=580) | 31% (n=45) | 48% (n=44) | 67% (n=43) | +66 [+52, +80] |
| Kimi-K2.6 (Moonshot) | clean | 2% (n=576) | 21% (n=34) | 34% (n=29) | 65% (n=17) | +63 [+40, +85] |
