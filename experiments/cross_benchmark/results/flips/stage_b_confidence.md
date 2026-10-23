# Stage B: confidence vs order flips (confidence)

Same pairwise prompts with a CONFIDENCE line; both orders; K samples per call. Outcome: the best judge's confident errors on its consistent pairs (stored run, as in Stage A). AUROC 0.5 = chance.

## bffpair (best judge gpt-oss-120b; judges deepseek-v3.1, gpt-oss-120b, gpt-oss-20b, nemotron3-nano-30b, nemotron3-super-120b, qwen3.5-4b, qwen3.5-9b, qwen3.6-35b-a3b; K = 1)

- Parse rate 98.7%, confidence line present 98.7%. Asking for confidence changed 16.2% of verdicts vs the stored run. Stated confidence: mean 93.98, sd 7.5, range 52.5–100.0.

**B-a: is a judge less confident on pairs it flips?** (AUROC of low confidence for its own flip)

| judge                |   flip_rate |   auroc_stated |   auroc_token |   auroc_vote |   stated_if_flip |   stated_if_cons |
|:---------------------|------------:|---------------:|--------------:|-------------:|-----------------:|-----------------:|
| deepseek-v3.1        |       0.165 |          0.707 |         0.719 |          nan |           87.979 |           94.466 |
| gpt-oss-120b         |       0.043 |          0.863 |         0.64  |          nan |           74.684 |           89.57  |
| gpt-oss-20b          |       0.106 |          0.751 |         0.523 |          nan |           84.872 |           92.753 |
| nemotron3-nano-30b   |       0.48  |          0.58  |         0.562 |          nan |           93.974 |           95.124 |
| nemotron3-super-120b |       0.217 |          0.659 |         0.634 |          nan |           87.552 |           93.168 |
| qwen3.5-4b           |       0.183 |          0.715 |         0.686 |          nan |           95.741 |           98.062 |
| qwen3.5-9b           |       0.188 |          0.705 |         0.709 |          nan |           91.958 |           97.035 |
| qwen3.6-35b-a3b      |       0.097 |          0.73  |         0.764 |          nan |           93.895 |           97.789 |

**B-b: does the best judge's own confidence flag its confident errors?** (349 pairs, 40 errors) stated 0.74 [0.63, 0.84]; token 0.59 [0.52, 0.66].

| stated   |   pairs |   error_rate |
|:---------|--------:|-------------:|
| 0-80     |      35 |        0.229 |
| 80-90    |      66 |        0.258 |
| 90-95    |      68 |        0.118 |
| 95-100   |     180 |        0.039 |

**B-c: others' flips by the best judge's confidence (stated terciles)**

| confidence   |   pairs |   errors |   error_rate |   auroc_others_flips |   auroc_pooled |
|:-------------|--------:|---------:|-------------:|---------------------:|---------------:|
| low          |     117 |       28 |        0.239 |                0.559 |          0.559 |
| mid          |     116 |       10 |        0.086 |                0.488 |          0.472 |
| high         |     116 |        2 |        0.017 |                0.575 |          0.596 |

**B-d: combined alarm.** Others' pooled score alone 0.63 [0.52, 0.73] (catches 25% of errors at 18% flagged).

| Own measure | Own AUROC | Combined with others | Correlation | Caught at 18%: own / combined |
|---|---|---|---|---|
| stated | 0.74 [0.63, 0.84] | 0.73 [0.64, 0.81] | +0.41 | 42% / 40% |
| token | 0.59 [0.52, 0.66] | 0.66 [0.58, 0.74] | +0.20 | 22% / 28% |

**B-e: checkers' confidence vs their flips** (deepseek-v3.1, gpt-oss-20b, nemotron3-nano-30b, nemotron3-super-120b, qwen3.5-4b, qwen3.5-9b, qwen3.6-35b-a3b): low stated confidence 0.74; their flips 0.62.

## judgebench (best judge qwen3.6-35b-a3b; judges deepseek-v3.1, gpt-oss-120b, gpt-oss-20b, nemotron3-nano-30b, nemotron3-super-120b, qwen3.5-4b, qwen3.5-9b, qwen3.6-35b-a3b; K = 1)

- Parse rate 92.6%, confidence line present 92.6%. Asking for confidence changed 19.8% of verdicts vs the stored run. Stated confidence: mean 91.56, sd 9.34, range 50.0–100.0.

**B-a: is a judge less confident on pairs it flips?** (AUROC of low confidence for its own flip)

| judge                |   flip_rate |   auroc_stated |   auroc_token |   auroc_vote |   stated_if_flip |   stated_if_cons |
|:---------------------|------------:|---------------:|--------------:|-------------:|-----------------:|-----------------:|
| deepseek-v3.1        |       0.209 |          0.69  |         0.597 |          nan |           84.76  |           91.634 |
| gpt-oss-120b         |       0.089 |          0.833 |         0.633 |          nan |           73.387 |           87.045 |
| gpt-oss-20b          |       0.106 |          0.647 |         0.446 |          nan |           85.824 |           91.541 |
| nemotron3-nano-30b   |       0.529 |          0.648 |         0.524 |          nan |           88.203 |           92.07  |
| nemotron3-super-120b |       0.237 |          0.708 |         0.67  |          nan |           82.217 |           90.773 |
| qwen3.5-4b           |       0.1   |          0.744 |         0.685 |          nan |           89.286 |           95.831 |
| qwen3.5-9b           |       0.086 |          0.714 |         0.578 |          nan |           91.333 |           95.729 |
| qwen3.6-35b-a3b      |       0.046 |          0.803 |         0.71  |          nan |           89.062 |           97.064 |

**B-b: does the best judge's own confidence flag its confident errors?** (263 pairs, 17 errors) stated 0.84 [0.75, 0.91]; token 0.81 [0.71, 0.89].

| stated   |   pairs |   error_rate |
|:---------|--------:|-------------:|
| 0-80     |       3 |        0     |
| 80-90    |      17 |        0.353 |
| 90-95    |      25 |        0.16  |
| 95-100   |     217 |        0.032 |

**B-c: others' flips by the best judge's confidence (stated terciles)**

| confidence   |   pairs |   errors |   error_rate |   auroc_others_flips |   auroc_pooled |
|:-------------|--------:|---------:|-------------:|---------------------:|---------------:|
| low          |      88 |       15 |        0.17  |                0.642 |          0.637 |
| mid          |      87 |        2 |        0.023 |                0.676 |          0.562 |
| high         |      87 |        0 |        0     |              nan     |        nan     |

**B-d: combined alarm.** Others' pooled score alone 0.78 [0.68, 0.87] (catches 53% of errors at 18% flagged).

| Own measure | Own AUROC | Combined with others | Correlation | Caught at 18%: own / combined |
|---|---|---|---|---|
| stated | 0.84 [0.75, 0.92] | 0.86 [0.76, 0.93] | +0.53 | 59% / 65% |
| token | 0.81 [0.71, 0.90] | 0.85 [0.75, 0.92] | +0.43 | 65% / 59% |

**B-e: checkers' confidence vs their flips** (deepseek-v3.1, gpt-oss-120b, gpt-oss-20b, nemotron3-nano-30b, nemotron3-super-120b, qwen3.5-4b, qwen3.5-9b): low stated confidence 0.83; their flips 0.73.

## alpacafarm (best judge deepseek-v3.1; judges deepseek-v3.1, gpt-oss-120b, gpt-oss-20b, nemotron3-nano-30b, nemotron3-super-120b, qwen3.5-4b, qwen3.5-9b, qwen3.6-35b-a3b; K = 1)

- Parse rate 99.8%, confidence line present 99.9%. Asking for confidence changed 16.8% of verdicts vs the stored run. Stated confidence: mean 85.54, sd 11.4, range 0.0–100.0.

**B-a: is a judge less confident on pairs it flips?** (AUROC of low confidence for its own flip)

| judge                |   flip_rate |   auroc_stated |   auroc_token |   auroc_vote |   stated_if_flip |   stated_if_cons |
|:---------------------|------------:|---------------:|--------------:|-------------:|-----------------:|-----------------:|
| deepseek-v3.1        |       0.184 |          0.774 |         0.776 |          nan |           69.554 |           82.243 |
| gpt-oss-120b         |       0.166 |          0.793 |         0.552 |          nan |           70.404 |           81.163 |
| gpt-oss-20b          |       0.19  |          0.77  |         0.497 |          nan |           78.121 |           86.007 |
| nemotron3-nano-30b   |       0.345 |          0.593 |         0.561 |          nan |           90.552 |           92.252 |
| nemotron3-super-120b |       0.273 |          0.721 |         0.524 |          nan |           78.85  |           85.453 |
| qwen3.5-4b           |       0.281 |          0.654 |         0.66  |          nan |           86.461 |           91.729 |
| qwen3.5-9b           |       0.251 |          0.681 |         0.705 |          nan |           78.889 |           86.127 |
| qwen3.6-35b-a3b      |       0.232 |          0.713 |         0.646 |          nan |           85.56  |           92.138 |

**B-b: does the best judge's own confidence flag its confident errors?** (382 pairs, 79 errors) stated 0.65 [0.58, 0.72]; token 0.66 [0.60, 0.73].

| stated   |   pairs |   error_rate |
|:---------|--------:|-------------:|
| 0-80     |     122 |        0.311 |
| 80-90    |     109 |        0.202 |
| 90-95    |      74 |        0.149 |
| 95-100   |      77 |        0.104 |

**B-c: others' flips by the best judge's confidence (stated terciles)**

| confidence   |   pairs |   errors |   error_rate |   auroc_others_flips |   auroc_pooled |
|:-------------|--------:|---------:|-------------:|---------------------:|---------------:|
| low          |     128 |       39 |        0.305 |                0.564 |          0.567 |
| mid          |     127 |       25 |        0.197 |                0.625 |          0.691 |
| high         |     127 |       15 |        0.118 |                0.678 |          0.721 |

**B-d: combined alarm.** Others' pooled score alone 0.69 [0.63, 0.75] (catches 34% of errors at 18% flagged).

| Own measure | Own AUROC | Combined with others | Correlation | Caught at 18%: own / combined |
|---|---|---|---|---|
| stated | 0.65 [0.58, 0.72] | 0.70 [0.65, 0.76] | +0.41 | 32% / 29% |
| token | 0.66 [0.60, 0.73] | 0.71 [0.65, 0.78] | +0.36 | 33% / 37% |

**B-e: checkers' confidence vs their flips** (gpt-oss-120b, gpt-oss-20b, nemotron3-nano-30b, nemotron3-super-120b, qwen3.5-4b, qwen3.5-9b, qwen3.6-35b-a3b): low stated confidence 0.65; their flips 0.65.

## mtbhuman (best judge gpt-oss-120b; judges deepseek-v3.1, gpt-oss-120b, gpt-oss-20b, nemotron3-nano-30b, nemotron3-super-120b, qwen3.5-4b, qwen3.5-9b, qwen3.6-35b-a3b; K = 1)

- Parse rate 99.6%, confidence line present 99.6%. Asking for confidence changed 12.5% of verdicts vs the stored run. Stated confidence: mean 91.01, sd 9.21, range 50.0–100.0.

**B-a: is a judge less confident on pairs it flips?** (AUROC of low confidence for its own flip)

| judge                |   flip_rate |   auroc_stated |   auroc_token |   auroc_vote |   stated_if_flip |   stated_if_cons |
|:---------------------|------------:|---------------:|--------------:|-------------:|-----------------:|-----------------:|
| deepseek-v3.1        |       0.112 |          0.775 |         0.731 |          nan |           79.792 |           90.921 |
| gpt-oss-120b         |       0.069 |          0.847 |         0.422 |          nan |           73.886 |           86.987 |
| gpt-oss-20b          |       0.131 |          0.806 |         0.516 |          nan |           80.702 |           90.421 |
| nemotron3-nano-30b   |       0.352 |          0.561 |         0.633 |          nan |           91.774 |           93.373 |
| nemotron3-super-120b |       0.125 |          0.762 |         0.628 |          nan |           81.375 |           89.324 |
| qwen3.5-4b           |       0.184 |          0.672 |         0.693 |          nan |           93.686 |           95.086 |
| qwen3.5-9b           |       0.202 |          0.795 |         0.825 |          nan |           86.077 |           93.887 |
| qwen3.6-35b-a3b      |       0.097 |          0.733 |         0.731 |          nan |           90.161 |           95.441 |

**B-b: does the best judge's own confidence flag its confident errors?** (282 pairs, 39 errors) stated 0.76 [0.69, 0.83]; token 0.61 [0.53, 0.70].

| stated   |   pairs |   error_rate |
|:---------|--------:|-------------:|
| 0-80     |      59 |        0.305 |
| 80-90    |      75 |        0.187 |
| 90-95    |      46 |        0.087 |
| 95-100   |     102 |        0.029 |

**B-c: others' flips by the best judge's confidence (stated terciles)**

| confidence   |   pairs |   errors |   error_rate |   auroc_others_flips |   auroc_pooled |
|:-------------|--------:|---------:|-------------:|---------------------:|---------------:|
| low          |      94 |       25 |        0.266 |                0.669 |          0.699 |
| mid          |      94 |       11 |        0.117 |                0.505 |          0.623 |
| high         |      94 |        3 |        0.032 |                0.712 |          0.773 |

**B-d: combined alarm.** Others' pooled score alone 0.76 [0.68, 0.84] (catches 54% of errors at 18% flagged).

| Own measure | Own AUROC | Combined with others | Correlation | Caught at 18%: own / combined |
|---|---|---|---|---|
| stated | 0.76 [0.69, 0.83] | 0.80 [0.73, 0.86] | +0.48 | 44% / 49% |
| token | 0.61 [0.52, 0.70] | 0.75 [0.67, 0.83] | +0.13 | 26% / 49% |

**B-e: checkers' confidence vs their flips** (deepseek-v3.1, gpt-oss-20b, nemotron3-nano-30b, nemotron3-super-120b, qwen3.5-4b, qwen3.5-9b, qwen3.6-35b-a3b): low stated confidence 0.78; their flips 0.73.
