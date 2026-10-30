# Selective judging: hold back doubted items for human review

Expert accuracy on kept items, and share of the expert's errors caught in the held-back set. Random hold-back keeps accuracy flat and catches errors in proportion to the share held back.

## bffpair (expert oss-120b, n=378, base accuracy 0.856)

| signal     |   acc_hold10 |   acc_hold20 |   caught_hold10 |   caught_hold20 |
|:-----------|-------------:|-------------:|----------------:|----------------:|
| deepseek   |        0.879 |        0.904 |           0.246 |           0.469 |
| expert_own |        0.886 |        0.901 |           0.288 |           0.452 |
| qwen-35b   |        0.877 |        0.901 |           0.234 |           0.452 |
| oss-20b    |        0.87  |        0.898 |           0.189 |           0.437 |
| weak_pool  |        0.879 |        0.897 |           0.248 |           0.431 |
| qwen-9b    |        0.877 |        0.897 |           0.235 |           0.427 |
| qwen-4b    |        0.868 |        0.889 |           0.178 |           0.382 |
| nem-super  |        0.865 |        0.881 |           0.157 |           0.339 |
| nem-nano   |        0.853 |        0.851 |           0.085 |           0.177 |

Top-20% flagged by weak pool (n=76): accuracy flagged vs rest

|           |   flagged |   rest |
|:----------|----------:|-------:|
| deepseek  |     0.625 |  0.833 |
| oss-120b  |     0.691 |  0.897 |
| oss-20b   |     0.658 |  0.866 |
| nem-nano  |     0.421 |  0.652 |
| nem-super |     0.625 |  0.806 |
| qwen-4b   |     0.487 |  0.818 |
| qwen-9b   |     0.546 |  0.861 |
| qwen-35b  |     0.592 |  0.902 |

Best possible pick: flagged 0.908, rest 0.959

## judgebench (expert qwen-35b, n=262, base accuracy 0.899)

| signal     |   acc_hold10 |   acc_hold20 |   caught_hold10 |   caught_hold20 |
|:-----------|-------------:|-------------:|----------------:|----------------:|
| expert_own |        0.929 |        0.95  |           0.369 |           0.606 |
| oss-120b   |        0.924 |        0.95  |           0.322 |           0.6   |
| weak_pool  |        0.926 |        0.945 |           0.34  |           0.566 |
| qwen-4b    |        0.923 |        0.941 |           0.31  |           0.531 |
| qwen-9b    |        0.92  |        0.936 |           0.289 |           0.49  |
| oss-20b    |        0.919 |        0.931 |           0.282 |           0.453 |
| deepseek   |        0.902 |        0.928 |           0.129 |           0.426 |
| nem-super  |        0.922 |        0.926 |           0.305 |           0.412 |
| nem-nano   |        0.906 |        0.912 |           0.166 |           0.302 |

Top-20% flagged by weak pool (n=53): accuracy flagged vs rest

|           |   flagged |   rest |
|:----------|----------:|-------:|
| deepseek  |     0.623 |  0.835 |
| oss-120b  |     0.557 |  0.9   |
| oss-20b   |     0.604 |  0.868 |
| nem-nano  |     0.462 |  0.598 |
| nem-super |     0.613 |  0.83  |
| qwen-4b   |     0.566 |  0.883 |
| qwen-9b   |     0.585 |  0.885 |
| qwen-35b  |     0.717 |  0.945 |

Best possible pick: flagged 0.943, rest 0.988

## alpacafarm (expert deepseek, n=488, base accuracy 0.730)

| signal     |   acc_hold10 |   acc_hold20 |   caught_hold10 |   caught_hold20 |
|:-----------|-------------:|-------------:|----------------:|----------------:|
| expert_own |        0.751 |        0.772 |           0.173 |           0.326 |
| nem-super  |        0.743 |        0.768 |           0.144 |           0.315 |
| weak_pool  |        0.745 |        0.76  |           0.152 |           0.292 |
| qwen-35b   |        0.737 |        0.758 |           0.125 |           0.284 |
| oss-120b   |        0.742 |        0.756 |           0.141 |           0.28  |
| nem-nano   |        0.735 |        0.75  |           0.119 |           0.261 |
| oss-20b    |        0.74  |        0.748 |           0.137 |           0.256 |
| qwen-9b    |        0.737 |        0.748 |           0.125 |           0.255 |
| qwen-4b    |        0.736 |        0.745 |           0.121 |           0.245 |

Top-20% flagged by weak pool (n=98): accuracy flagged vs rest

|           |   flagged |   rest |
|:----------|----------:|-------:|
| deepseek  |     0.607 |  0.76  |
| oss-120b  |     0.571 |  0.753 |
| oss-20b   |     0.49  |  0.745 |
| nem-nano  |     0.52  |  0.676 |
| nem-super |     0.617 |  0.75  |
| qwen-4b   |     0.49  |  0.706 |
| qwen-9b   |     0.628 |  0.746 |
| qwen-35b  |     0.582 |  0.745 |

Best possible pick: flagged 0.913, rest 0.931

## mtbhuman (expert oss-120b, n=300, base accuracy 0.840)

| signal     |   acc_hold10 |   acc_hold20 |   caught_hold10 |   caught_hold20 |
|:-----------|-------------:|-------------:|----------------:|----------------:|
| qwen-9b    |        0.863 |        0.892 |           0.229 |           0.458 |
| weak_pool  |        0.867 |        0.89  |           0.25  |           0.448 |
| qwen-4b    |        0.859 |        0.888 |           0.209 |           0.439 |
| expert_own |        0.863 |        0.888 |           0.229 |           0.438 |
| deepseek   |        0.864 |        0.882 |           0.237 |           0.411 |
| qwen-35b   |        0.855 |        0.879 |           0.187 |           0.392 |
| oss-20b    |        0.853 |        0.869 |           0.171 |           0.344 |
| nem-super  |        0.86  |        0.865 |           0.211 |           0.323 |
| nem-nano   |        0.841 |        0.845 |           0.104 |           0.227 |

Top-20% flagged by weak pool (n=61): accuracy flagged vs rest

|           |   flagged |   rest |
|:----------|----------:|-------:|
| deepseek  |     0.623 |  0.885 |
| oss-120b  |     0.639 |  0.891 |
| oss-20b   |     0.631 |  0.87  |
| nem-nano  |     0.566 |  0.78  |
| nem-super |     0.623 |  0.889 |
| qwen-4b   |     0.541 |  0.82  |
| qwen-9b   |     0.639 |  0.862 |
| qwen-35b  |     0.631 |  0.881 |

Best possible pick: flagged 0.885, rest 0.960
