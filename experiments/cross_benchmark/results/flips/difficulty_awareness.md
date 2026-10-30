# Do weaker judges sense how hard an item is for the expert? (no new calls)

Outcome: the best judge is wrong in at least one order (all pairs). Doubt = a weaker judge's low stated confidence. AUROC 0.5 = chance. 28 judge-benchmark points (7 weaker judges x 4 benchmarks).

## Summary

- T1_mean_auc_all: 0.704
- T1_mean_auc_when_right: 0.717
- T1_mean_auc_when_wrong: 0.550
- T1_points_right_above_0_6: 26
- T1_points_right_p05: 26
- T1_n_points: 28
- T1_sign_test_right_gt_0_5_p: 0.000
- LOG_doubt_positive_p05: 19
- LOG_median_coef_doubt: 0.361
- T2_mean_best_minus_peers: 0.022
- T2_wilcoxon_p: 0.000
- T2_share_best_higher: 0.786
- T5_mean_rho_leave2out: 0.418
- T5_mean_auc_human_split: 0.624
- T5_mean_auc_best_unsolved: 0.535
- T5_mean_auc_own_unsolved: 0.501
- T4_increasing_share: 0.700

## T1. Hard for me vs hard for the expert

| bench      | short     |   acc |   auc_all |   auc_when_right |   auc_when_wrong |   n_right |   best_err_when_right |   n_wrong |   best_err_when_wrong |   p_when_right |
|:-----------|:----------|------:|----------:|-----------------:|-----------------:|----------:|----------------------:|----------:|----------------------:|---------------:|
| bffpair    | oss-20b   | 0.827 |     0.788 |            0.796 |            0.618 |       342 |                 0.053 |        97 |                 0.639 |          0     |
| bffpair    | deepseek  | 0.787 |     0.762 |            0.767 |            0.612 |       312 |                 0.058 |       130 |                 0.477 |          0     |
| bffpair    | qwen-35b  | 0.843 |     0.756 |            0.76  |            0.471 |       358 |                 0.059 |        83 |                 0.711 |          0     |
| bffpair    | qwen-9b   | 0.785 |     0.722 |            0.843 |            0.533 |       309 |                 0.055 |       131 |                 0.481 |          0     |
| bffpair    | qwen-4b   | 0.752 |     0.677 |            0.654 |            0.548 |       293 |                 0.068 |       148 |                 0.405 |          0.003 |
| bffpair    | nem-super | 0.767 |     0.719 |            0.771 |            0.597 |       291 |                 0.086 |       150 |                 0.367 |          0     |
| bffpair    | nem-nano  | 0.593 |     0.57  |            0.627 |            0.534 |       164 |                 0.104 |       278 |                 0.227 |          0.043 |
| judgebench | oss-120b  | 0.851 |     0.803 |            0.749 |            0.595 |       273 |                 0.037 |        69 |                 0.493 |          0.003 |
| judgebench | oss-20b   | 0.812 |     0.751 |            0.738 |            0.619 |       234 |                 0.068 |        71 |                 0.366 |          0.001 |
| judgebench | deepseek  | 0.793 |     0.737 |            0.778 |            0.595 |       245 |                 0.073 |       105 |                 0.257 |          0     |
| judgebench | qwen-9b   | 0.851 |     0.767 |            0.741 |            0.543 |       263 |                 0.038 |        70 |                 0.471 |          0.002 |
| judgebench | qwen-4b   | 0.839 |     0.796 |            0.679 |            0.622 |       258 |                 0.043 |        72 |                 0.458 |          0.014 |
| judgebench | nem-super | 0.791 |     0.761 |            0.777 |            0.65  |       236 |                 0.042 |       105 |                 0.314 |          0.001 |
| judgebench | nem-nano  | 0.563 |     0.581 |            0.569 |            0.573 |       112 |                 0.08  |       238 |                 0.151 |          0.248 |
| alpacafarm | oss-120b  | 0.715 |     0.7   |            0.723 |            0.464 |       317 |                 0.192 |       183 |                 0.705 |          0     |
| alpacafarm | oss-20b   | 0.693 |     0.646 |            0.706 |            0.451 |       295 |                 0.183 |       206 |                 0.66  |          0     |
| alpacafarm | qwen-35b  | 0.714 |     0.659 |            0.697 |            0.535 |       302 |                 0.192 |       199 |                 0.663 |          0     |
| alpacafarm | qwen-9b   | 0.724 |     0.631 |            0.686 |            0.44  |       306 |                 0.196 |       195 |                 0.667 |          0     |
| alpacafarm | qwen-4b   | 0.659 |     0.634 |            0.686 |            0.453 |       263 |                 0.163 |       238 |                 0.618 |          0     |
| alpacafarm | nem-super | 0.724 |     0.664 |            0.678 |            0.533 |       301 |                 0.189 |       200 |                 0.665 |          0     |
| alpacafarm | nem-nano  | 0.644 |     0.59  |            0.646 |            0.507 |       236 |                 0.186 |       265 |                 0.551 |          0.001 |
| mtbhuman   | oss-20b   | 0.82  |     0.73  |            0.757 |            0.526 |       249 |                 0.044 |        72 |                 0.708 |          0.002 |
| mtbhuman   | deepseek  | 0.835 |     0.773 |            0.736 |            0.546 |       248 |                 0.069 |        73 |                 0.616 |          0     |
| mtbhuman   | qwen-35b  | 0.831 |     0.725 |            0.756 |            0.548 |       246 |                 0.061 |        74 |                 0.622 |          0     |
| mtbhuman   | qwen-9b   | 0.816 |     0.741 |            0.742 |            0.599 |       243 |                 0.049 |        78 |                 0.641 |          0.002 |
| mtbhuman   | qwen-4b   | 0.765 |     0.749 |            0.773 |            0.648 |       215 |                 0.047 |       106 |                 0.491 |          0.001 |
| mtbhuman   | nem-super | 0.831 |     0.724 |            0.734 |            0.501 |       249 |                 0.064 |        72 |                 0.639 |          0.001 |
| mtbhuman   | nem-nano  | 0.734 |     0.55  |            0.509 |            0.538 |       184 |                 0.071 |       137 |                 0.358 |          0.46  |

Logistic, within benchmark: best wrong ~ weak judge wrong + weak judge doubt (z-scored)

| bench      | short     |   coef_own_wrong |   p_own_wrong |   coef_doubt |   p_doubt |
|:-----------|:----------|-----------------:|--------------:|-------------:|----------:|
| bffpair    | oss-20b   |            3.185 |         0     |        0.49  |     0.001 |
| bffpair    | deepseek  |            2.349 |         0     |        0.48  |     0     |
| bffpair    | qwen-35b  |            3.353 |         0     |        0.483 |     0.001 |
| bffpair    | qwen-9b   |            2.603 |         0     |        0.359 |     0.005 |
| bffpair    | qwen-4b   |            2.026 |         0     |        0.356 |     0.005 |
| bffpair    | nem-super |            1.624 |         0     |        0.452 |     0     |
| bffpair    | nem-nano  |            0.93  |         0.002 |        0.001 |     0.992 |
| judgebench | oss-120b  |            2.628 |         0     |        0.598 |     0.005 |
| judgebench | oss-20b   |            1.751 |         0     |        0.623 |     0     |
| judgebench | deepseek  |            1.228 |         0     |        0.428 |     0.004 |
| judgebench | qwen-9b   |            2.825 |         0     |        0.351 |     0.048 |
| judgebench | qwen-4b   |            2.533 |         0     |        0.402 |     0.021 |
| judgebench | nem-super |            2.118 |         0     |        0.723 |     0     |
| judgebench | nem-nano  |            0.681 |         0.084 |        0.192 |     0.173 |
| alpacafarm | oss-120b  |            2.025 |         0     |        0.413 |     0.001 |
| alpacafarm | oss-20b   |            2.043 |         0     |        0.252 |     0.021 |
| alpacafarm | qwen-35b  |            2.04  |         0     |        0.342 |     0.001 |
| alpacafarm | qwen-9b   |            2.016 |         0     |        0.195 |     0.067 |
| alpacafarm | qwen-4b   |            2.139 |         0     |       -0.046 |     0.657 |
| alpacafarm | nem-super |            1.992 |         0     |        0.409 |     0     |
| alpacafarm | nem-nano  |            1.637 |         0     |        0.136 |     0.171 |
| mtbhuman   | oss-20b   |            3.816 |         0     |        0.32  |     0.104 |
| mtbhuman   | deepseek  |            2.776 |         0     |        0.317 |     0.066 |
| mtbhuman   | qwen-35b  |            3.093 |         0     |        0.276 |     0.099 |
| mtbhuman   | qwen-9b   |            3.389 |         0     |        0.398 |     0.021 |
| mtbhuman   | qwen-4b   |            2.874 |         0     |        0.421 |     0.007 |
| mtbhuman   | nem-super |            3.012 |         0     |        0.363 |     0.044 |
| mtbhuman   | nem-nano  |            1.983 |         0     |        0.049 |     0.731 |

## T2. Expert vs peers

| bench      | short     |   acc |   auc_best |   auc_peers |   auc_peers_min |   auc_peers_max |   auc_stronger_peers |   auc_weaker_peers |
|:-----------|:----------|------:|-----------:|------------:|----------------:|----------------:|---------------------:|-------------------:|
| bffpair    | oss-20b   | 0.827 |      0.788 |       0.701 |           0.641 |           0.768 |                0.768 |              0.688 |
| bffpair    | deepseek  | 0.787 |      0.762 |       0.74  |           0.686 |           0.791 |                0.768 |              0.727 |
| bffpair    | qwen-35b  | 0.843 |      0.756 |       0.671 |           0.605 |           0.722 |              nan     |              0.671 |
| bffpair    | qwen-9b   | 0.785 |      0.722 |       0.693 |           0.666 |           0.751 |                0.711 |              0.676 |
| bffpair    | qwen-4b   | 0.752 |      0.677 |       0.668 |           0.62  |           0.729 |                0.677 |              0.62  |
| bffpair    | nem-super | 0.767 |      0.719 |       0.671 |           0.606 |           0.728 |                0.684 |              0.644 |
| bffpair    | nem-nano  | 0.593 |      0.57  |       0.566 |           0.527 |           0.598 |                0.566 |            nan     |
| judgebench | oss-120b  | 0.851 |      0.803 |       0.744 |           0.633 |           0.807 |                0.807 |              0.731 |
| judgebench | oss-20b   | 0.812 |      0.751 |       0.714 |           0.673 |           0.764 |                0.748 |              0.681 |
| judgebench | deepseek  | 0.793 |      0.737 |       0.716 |           0.678 |           0.749 |                0.733 |              0.683 |
| judgebench | qwen-9b   | 0.851 |      0.767 |       0.739 |           0.646 |           0.82  |              nan     |              0.739 |
| judgebench | qwen-4b   | 0.839 |      0.796 |       0.76  |           0.676 |           0.826 |                0.817 |              0.731 |
| judgebench | nem-super | 0.791 |      0.761 |       0.707 |           0.64  |           0.758 |                0.721 |              0.64  |
| judgebench | nem-nano  | 0.563 |      0.581 |       0.519 |           0.492 |           0.546 |                0.519 |            nan     |
| alpacafarm | oss-120b  | 0.715 |      0.7   |       0.695 |           0.674 |           0.735 |                0.687 |              0.7   |
| alpacafarm | oss-20b   | 0.693 |      0.646 |       0.651 |           0.614 |           0.697 |                0.641 |              0.673 |
| alpacafarm | qwen-35b  | 0.714 |      0.659 |       0.645 |           0.604 |           0.671 |                0.643 |              0.646 |
| alpacafarm | qwen-9b   | 0.724 |      0.631 |       0.656 |           0.625 |           0.689 |                0.625 |              0.662 |
| alpacafarm | qwen-4b   | 0.659 |      0.634 |       0.625 |           0.607 |           0.657 |                0.628 |              0.608 |
| alpacafarm | nem-super | 0.724 |      0.664 |       0.666 |           0.638 |           0.68  |              nan     |              0.666 |
| alpacafarm | nem-nano  | 0.644 |      0.59  |       0.599 |           0.565 |           0.629 |                0.599 |            nan     |
| mtbhuman   | oss-20b   | 0.82  |      0.73  |       0.723 |           0.673 |           0.746 |                0.733 |              0.713 |
| mtbhuman   | deepseek  | 0.835 |      0.773 |       0.765 |           0.701 |           0.798 |              nan     |              0.765 |
| mtbhuman   | qwen-35b  | 0.831 |      0.725 |       0.693 |           0.658 |           0.72  |                0.711 |              0.69  |
| mtbhuman   | qwen-9b   | 0.816 |      0.741 |       0.734 |           0.665 |           0.789 |                0.749 |              0.702 |
| mtbhuman   | qwen-4b   | 0.765 |      0.749 |       0.716 |           0.632 |           0.746 |                0.733 |              0.632 |
| mtbhuman   | nem-super | 0.831 |      0.724 |       0.724 |           0.71  |           0.74  |                0.71  |              0.727 |
| mtbhuman   | nem-nano  | 0.734 |      0.55  |       0.585 |           0.549 |           0.63  |                0.585 |            nan     |

## T4. Within model families (sorted by accuracy)

| bench      | family   | judges                       | acc          | auc_all            | auc_when_right     | increasing   |
|:-----------|:---------|:-----------------------------|:-------------|:-------------------|:-------------------|:-------------|
| alpacafarm | Nemotron | nem-nano < nem-super         | 64 < 72      | 0.59 → 0.66        | 0.65 → 0.68        | True         |
| alpacafarm | Qwen     | qwen-4b < qwen-35b < qwen-9b | 66 < 71 < 72 | 0.63 → 0.66 → 0.63 | 0.69 → 0.70 → 0.69 | False        |
| alpacafarm | gpt-oss  | oss-20b < oss-120b           | 69 < 71      | 0.65 → 0.70        | 0.71 → 0.72        | True         |
| bffpair    | Nemotron | nem-nano < nem-super         | 59 < 77      | 0.57 → 0.72        | 0.63 → 0.77        | True         |
| bffpair    | Qwen     | qwen-4b < qwen-9b < qwen-35b | 75 < 79 < 84 | 0.68 → 0.72 → 0.76 | 0.65 → 0.84 → 0.76 | True         |
| judgebench | Nemotron | nem-nano < nem-super         | 56 < 79      | 0.58 → 0.76        | 0.57 → 0.78        | True         |
| judgebench | Qwen     | qwen-4b < qwen-9b            | 84 < 85      | 0.80 → 0.77        | 0.68 → 0.74        | False        |
| judgebench | gpt-oss  | oss-20b < oss-120b           | 81 < 85      | 0.75 → 0.80        | 0.74 → 0.75        | True         |
| mtbhuman   | Nemotron | nem-nano < nem-super         | 73 < 83      | 0.55 → 0.72        | 0.51 → 0.73        | True         |
| mtbhuman   | Qwen     | qwen-4b < qwen-9b < qwen-35b | 76 < 82 < 83 | 0.75 → 0.74 → 0.72 | 0.77 → 0.74 → 0.76 | False        |

## T5. Independent difficulty measures

| bench      | short     |   rho_leave2out |   auc_best_unsolved |   auc_own_unsolved |   auc_human_split |   n_human_votes |
|:-----------|:----------|----------------:|--------------------:|-------------------:|------------------:|----------------:|
| bffpair    | oss-20b   |           0.439 |               0.542 |              0.504 |           nan     |             nan |
| bffpair    | deepseek  |           0.575 |               0.546 |              0.484 |           nan     |             nan |
| bffpair    | qwen-35b  |           0.431 |               0.556 |              0.534 |           nan     |             nan |
| bffpair    | qwen-9b   |           0.482 |               0.548 |              0.573 |           nan     |             nan |
| bffpair    | qwen-4b   |           0.416 |               0.486 |              0.501 |           nan     |             nan |
| bffpair    | nem-super |           0.366 |               0.562 |              0.453 |           nan     |             nan |
| bffpair    | nem-nano  |           0.156 |               0.505 |              0.459 |           nan     |             nan |
| judgebench | oss-120b  |           0.542 |             nan     |            nan     |           nan     |             nan |
| judgebench | oss-20b   |           0.494 |             nan     |            nan     |           nan     |             nan |
| judgebench | deepseek  |           0.509 |             nan     |            nan     |           nan     |             nan |
| judgebench | qwen-9b   |           0.54  |             nan     |            nan     |           nan     |             nan |
| judgebench | qwen-4b   |           0.613 |             nan     |            nan     |           nan     |             nan |
| judgebench | nem-super |           0.468 |             nan     |            nan     |           nan     |             nan |
| judgebench | nem-nano  |           0.066 |             nan     |            nan     |           nan     |             nan |
| alpacafarm | oss-120b  |           0.474 |             nan     |            nan     |             0.603 |             500 |
| alpacafarm | oss-20b   |           0.372 |             nan     |            nan     |             0.584 |             501 |
| alpacafarm | qwen-35b  |           0.346 |             nan     |            nan     |             0.576 |             501 |
| alpacafarm | qwen-9b   |           0.377 |             nan     |            nan     |             0.617 |             501 |
| alpacafarm | qwen-4b   |           0.297 |             nan     |            nan     |             0.587 |             501 |
| alpacafarm | nem-super |           0.404 |             nan     |            nan     |             0.575 |             501 |
| alpacafarm | nem-nano  |           0.24  |             nan     |            nan     |             0.568 |             501 |
| mtbhuman   | oss-20b   |           0.496 |             nan     |            nan     |             0.659 |             182 |
| mtbhuman   | deepseek  |           0.57  |             nan     |            nan     |             0.695 |             182 |
| mtbhuman   | qwen-35b  |           0.401 |             nan     |            nan     |             0.701 |             182 |
| mtbhuman   | qwen-9b   |           0.505 |             nan     |            nan     |             0.697 |             182 |
| mtbhuman   | qwen-4b   |           0.44  |             nan     |            nan     |             0.668 |             182 |
| mtbhuman   | nem-super |           0.5   |             nan     |            nan     |             0.71  |             182 |
| mtbhuman   | nem-nano  |           0.194 |             nan     |            nan     |             0.495 |             182 |

Controlled BFF pairs: mean stated confidence by condition (real = real BFF pairs)

| judge     |   corrupt |   identical |   pad |   real |
|:----------|----------:|------------:|------:|-------:|
| deepseek  |      87.6 |        50   |  52.8 |   93.4 |
| oss-120b  |      87.3 |        76.6 |  72.2 |   88.9 |
| oss-20b   |      89.5 |        89.3 |  82.9 |   92   |
| nem-nano  |      94.9 |        95.7 |  95.7 |   94.6 |
| nem-super |      89.3 |        60.5 |  64.5 |   91.9 |
| qwen-4b   |      95.3 |        85.9 |  85.5 |   97.6 |
| qwen-9b   |      96.4 |        92.2 |  87.1 |   96.1 |
| qwen-35b  |      98   |        91.3 |  88.9 |   97.4 |
