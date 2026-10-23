# C3: semantic controls and text-only flip prediction

Embeddings: all-MiniLM-L6-v2 on question, answer A, answer B. Target and outcome as in Stage A (best judge's confident errors on its consistent pairs). AUROC with 95% bootstrap CI over questions.

## bffpair (best judge gpt-oss-120b)

| Signal | AUROC |
|---|---|
| Semantic similarity cos(A,B) alone | 0.48 |
| Lexical + semantic controls | 0.71 [0.60, 0.81] |
| Controls + real flips | 0.71 |
| Real flip count | 0.63 |
| Flip count predicted from text only | 0.52 |

- Gain from real flips over lexical + semantic controls: 0.01 [-0.03, 0.05].
- Correlation of flip count with semantic features: cos_ab +0.06, cos_aq +0.10, cos_bq +0.02, rel_gap -0.02.
- Text-only prediction of the flip count: r = -0.05 with the real count (grouped CV).

## judgebench (best judge qwen3.6-35b-a3b)

| Signal | AUROC |
|---|---|
| Semantic similarity cos(A,B) alone | 0.42 |
| Lexical + semantic controls | 0.62 [0.46, 0.77] |
| Controls + real flips | 0.71 |
| Real flip count | 0.77 |
| Flip count predicted from text only | 0.70 |

- Gain from real flips over lexical + semantic controls: 0.09 [0.04, 0.15].
- Correlation of flip count with semantic features: cos_ab +0.00, cos_aq +0.07, cos_bq +0.13, rel_gap -0.07.
- Text-only prediction of the flip count: r = 0.29 with the real count (grouped CV).

## alpacafarm (best judge deepseek-v3.1)

| Signal | AUROC |
|---|---|
| Semantic similarity cos(A,B) alone | 0.46 |
| Lexical + semantic controls | 0.55 [0.48, 0.62] |
| Controls + real flips | 0.62 |
| Real flip count | 0.66 |
| Flip count predicted from text only | 0.48 |

- Gain from real flips over lexical + semantic controls: 0.07 [0.02, 0.11].
- Correlation of flip count with semantic features: cos_ab +0.00, cos_aq -0.09, cos_bq -0.15, rel_gap -0.05.
- Text-only prediction of the flip count: r = 0.20 with the real count (grouped CV).

## mtbhuman (best judge gpt-oss-120b)

| Signal | AUROC |
|---|---|
| Semantic similarity cos(A,B) alone | 0.37 |
| Lexical + semantic controls | 0.72 [0.61, 0.81] |
| Controls + real flips | 0.76 |
| Real flip count | 0.70 |
| Flip count predicted from text only | 0.62 |

- Gain from real flips over lexical + semantic controls: 0.04 [-0.00, 0.09].
- Correlation of flip count with semantic features: cos_ab +0.12, cos_aq -0.11, cos_bq +0.09, rel_gap -0.10.
- Text-only prediction of the flip count: r = 0.02 with the real count (grouped CV).
