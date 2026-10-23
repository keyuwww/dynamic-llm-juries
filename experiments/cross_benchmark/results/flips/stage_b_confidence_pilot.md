# Stage B: confidence vs order flips (confidence_pilot)

Same pairwise prompts with a CONFIDENCE line; both orders; K samples per call. Outcome: the best judge's confident errors on its consistent pairs (stored run, as in Stage A). AUROC 0.5 = chance.

## bffpair (best judge gpt-oss-120b; judges gpt-oss-120b, gpt-oss-20b, nemotron3-nano-30b; K = 3)

- Parse rate 98.1%, confidence line present 98.2%. Asking for confidence changed 20.1% of verdicts vs the stored run. Stated confidence: mean 91.99, sd 6.58, range 59.17–100.0.

**B-a: is a judge less confident on pairs it flips?** (AUROC of low confidence for its own flip)

| judge              |   flip_rate |   auroc_stated |   auroc_token |   auroc_vote |   stated_if_flip |   stated_if_cons |
|:-------------------|------------:|---------------:|--------------:|-------------:|-----------------:|-----------------:|
| gpt-oss-120b       |       0.07  |          0.855 |         0.663 |        0.978 |           76.647 |           89.913 |
| gpt-oss-20b        |       0.093 |          0.746 |         0.692 |        0.943 |           87.299 |           92.635 |
| nemotron3-nano-30b |       0.475 |          0.533 |         0.574 |        0.719 |           94.762 |           94.942 |

**B-b: does the best judge's own confidence flag its confident errors?** (349 pairs, 40 errors) stated 0.80 [0.70, 0.89]; token 0.63 [0.52, 0.71]; vote spread 0.58 [0.49, 0.69].

| stated   |   pairs |   error_rate |
|:---------|--------:|-------------:|
| 0-80     |      32 |        0.438 |
| 80-90    |      77 |        0.195 |
| 90-95    |      92 |        0.087 |
| 95-100   |     148 |        0.02  |

**B-c: others' flips by the best judge's confidence (stated terciles)**

| confidence   |   pairs |   errors |   error_rate |   auroc_others_flips |   auroc_pooled |
|:-------------|--------:|---------:|-------------:|---------------------:|---------------:|
| low          |     117 |       30 |        0.256 |                0.506 |          0.503 |
| mid          |     116 |        8 |        0.069 |                0.554 |          0.573 |
| high         |     116 |        2 |        0.017 |                0.827 |          0.761 |

**B-d: combined alarm.** Others' pooled score alone 0.63 [0.52, 0.73] (catches 32% of errors at 18% flagged).

| Own measure | Own AUROC | Combined with others | Correlation | Caught at 18%: own / combined |
|---|---|---|---|---|
| stated | 0.80 [0.70, 0.89] | 0.76 [0.69, 0.84] | +0.42 | 48% / 42% |
| token | 0.63 [0.53, 0.72] | 0.68 [0.59, 0.75] | +0.17 | 30% / 25% |
| vote | 0.60 [0.53, 0.66] | 0.66 [0.56, 0.75] | +0.30 | 32% / 35% |

**B-e: checkers' confidence vs their flips** (gpt-oss-20b, nemotron3-nano-30b): low stated confidence 0.66; their flips 0.57; low vote stability 0.63.

**C1: noise.** Share of a judge's flips that repeat in at least 2 of 3 sample pairings: gpt-oss-120b 46%, gpt-oss-20b 52%, nemotron3-nano-30b 73%. Checkers' flips as an alarm: single run 0.57, all samples 0.57, repeatable flips only 0.53.

## mtbhuman (best judge gpt-oss-120b; judges gpt-oss-120b, gpt-oss-20b, nemotron3-nano-30b; K = 3)

- Parse rate 99.4%, confidence line present 99.6%. Asking for confidence changed 14.0% of verdicts vs the stored run. Stated confidence: mean 89.41, sd 7.66, range 62.5–100.0.

**B-a: is a judge less confident on pairs it flips?** (AUROC of low confidence for its own flip)

| judge              |   flip_rate |   auroc_stated |   auroc_token |   auroc_vote |   stated_if_flip |   stated_if_cons |
|:-------------------|------------:|---------------:|--------------:|-------------:|-----------------:|-----------------:|
| gpt-oss-120b       |       0.081 |          0.863 |         0.482 |        0.979 |           74.09  |           87.145 |
| gpt-oss-20b        |       0.093 |          0.779 |         0.654 |        0.951 |           83.111 |           89.953 |
| nemotron3-nano-30b |       0.349 |          0.641 |         0.603 |        0.811 |           91.589 |           93.485 |

**B-b: does the best judge's own confidence flag its confident errors?** (282 pairs, 39 errors) stated 0.78 [0.71, 0.84]; token 0.58 [0.48, 0.69]; vote spread 0.65 [0.57, 0.74].

| stated   |   pairs |   error_rate |
|:---------|--------:|-------------:|
| 0-80     |      67 |        0.269 |
| 80-90    |      70 |        0.229 |
| 90-95    |      62 |        0.065 |
| 95-100   |      83 |        0.012 |

**B-c: others' flips by the best judge's confidence (stated terciles)**

| confidence   |   pairs |   errors |   error_rate |   auroc_others_flips |   auroc_pooled |
|:-------------|--------:|---------:|-------------:|---------------------:|---------------:|
| low          |      94 |       24 |        0.255 |                0.654 |          0.665 |
| mid          |      94 |       14 |        0.149 |                0.622 |          0.757 |
| high         |      94 |        1 |        0.011 |                0.323 |          0.317 |

**B-d: combined alarm.** Others' pooled score alone 0.76 [0.68, 0.84] (catches 49% of errors at 18% flagged).

| Own measure | Own AUROC | Combined with others | Correlation | Caught at 18%: own / combined |
|---|---|---|---|---|
| stated | 0.78 [0.71, 0.84] | 0.81 [0.75, 0.87] | +0.51 | 38% / 49% |
| token | 0.58 [0.48, 0.69] | 0.72 [0.63, 0.81] | +0.17 | 26% / 44% |
| vote | 0.63 [0.56, 0.69] | 0.78 [0.70, 0.85] | +0.33 | 44% / 56% |

**B-e: checkers' confidence vs their flips** (gpt-oss-20b, nemotron3-nano-30b): low stated confidence 0.72; their flips 0.57; low vote stability 0.70.

**C1: noise.** Share of a judge's flips that repeat in at least 2 of 3 sample pairings: gpt-oss-120b 80%, gpt-oss-20b 52%, nemotron3-nano-30b 71%. Checkers' flips as an alarm: single run 0.57, all samples 0.66, repeatable flips only 0.64.
