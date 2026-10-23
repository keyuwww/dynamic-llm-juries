# Stage C: controlled pairs and single-answer grading

## C2. Controlled BFF pairs

236 pairs (82 identical, 72 corrupted, 82 padded per judge), both orders, 8 judges.

- **identical**: same answer in both slots. `first_both` / `second_both` = picked the same position in both orders (pure position preference).
- **corrupt**: original vs the same answer with its last figure changed by +10%. `flip` = picked the same position both times; `conf_wrong` = picked the corrupted answer in both orders.
- **pad**: original vs the same answer plus a neutral paragraph.

| judge     |   identical_first_both |   identical_second_both |   corrupt_acc |   corrupt_flip |   corrupt_conf_wrong |   pad_prefers_long_both |   pad_prefers_short_both |   pad_flip |   real_bff_flip |
|:----------|-----------------------:|------------------------:|--------------:|---------------:|---------------------:|------------------------:|-------------------------:|-----------:|----------------:|
| oss-120b  |                   98.8 |                     0   |          90.8 |           18.3 |                  0   |                    48.1 |                      7.4 |       44.4 |             4.3 |
| oss-20b   |                   98.8 |                     0   |          86.8 |           26.5 |                  0   |                    51.9 |                      6.5 |       41.6 |            11.5 |
| deepseek  |                  100   |                     0   |          88.7 |           22.5 |                  0   |                    12   |                      0   |       88   |            16.6 |
| qwen-35b  |                   96.2 |                     0   |          97.9 |            4.3 |                  0   |                    42.7 |                     12.2 |       45.1 |             9.9 |
| qwen-9b   |                  100   |                     0   |          88.7 |           19.7 |                  1.4 |                    26.8 |                      3.7 |       69.5 |            19.4 |
| qwen-4b   |                   97.5 |                     0   |          92.3 |           15.5 |                  0   |                    25   |                      2.5 |       72.5 |            18.9 |
| nem-super |                   92.6 |                     0   |          80.3 |           33.8 |                  2.8 |                    40.2 |                      4.9 |       54.9 |            22   |
| nem-nano  |                   41.5 |                    14.6 |          56.4 |           50   |                 18.6 |                    14.6 |                     15.9 |       69.5 |            48.1 |

Stated confidence on corrupted pairs (mean of both orders): qwen-9b right 98 / wrong-both 100, nem-super right 95 / wrong-both 75, nem-nano right 96 / wrong-both 93.

## C4. Single-answer grading (RewardBench 2 other)

Best judge gpt-oss-120b; 958 items, 158 errors (16.5%). No order to swap, so the cross-judge signal is plain disagreement plus the other judges' stated confidence.

| Signal | AUROC [95% CI] | Errors caught at 18% flagged |
|---|---|---|
| own stated confidence (low) | 0.61 [0.56, 0.66] | 32% |
| own token probability (low) | 0.47 [0.43, 0.51] | 14% |
| others disagreeing (count) | 0.73 [0.68, 0.77] | 43% |
| others' low stated confidence | 0.65 [0.60, 0.70] | 35% |
| own confidence + others disagreeing | 0.71 [0.66, 0.76] | 39% |
| own + disagreeing + others' low confidence | 0.72 [0.66, 0.77] | 42% |
