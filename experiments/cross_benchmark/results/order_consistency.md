# Order consistency vs errors (stored verdicts, no new calls)

Each pair is judged in both orders. *Flip* = the judge picked the same position both times, so exactly one of its two verdicts is wrong by construction. Percentages are of pairs unless noted.

## bffpair (378 pairs with all 8 judges; best judge gpt-oss-120b)

### Per judge

| judge                |   pairs |   acc_all |   flip_rate |   acc_consistent |   wrong_both |   share_errors_on_flips |
|:---------------------|--------:|----------:|------------:|-----------------:|-------------:|------------------------:|
| gpt-oss-120b         |     437 |      85.7 |         8   |             88.8 |         10.3 |                    28   |
| qwen3.6-35b-a3b      |     434 |      84.3 |         6.9 |             86.9 |         12.2 |                    22.1 |
| gpt-oss-20b          |     414 |      82.7 |        12.3 |             87.3 |         11.1 |                    35.7 |
| deepseek-v3.1        |     441 |      78.7 |        16.3 |             84.3 |         13.2 |                    38.3 |
| qwen3.5-9b           |     428 |      78.5 |        18.2 |             84.9 |         12.4 |                    42.4 |
| nemotron3-super-120b |     432 |      76.7 |        22.9 |             84.7 |         11.8 |                    49.3 |
| qwen3.5-4b           |     423 |      75.2 |        20.3 |             81.6 |         14.7 |                    41   |
| nemotron3-nano-30b   |     442 |      59.3 |        44.3 |             66.7 |         18.6 |                    54.4 |

- `acc_consistent`: accuracy on the pairs where the judge did not flip (abstain-on-flip). `wrong_both`: share of pairs where it picked the wrong answer in both orders (a confident error).
- `share_errors_on_flips`: share of the judge's verdict errors that sit on its flipped pairs.

### Do other judges' flips predict the best judge's errors? (best = gpt-oss-120b)

|   k |   pairs |   best_err_any |   best_wrong_both |   best_flip |
|----:|--------:|---------------:|------------------:|------------:|
|   0 |     131 |            9.2 |               6.1 |         3.1 |
|   1 |     110 |           18.2 |              12.7 |         5.5 |
|   2 |      61 |           16.4 |               8.2 |         8.2 |
|   3 |      46 |           23.9 |              10.9 |        13   |
|   4 |      19 |           52.6 |              31.6 |        21.1 |
|   5 |      11 |           54.5 |              18.2 |        36.4 |

- AUROC of 'number of other judges that flip' for the best judge's confident errors, among the 349 pairs where the best judge itself was consistent: **0.626**.
- Mean lift of P(judge B flips | judge A flips) over B's base flip rate, across judge pairs: **1.94x**.

### Flip rate without vs with the expert reference

| judge                |   flip_none |   flip_ref |
|:---------------------|------------:|-----------:|
| deepseek-v3.1        |        16.3 |       10   |
| gpt-oss-120b         |         8   |        7.9 |
| gpt-oss-20b          |        12.3 |       12   |
| nemotron3-nano-30b   |        44.3 |       47.2 |
| nemotron3-super-120b |        22.9 |       21.4 |
| qwen3.5-4b           |        20.3 |       17.2 |
| qwen3.5-9b           |        18.2 |       15.2 |
| qwen3.6-35b-a3b      |         6.9 |        8.8 |

## judgebench (282 pairs with all 8 judges; best judge qwen3.6-35b-a3b)

### Per judge

| judge                |   pairs |   acc_all |   flip_rate |   acc_consistent |   wrong_both |   share_errors_on_flips |
|:---------------------|--------:|----------:|------------:|-----------------:|-------------:|------------------------:|
| qwen3.6-35b-a3b      |     345 |      90.6 |         7.2 |             93.8 |          5.8 |                    38.5 |
| qwen3.5-9b           |     335 |      85.1 |        13.1 |             90.4 |          8.4 |                    44   |
| gpt-oss-120b         |     348 |      85.1 |        10.3 |             89.1 |          9.8 |                    34.6 |
| qwen3.5-4b           |     335 |      83.9 |        13.1 |             89   |          9.6 |                    40.7 |
| gpt-oss-20b          |     309 |      81.2 |        12.9 |             85.9 |         12.3 |                    34.5 |
| deepseek-v3.1        |     350 |      79.3 |        18.6 |             86   |         11.4 |                    44.8 |
| nemotron3-super-120b |     321 |      79.1 |        24.3 |             88.5 |          8.7 |                    58.2 |
| nemotron3-nano-30b   |     348 |      56.3 |        49.4 |             62.5 |         19   |                    56.6 |

- `acc_consistent`: accuracy on the pairs where the judge did not flip (abstain-on-flip). `wrong_both`: share of pairs where it picked the wrong answer in both orders (a confident error).
- `share_errors_on_flips`: share of the judge's verdict errors that sit on its flipped pairs.

### Do other judges' flips predict the best judge's errors? (best = qwen3.6-35b-a3b)

|   k |   pairs |   best_err_any |   best_wrong_both |   best_flip |
|----:|--------:|---------------:|------------------:|------------:|
|   0 |      81 |            3.7 |               1.2 |         2.5 |
|   1 |      88 |            3.4 |               1.1 |         2.3 |
|   2 |      52 |           19.2 |              13.5 |         5.8 |
|   3 |      39 |           28.2 |              17.9 |        10.3 |
|   4 |      18 |           44.4 |               5.6 |        38.9 |
|   5 |       3 |           33.3 |               0   |        33.3 |
|   6 |       1 |            0   |               0   |         0   |

- AUROC of 'number of other judges that flip' for the best judge's confident errors, among the 263 pairs where the best judge itself was consistent: **0.770**.
- Mean lift of P(judge B flips | judge A flips) over B's base flip rate, across judge pairs: **1.86x**.

## alpacafarm (488 pairs with all 8 judges; best judge deepseek-v3.1)

### Per judge

| judge                |   pairs |   acc_all |   flip_rate |   acc_consistent |   wrong_both |   share_errors_on_flips |
|:---------------------|--------:|----------:|------------:|-----------------:|-------------:|------------------------:|
| deepseek-v3.1        |     501 |      73   |        21.8 |             79.3 |         16.2 |                    40.2 |
| nemotron3-super-120b |     500 |      72.4 |        24.8 |             79.8 |         15.2 |                    44.9 |
| qwen3.5-9b           |     498 |      72.4 |        23.1 |             79.1 |         16.1 |                    41.8 |
| gpt-oss-120b         |     501 |      71.5 |        16.4 |             75.7 |         20.4 |                    28.7 |
| qwen3.6-35b-a3b      |     500 |      71.4 |        22.4 |             77.6 |         17.4 |                    39.2 |
| gpt-oss-20b          |     492 |      69.3 |        22.4 |             74.9 |         19.5 |                    36.4 |
| qwen3.5-4b           |     499 |      65.9 |        27.3 |             71.9 |         20.4 |                    40   |
| nemotron3-nano-30b   |     500 |      64.4 |        34.8 |             72.1 |         18.2 |                    48.9 |

- `acc_consistent`: accuracy on the pairs where the judge did not flip (abstain-on-flip). `wrong_both`: share of pairs where it picked the wrong answer in both orders (a confident error).
- `share_errors_on_flips`: share of the judge's verdict errors that sit on its flipped pairs.

### Do other judges' flips predict the best judge's errors? (best = deepseek-v3.1)

|   k |   pairs |   best_err_any |   best_wrong_both |   best_flip |
|----:|--------:|---------------:|------------------:|------------:|
|   0 |     151 |           15.2 |               9.3 |         6   |
|   1 |     102 |           32.4 |              15.7 |        16.7 |
|   2 |      95 |           47.4 |              22.1 |        25.3 |
|   3 |      58 |           63.8 |              20.7 |        43.1 |
|   4 |      52 |           59.6 |              17.3 |        42.3 |
|   5 |      26 |           50   |              23.1 |        26.9 |
|   6 |       4 |           75   |              25   |        50   |

- AUROC of 'number of other judges that flip' for the best judge's confident errors, among the 382 pairs where the best judge itself was consistent: **0.661**.
- Mean lift of P(judge B flips | judge A flips) over B's base flip rate, across judge pairs: **1.56x**.

## mtbhuman (300 pairs with all 8 judges; best judge gpt-oss-120b)

### Per judge

| judge                |   pairs |   acc_all |   flip_rate |   acc_consistent |   wrong_both |   share_errors_on_flips |
|:---------------------|--------:|----------:|------------:|-----------------:|-------------:|------------------------:|
| gpt-oss-120b         |     321 |      83.8 |         6.2 |             86   |         13.1 |                    19.2 |
| deepseek-v3.1        |     321 |      83.5 |        12.5 |             88.3 |         10.3 |                    37.7 |
| nemotron3-super-120b |     319 |      83.1 |        11.3 |             87.3 |         11.3 |                    33.3 |
| qwen3.6-35b-a3b      |     319 |      83.1 |        12.5 |             87.8 |         10.7 |                    37   |
| gpt-oss-20b          |     309 |      82   |        10.7 |             85.9 |         12.6 |                    29.7 |
| qwen3.5-9b           |     316 |      81.6 |        12.7 |             86.2 |         12   |                    34.5 |
| qwen3.5-4b           |     319 |      76.5 |        19.4 |             82.9 |         13.8 |                    41.3 |
| nemotron3-nano-30b   |     318 |      73.4 |        33   |             85   |         10.1 |                    62.1 |

- `acc_consistent`: accuracy on the pairs where the judge did not flip (abstain-on-flip). `wrong_both`: share of pairs where it picked the wrong answer in both orders (a confident error).
- `share_errors_on_flips`: share of the judge's verdict errors that sit on its flipped pairs.

### Do other judges' flips predict the best judge's errors? (best = gpt-oss-120b)

|   k |   pairs |   best_err_any |   best_wrong_both |   best_flip |
|----:|--------:|---------------:|------------------:|------------:|
|   0 |     130 |            7.7 |               6.9 |         0.8 |
|   1 |      92 |           12   |               9.8 |         2.2 |
|   2 |      31 |           41.9 |              29   |        12.9 |
|   3 |      28 |           53.6 |              25   |        28.6 |
|   4 |      12 |           25   |               8.3 |        16.7 |
|   5 |       3 |           33.3 |              33.3 |         0   |
|   6 |       4 |          100   |              75   |        25   |

- AUROC of 'number of other judges that flip' for the best judge's confident errors, among the 282 pairs where the best judge itself was consistent: **0.703**.
- Mean lift of P(judge B flips | judge A flips) over B's base flip rate, across judge pairs: **2.29x**.
