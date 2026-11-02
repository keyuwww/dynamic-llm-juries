# A6 qualitative coding: summary

120 verdicts, 20 per cell, coded blind to confidence level and flips by four LLM coders (Claude).
Coders' judge_right matches the data on 100% of records. Reasoning-based codes are left blank for 18 verdict-only records; 9 records had reasoning cut at 6,000 characters.

## Share of records with each code, by cell

| cell   |   n |   gold_questionable |   noticed_decisive |   hedging |   says_close |   reads_high |   reads_low |   no_reasoning |   truncated |
|:-------|----:|--------------------:|-------------------:|----------:|-------------:|-------------:|------------:|---------------:|------------:|
| HW     |  20 |                0.55 |               0.65 |      0.18 |         0.12 |         0.88 |        0.06 |              3 |           2 |
| MW     |  20 |                0.45 |               0.73 |      0.27 |         0.6  |         0.73 |        0.07 |              5 |           0 |
| LW     |  20 |                0.35 |               0.31 |      0.62 |         0.81 |         0.12 |        0.38 |              4 |           2 |
| HF     |  20 |                0.1  |               0.5  |      0.31 |         0.19 |         0.56 |        0.12 |              4 |           4 |
| HR     |  20 |                0    |               0.95 |      0.25 |         0.1  |         0.9  |        0    |              0 |           1 |
| LR     |  20 |                0.1  |               0.89 |      0.72 |         0.78 |         0.33 |        0.17 |              2 |           0 |

## Error type among wrong verdicts (row shares)

| cell   |   n |   arithmetic_logic_slip |   gold_questionable |   misread_question_or_constraint |   missed_factual_error |   near_tie |   other |   preferred_length_or_style |
|:-------|----:|------------------------:|--------------------:|---------------------------------:|-----------------------:|-----------:|--------:|----------------------------:|
| HW     |  20 |                    0.05 |                0.45 |                             0.05 |                   0.15 |       0.2  |    0.05 |                        0.05 |
| MW     |  20 |                    0.1  |                0.35 |                             0    |                   0.25 |       0.25 |    0    |                        0.05 |
| LW     |  20 |                    0    |                0.15 |                             0.05 |                   0.25 |       0.45 |    0.05 |                        0.05 |
| HF     |   8 |                    0.5  |                0    |                             0.25 |                   0.12 |       0.12 |    0    |                        0    |

## Can a blind reader tell the confidence level from the reasoning? (AUROC of perceived confidence)

| contrast   |   auc_perceived_confidence | n     |
|:-----------|---------------------------:|:------|
| HW vs LW   |                       0.88 | 17/16 |
| HR vs LR   |                       0.79 | 20/18 |
| HW vs HR   |                       0.49 | 17/20 |
| LW vs LR   |                       0.34 | 16/18 |
