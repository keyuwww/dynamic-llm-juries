# Replication: parser x label sensitivity (post hoc)

| parser | labels | n | 0/7 | 1-3 | 4-6 | 7/7 | gap 7-0 | slope | same candidate | competitor | 8th answer |
|---|---|---|---|---|---|---|---|---|---|---|---|
| strict | key | 4151 | 19 | 40 | 51 | 63 | +44.6 [+37.3, +51.8] | +46.8 [+41.0, +52.8] | +18.8 [+11.3, +26.1] | -28.9 [-36.2, -21.8] | +8.4 [+2.9, +14.2] |
| strict | high_audit | 3676 | 18 | 38 | 42 | 56 | +38.3 [+27.4, +49.3] | +41.4 [+34.1, +48.6] | +18.9 [+9.9, +27.9] | -27.8 [-35.4, -20.4] | +5.9 [-0.4, +12.2] |
| strict | full_audit | 3240 | 16 | 37 | 43 | 56 | +40.1 [+29.1, +50.8] | +42.5 [+34.9, +50.0] | +18.8 [+9.9, +28.0] | -30.5 [-38.7, -22.2] | +5.2 [-1.7, +12.4] |
| lenient | key | 5306 | 18 | 39 | 51 | 64 | +46.4 [+39.9, +52.8] | +47.9 [+42.8, +53.1] | +20.6 [+14.2, +26.9] | -27.1 [-33.8, -20.9] | +7.5 [+2.5, +12.7] |
| lenient | high_audit | 4702 | 17 | 36 | 47 | 59 | +42.0 [+32.5, +51.2] | +44.5 [+38.0, +51.0] | +21.2 [+14.1, +28.4] | -25.7 [-32.8, -19.0] | +5.7 [+0.4, +11.3] |
| lenient | full_audit | 4165 | 16 | 35 | 46 | 59 | +43.2 [+33.9, +52.6] | +44.8 [+37.7, +51.4] | +20.0 [+12.2, +28.1] | -27.1 [-34.8, -19.6] | +6.7 [+0.7, +12.7] |

Per-judge n and slope:

- strict|key: qwen3.6-35b-a3b n=742 +60.7 [+50.2, +70.6]; qwen3.5-9b n=960 +34.2 [+24.5, +44.3]; deepseek-v4.1-flash n=1302 +49.8 [+41.3, +58.7]; kimi-k2.6 n=1147 +44.7 [+35.0, +54.5]
- strict|high_audit: qwen3.6-35b-a3b n=656 +57.8 [+42.9, +70.3]; qwen3.5-9b n=856 +33.0 [+20.2, +45.6]; deepseek-v4.1-flash n=1152 +46.4 [+34.7, +57.6]; kimi-k2.6 n=1012 +29.9 [+16.0, +44.2]
- strict|full_audit: qwen3.6-35b-a3b n=573 +60.5 [+47.1, +74.3]; qwen3.5-9b n=754 +35.8 [+23.6, +48.2]; deepseek-v4.1-flash n=1021 +45.3 [+33.3, +56.8]; kimi-k2.6 n=892 +30.4 [+16.2, +45.5]
- lenient|key: qwen3.6-35b-a3b n=1318 +58.9 [+51.1, +66.9]; qwen3.5-9b n=1327 +35.6 [+27.8, +44.3]; deepseek-v4.1-flash n=1334 +50.0 [+41.1, +58.4]; kimi-k2.6 n=1327 +47.3 [+38.4, +56.6]
- lenient|high_audit: qwen3.6-35b-a3b n=1167 +55.3 [+45.7, +65.4]; qwen3.5-9b n=1177 +38.5 [+28.3, +48.9]; deepseek-v4.1-flash n=1182 +46.8 [+34.8, +58.2]; kimi-k2.6 n=1176 +35.4 [+23.3, +48.5]
- lenient|full_audit: qwen3.6-35b-a3b n=1032 +57.1 [+46.4, +67.4]; qwen3.5-9b n=1044 +38.8 [+28.5, +49.2]; deepseek-v4.1-flash n=1048 +45.6 [+33.3, +57.4]; kimi-k2.6 n=1041 +35.4 [+22.1, +49.2]

Audit coverage: {'responses': 1336, 'audited': 1336, 'no_verdict': 4, 'extra_strata': {'low': 903, 'lenient_high': 72}}

Auditor verdicts by highest belief of any judge (lenient):
- 4-6: {'LABEL_OK': 167, 'LABEL_WRONG': 33, 'CONTESTED': 45, None: 3}
- 0/7: {'LABEL_OK': 484, 'LABEL_WRONG': 16, 'CONTESTED': 29}
- 1-3: {'LABEL_OK': 311, 'LABEL_WRONG': 28, 'CONTESTED': 43, None: 1}
- 7/7: {'CONTESTED': 33, 'LABEL_OK': 87, 'LABEL_WRONG': 56}
