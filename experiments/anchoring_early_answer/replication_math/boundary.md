# Math replication: observed rates and any-match contrast (post hoc)

## key: 3228 judgments, 819 candidates

| bin | judgments | candidates | approved | rate [95%] |
|---|---|---|---|---|
| 0/7 | 3062 | 810 | 113 | 3.7 [2.8, 4.6] |
| 1-3 | 117 | 83 | 22 | 18.8 [10.1, 27.9] |
| 4-6 | 36 | 26 | 15 | 41.7 [27.3, 55.6] |
| 7/7 | 13 | 7 | 12 | 92.3 [80.0, 100.0] |

- any match vs none (judge FE): +25.7 [+15.9, +35.9]; rates 29.5% (166 judgments, 95 candidates) vs 3.7% (3062)
  - qwen3.6-35b-a3b: +32.1 [+18.2, +47.4]; 34.1% (n=41) vs 2.1% (n=771)
  - qwen3.5-9b: +19.3 [+8.4, +30.9]; 22.6% (n=53) vs 3.3% (n=750)
  - deepseek-v4.1-flash: +22.2 [+9.6, +35.4]; 28.6% (n=49) vs 6.4% (n=768)
  - kimi-k2.6: +36.2 [+16.0, +58.3]; 39.1% (n=23) vs 3.0% (n=773)

## audited: 3087 judgments, 782 candidates

| bin | judgments | candidates | approved | rate [95%] |
|---|---|---|---|---|
| 0/7 | 2967 | 780 | 90 | 3.0 [2.2, 3.9] |
| 1-3 | 102 | 72 | 14 | 13.7 [5.9, 22.9] |
| 4-6 | 18 | 16 | 4 | 22.2 [5.9, 38.9] |
| 7/7 | 0 | 0 | 0 | – |

- any match vs none (judge FE): +11.8 [+3.9, +20.6]; rates 15.0% (120 judgments, 78 candidates) vs 3.0% (2967)
  - qwen3.6-35b-a3b: +20.5 [+6.7, +36.0]; 21.9% (n=32) vs 1.3% (n=743)
  - qwen3.5-9b: +10.0 [+0.5, +20.8]; 12.5% (n=40) vs 2.5% (n=728)
  - deepseek-v4.1-flash: +11.1 [-0.9, +25.3]; 17.1% (n=35) vs 6.0% (n=745)
  - kimi-k2.6: -2.3 [-3.5, -1.2]; 0.0% (n=13) vs 2.3% (n=751)

