# Judge pairs: who catches whose confident errors (stored verdicts, no new calls)

Target judge j = column, checker i = row. Confident error = j wrong in both orders, counted on pairs where j is consistent. In-sample, no CIs.

## bffpair

Accuracy (both orders): oss-120b 85.7, qwen-35b 84.3, oss-20b 82.7, deepseek 78.7, qwen-9b 78.5, nem-super 76.7, qwen-4b 75.2, nem-nano 59.3

### AUROC of checker i's flips for target j's confident errors (0.5 = chance)

|           |   oss-120b |   oss-20b |   deepseek |   qwen-35b |   qwen-9b |   qwen-4b |   nem-super |   nem-nano |
|:----------|-----------:|----------:|-----------:|-----------:|----------:|----------:|------------:|-----------:|
| oss-120b  |     nan    |      0.55 |       0.56 |       0.6  |      0.55 |      0.57 |        0.54 |       0.54 |
| oss-20b   |       0.55 |    nan    |       0.59 |       0.6  |      0.62 |      0.57 |        0.58 |       0.52 |
| deepseek  |       0.59 |      0.56 |     nan    |       0.59 |      0.58 |      0.58 |        0.53 |       0.55 |
| qwen-35b  |       0.56 |      0.54 |       0.53 |     nan    |      0.52 |      0.56 |        0.53 |       0.53 |
| qwen-9b   |       0.55 |      0.57 |       0.59 |       0.54 |    nan    |      0.57 |        0.58 |       0.56 |
| qwen-4b   |       0.48 |      0.5  |       0.52 |       0.51 |      0.5  |    nan    |        0.48 |       0.57 |
| nem-super |       0.57 |      0.57 |       0.57 |       0.58 |      0.56 |      0.61 |      nan    |       0.6  |
| nem-nano  |       0.51 |      0.5  |       0.55 |       0.53 |      0.57 |      0.58 |        0.55 |     nan    |

### Share of j's confident errors flagged by i (flip or consistent disagreement), %

|           |   oss-120b |   oss-20b |   deepseek |   qwen-35b |   qwen-9b |   qwen-4b |   nem-super |   nem-nano |
|:----------|-----------:|----------:|-----------:|-----------:|----------:|----------:|------------:|-----------:|
| oss-120b  |      nan   |      32.6 |       51.7 |       39.6 |      37.7 |      49.2 |        52.9 |       82.9 |
| oss-20b   |       29.5 |     nan   |       45.5 |       43.1 |      43.1 |      46.6 |        48   |       71.6 |
| deepseek  |       37.8 |      34.8 |      nan   |       35.8 |      37.7 |      37.1 |        36   |       72   |
| qwen-35b  |       28.9 |      35.6 |       40.4 |      nan   |      28.8 |      38.7 |        44   |       72.5 |
| qwen-9b   |       25   |      35.6 |       41.1 |       30.2 |     nan   |      32.8 |        41.2 |       78.8 |
| qwen-4b   |       29.5 |      29.5 |       31.6 |       26.9 |      21.2 |     nan   |        30.6 |       71.4 |
| nem-super |       44.2 |      43.5 |       44.8 |       46.2 |      41.2 |      44.3 |       nan   |       77.5 |
| nem-nano  |       68.9 |      54.3 |       60.3 |       58.5 |      67.9 |      64.5 |        64.7 |      nan   |

### False-alarm rate: share of j's correct pairs flagged by i, %

|           |   oss-120b |   oss-20b |   deepseek |   qwen-35b |   qwen-9b |   qwen-4b |   nem-super |   nem-nano |
|:----------|-----------:|----------:|-----------:|-----------:|----------:|----------:|------------:|-----------:|
| oss-120b  |      nan   |       4.4 |        5.5 |        5.7 |       5.1 |       6.6 |         7.8 |       10.4 |
| oss-20b   |       10.4 |     nan   |        8.8 |       10.9 |       7.4 |      10.3 |        10.9 |       11.5 |
| deepseek  |       18.5 |      14.8 |      nan   |       16.8 |      11.4 |      10.2 |        12.4 |       14.6 |
| qwen-35b  |        6.6 |       6.1 |        4.6 |      nan   |       4.4 |       4.1 |         6.5 |        7.4 |
| qwen-9b   |       18.8 |      14.8 |       12.6 |       17.4 |     nan   |       9.7 |        13.5 |       16.5 |
| qwen-4b   |       25.1 |      23   |       17.1 |       22.7 |      16   |     nan   |        18.3 |       15.7 |
| nem-super |       26.2 |      23   |       18.8 |       24.7 |      19.4 |      17.7 |       nan   |       18.5 |
| nem-nano  |       59.1 |      56.5 |       55   |       57.3 |      55.6 |      51.3 |        53.2 |      nan   |

### Error correlation (phi) between judges

|           |   oss-120b |   oss-20b |   deepseek |   qwen-35b |   qwen-9b |   qwen-4b |   nem-super |   nem-nano |
|:----------|-----------:|----------:|-----------:|-----------:|----------:|----------:|------------:|-----------:|
| oss-120b  |     nan    |      0.57 |       0.46 |       0.61 |      0.53 |      0.42 |        0.37 |       0.12 |
| oss-20b   |       0.57 |    nan    |       0.49 |       0.54 |      0.51 |      0.43 |        0.41 |       0.19 |
| deepseek  |       0.46 |      0.49 |     nan    |       0.53 |      0.52 |      0.54 |        0.49 |       0.21 |
| qwen-35b  |       0.61 |      0.54 |       0.53 |     nan    |      0.56 |      0.54 |        0.42 |       0.18 |
| qwen-9b   |       0.53 |      0.51 |       0.52 |       0.56 |    nan    |      0.6  |        0.47 |       0.17 |
| qwen-4b   |       0.42 |      0.43 |       0.54 |       0.54 |      0.6  |    nan    |        0.5  |       0.21 |
| nem-super |       0.37 |      0.41 |       0.49 |       0.42 |      0.47 |      0.5  |      nan    |       0.19 |
| nem-nano  |       0.12 |      0.19 |       0.21 |       0.18 |      0.17 |      0.21 |        0.19 |     nan    |

### Reciprocity and what catching follows

- Correlation of the flip-AUROC matrix with its transpose: **-0.19** (mean |i→j − j→i| = 0.038).
- Same for catch-any: **0.76** (mean |i→j − j→i| = 9.5 pts).
- Spearman, flip-AUROC vs error phi: +0.11; vs checker accuracy: +0.15; vs target accuracy: -0.08.
- Spearman, catch-any vs phi: -0.84; false alarms vs checker accuracy: -0.92.

### Best mutual pairs (mean of catch-any both ways minus mean false alarms)

| pair                 |   i_catches_j |   j_catches_i |   mean_catch |   mean_false |   net |   phi |   acc_gap |
|:---------------------|--------------:|--------------:|-------------:|-------------:|------:|------:|----------:|
| oss-120b + nem-nano  |          82.9 |          68.9 |         75.9 |         34.8 |  41.1 |  0.12 |      26.4 |
| qwen-9b + nem-nano   |          78.8 |          67.9 |         73.3 |         36   |  37.3 |  0.17 |      19.2 |
| nem-super + nem-nano |          77.5 |          64.7 |         71.1 |         35.9 |  35.2 |  0.19 |      17.5 |
| qwen-4b + nem-nano   |          71.4 |          64.5 |         68   |         33.5 |  34.5 |  0.21 |      15.9 |
| qwen-35b + nem-nano  |          72.5 |          58.5 |         65.5 |         32.3 |  33.2 |  0.18 |      25.1 |
| oss-120b + deepseek  |          51.7 |          37.8 |         44.8 |         12   |  32.7 |  0.46 |       7   |
| oss-120b + nem-super |          52.9 |          44.2 |         48.6 |         17   |  31.5 |  0.37 |       9   |
| deepseek + nem-nano  |          72   |          60.3 |         66.1 |         34.8 |  31.3 |  0.21 |      19.4 |

## judgebench

Accuracy (both orders): qwen-35b 90.6, qwen-9b 85.1, oss-120b 85.1, qwen-4b 83.9, oss-20b 81.2, deepseek 79.3, nem-super 79.1, nem-nano 56.3

### AUROC of checker i's flips for target j's confident errors (0.5 = chance)

|           |   oss-120b |   oss-20b |   deepseek |   qwen-35b |   qwen-9b |   qwen-4b |   nem-super |   nem-nano |
|:----------|-----------:|----------:|-----------:|-----------:|----------:|----------:|------------:|-----------:|
| oss-120b  |     nan    |      0.53 |       0.59 |       0.59 |      0.63 |      0.66 |        0.58 |       0.55 |
| oss-20b   |       0.51 |    nan    |       0.59 |       0.59 |      0.62 |      0.56 |        0.62 |       0.53 |
| deepseek  |       0.54 |      0.57 |     nan    |       0.51 |      0.62 |      0.63 |        0.69 |       0.52 |
| qwen-35b  |       0.61 |      0.57 |       0.57 |     nan    |      0.55 |      0.62 |        0.61 |       0.54 |
| qwen-9b   |       0.56 |      0.57 |       0.57 |       0.55 |    nan    |      0.65 |        0.58 |       0.55 |
| qwen-4b   |       0.6  |      0.6  |       0.64 |       0.55 |      0.67 |    nan    |        0.67 |       0.57 |
| nem-super |       0.63 |      0.61 |       0.64 |       0.69 |      0.63 |      0.66 |      nan    |       0.68 |
| nem-nano  |       0.51 |      0.56 |       0.46 |       0.51 |      0.55 |      0.48 |        0.55 |     nan    |

### Share of j's confident errors flagged by i (flip or consistent disagreement), %

|           |   oss-120b |   oss-20b |   deepseek |   qwen-35b |   qwen-9b |   qwen-4b |   nem-super |   nem-nano |
|:----------|-----------:|----------:|-----------:|-----------:|----------:|----------:|------------:|-----------:|
| oss-120b  |      nan   |      39.5 |       60   |       45   |      57.1 |      56.2 |        67.9 |       80.3 |
| oss-20b   |       30.3 |     nan   |       58.8 |       50   |      60.7 |      54.8 |        60.7 |       77.6 |
| deepseek  |       52.9 |      63.2 |      nan   |       60   |      57.1 |      59.4 |        67.9 |       69.7 |
| qwen-35b  |       67.6 |      73.7 |       78.9 |      nan   |      46.4 |      56.2 |        82.1 |       92.4 |
| qwen-9b   |       63.6 |      70.3 |       67.6 |       25   |     nan   |      48.4 |        67.9 |       89.1 |
| qwen-4b   |       58.8 |      62.2 |       66.7 |       22.2 |      40.7 |     nan   |        69.2 |       82.3 |
| nem-super |       71   |      67.6 |       75.7 |       73.7 |      66.7 |      74.2 |       nan   |       84.7 |
| nem-nano  |       61.8 |      65.8 |       50   |       75   |      75   |      65.6 |        67.9 |      nan   |

### False-alarm rate: share of j's correct pairs flagged by i, %

|           |   oss-120b |   oss-20b |   deepseek |   qwen-35b |   qwen-9b |   qwen-4b |   nem-super |   nem-nano |
|:----------|-----------:|----------:|-----------:|-----------:|----------:|----------:|------------:|-----------:|
| oss-120b  |      nan   |       9.5 |        9.4 |       11.7 |      11   |       9.3 |         9.8 |       11   |
| oss-20b   |       14   |     nan   |       14.6 |       19.2 |      16.3 |      13.5 |        13.1 |       11.5 |
| deepseek  |       20.5 |      19   |      nan   |       25.3 |      18.6 |      17.4 |        16.7 |       15.5 |
| qwen-35b  |        3.6 |       6.1 |        7.4 |      nan   |       3.8 |       3.5 |         3.7 |        8.3 |
| qwen-9b   |       12.7 |      14.1 |        9.7 |       13.4 |     nan   |       6.4 |        11.3 |       14   |
| qwen-4b   |       12   |      12.8 |        8.5 |       14.6 |       7.5 |     nan   |        11.8 |       14.6 |
| nem-super |       23.9 |      22.5 |       20.1 |       25.6 |      23.8 |      22.4 |       nan   |       12   |
| nem-nano  |       64.9 |      62.9 |       61.7 |       66.8 |      64.8 |      65.8 |        58.7 |      nan   |

### Error correlation (phi) between judges

|           |   oss-120b |   oss-20b |   deepseek |   qwen-35b |   qwen-9b |   qwen-4b |   nem-super |   nem-nano |
|:----------|-----------:|----------:|-----------:|-----------:|----------:|----------:|------------:|-----------:|
| oss-120b  |     nan    |      0.51 |       0.33 |       0.49 |      0.35 |      0.45 |        0.29 |       0.17 |
| oss-20b   |       0.51 |    nan    |       0.31 |       0.34 |      0.32 |      0.36 |        0.33 |       0.15 |
| deepseek  |       0.33 |      0.31 |     nan    |       0.22 |      0.34 |      0.39 |        0.34 |       0.2  |
| qwen-35b  |       0.49 |      0.34 |       0.22 |     nan    |      0.5  |      0.48 |        0.27 |       0.05 |
| qwen-9b   |       0.35 |      0.32 |       0.34 |       0.5  |    nan    |      0.55 |        0.24 |       0.07 |
| qwen-4b   |       0.45 |      0.36 |       0.39 |       0.48 |      0.55 |    nan    |        0.29 |       0.16 |
| nem-super |       0.29 |      0.33 |       0.34 |       0.27 |      0.24 |      0.29 |      nan    |       0.19 |
| nem-nano  |       0.17 |      0.15 |       0.2  |       0.05 |      0.07 |      0.16 |        0.19 |     nan    |

### Reciprocity and what catching follows

- Correlation of the flip-AUROC matrix with its transpose: **0.51** (mean |i→j − j→i| = 0.043).
- Same for catch-any: **0.50** (mean |i→j − j→i| = 12.1 pts).
- Spearman, flip-AUROC vs error phi: +0.34; vs checker accuracy: +0.07; vs target accuracy: +0.01.
- Spearman, catch-any vs phi: -0.73; false alarms vs checker accuracy: -0.89.

### Best mutual pairs (mean of catch-any both ways minus mean false alarms)

| pair                 |   i_catches_j |   j_catches_i |   mean_catch |   mean_false |   net |   phi |   acc_gap |
|:---------------------|--------------:|--------------:|-------------:|-------------:|------:|------:|----------:|
| qwen-35b + nem-super |          82.1 |          73.7 |         77.9 |         14.7 |  63.2 |  0.27 |      11.5 |
| qwen-4b + nem-super  |          69.2 |          74.2 |         71.7 |         17.1 |  54.6 |  0.29 |       4.8 |
| deepseek + nem-super |          67.9 |          75.7 |         71.8 |         18.4 |  53.3 |  0.34 |       0.2 |
| deepseek + qwen-35b  |          60   |          78.9 |         69.5 |         16.4 |  53.1 |  0.22 |      11.3 |
| oss-120b + nem-super |          67.9 |          71   |         69.4 |         16.8 |  52.6 |  0.29 |       5.9 |
| oss-20b + qwen-9b    |          60.7 |          70.3 |         65.5 |         15.2 |  50.3 |  0.32 |       3.8 |
| deepseek + qwen-4b   |          59.4 |          66.7 |         63   |         13   |  50.1 |  0.39 |       4.6 |
| qwen-9b + nem-super  |          67.9 |          66.7 |         67.3 |         17.5 |  49.7 |  0.24 |       5.9 |

## alpacafarm

Accuracy (both orders): deepseek 73.0, nem-super 72.4, qwen-9b 72.4, oss-120b 71.5, qwen-35b 71.4, oss-20b 69.3, qwen-4b 65.9, nem-nano 64.4

### AUROC of checker i's flips for target j's confident errors (0.5 = chance)

|           |   oss-120b |   oss-20b |   deepseek |   qwen-35b |   qwen-9b |   qwen-4b |   nem-super |   nem-nano |
|:----------|-----------:|----------:|-----------:|-----------:|----------:|----------:|------------:|-----------:|
| oss-120b  |     nan    |      0.57 |       0.56 |       0.54 |      0.54 |      0.52 |        0.56 |       0.6  |
| oss-20b   |       0.59 |    nan    |       0.56 |       0.57 |      0.56 |      0.59 |        0.59 |       0.58 |
| deepseek  |       0.56 |      0.6  |     nan    |       0.59 |      0.54 |      0.59 |        0.57 |       0.6  |
| qwen-35b  |       0.58 |      0.56 |       0.58 |     nan    |      0.57 |      0.58 |        0.56 |       0.58 |
| qwen-9b   |       0.56 |      0.57 |       0.54 |       0.58 |    nan    |      0.58 |        0.56 |       0.57 |
| qwen-4b   |       0.55 |      0.59 |       0.53 |       0.49 |      0.48 |    nan    |        0.49 |       0.58 |
| nem-super |       0.6  |      0.6  |       0.59 |       0.57 |      0.55 |      0.58 |      nan    |       0.58 |
| nem-nano  |       0.54 |      0.57 |       0.55 |       0.56 |      0.55 |      0.55 |        0.54 |     nan    |

### Share of j's confident errors flagged by i (flip or consistent disagreement), %

|           |   oss-120b |   oss-20b |   deepseek |   qwen-35b |   qwen-9b |   qwen-4b |   nem-super |   nem-nano |
|:----------|-----------:|----------:|-----------:|-----------:|----------:|----------:|------------:|-----------:|
| oss-120b  |      nan   |      37.5 |       38.3 |       33.3 |      32.5 |      45.1 |        36.8 |       50.5 |
| oss-20b   |       40.6 |     nan   |       46.2 |       43.7 |      40.5 |      54.5 |        42.1 |       56.2 |
| deepseek  |       51   |      55.2 |      nan   |       50.6 |      41.2 |      52.9 |        46.1 |       58.2 |
| qwen-35b  |       43.1 |      49   |       46.9 |      nan   |      37.5 |      45.1 |        38.2 |       54.9 |
| qwen-9b   |       46.5 |      51   |       41.2 |       42.5 |     nan   |      43.1 |        42.1 |       56.2 |
| qwen-4b   |       44.6 |      53.1 |       40.7 |       34.9 |      27.5 |     nan   |        32.9 |       52.7 |
| nem-super |       52.9 |      54.2 |       49.4 |       46   |      45   |      50   |       nan   |       55.6 |
| nem-nano  |       55.9 |      59.4 |       53.1 |       52.9 |      51.2 |      57.8 |        47.4 |      nan   |

### False-alarm rate: share of j's correct pairs flagged by i, %

|           |   oss-120b |   oss-20b |   deepseek |   qwen-35b |   qwen-9b |   qwen-4b |   nem-super |   nem-nano |
|:----------|-----------:|----------:|-----------:|-----------:|----------:|----------:|------------:|-----------:|
| oss-120b  |      nan   |      11.5 |       17.7 |       15   |      17.2 |      16.1 |        15.3 |       14.9 |
| oss-20b   |       18.4 |     nan   |       23   |       22.9 |      22.3 |      19.8 |        20.4 |       21.2 |
| deepseek  |       19.2 |      17.8 |      nan   |       19.3 |      19.5 |      16.1 |        19   |       18.7 |
| qwen-35b  |       19.2 |      21   |       21.6 |      nan   |      18.5 |      18.4 |        17.7 |       17.9 |
| qwen-9b   |       20.8 |      19.3 |       21   |       17.7 |     nan   |      15.7 |        20.3 |       17.9 |
| qwen-4b   |       30.9 |      27.6 |       29.4 |       29.2 |      27.4 |     nan   |        29.3 |       27.5 |
| nem-super |       19.9 |      18.2 |       21.6 |       17.7 |      21.1 |      18.8 |       nan   |       20.4 |
| nem-nano  |       36.9 |      36.4 |       38.4 |       36.2 |      36.6 |      35.2 |        37.7 |      nan   |

### Error correlation (phi) between judges

|           |   oss-120b |   oss-20b |   deepseek |   qwen-35b |   qwen-9b |   qwen-4b |   nem-super |   nem-nano |
|:----------|-----------:|----------:|-----------:|-----------:|----------:|----------:|------------:|-----------:|
| oss-120b  |     nan    |      0.53 |       0.45 |       0.52 |      0.48 |      0.44 |        0.49 |       0.34 |
| oss-20b   |       0.53 |    nan    |       0.39 |       0.42 |      0.42 |      0.37 |        0.41 |       0.3  |
| deepseek  |       0.45 |      0.39 |     nan    |       0.42 |      0.44 |      0.41 |        0.43 |       0.35 |
| qwen-35b  |       0.52 |      0.42 |       0.42 |     nan    |      0.51 |      0.46 |        0.48 |       0.34 |
| qwen-9b   |       0.48 |      0.42 |       0.44 |       0.51 |    nan    |      0.48 |        0.42 |       0.32 |
| qwen-4b   |       0.44 |      0.37 |       0.41 |       0.46 |      0.48 |    nan    |        0.47 |       0.29 |
| nem-super |       0.49 |      0.41 |       0.43 |       0.48 |      0.42 |      0.47 |      nan    |       0.33 |
| nem-nano  |       0.34 |      0.3  |       0.35 |       0.34 |      0.32 |      0.29 |        0.33 |     nan    |

### Reciprocity and what catching follows

- Correlation of the flip-AUROC matrix with its transpose: **-0.18** (mean |i→j − j→i| = 0.031).
- Same for catch-any: **0.30** (mean |i→j − j→i| = 7.4 pts).
- Spearman, flip-AUROC vs error phi: -0.14; vs checker accuracy: +0.40; vs target accuracy: -0.46.
- Spearman, catch-any vs phi: -0.76; false alarms vs checker accuracy: -0.65.

### Best mutual pairs (mean of catch-any both ways minus mean false alarms)

| pair                 |   i_catches_j |   j_catches_i |   mean_catch |   mean_false |   net |   phi |   acc_gap |
|:---------------------|--------------:|--------------:|-------------:|-------------:|------:|------:|----------:|
| oss-20b + deepseek   |          46.2 |          55.2 |         50.7 |         20.4 |  30.3 |  0.39 |       3.6 |
| oss-20b + qwen-4b    |          54.5 |          53.1 |         53.8 |         23.7 |  30.1 |  0.37 |       3.4 |
| oss-20b + nem-nano   |          56.2 |          59.4 |         57.8 |         28.8 |  29   |  0.3  |       4.9 |
| oss-20b + nem-super  |          42.1 |          54.2 |         48.1 |         19.3 |  28.8 |  0.41 |       3.1 |
| deepseek + qwen-35b  |          50.6 |          46.9 |         48.7 |         20.4 |  28.3 |  0.42 |       1.6 |
| deepseek + nem-super |          46.1 |          49.4 |         47.7 |         20.3 |  27.4 |  0.43 |       0.6 |
| oss-120b + nem-nano  |          50.5 |          55.9 |         53.2 |         25.9 |  27.3 |  0.34 |       7.1 |
| oss-120b + nem-super |          36.8 |          52.9 |         44.9 |         17.6 |  27.3 |  0.49 |       0.9 |

## mtbhuman

Accuracy (both orders): oss-120b 83.8, deepseek 83.5, qwen-35b 83.1, nem-super 83.1, oss-20b 82.0, qwen-9b 81.6, qwen-4b 76.5, nem-nano 73.4

### AUROC of checker i's flips for target j's confident errors (0.5 = chance)

|           |   oss-120b |   oss-20b |   deepseek |   qwen-35b |   qwen-9b |   qwen-4b |   nem-super |   nem-nano |
|:----------|-----------:|----------:|-----------:|-----------:|----------:|----------:|------------:|-----------:|
| oss-120b  |     nan    |      0.55 |       0.51 |       0.53 |      0.55 |      0.6  |        0.54 |       0.55 |
| oss-20b   |       0.58 |    nan    |       0.56 |       0.6  |      0.62 |      0.57 |        0.54 |       0.61 |
| deepseek  |       0.54 |      0.52 |     nan    |       0.6  |      0.57 |      0.59 |        0.59 |       0.54 |
| qwen-35b  |       0.56 |      0.58 |       0.55 |     nan    |      0.59 |      0.66 |        0.55 |       0.57 |
| qwen-9b   |       0.65 |      0.63 |       0.58 |       0.59 |    nan    |      0.58 |        0.6  |       0.6  |
| qwen-4b   |       0.6  |      0.55 |       0.53 |       0.57 |      0.53 |    nan    |        0.55 |       0.52 |
| nem-super |       0.58 |      0.58 |       0.58 |       0.62 |      0.6  |      0.6  |      nan    |       0.55 |
| nem-nano  |       0.56 |      0.57 |       0.54 |       0.59 |      0.58 |      0.62 |        0.6  |     nan    |

### Share of j's confident errors flagged by i (flip or consistent disagreement), %

|           |   oss-120b |   oss-20b |   deepseek |   qwen-35b |   qwen-9b |   qwen-4b |   nem-super |   nem-nano |
|:----------|-----------:|----------:|-----------:|-----------:|----------:|----------:|------------:|-----------:|
| oss-120b  |      nan   |      23.1 |       18.2 |       26.5 |      39.5 |      50   |        27.8 |       46.9 |
| oss-20b   |       25   |     nan   |       27.3 |       35.3 |      45.9 |      43.2 |        25.7 |       58.1 |
| deepseek  |       35.7 |      38.5 |      nan   |       38.2 |      42.1 |      47.7 |        38.9 |       53.1 |
| qwen-35b  |       37.5 |      42.1 |       36.4 |      nan   |      36.8 |      47.7 |        38.9 |       61.3 |
| qwen-9b   |       42.5 |      47.4 |       33.3 |       27.3 |     nan   |      38.6 |        38.9 |       61.3 |
| qwen-4b   |       47.6 |      35.9 |       30.3 |       32.4 |      28.9 |     nan   |        33.3 |       59.4 |
| nem-super |       38.1 |      33.3 |       33.3 |       35.3 |      42.1 |      45.5 |       nan   |       65.6 |
| nem-nano  |       59.5 |      66.7 |       53.1 |       64.7 |      67.6 |      69.8 |        68.6 |      nan   |

### False-alarm rate: share of j's correct pairs flagged by i, %

|           |   oss-120b |   oss-20b |   deepseek |   qwen-35b |   qwen-9b |   qwen-4b |   nem-super |   nem-nano |
|:----------|-----------:|----------:|-----------:|-----------:|----------:|----------:|------------:|-----------:|
| oss-120b  |      nan   |       3   |        6.9 |        5.7 |       4.2 |       4.7 |         6.5 |        7.2 |
| oss-20b   |        8.4 |     nan   |       10.5 |        9.3 |       7.4 |       8.7 |         8.8 |       11.3 |
| deepseek  |       10.8 |       9.7 |      nan   |        9.4 |       8.8 |       7.5 |         8.5 |       11   |
| qwen-35b  |       10.8 |       9.7 |       10.1 |      nan   |       8.8 |       5.6 |         9.8 |       11.1 |
| qwen-9b   |       10.9 |       8.9 |       11.1 |       10.7 |     nan   |       7.6 |        10.6 |       10.1 |
| qwen-4b   |       21   |      20   |       19.9 |       17.6 |      17.4 |     nan   |        19.5 |       20   |
| nem-super |       10.1 |       6.8 |        8.1 |        8.6 |       7.2 |       6.6 |       nan   |       11.7 |
| nem-nano  |       34.4 |      33.5 |       34.6 |       34.2 |      31.8 |      31.8 |        35.5 |      nan   |

### Error correlation (phi) between judges

|           |   oss-120b |   oss-20b |   deepseek |   qwen-35b |   qwen-9b |   qwen-4b |   nem-super |   nem-nano |
|:----------|-----------:|----------:|-----------:|-----------:|----------:|----------:|------------:|-----------:|
| oss-120b  |     nan    |      0.73 |       0.59 |       0.58 |      0.58 |      0.48 |        0.6  |       0.3  |
| oss-20b   |       0.73 |    nan    |       0.57 |       0.53 |      0.52 |      0.5  |        0.6  |       0.28 |
| deepseek  |       0.59 |      0.57 |     nan    |       0.48 |      0.54 |      0.46 |        0.55 |       0.3  |
| qwen-35b  |       0.58 |      0.53 |       0.48 |     nan    |      0.57 |      0.55 |        0.57 |       0.27 |
| qwen-9b   |       0.58 |      0.52 |       0.54 |       0.57 |    nan    |      0.53 |        0.53 |       0.26 |
| qwen-4b   |       0.48 |      0.5  |       0.46 |       0.55 |      0.53 |    nan    |        0.5  |       0.23 |
| nem-super |       0.6  |      0.6  |       0.55 |       0.57 |      0.53 |      0.5  |      nan    |       0.23 |
| nem-nano  |       0.3  |      0.28 |       0.3  |       0.27 |      0.26 |      0.23 |        0.23 |     nan    |

### Reciprocity and what catching follows

- Correlation of the flip-AUROC matrix with its transpose: **0.02** (mean |i→j − j→i| = 0.036).
- Same for catch-any: **0.76** (mean |i→j − j→i| = 7.6 pts).
- Spearman, flip-AUROC vs error phi: -0.15; vs checker accuracy: -0.19; vs target accuracy: -0.15.
- Spearman, catch-any vs phi: -0.79; false alarms vs checker accuracy: -0.78.

### Best mutual pairs (mean of catch-any both ways minus mean false alarms)

| pair                 |   i_catches_j |   j_catches_i |   mean_catch |   mean_false |   net |   phi |   acc_gap |
|:---------------------|--------------:|--------------:|-------------:|-------------:|------:|------:|----------:|
| qwen-9b + nem-nano   |          61.3 |          67.6 |         64.4 |         20.9 |  43.5 |  0.26 |       8.2 |
| nem-super + nem-nano |          65.6 |          68.6 |         67.1 |         23.6 |  43.5 |  0.23 |       9.6 |
| qwen-35b + nem-nano  |          61.3 |          64.7 |         63   |         22.6 |  40.4 |  0.27 |       9.6 |
| oss-20b + nem-nano   |          58.1 |          66.7 |         62.4 |         22.4 |  40   |  0.28 |       8.6 |
| qwen-4b + nem-nano   |          59.4 |          69.8 |         64.6 |         25.9 |  38.7 |  0.23 |       3.1 |
| oss-20b + qwen-9b    |          45.9 |          47.4 |         46.7 |          8.1 |  38.5 |  0.52 |       0.4 |
| oss-120b + qwen-4b   |          50   |          47.6 |         48.8 |         12.9 |  36   |  0.48 |       7.3 |
| oss-120b + qwen-9b   |          39.5 |          42.5 |         41   |          7.6 |  33.4 |  0.58 |       2.2 |
