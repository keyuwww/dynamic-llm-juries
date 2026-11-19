# Fixed-effect checks (stated verdict, audited wrong answers, all seven judges)

Rows 4883; duplicated (judge, candidate) rows 0; candidates 978 (767 judged by 2+ families); question ids spanning benchmarks 0.

| spec | groups | identifying groups (questions) | belief variance left | sweeps to 1e-10 | slope, 60 sweeps | converged | exact | 95% CI (1,000 question draws) |
|---|---|---|---|---|---|---|---|---|
| J | 21 | 21 (633) | 0.83 | 2 | +37.62 | +37.62 | +37.62 | +37.6 [+26.8, +48.9] |
| JQ | 2771 | 169 (88) | 0.07 | 2 | +46.86 | +46.86 | +46.86 | +46.9 [+28.0, +70.2] |
| CJ | 978 | 313 (251) | 0.29 | 29 | +19.95 | +19.95 | +19.95 | +20.0 [+9.4, +31.0] |
| CJQ | 978 | 313 (251) | 0.04 | 22 | +20.62 | +20.62 | +20.62 | +20.6 [-6.1, +47.1] |

## Leave one family out

| left out | J | JQ | CJ |
|---|---|---|---|
| 3 Qwens | +34.0 [+22.2, +45.0] | +41.2 [+17.5, +68.4] | +27.1 [+12.5, +41.1] |
| Nemotron-3-Super | +34.3 [+23.7, +45.7] | +44.0 [+23.8, +66.3] | +17.7 [+6.1, +28.9] |
| DeepSeek-V4.1-Flash | +37.5 [+27.6, +48.3] | +47.2 [+25.6, +76.5] | +19.1 [+8.8, +30.2] |
| Kimi-K2.6 | +37.6 [+26.8, +48.1] | +53.9 [+34.3, +79.8] | +17.7 [+6.8, +29.0] |
| Nemotron-3-Nano | +44.5 [+31.5, +56.2] | +46.9 [+25.0, +74.1] | +22.5 [+9.3, +36.4] |

## Per benchmark

| benchmark | J | JQ | CJ |
|---|---|---|---|
| rb2math | +47.2 [+11.3, +74.2] | +37.5 [+6.9, +78.9] | +19.3 [+4.9, +34.7] |
| judgebench | +34.7 [+22.3, +46.7] | +44.9 [+3.6, +95.7] | +19.8 [+2.5, +39.4] |
| bff | +35.6 [+21.5, +50.2] | +61.7 [+39.1, +119.9] | +20.7 [-0.3, +40.1] |

## Within question (JQ), per family, stated verdict

- 3 Qwens: +61.1 [+32.0, +111.0]
- Nemotron-3-Super: +71.8 [+21.4, +180.2]
- DeepSeek-V4.1-Flash: +44.8 [-9.4, +84.5]
- Kimi-K2.6: -12.8 [-69.0, +21.3]
- Nemotron-3-Nano: +46.8 [+8.4, +81.0]
