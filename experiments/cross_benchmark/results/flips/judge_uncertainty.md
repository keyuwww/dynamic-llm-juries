# Each judge's accuracy vs its ability to flag the best judge's confident errors

AUROC 0.5 = chance. flag_* = for the best judge's confident errors; self_conf = for the judge's own errors.

| bench      | short     | is_best   |   acc |   flag_conf |   flag_flip |   self_conf |   self_error_rate |
|:-----------|:----------|:----------|------:|------------:|------------:|------------:|------------------:|
| bffpair    | oss-120b  | True      | 0.857 |       0.739 |     nan     |       0.791 |             0.156 |
| bffpair    | oss-20b   | False     | 0.827 |       0.75  |       0.536 |       0.747 |             0.214 |
| bffpair    | deepseek  | False     | 0.787 |       0.737 |       0.609 |       0.786 |             0.294 |
| bffpair    | qwen-35b  | False     | 0.843 |       0.685 |       0.557 |       0.743 |             0.204 |
| bffpair    | qwen-9b   | False     | 0.785 |       0.685 |       0.546 |       0.737 |             0.318 |
| bffpair    | qwen-4b   | False     | 0.752 |       0.638 |       0.48  |       0.716 |             0.336 |
| bffpair    | nem-super | False     | 0.767 |       0.684 |       0.592 |       0.697 |             0.329 |
| bffpair    | nem-nano  | False     | 0.593 |       0.535 |       0.513 |       0.586 |             0.62  |
| judgebench | oss-120b  | False     | 0.851 |       0.836 |       0.581 |       0.869 |             0.187 |
| judgebench | oss-20b   | False     | 0.812 |       0.749 |       0.563 |       0.787 |             0.243 |
| judgebench | deepseek  | False     | 0.793 |       0.77  |       0.532 |       0.713 |             0.34  |
| judgebench | qwen-35b  | True      | 0.906 |       0.841 |     nan     |       0.853 |             0.128 |
| judgebench | qwen-9b   | False     | 0.851 |       0.807 |       0.563 |       0.802 |             0.165 |
| judgebench | qwen-4b   | False     | 0.839 |       0.843 |       0.559 |       0.841 |             0.203 |
| judgebench | nem-super | False     | 0.791 |       0.753 |       0.728 |       0.77  |             0.352 |
| judgebench | nem-nano  | False     | 0.563 |       0.566 |       0.523 |       0.653 |             0.671 |
| alpacafarm | oss-120b  | False     | 0.715 |       0.654 |       0.561 |       0.737 |             0.356 |
| alpacafarm | oss-20b   | False     | 0.693 |       0.617 |       0.563 |       0.692 |             0.385 |
| alpacafarm | deepseek  | True      | 0.73  |       0.648 |     nan     |       0.723 |             0.362 |
| alpacafarm | qwen-35b  | False     | 0.714 |       0.601 |       0.582 |       0.658 |             0.405 |
| alpacafarm | qwen-9b   | False     | 0.724 |       0.592 |       0.546 |       0.674 |             0.435 |
| alpacafarm | qwen-4b   | False     | 0.659 |       0.606 |       0.526 |       0.652 |             0.467 |
| alpacafarm | nem-super | False     | 0.724 |       0.638 |       0.585 |       0.694 |             0.425 |
| alpacafarm | nem-nano  | False     | 0.644 |       0.616 |       0.549 |       0.62  |             0.515 |
| mtbhuman   | oss-120b  | True      | 0.838 |       0.761 |     nan     |       0.783 |             0.187 |
| mtbhuman   | oss-20b   | False     | 0.82  |       0.723 |       0.585 |       0.773 |             0.243 |
| mtbhuman   | deepseek  | False     | 0.835 |       0.776 |       0.53  |       0.783 |             0.224 |
| mtbhuman   | qwen-35b  | False     | 0.831 |       0.732 |       0.561 |       0.726 |             0.231 |
| mtbhuman   | qwen-9b   | False     | 0.816 |       0.752 |       0.645 |       0.771 |             0.287 |
| mtbhuman   | qwen-4b   | False     | 0.765 |       0.747 |       0.572 |       0.712 |             0.296 |
| mtbhuman   | nem-super | False     | 0.831 |       0.71  |       0.582 |       0.77  |             0.252 |
| mtbhuman   | nem-nano  | False     | 0.734 |       0.58  |       0.572 |       0.593 |             0.489 |

Spearman across non-best judges (32 - 4 = 28 judge-benchmark points): rho_acc_flag_conf +0.85, rho_acc_flag_flip +0.24, rho_acc_self_conf +0.88, share_flag_conf_above_0_6 +0.86, mean_flag_conf_weak +0.66, mean_flag_conf_strong +0.72
