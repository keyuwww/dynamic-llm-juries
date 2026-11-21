# Majority-vote juries at a matched budget (Nov 21 review B4; post hoc)

Counts: {'items_any_verdict': 1604, 'missing_some_verdict': 81, 'dropped_by_audit': 82, 'kept': 1441}; right 747, wrong 694, questions 815; cross-family triples 17.

| policy | false acceptance | false rejection | balanced accuracy |
|---|---|---|---|
| single: deepseek-v4.1-flash | 24.8 | 15.9 | 79.6 |
| single: kimi-k2.6 | 15.7 | 17.4 | 83.4 |
| single: nemotron3-nano-30b | 39.8 | 38.3 | 61.0 |
| single: nemotron3-super-120b | 35.9 | 18.3 | 72.9 |
| single: qwen3.5-4b | 29.0 | 14.7 | 78.2 |
| single: qwen3.5-9b | 28.0 | 15.0 | 78.5 |
| single: qwen3.6-35b-a3b | 19.2 | 14.2 | 83.3 |
| same family: 3 Qwens | 25.5 | 11.5 | 81.5 |
| cross family: Qwen3.6 + Nemotron-Super + DeepSeek | 23.8 | 12.7 | 81.8 |
| cross family: Qwen3.6 + Nemotron-Super + Kimi | 18.7 | 12.9 | 84.2 |
| cross family: Nemotron-Super + DeepSeek + Kimi (no Qwen) | 22.9 | 13.0 | 82.1 |
| cross family: mean over all triples | 23.3 | 13.4 | 81.6 |
| cross family: range of balanced accuracy over triples | | | 78.9–84.6 |

## By the Qwens' mean belief (false acceptance on wrong / false rejection on right, %)

- 0/7 (wrong 512, right 27): same family: 3 Qwens: 15.6 / 74.1; cross family: Qwen3.6 + Nemotron-Super + DeepSeek: 11.9 / 74.1; cross family: Qwen3.6 + Nemotron-Super + Kimi: 5.1 / 74.1; cross family: Nemotron-Super + DeepSeek + Kimi (no Qwen): 10.7 / 74.1; single: qwen3.6-35b-a3b: 5.9 / 77.8; cross family: mean over all triples: 12.9 / 73.2
- 1-3 (wrong 90, right 38): same family: 3 Qwens: 31.1 / 34.2; cross family: Qwen3.6 + Nemotron-Super + DeepSeek: 37.8 / 50.0; cross family: Qwen3.6 + Nemotron-Super + Kimi: 38.9 / 36.8; cross family: Nemotron-Super + DeepSeek + Kimi (no Qwen): 41.1 / 34.2; single: qwen3.6-35b-a3b: 34.4 / 55.3; cross family: mean over all triples: 36.9 / 40.1
- 4-6 (wrong 89, right 177): same family: 3 Qwens: 74.2 / 13.0; cross family: Qwen3.6 + Nemotron-Super + DeepSeek: 75.3 / 14.7; cross family: Qwen3.6 + Nemotron-Super + Kimi: 74.2 / 11.9; cross family: Nemotron-Super + DeepSeek + Kimi (no Qwen): 73.0 / 15.3; single: qwen3.6-35b-a3b: 77.5 / 12.4; cross family: mean over all triples: 67.5 / 14.8
- 7/7 (wrong 3, right 505): same family: 3 Qwens: 100.0 / 5.9; cross family: Qwen3.6 + Nemotron-Super + DeepSeek: 100.0 / 5.9; cross family: Qwen3.6 + Nemotron-Super + Kimi: 100.0 / 8.1; cross family: Nemotron-Super + DeepSeek + Kimi (no Qwen): 66.7 / 7.3; single: qwen3.6-35b-a3b: 100.0 / 8.3; cross family: mean over all triples: 82.4 / 7.7

## Paired differences (points; [95%] resampling questions): false acceptance, false rejection, balanced accuracy

- Qwen3.6 + Nemotron-Super + DeepSeek minus 3 Qwens: -1.7 [-4.8, +1.3], +1.2 [-1.0, +3.3], +0.3 [-1.6, +2.2]
- Qwen3.6 + Nemotron-Super + DeepSeek minus Qwen3.6 alone: +4.6 [+2.0, +7.2], -1.5 [-3.8, +0.8], -1.6 [-3.4, +0.2]
- Qwen3.6 + Nemotron-Super + Kimi minus 3 Qwens: -6.8 [-9.8, -3.7], +1.3 [-0.8, +3.5], +2.7 [+0.9, +4.6]
- Qwen3.6 + Nemotron-Super + Kimi minus Qwen3.6 alone: -0.4 [-2.0, +1.2], -1.3 [-2.9, +0.3], +0.9 [-0.2, +2.0]
- Nemotron-Super + DeepSeek + Kimi (no Qwen) minus 3 Qwens: -2.6 [-6.1, +0.7], +1.5 [-0.9, +3.9], +0.6 [-1.4, +2.8]
- Nemotron-Super + DeepSeek + Kimi (no Qwen) minus Qwen3.6 alone: +3.7 [+0.6, +6.7], -1.2 [-4.0, +1.6], -1.3 [-3.3, +0.8]
- 3 Qwens minus Qwen3.6 alone: +6.3 [+3.6, +9.1], -2.7 [-4.6, -0.6], -1.8 [-3.6, -0.1]
- believed wrong (n=92): Qwen3.6 + Nemotron-Super + DeepSeek minus 3 Qwens, false acceptance: +1.1 [-7.5, +10.8]
- believed wrong (n=92): Qwen3.6 + Nemotron-Super + Kimi minus 3 Qwens, false acceptance: +0.0 [-8.1, +8.4]
- believed wrong (n=92): Nemotron-Super + DeepSeek + Kimi (no Qwen) minus 3 Qwens, false acceptance: -2.2 [-12.1, +8.6]

## False acceptance on the 92 wrong answers the Qwens believe (mean >= 4/7)

- single: deepseek-v4.1-flash: 69.6
- single: kimi-k2.6: 69.6
- single: nemotron3-nano-30b: 41.3
- single: nemotron3-super-120b: 69.6
- single: qwen3.5-4b: 29.3
- single: qwen3.5-9b: 75.0
- single: qwen3.6-35b-a3b: 78.3
- same family: 3 Qwens: 75.0
- cross family: Qwen3.6 + Nemotron-Super + DeepSeek: 76.1
- cross family: Qwen3.6 + Nemotron-Super + Kimi: 75.0
- cross family: Nemotron-Super + DeepSeek + Kimi (no Qwen): 72.8
