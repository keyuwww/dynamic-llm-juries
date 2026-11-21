# Within-question hidden-state test, layer chosen without the test questions (post hoc)

Share of (believed, never-reached) wrong-answer pairs from the same BBEH question in which the believed answer scores higher on the correctness direction (0.5 = no difference).

| model | role | questions (pairs) | paper's selection on all questions (layer) [95%, first split] | top third of layers | nested choice [95%] | layers chosen (most often) | middle layer (layer) | verdict log-odds [95%] |
|---|---|---|---|---|---|---|---|---|
| qwen3.5-9b | snap verdict | 39 (135) | 0.64 (32) [0.52, 0.78] | 0.60 | 0.62 [0.55, 0.69] | [2, 4, 6, 8, 14, 16, 18, 20, 22, 26, 32] (32) | 0.58 (16) | 0.69 [0.57, 0.80] |
| qwen3.5-9b | solving | 39 (135) | 0.60 (30) [0.45, 0.71] | 0.59 | 0.59 [0.50, 0.66] | [2, 12, 14, 18, 20, 22, 28, 30, 32] (30) | 0.56 (16) | – |
| qwen3.5-9b | after explanation | 39 (135) | 0.71 (22) [0.59, 0.84] | 0.71 | 0.70 [0.58, 0.82] | [16, 18, 20, 22, 32] (22) | 0.68 (16) | 0.70 [0.59, 0.80] |
| qwen3.6-35b-a3b | snap verdict | 37 (121) | 0.60 (28) [0.46, 0.74] | 0.59 | 0.58 [0.49, 0.67] | [2, 10, 12, 18, 20, 22, 24, 26, 30, 32, 34, 36, 38] (34) | 0.61 (20) | 0.60 [0.47, 0.73] |
| qwen3.6-35b-a3b | solving | 37 (121) | 0.56 (40) [0.34, 0.66] | 0.59 | 0.59 [0.51, 0.66] | [2, 6, 22, 26, 30, 34, 36, 38, 40] (40) | 0.62 (20) | – |
| qwen3.6-35b-a3b | after explanation | 37 (121) | 0.75 (28) [0.62, 0.86] | 0.77 | 0.77 [0.67, 0.86] | [16, 18, 22, 26, 28, 30, 40] (26) | 0.78 (20) | 0.78 [0.66, 0.87] |
| nemotron3-nano-30b | snap verdict | 22 (67) | 0.56 (8) [0.39, 0.68] | 0.59 | 0.59 [0.53, 0.68] | [2, 4, 6, 8, 12, 18, 20, 22, 32, 34, 36, 40, 44, 48] (8) | 0.56 (26) | 0.47 [0.27, 0.71] |
| nemotron3-nano-30b | solving | 22 (67) | 0.59 (46) [0.41, 0.82] | 0.59 | 0.56 [0.44, 0.68] | [6, 8, 10, 12, 28, 30, 36, 38, 42, 44, 46, 48, 50, 52] (46) | 0.57 (26) | – |
