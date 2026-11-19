# Fresh-question replication (MMLU-Pro, questions 80..6079)

Excluded judgments: {'< 5 own answers with a letter': 1175, 'verdict unparsed': 18}. Audit verdicts on wrong responses believed >= 4/7: {'CONTESTED': 71, 'LABEL_OK': 207, 'LABEL_WRONG': 81, None: 2}

## All pairs (MMLU-Pro key): 4151 judgments, 1333 questions

| judge | n | 0/7 | 1-3 | 4-6 | 7/7 | linear slope (judge FE) |
|---|---|---|---|---|---|---|
| qwen3.6-35b-a3b | 742 | 15 (500) | 39 (120) | 56 (79) | 74 (43) | +60.7 [+50.2, +70.6] |
| qwen3.5-9b | 960 | 21 (577) | 42 (216) | 45 (110) | 53 (57) | +34.2 [+24.5, +44.3] |
| deepseek-v4.1-flash | 1302 | 20 (868) | 40 (241) | 55 (123) | 69 (70) | +49.8 [+41.3, +58.7] |
| kimi-k2.6 | 1147 | 17 (822) | 39 (179) | 48 (88) | 59 (58) | +44.7 [+35.0, +54.5] |
| pooled | 4151 | 19 (2767) | 40 (756) | 51 (400) | 63 (228) | +46.8 [+41.0, +52.8] |

- 7/7 minus 0/7 (pooled): +44.6 [+37.3, +51.8]
- same candidate across judges (candidate + judge FE): +18.8 [+11.3, +26.1]
- target belief +20.5 [+11.3, +29.3], competitor belief -28.9 [-36.2, -21.8] (judge FE)
- one-sample label +8.4 [+2.9, +14.2], belief +40.4 [+33.7, +47.6] (judge FE)

## Audit-filtered: 3676 judgments, 1181 questions

| judge | n | 0/7 | 1-3 | 4-6 | 7/7 | linear slope (judge FE) |
|---|---|---|---|---|---|---|
| qwen3.6-35b-a3b | 656 | 14 (487) | 39 (100) | 46 (48) | 76 (21) | +57.8 [+42.9, +70.3] |
| qwen3.5-9b | 856 | 20 (564) | 39 (191) | 43 (65) | 47 (36) | +33.0 [+20.2, +45.6] |
| deepseek-v4.1-flash | 1152 | 20 (842) | 38 (216) | 47 (66) | 64 (28) | +46.4 [+34.7, +57.6] |
| kimi-k2.6 | 1012 | 17 (798) | 36 (149) | 32 (47) | 39 (18) | +29.9 [+16.0, +44.2] |
| pooled | 3676 | 18 (2691) | 38 (656) | 42 (226) | 56 (103) | +41.4 [+34.1, +48.6] |

- 7/7 minus 0/7 (pooled): +38.3 [+27.4, +49.3]
- same candidate across judges (candidate + judge FE): +18.9 [+9.9, +27.9]
- target belief +15.4 [+5.3, +25.6], competitor belief -27.8 [-35.4, -20.4] (judge FE)
- one-sample label +5.9 [-0.4, +12.2], belief +37.3 [+28.8, +45.3] (judge FE)

