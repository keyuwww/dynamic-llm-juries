# Explicit predictions of expert difficulty vs implicit doubt

AUROC for the best judge's errors (wrong in either order, all pairs); 0.5 = chance. explicit_q = question only; explicit_qa = with both answers; implicit = the judge's low stated confidence on its own verdict.

## Summary (non-expert predictors)

- mean_explicit_q: 0.534
- mean_explicit_qa: 0.687
- mean_implicit: 0.721
- mean_explicit_qa_when_right: 0.700
- mean_rho_qa_vs_implicit: 0.566
- mean_rho_q_vs_qa: 0.093
- qa_minus_implicit_wilcoxon_p: 0.001
- q_above_0_5_sign_p: 0.332

## Per judge

| bench      | short     | is_best   |   explicit_q |   n_explicit_q |   explicit_qa |   n_explicit_qa |   implicit |   n_implicit |   explicit_qa_when_right |   rho_qa_vs_implicit |   rho_q_vs_qa |   mean_pred_qa |   share_pred_ge_90 |
|:-----------|:----------|:----------|-------------:|---------------:|--------------:|----------------:|-----------:|-------------:|-------------------------:|---------------------:|--------------:|---------------:|-------------------:|
| bffpair    | oss-120b  | True      |        0.429 |            442 |         0.79  |             442 |      0.814 |          441 |                  nan     |                0.717 |        -0.051 |         85.095 |              0.493 |
| bffpair    | oss-20b   | False     |        0.552 |            442 |         0.751 |             442 |      0.788 |          439 |                    0.749 |                0.621 |         0.144 |         89.192 |              0.742 |
| bffpair    | nem-super | False     |        0.549 |            442 |         0.609 |             442 |      0.719 |          441 |                    0.59  |                0.472 |         0.215 |         83.339 |              0.425 |
| bffpair    | qwen-4b   | False     |        0.625 |            442 |         0.619 |             442 |      0.677 |          441 |                    0.646 |                0.418 |         0.136 |         92.233 |              0.86  |
| bffpair    | qwen-9b   | False     |        0.519 |            442 |         0.657 |             442 |      0.722 |          440 |                    0.718 |                0.401 |         0.066 |         87.032 |              0.778 |
| bffpair    | qwen-35b  | False     |        0.632 |            438 |         0.736 |             442 |      0.756 |          441 |                    0.73  |                0.57  |         0.076 |         96.333 |              0.934 |
| judgebench | oss-120b  | False     |        0.493 |            350 |         0.751 |             350 |      0.803 |          342 |                    0.765 |                0.687 |         0.051 |         83.7   |              0.449 |
| judgebench | oss-20b   | False     |        0.5   |            334 |         0.778 |             336 |      0.751 |          300 |                    0.84  |                0.631 |         0.018 |         88.068 |              0.686 |
| judgebench | nem-super | False     |        0.698 |            325 |         0.708 |             349 |      0.761 |          340 |                    0.688 |                0.548 |         0.237 |         83.685 |              0.489 |
| judgebench | qwen-4b   | False     |        0.593 |            339 |         0.741 |             350 |      0.796 |          330 |                    0.693 |                0.529 |         0.11  |         90.589 |              0.806 |
| judgebench | qwen-9b   | False     |        0.519 |            345 |         0.711 |             350 |      0.767 |          333 |                    0.696 |                0.595 |         0.128 |         91.557 |              0.806 |
| judgebench | qwen-35b  | True      |        0.527 |            343 |         0.753 |             349 |      0.811 |          336 |                  nan     |                0.653 |         0.139 |         96.195 |              0.926 |
| alpacafarm | oss-120b  | False     |        0.481 |            501 |         0.69  |             501 |      0.7   |          500 |                    0.711 |                0.714 |        -0.002 |         74.475 |              0.124 |
| alpacafarm | oss-20b   | False     |        0.491 |            501 |         0.648 |             501 |      0.646 |          501 |                    0.645 |                0.593 |         0.046 |         78.509 |              0.367 |
| alpacafarm | nem-super | False     |        0.475 |            500 |         0.636 |             500 |      0.663 |          500 |                    0.675 |                0.53  |         0.114 |         78.926 |              0.251 |
| alpacafarm | qwen-4b   | False     |        0.486 |            500 |         0.627 |             501 |      0.634 |          501 |                    0.717 |                0.429 |         0.047 |         83.24  |              0.615 |
| alpacafarm | qwen-9b   | False     |        0.5   |            499 |         0.639 |             499 |      0.632 |          499 |                    0.682 |                0.519 |         0.022 |         77.848 |              0.465 |
| alpacafarm | qwen-35b  | False     |        0.515 |            498 |         0.644 |             500 |      0.658 |          500 |                    0.691 |                0.626 |         0.072 |         84.942 |              0.577 |
| mtbhuman   | oss-120b  | True      |        0.45  |            320 |         0.754 |             320 |      0.799 |          320 |                  nan     |                0.791 |         0.012 |         83.588 |              0.452 |
| mtbhuman   | oss-20b   | False     |        0.484 |            318 |         0.708 |             319 |      0.726 |          319 |                    0.683 |                0.681 |         0.071 |         86.73  |              0.623 |
| mtbhuman   | nem-super | False     |        0.552 |            311 |         0.734 |             319 |      0.726 |          319 |                    0.662 |                0.575 |         0.234 |         84.467 |              0.514 |
| mtbhuman   | qwen-4b   | False     |        0.489 |            316 |         0.635 |             321 |      0.749 |          321 |                    0.578 |                0.472 |         0.037 |         90.019 |              0.804 |
| mtbhuman   | qwen-9b   | False     |        0.531 |            313 |         0.659 |             319 |      0.741 |          319 |                    0.747 |                0.583 |         0.108 |         85.37  |              0.726 |
| mtbhuman   | qwen-35b  | False     |        0.519 |            313 |         0.74  |             321 |      0.725 |          320 |                    0.797 |                0.699 |         0.023 |         93.265 |              0.841 |

## Pooled over non-expert predictors (mean within-judge rank)

| bench      | expert          |   predictors |   explicit_q |   explicit_qa |   implicit |
|:-----------|:----------------|-------------:|-------------:|--------------:|-----------:|
| bffpair    | gpt-oss-120b    |            5 |        0.627 |         0.767 |      0.798 |
| judgebench | qwen3.6-35b-a3b |            5 |        0.608 |         0.825 |      0.82  |
| alpacafarm | deepseek-v3.1   |            6 |        0.488 |         0.711 |      0.695 |
| mtbhuman   | gpt-oss-120b    |            5 |        0.518 |         0.777 |      0.787 |
