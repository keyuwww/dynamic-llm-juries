# Stage A results: order flips and the best judge's confident errors

Stored verdicts, no new calls. Target = best judge per benchmark; outcome = its confident error (wrong in both orders) on pairs where it is consistent. AUROC with 95% bootstrap CI over question groups; models are out-of-fold (5x grouped 5-fold).

## bffpair (best judge gpt-oss-120b; 349 consistent pairs, 40 confident errors = 11.5%)

| Signal | AUROC |
|---|---|
| Controls only | 0.72 [0.61, 0.82] |
| Others' flip count | 0.63 [0.51, 0.72] |
| Controls + flips | 0.72 [0.63, 0.82] |
| Others' consistent disagreement | 0.58 [0.49, 0.66] |
| Pooled agreement score | 0.63 [0.52, 0.74] |
| Disagreement + flips | 0.52 [0.40, 0.65] |
| Controls + disagreement + flips | 0.72 [0.62, 0.81] |

- A1 gain from flips over controls: 0.01 [-0.03, 0.04]. Top single controls: open_endedness 0.66, len_gap 0.64, len_total 0.59, bullets_gap 0.58, context_load 0.58, constraints 0.57.
- A3 gain from flips over disagreement: -0.06 [-0.14, 0.04]; over controls + disagreement: 0.01 [-0.02, 0.04]. corr(flips, disagreement) = +0.31.
- A2 matched: error rate 9.5% with 0–1 flips vs 15.3% with ≥ 2 flips; within strata the difference is +3.8 pts (32 strata).
- Errors caught at a fixed flag rate (flips / disagreement / both / controls + both): 10% → 25 / 18 / 15 / 15%; 18% → 32 / 32 / 25 / 38%; 30% → 40 / 40 / 35 / 57%.
- A5 same pair vs sibling pairs of the same question: 0.63 [0.52, 0.73] vs 0.67 [0.54, 0.80]; both 0.64 [0.49, 0.78] (n = 346).
- A6 flip rate when the judge solved vs did not solve the question: gpt-oss-120b 7% vs 8%; gpt-oss-20b 13% vs 9%; deepseek-v3.1 12% vs 19%; qwen3.6-35b-a3b 5% vs 7%; qwen3.5-9b 14% vs 18%; qwen3.5-4b 17% vs 18%; nemotron3-super-120b 21% vs 24%; nemotron3-nano-30b 42% vs 46%. Target's confident-error rate: 10.6% when it solved the question (n=265) vs 11.1% when it did not (n=54). corr(others' flips, judges that solved) = -0.04.
- A7 leave-one-judge-out, mean AUROC for a held-out judge's confident errors: others' flips 0.67 vs others' labelled errors 0.95.
- A9 checkers chosen on training folds (flag if a checker flips or disagrees): 1 → flag 18%, catch 30% (pooled flips 32%, disagreement 32%, random 18%); 2 → flag 28%, catch 50% (pooled flips 42%, disagreement 40%, random 28%); 3 → flag 33%, catch 57% (pooled flips 45%, disagreement 45%, random 33%).
- Floor: 15% of the confident errors (n = 6) have no other judge flipping or disagreeing.

## judgebench (best judge qwen3.6-35b-a3b; 263 consistent pairs, 17 confident errors = 6.5%)

| Signal | AUROC |
|---|---|
| Controls only | 0.63 [0.47, 0.79] |
| Others' flip count | 0.77 [0.66, 0.86] |
| Controls + flips | 0.71 [0.57, 0.83] |
| Others' consistent disagreement | 0.67 [0.53, 0.80] |
| Pooled agreement score | 0.78 [0.69, 0.87] |
| Disagreement + flips | 0.75 [0.64, 0.86] |
| Controls + disagreement + flips | 0.71 [0.59, 0.82] |

- A1 gain from flips over controls: 0.08 [0.03, 0.14]. Top single controls: reasoning 0.64, context_load 0.63, hedge_gap 0.62, knowledge 0.62, len_gap 0.59, longer_is_better 0.57.
- A3 gain from flips over disagreement: 0.08 [-0.05, 0.20]; over controls + disagreement: 0.07 [0.02, 0.13]. corr(flips, disagreement) = +0.24.
- A2 matched: error rate 1.2% with 0–1 flips vs 15.3% with ≥ 2 flips; within strata the difference is +9.1 pts (33 strata).
- Errors caught at a fixed flag rate (flips / disagreement / both / controls + both): 10% → 24 / 29 / 24 / 35%; 18% → 47 / 53 / 47 / 41%; 30% → 71 / 59 / 71 / 53%.
- A7 leave-one-judge-out, mean AUROC for a held-out judge's confident errors: others' flips 0.78 vs others' labelled errors 0.91.
- A9 checkers chosen on training folds (flag if a checker flips or disagrees): 1 → flag 29%, catch 65% (pooled flips 65%, disagreement 53%, random 29%); 2 → flag 39%, catch 82% (pooled flips 88%, disagreement 65%, random 39%); 3 → flag 43%, catch 82% (pooled flips 88%, disagreement 71%, random 43%).
- Floor: 0% of the confident errors (n = 0) have no other judge flipping or disagreeing.

## alpacafarm (best judge deepseek-v3.1; 382 consistent pairs, 79 confident errors = 20.7%)

| Signal | AUROC |
|---|---|
| Controls only | 0.55 [0.47, 0.62] |
| Others' flip count | 0.66 [0.59, 0.73] |
| Controls + flips | 0.60 [0.53, 0.67] |
| Others' consistent disagreement | 0.61 [0.55, 0.68] |
| Pooled agreement score | 0.69 [0.62, 0.75] |
| Disagreement + flips | 0.66 [0.59, 0.73] |
| Controls + disagreement + flips | 0.64 [0.58, 0.71] |

- A1 gain from flips over controls: 0.06 [0.01, 0.10]. Top single controls: human_margin 0.60, longer_is_better 0.56, knowledge 0.53, hedge_gap 0.52, len_gap 0.52, bullets_gap 0.52.
- A3 gain from flips over disagreement: 0.05 [-0.00, 0.10]; over controls + disagreement: 0.03 [-0.00, 0.06]. corr(flips, disagreement) = +0.24.
- A2 matched: error rate 13.2% with 0–1 flips vs 31.6% with ≥ 2 flips; within strata the difference is +18.9 pts (39 strata).
- Errors caught at a fixed flag rate (flips / disagreement / both / controls + both): 10% → 18 / 18 / 19 / 13%; 18% → 27 / 30 / 32 / 32%; 30% → 46 / 46 / 46 / 48%.
- A7 leave-one-judge-out, mean AUROC for a held-out judge's confident errors: others' flips 0.68 vs others' labelled errors 0.94.
- A7 human split (60% of pairs): AUROC flips 0.59, labelled errors 0.63.
- A9 checkers chosen on training folds (flag if a checker flips or disagrees): 1 → flag 29%, catch 44% (pooled flips 44%, disagreement 44%, random 29%); 2 → flag 39%, catch 61% (pooled flips 61%, disagreement 48%, random 39%); 3 → flag 45%, catch 66% (pooled flips 65%, disagreement 51%, random 45%).
- Floor: 13% of the confident errors (n = 10) have no other judge flipping or disagreeing.

## mtbhuman (best judge gpt-oss-120b; 282 consistent pairs, 39 confident errors = 13.8%)

| Signal | AUROC |
|---|---|
| Controls only | 0.72 [0.62, 0.80] |
| Others' flip count | 0.70 [0.63, 0.78] |
| Controls + flips | 0.77 [0.67, 0.86] |
| Others' consistent disagreement | 0.66 [0.58, 0.75] |
| Pooled agreement score | 0.76 [0.68, 0.84] |
| Disagreement + flips | 0.74 [0.65, 0.82] |
| Controls + disagreement + flips | 0.81 [0.73, 0.88] |

- A1 gain from flips over controls: 0.05 [0.01, 0.10]. Top single controls: len_gap 0.75, longer_is_better 0.65, same_final_number 0.61, human_margin 0.59, sim 0.59, len_total 0.59.
- A3 gain from flips over disagreement: 0.08 [0.00, 0.15]; over controls + disagreement: 0.03 [0.00, 0.07]. corr(flips, disagreement) = +0.22.
- A2 matched: error rate 8.2% with 0–1 flips vs 33.3% with ≥ 2 flips; within strata the difference is +26.1 pts (34 strata).
- Errors caught at a fixed flag rate (flips / disagreement / both / controls + both): 10% → 21 / 33 / 28 / 41%; 18% → 49 / 44 / 54 / 62%; 30% → 59 / 46 / 67 / 69%.
- A5 same pair vs sibling pairs of the same question: 0.70 [0.62, 0.78] vs 0.52 [0.41, 0.63]; both 0.65 [0.55, 0.74] (n = 279).
- A7 leave-one-judge-out, mean AUROC for a held-out judge's confident errors: others' flips 0.70 vs others' labelled errors 0.96.
- A7 human split (14% of pairs): AUROC flips 0.61, labelled errors 0.65.
- A9 checkers chosen on training folds (flag if a checker flips or disagrees): 1 → flag 17%, catch 23% (pooled flips 41%, disagreement 44%, random 17%); 2 → flag 27%, catch 44% (pooled flips 59%, disagreement 46%, random 27%); 3 → flag 31%, catch 54% (pooled flips 59%, disagreement 54%, random 31%).
- Floor: 18% of the confident errors (n = 7) have no other judge flipping or disagreeing.
