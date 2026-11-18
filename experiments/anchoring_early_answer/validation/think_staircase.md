# Belief staircase with thinking ON vs OFF (three Qwens, audited labels)

Wrong answers approved, by belief (how often the judge reaches that answer in 7 thinking-off solves). Same answers in both rows: only those with a thinking-on verdict and a thinking-off verdict. Gap = 7/7 minus 0/7, 95% interval resampling answers.

Audited wrong answers × judges: 2011; used 2011; left out: .

| judge | grading | 0/7 | 1-3 | 4-6 | 7/7 | gap 7/7 − 0/7 |
|---|---|---|---|---|---|---|
| 3 Qwens pooled | thinking off | 17% (n=1689) | 30% (n=202) | 45% (n=88) | 59% (n=32) | +43 [+20, +62] |
| 3 Qwens pooled | thinking on | 3% (n=1689) | 21% (n=202) | 35% (n=88) | 53% (n=32) | +50 [+28, +71] |
| qwen3.5-4b | thinking off | 26% (n=565) | 33% (n=103) | 49% (n=37) | 50% (n=10) | +24 [-10, +62] |
| qwen3.5-4b | thinking on | 2% (n=565) | 20% (n=103) | 46% (n=37) | 40% (n=10) | +38 [+7, +76] |
| qwen3.5-9b | thinking off | 18% (n=554) | 34% (n=58) | 37% (n=35) | 75% (n=12) | +57 [+27, +82] |
| qwen3.5-9b | thinking on | 3% (n=554) | 16% (n=58) | 17% (n=35) | 50% (n=12) | +47 [+13, +77] |
| qwen3.6-35b-a3b | thinking off | 6% (n=570) | 15% (n=41) | 56% (n=16) | 50% (n=10) | +44 [+10, +77] |
| qwen3.6-35b-a3b | thinking on | 4% (n=570) | 29% (n=41) | 50% (n=16) | 70% (n=10) | +66 [+32, +96] |

Thinking on minus thinking off, pooled gap: +8 [-9, +26] points.

## By benchmark (pooled Qwens, thinking on)

| bench | 0/7 | 1-3 | 4-6 | 7/7 |
|---|---|---|---|---|
| rb2math | 1% (n=1225) | 6% (n=52) | 67% (n=6) | 100% (n=2) |
| judgebench | 10% (n=132) | 29% (n=83) | 39% (n=44) | 50% (n=16) |
| bff | 5% (n=332) | 22% (n=67) | 26% (n=38) | 50% (n=14) |

## Right answers approved (pooled Qwens)

| grading | 0/7 | 1-3 | 4-6 | 7/7 |
|---|---|---|---|---|
| thinking off | 30% (n=102) | 71% (n=143) | 85% (n=469) | 91% (n=1723) |
| thinking on | 22% (n=102) | 76% (n=143) | 90% (n=469) | 96% (n=1723) |
