# Math replication (DAPO-Math, questions 80..1879)

Excluded judgments: {'verdict unparsed': 29, '< 5 own answers parsed': 19}. Audit verdicts: {'LABEL_OK': 782, 'LABEL_WRONG': 21, 'CONTESTED': 9, None: 7}

## Answer key: 3228 judgments, 819 questions

| judge | n | 0/7 | 1-3 | 4-6 | 7/7 | slope (judge FE) |
|---|---|---|---|---|---|---|
| qwen3.6-35b-a3b | 812 | 2 (771) | 23 (26) | 42 (12) | 100 (3) | +77.8 [+52.8, +100.0] |
| qwen3.5-9b | 803 | 3 (750) | 15 (41) | 44 (9) | 67 (3) | +57.7 [+26.0, +92.9] |
| deepseek-v4.1-flash | 817 | 6 (768) | 20 (35) | 42 (12) | 100 (2) | +65.1 [+33.1, +95.3] |
| kimi-k2.6 | 796 | 3 (773) | 20 (15) | 33 (3) | 100 (5) | +85.5 [+55.8, +105.3] |
| pooled | 3228 | 4 (3062) | 19 (117) | 42 (36) | 92 (13) | +71.0 [+53.7, +85.3] |

- 7/7 minus 0/7: +88.6 [+73.6, +97.0]
- same candidate: -2.5 [-20.1, +17.3]
- target +52.8 [+29.5, +71.5], competitor -17.0 [-28.9, -5.9]
- one-sample label +10.0 [-7.4, +28.1], belief +62.2 [+39.5, +82.9]

## Audit-filtered (all responses audited): 3087 judgments, 782 questions

| judge | n | 0/7 | 1-3 | 4-6 | 7/7 | slope (judge FE) |
|---|---|---|---|---|---|---|
| qwen3.6-35b-a3b | 775 | 1 (743) | 24 (25) | 14 (7) | - (0) | +49.9 [+12.6, +99.3] |
| qwen3.5-9b | 768 | 2 (728) | 9 (34) | 33 (6) | - (0) | +39.6 [+2.6, +87.1] |
| deepseek-v4.1-flash | 780 | 6 (745) | 16 (31) | 25 (4) | - (0) | +44.7 [-1.6, +103.7] |
| kimi-k2.6 | 764 | 2 (751) | 0 (12) | 0 (1) | - (0) | -7.2 [-13.7, -3.9] |
| pooled | 3087 | 3 (2967) | 14 (102) | 22 (18) | - | +40.5 [+16.3, +69.9] |

- 7/7 minus 0/7: +nan [+nan, +nan]
- same candidate: -3.6 [-20.3, +15.1]
- target +21.7 [-6.4, +53.7], competitor -15.4 [-28.0, -3.8]
- one-sample label +2.9 [-12.6, +20.8], belief +38.6 [+12.3, +68.1]

Auditor verdicts by highest belief:
- 0/7: {'LABEL_OK': 704, 'CONTESTED': 5, 'LABEL_WRONG': 12, None: 3}
- 1-3: {'LABEL_OK': 62, 'CONTESTED': 2, None: 3, 'LABEL_WRONG': 2}
- 4-6: {'LABEL_OK': 16, 'LABEL_WRONG': 2, None: 1}
- 7/7: {'LABEL_WRONG': 5, 'CONTESTED': 2}
