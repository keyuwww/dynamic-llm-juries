# Majority-vote juries at a matched budget (Nov 21 review B4; post hoc)

Counts: {'items_any_verdict': 1604, 'missing_some_verdict': 81, 'judgebench_pairs_never_audited': 67, 'dropped_by_audit': 154, 'kept': 1369}; right 434, wrong 935, questions 755; cross-family triples 17.

| policy | false acceptance | false rejection | balanced accuracy |
|---|---|---|---|
| single: deepseek-v4.1-flash | 16.0 | 14.3 | 84.8 |
| single: kimi-k2.6 | 4.7 | 24.2 | 85.6 |
| single: nemotron3-nano-30b | 41.5 | 27.2 | 65.7 |
| single: nemotron3-super-120b | 28.1 | 8.5 | 81.7 |
| single: qwen3.5-4b | 25.3 | 16.1 | 79.3 |
| single: qwen3.5-9b | 18.4 | 16.4 | 82.6 |
| single: qwen3.6-35b-a3b | 6.8 | 21.0 | 86.1 |
| self-consistency: qwen3.5-4b x3 | 24.5 | 15.0 | 80.3 |
| self-consistency: qwen3.5-9b x3 | 15.7 | 13.8 | 85.2 |
| self-consistency: qwen3.6-35b-a3b x3 | 5.7 | 20.5 | 86.9 |
| self-consistency: nemotron3-super-120b x3 | 28.7 | 8.5 | 81.4 |
| self-consistency: deepseek-v4.1-flash x3 | 13.4 | 13.8 | 86.4 |
| self-consistency: kimi-k2.6 x3 | 3.9 | 24.0 | 86.1 |
| same family: 3 Qwens | 14.8 | 14.7 | 85.2 |
| cross family: Qwen3.6 + Nemotron-Super + DeepSeek | 12.6 | 12.9 | 87.2 |
| cross family: Qwen3.6 + Nemotron-Super + Kimi | 6.6 | 17.5 | 87.9 |
| cross family: Nemotron-Super + DeepSeek + Kimi (no Qwen) | 12.7 | 12.7 | 87.3 |
| cross family: mean over all triples | 13.4 | 15.0 | 85.8 |
| cross family: range of balanced accuracy over triples | | | 81.1–88.3 |

## By the Qwens' mean belief (false acceptance on wrong / false rejection on right, %)

- 0/7 (wrong 774, right 27): same family: 3 Qwens: 11.9 / 74.1; cross family: Qwen3.6 + Nemotron-Super + DeepSeek: 10.3 / 74.1; cross family: Qwen3.6 + Nemotron-Super + Kimi: 4.1 / 74.1; cross family: Nemotron-Super + DeepSeek + Kimi (no Qwen): 10.2 / 74.1; single: qwen3.6-35b-a3b: 4.4 / 77.8; self-consistency: qwen3.5-4b x3: 20.9 / 66.7; self-consistency: qwen3.5-9b x3: 12.8 / 74.1; self-consistency: qwen3.6-35b-a3b x3: 3.1 / 77.8; self-consistency: nemotron3-super-120b x3: 25.8 / 59.3; self-consistency: deepseek-v4.1-flash x3: 11.2 / 70.4; self-consistency: kimi-k2.6 x3: 1.9 / 85.2; cross family: mean over all triples: 11.0 / 73.2
- 1-3 (wrong 127, right 21): same family: 3 Qwens: 22.0 / 28.6; cross family: Qwen3.6 + Nemotron-Super + DeepSeek: 17.3 / 42.9; cross family: Qwen3.6 + Nemotron-Super + Kimi: 12.6 / 38.1; cross family: Nemotron-Super + DeepSeek + Kimi (no Qwen): 20.5 / 38.1; single: qwen3.6-35b-a3b: 13.4 / 57.1; self-consistency: qwen3.5-4b x3: 34.6 / 19.0; self-consistency: qwen3.5-9b x3: 24.4 / 28.6; self-consistency: qwen3.6-35b-a3b x3: 11.8 / 57.1; self-consistency: nemotron3-super-120b x3: 35.4 / 9.5; self-consistency: deepseek-v4.1-flash x3: 17.3 / 42.9; self-consistency: kimi-k2.6 x3: 7.9 / 57.1; cross family: mean over all triples: 19.6 / 38.9
- 4-6 (wrong 31, right 85): same family: 3 Qwens: 51.6 / 14.1; cross family: Qwen3.6 + Nemotron-Super + DeepSeek: 45.2 / 12.9; cross family: Qwen3.6 + Nemotron-Super + Kimi: 38.7 / 16.5; cross family: Nemotron-Super + DeepSeek + Kimi (no Qwen): 38.7 / 9.4; single: qwen3.6-35b-a3b: 35.5 / 18.8; self-consistency: qwen3.5-4b x3: 67.7 / 20.0; self-consistency: qwen3.5-9b x3: 48.4 / 14.1; self-consistency: qwen3.6-35b-a3b x3: 38.7 / 20.0; self-consistency: nemotron3-super-120b x3: 71.0 / 4.7; self-consistency: deepseek-v4.1-flash x3: 45.2 / 11.8; self-consistency: kimi-k2.6 x3: 29.0 / 23.5; cross family: mean over all triples: 42.5 / 13.4
- 7/7 (wrong 3, right 301): same family: 3 Qwens: 66.7 / 8.6; cross family: Qwen3.6 + Nemotron-Super + DeepSeek: 66.7 / 5.3; cross family: Qwen3.6 + Nemotron-Super + Kimi: 66.7 / 11.3; cross family: Nemotron-Super + DeepSeek + Kimi (no Qwen): 66.7 / 6.3; single: qwen3.6-35b-a3b: 66.7 / 14.0; self-consistency: qwen3.5-4b x3: 66.7 / 8.6; self-consistency: qwen3.5-9b x3: 66.7 / 7.3; self-consistency: qwen3.6-35b-a3b x3: 66.7 / 13.0; self-consistency: nemotron3-super-120b x3: 33.3 / 5.0; self-consistency: deepseek-v4.1-flash x3: 66.7 / 7.3; self-consistency: kimi-k2.6 x3: 66.7 / 16.3; cross family: mean over all triples: 62.7 / 8.6

## Paired differences (points; [95%] resampling questions): false acceptance, false rejection, balanced accuracy

- Qwen3.6 + Nemotron-Super + DeepSeek minus 3 Qwens: -2.1 [-4.5, +0.3], -1.8 [-4.5, +0.5], +2.0 [+0.3, +3.8]
- Qwen3.6 + Nemotron-Super + DeepSeek minus Qwen3.6 alone: +5.8 [+3.7, +7.9], -8.1 [-11.0, -5.3], +1.1 [-0.6, +2.9]
- Qwen3.6 + Nemotron-Super + Kimi minus 3 Qwens: -8.1 [-10.4, -5.9], +2.8 [-0.2, +5.8], +2.7 [+0.8, +4.5]
- Qwen3.6 + Nemotron-Super + Kimi minus Qwen3.6 alone: -0.2 [-1.5, +1.0], -3.5 [-5.8, -1.3], +1.8 [+0.6, +3.2]
- Nemotron-Super + DeepSeek + Kimi (no Qwen) minus 3 Qwens: -2.0 [-4.7, +0.7], -2.1 [-5.0, +0.8], +2.1 [+0.1, +4.1]
- Nemotron-Super + DeepSeek + Kimi (no Qwen) minus Qwen3.6 alone: +5.9 [+3.5, +8.5], -8.3 [-11.6, -4.9], +1.2 [-1.0, +3.3]
- 3 Qwens minus Qwen3.6 alone: +7.9 [+6.1, +10.0], -6.2 [-9.1, -3.7], -0.8 [-2.5, +0.8]
- qwen3.5-4b x3 minus qwen3.5-4b alone: -0.9 [-2.8, +0.9], -1.2 [-3.4, +0.9], +1.0 [-0.4, +2.5]
- qwen3.5-9b x3 minus qwen3.5-9b alone: -2.7 [-4.5, -0.9], -2.5 [-4.5, -0.7], +2.6 [+1.4, +3.9]
- qwen3.6-35b-a3b x3 minus qwen3.6-35b-a3b alone: -1.2 [-2.3, -0.1], -0.5 [-2.4, +1.5], +0.8 [-0.3, +2.0]
- nemotron3-super-120b x3 minus nemotron3-super-120b alone: +0.5 [-1.3, +2.3], +0.0 [-1.7, +1.7], -0.3 [-1.5, +0.9]
- deepseek-v4.1-flash x3 minus deepseek-v4.1-flash alone: -2.7 [-4.2, -1.2], -0.5 [-2.4, +1.3], +1.6 [+0.4, +2.7]
- kimi-k2.6 x3 minus kimi-k2.6 alone: -0.9 [-1.8, +0.0], -0.2 [-2.5, +2.0], +0.5 [-0.7, +1.8]
- Qwen3.6 + Nemotron-Super + DeepSeek minus self-consistency: qwen3.6-35b-a3b x3: +7.0 [+4.8, +9.1], -7.6 [-10.9, -4.6], +0.3 [-1.4, +2.3]
- Qwen3.6 + Nemotron-Super + Kimi minus self-consistency: qwen3.6-35b-a3b x3: +1.0 [-0.5, +2.4], -3.0 [-5.6, -0.7], +1.0 [-0.3, +2.5]
- Nemotron-Super + DeepSeek + Kimi (no Qwen) minus self-consistency: qwen3.6-35b-a3b x3: +7.1 [+4.8, +9.5], -7.8 [-11.4, -4.4], +0.4 [-1.7, +2.5]
- 3 Qwens minus self-consistency: qwen3.6-35b-a3b x3: +9.1 [+6.9, +11.2], -5.8 [-9.0, -2.8], -1.7 [-3.5, +0.2]
- believed wrong (n=34): Qwen3.6 + Nemotron-Super + DeepSeek minus 3 Qwens, false acceptance: -5.9 [-24.2, +11.8]
- believed wrong (n=34): Qwen3.6 + Nemotron-Super + Kimi minus 3 Qwens, false acceptance: -11.8 [-26.5, +0.0]
- believed wrong (n=34): Nemotron-Super + DeepSeek + Kimi (no Qwen) minus 3 Qwens, false acceptance: -11.8 [-32.4, +6.2]
- believed wrong (n=34): qwen3.5-4b x3 minus 3 Qwens, false acceptance: +14.7 [-3.0, +33.3]
- believed wrong (n=34): qwen3.5-9b x3 minus 3 Qwens, false acceptance: -2.9 [-18.2, +12.1]
- believed wrong (n=34): qwen3.6-35b-a3b x3 minus 3 Qwens, false acceptance: -11.8 [-26.5, +0.0]

## False acceptance on the 34 wrong answers the Qwens believe (mean >= 4/7)

- single: deepseek-v4.1-flash: 41.2
- single: kimi-k2.6: 26.5
- single: nemotron3-nano-30b: 52.9
- single: nemotron3-super-120b: 67.6
- single: qwen3.5-4b: 58.8
- single: qwen3.5-9b: 52.9
- single: qwen3.6-35b-a3b: 38.2
- self-consistency: qwen3.5-4b x3: 67.6
- self-consistency: qwen3.5-9b x3: 50.0
- self-consistency: qwen3.6-35b-a3b x3: 41.2
- self-consistency: nemotron3-super-120b x3: 67.6
- self-consistency: deepseek-v4.1-flash x3: 47.1
- self-consistency: kimi-k2.6 x3: 32.4
- same family: 3 Qwens: 52.9
- cross family: Qwen3.6 + Nemotron-Super + DeepSeek: 47.1
- cross family: Qwen3.6 + Nemotron-Super + Kimi: 41.2
- cross family: Nemotron-Super + DeepSeek + Kimi (no Qwen): 41.2

Repeats: {'units_with_fewer_than_two_repeats': {'qwen3.5-4b': 0, 'qwen3.5-9b': 0, 'qwen3.6-35b-a3b': 0, 'nemotron3-super-120b': 0, 'deepseek-v4.1-flash': 0, 'kimi-k2.6': 0}, 'spent': 38.87582172, 'parser_vs_paper_original': {'agree': 8823, 'n': 8823}, 'cut_off': 8}

## Repeatability: approvals of wrong answers, by the judge's own belief

Share of the two repeat verdicts that approve again, when the original verdict approved a wrong answer; and the approval rate over all three draws.

- qwen3.5-4b | own belief 0/7: approvals 170, repeated 66.8%; wrong 752, approved over 3 draws 22.0%
- qwen3.5-4b | own belief 1-3: approvals 45, repeated 66.7%; wrong 138, approved over 3 draws 35.5%
- qwen3.5-4b | own belief 4-7: approvals 22, repeated 88.6%; wrong 45, approved over 3 draws 54.1%
- qwen3.5-9b | own belief 0/7: approvals 122, repeated 57.0%; wrong 802, approved over 3 draws 15.3%
- qwen3.5-9b | own belief 1-3: approvals 25, repeated 50.0%; wrong 80, approved over 3 draws 26.7%
- qwen3.5-9b | own belief 4-7: approvals 25, repeated 80.0%; wrong 53, approved over 3 draws 49.7%
- qwen3.6-35b-a3b | own belief 0/7: approvals 42, repeated 48.8%; wrong 847, approved over 3 draws 4.8%
- qwen3.6-35b-a3b | own belief 1-3: approvals 7, repeated 57.1%; wrong 58, approved over 3 draws 13.2%
- qwen3.6-35b-a3b | own belief 4-7: approvals 15, repeated 80.0%; wrong 30, approved over 3 draws 52.2%
- nemotron3-super-120b | own belief 0/7: approvals 189, repeated 69.6%; wrong 776, approved over 3 draws 25.8%
- nemotron3-super-120b | own belief 1-3: approvals 40, repeated 62.5%; wrong 106, approved over 3 draws 35.8%
- nemotron3-super-120b | own belief 4-7: approvals 34, repeated 89.7%; wrong 53, approved over 3 draws 66.0%
- deepseek-v4.1-flash | own belief 0/7: approvals 108, repeated 54.6%; wrong 830, approved over 3 draws 11.9%
- deepseek-v4.1-flash | own belief 1-3: approvals 27, repeated 63.0%; wrong 65, approved over 3 draws 41.0%
- deepseek-v4.1-flash | own belief 4-7: approvals 15, repeated 60.0%; wrong 40, approved over 3 draws 37.5%
- kimi-k2.6 | own belief 0/7: approvals 22, repeated 40.9%; wrong 854, approved over 3 draws 2.3%
- kimi-k2.6 | own belief 1-3: approvals 5, repeated 40.0%; wrong 40, approved over 3 draws 14.2%
- kimi-k2.6 | own belief 4-7: approvals 17, repeated 76.5%; wrong 41, approved over 3 draws 39.8%
- pooled (approval-weighted): 0/7: 653 approvals, repeated 61.7%; 1-3: 149 approvals, repeated 60.7%; 4-7: 128 approvals, repeated 81.2%
- pooled repeat-approval with 95% intervals (questions resampled): 0/7 61.7 [57.7, 65.7]; 1-3 60.7 [54.2, 67.0]; 4-7 81.2 [73.7, 87.3]; 4-7 minus 0/7 19.5 [11.5, 26.6]
