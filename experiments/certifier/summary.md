# Certifier: per-item judge router (11-judge mixed pool: Jev/Laya/jeff + 8 Tinker models)

Trained on already-collected judge verdicts only -- no new API calls. Out-of-fold (5-fold, grouped by item) logistic-regression reliability predictor over structural features (log input tokens, the judge's own confidence, judge identity); top-K most reliable judges per item vote, weighted by predicted reliability.

**Note:** this 11-judge mixed pool is a different, larger pool than the dashboard's oracle metric, which is restricted to the 8-model Tinker pool only per an earlier explicit decision. Do not compare these oracle numbers directly to the dashboard's.

## BFF noref (n=459)

| Strategy | Cohen's kappa | Accuracy |
|---|---|---|
| oracle (any of 11 judges correct) | 1.000 | 1.000 |
| certifier top-3 | 0.745 | 0.874 |
| certifier top-4 | 0.737 | 0.869 |
| certifier top-6 | 0.710 | 0.856 |
| certifier top-2 | 0.705 | 0.854 |
| single judge: gpt-oss-120b | 0.705 | 0.854 |
| certifier top-1 | 0.705 | 0.854 |
| certifier top-5 | 0.679 | 0.841 |
| certifier top-9 | 0.659 | 0.832 |
| single judge: gpt-oss-20b | 0.653 | 0.826 |
| certifier top-10 | 0.646 | 0.826 |
| certifier top-11 | 0.645 | 0.826 |
| certifier top-8 | 0.642 | 0.824 |
| unweighted majority (all) | 0.641 | 0.824 |
| certifier top-7 | 0.638 | 0.821 |
| single judge: deepseek-v3.1 | 0.603 | 0.806 |
| single judge: qwen3.6-35b-a3b | 0.537 | 0.765 |
| single judge: jev | 0.505 | 0.760 |
| single judge: qwen3.5-4b | 0.481 | 0.745 |
| single judge: qwen3.5-9b | 0.473 | 0.739 |
| single judge: nemotron3-super-120b | 0.459 | 0.741 |
| single judge: nemotron3-nano-30b | 0.325 | 0.667 |
| single judge: jeff | 0.314 | 0.641 |
| single judge: laya | 0.095 | 0.593 |

## BFF ref (n=456)

| Strategy | Cohen's kappa | Accuracy |
|---|---|---|
| oracle (any of 11 judges correct) | 1.000 | 1.000 |
| certifier top-3 | 0.881 | 0.941 |
| certifier top-5 | 0.877 | 0.939 |
| certifier top-4 | 0.876 | 0.939 |
| certifier top-11 | 0.873 | 0.936 |
| unweighted majority (all) | 0.873 | 0.936 |
| certifier top-10 | 0.873 | 0.936 |
| certifier top-7 | 0.872 | 0.936 |
| certifier top-8 | 0.872 | 0.936 |
| certifier top-9 | 0.868 | 0.934 |
| certifier top-1 | 0.868 | 0.934 |
| certifier top-6 | 0.863 | 0.932 |
| single judge: deepseek-v3.1 | 0.858 | 0.930 |
| single judge: jev | 0.856 | 0.928 |
| single judge: nemotron3-super-120b | 0.855 | 0.928 |
| certifier top-2 | 0.845 | 0.923 |
| single judge: gpt-oss-120b | 0.842 | 0.921 |
| single judge: qwen3.5-4b | 0.817 | 0.908 |
| single judge: qwen3.5-9b | 0.782 | 0.890 |
| single judge: gpt-oss-20b | 0.756 | 0.879 |
| single judge: qwen3.6-35b-a3b | 0.753 | 0.875 |
| single judge: nemotron3-nano-30b | 0.587 | 0.792 |
| single judge: jeff | 0.397 | 0.680 |
| single judge: laya | 0.115 | 0.601 |

## Safety (n=1800)

| Strategy | Cohen's kappa | Accuracy |
|---|---|---|
| oracle (any of 11 judges correct) | 0.958 | 0.984 |
| certifier top-4 | 0.640 | 0.841 |
| certifier top-3 | 0.639 | 0.838 |
| certifier top-2 | 0.637 | 0.847 |
| single judge: gpt-oss-20b | 0.637 | 0.847 |
| certifier top-1 | 0.637 | 0.846 |
| certifier top-5 | 0.625 | 0.828 |
| certifier top-6 | 0.609 | 0.820 |
| certifier top-7 | 0.594 | 0.810 |
| single judge: jev | 0.591 | 0.811 |
| certifier top-9 | 0.583 | 0.804 |
| certifier top-11 | 0.582 | 0.803 |
| certifier top-10 | 0.581 | 0.802 |
| certifier top-8 | 0.575 | 0.799 |
| unweighted majority (all) | 0.571 | 0.797 |
| single judge: qwen3.5-9b | 0.547 | 0.786 |
| single judge: gpt-oss-120b | 0.533 | 0.779 |
| single judge: nemotron3-nano-30b | 0.532 | 0.786 |
| single judge: nemotron3-super-120b | 0.480 | 0.741 |
| single judge: deepseek-v3.1 | 0.466 | 0.729 |
| single judge: qwen3.5-4b | 0.464 | 0.732 |
| single judge: qwen3.6-35b-a3b | 0.459 | 0.726 |
| single judge: jeff | 0.195 | 0.611 |
| single judge: laya | 0.053 | 0.482 |
