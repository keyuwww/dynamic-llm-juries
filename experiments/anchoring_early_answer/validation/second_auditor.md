# Second label auditor: Kimi-K3.1-Pro vs GLM-5.3

1085 answers with a verdict from both (of 1091). Rows GLM-5.3, columns Kimi-K3.1-Pro.

| GLM \ Kimi | LABEL_OK | LABEL_WRONG | CONTESTED |
|---|---|---|---|
| LABEL_OK | 960 | 9 | 6 |
| LABEL_WRONG | 8 | 51 | 3 |
| CONTESTED | 20 | 3 | 25 |
- rb2math: n=452, same clearly-wrong-or-not call 98%
- bff: n=182, same clearly-wrong-or-not call 96%
- judgebench: n=451, same clearly-wrong-or-not call 94%

Same three-way verdict: 95%. Same 'clearly wrong or not' call: 96% (Cohen's kappa 0.77).

## Staircase of wrong answers approved, by label set

| judge | labels | 0/7 | 1-3 | 4-6 | 7/7 | gap |
|---|---|---|---|---|---|---|
| 3 Qwens | GLM-5.3 'clearly wrong' | 17% (n=1689) | 30% (n=202) | 45% (n=88) | 59% (n=32) | +43 [+20, +62] |
| 3 Qwens | Kimi-K3.1-Pro 'clearly wrong' | 17% (n=1709) | 31% (n=213) | 48% (n=93) | 56% (n=43) | +38 [+20, +56] |
| 3 Qwens | both 'clearly wrong' | 17% (n=1681) | 30% (n=192) | 43% (n=77) | 52% (n=27) | +35 [+13, +57] |
| Nemotron-3-Super | GLM-5.3 'clearly wrong' | 25% (n=581) | 49% (n=61) | 59% (n=29) | 86% (n=14) | +61 [+40, +77] |
| Nemotron-3-Super | Kimi-K3.1-Pro 'clearly wrong' | 25% (n=585) | 49% (n=68) | 61% (n=31) | 80% (n=15) | +55 [+33, +75] |
| Nemotron-3-Super | both 'clearly wrong' | 25% (n=578) | 50% (n=60) | 63% (n=27) | 82% (n=11) | +57 [+30, +77] |
| DeepSeek-V4.1-Flash | GLM-5.3 'clearly wrong' | 13% (n=566) | 37% (n=38) | 38% (n=21) | 47% (n=15) | +34 [+9, +58] |
| DeepSeek-V4.1-Flash | Kimi-K3.1-Pro 'clearly wrong' | 13% (n=567) | 41% (n=46) | 33% (n=21) | 50% (n=18) | +37 [+14, +60] |
| DeepSeek-V4.1-Flash | both 'clearly wrong' | 13% (n=563) | 35% (n=37) | 28% (n=18) | 50% (n=12) | +37 [+9, +66] |
| Kimi-K2.6 | GLM-5.3 'clearly wrong' | 1% (n=570) | 14% (n=28) | 33% (n=27) | 58% (n=12) | +57 [+23, +87] |
| Kimi-K2.6 | Kimi-K3.1-Pro 'clearly wrong' | 1% (n=572) | 25% (n=36) | 37% (n=27) | 33% (n=12) | +32 [+4, +61] |
| Kimi-K2.6 | both 'clearly wrong' | 1% (n=568) | 15% (n=27) | 33% (n=24) | 40% (n=5) | +39 [-2, +99] |
| Nemotron-3-Nano | GLM-5.3 'clearly wrong' | 37% (n=589) | 45% (n=231) | 46% (n=79) | 55% (n=11) | +18 [-11, +43] |
| Nemotron-3-Nano | Kimi-K3.1-Pro 'clearly wrong' | 37% (n=593) | 44% (n=237) | 43% (n=83) | 58% (n=12) | +21 [-7, +46] |
| Nemotron-3-Nano | both 'clearly wrong' | 37% (n=586) | 45% (n=223) | 45% (n=77) | 55% (n=11) | +18 [-13, +42] |
