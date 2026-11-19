# Fresh-question replication (MMLU-Pro, questions 80..6079) -- POST-HOC LENIENT LETTER PARSING (sensitivity only)

Excluded judgments: {'< 5 own answers with a letter': 20, 'verdict unparsed': 18}. Audit verdicts on wrong responses believed >= 4/7: {'LABEL_OK': 207, 'CONTESTED': 71, 'LABEL_WRONG': 81, None: 2}

## All pairs (MMLU-Pro key): 5306 judgments, 1336 questions

| judge | n | 0/7 | 1-3 | 4-6 | 7/7 | linear slope (judge FE) |
|---|---|---|---|---|---|---|
| qwen3.6-35b-a3b | 1318 | 13 (848) | 35 (242) | 52 (149) | 72 (79) | +58.9 [+51.1, +66.9] |
| qwen3.5-9b | 1327 | 22 (773) | 42 (322) | 48 (164) | 54 (68) | +35.6 [+27.8, +44.3] |
| deepseek-v4.1-flash | 1334 | 20 (888) | 40 (252) | 54 (127) | 70 (67) | +50.0 [+41.1, +58.4] |
| kimi-k2.6 | 1327 | 16 (949) | 39 (214) | 52 (98) | 58 (66) | +47.3 [+38.4, +56.6] |
| pooled | 5306 | 18 (3458) | 39 (1030) | 51 (538) | 64 (280) | +47.9 [+42.8, +53.1] |

- 7/7 minus 0/7 (pooled): +46.4 [+39.9, +52.8]
- same candidate across judges (candidate + judge FE): +20.6 [+14.2, +26.9]
- target belief +23.4 [+15.1, +31.2], competitor belief -27.1 [-33.8, -20.9] (judge FE)
- one-sample label +7.5 [+2.5, +12.7], belief +41.4 [+34.8, +47.7] (judge FE)

## Audit-filtered: 4702 judgments, 1184 questions

| judge | n | 0/7 | 1-3 | 4-6 | 7/7 | linear slope (judge FE) |
|---|---|---|---|---|---|---|
| qwen3.6-35b-a3b | 1167 | 12 (828) | 31 (204) | 47 (97) | 71 (38) | +55.3 [+45.7, +65.4] |
| qwen3.5-9b | 1177 | 21 (752) | 39 (276) | 49 (106) | 56 (43) | +38.5 [+28.3, +48.9] |
| deepseek-v4.1-flash | 1182 | 20 (862) | 38 (224) | 47 (70) | 65 (26) | +46.8 [+34.8, +58.2] |
| kimi-k2.6 | 1176 | 16 (923) | 36 (177) | 39 (51) | 40 (25) | +35.4 [+23.3, +48.5] |
| pooled | 4702 | 17 (3365) | 36 (881) | 47 (324) | 59 (132) | +44.5 [+38.0, +51.0] |

- 7/7 minus 0/7 (pooled): +42.0 [+32.5, +51.2]
- same candidate across judges (candidate + judge FE): +21.2 [+14.1, +28.4]
- target belief +20.7 [+11.9, +29.9], competitor belief -25.7 [-32.8, -19.0] (judge FE)
- one-sample label +5.7 [+0.4, +11.3], belief +39.7 [+31.8, +47.5] (judge FE)

