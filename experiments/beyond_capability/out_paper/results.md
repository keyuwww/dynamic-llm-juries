# Paper results: every method vs the forced verdict

Gain over the forced verdict ×100 [95% interval], pooled over judges. Ranking = within-group AUROC; best-of-n = accuracy of the top-scored answer.

## pool_unsolved|all (19 judges; verdict ranking 50.8, verdict best-of-n 58.3, random 58.4)

| Method | Ranking gain | Best-of-n gain |
|---|---|---|
| Reason first | -0.2 [-1.1, +0.8] | -1.1 [-2.4, +0.2] |
| Stretch ×4 | +2.2 [+1.7, +2.6] | +2.3 [+1.5, +3.1] |
| Stretch ×11 | +4.2 [+3.4, +4.9] | +4.2 [+3.1, +5.3] |
| Direction | +10.1 [+8.3, +11.8] | +9.6 [+7.5, +11.5] |
| Verdict + direction | +6.5 [+5.5, +7.6] | +6.6 [+5.3, +7.9] |
| Reason first + direction | +6.6 [+5.2, +7.8] | +6.0 [+4.3, +7.5] |

## pool|all (19 judges; verdict ranking 53.3, verdict best-of-n 61.6, random 59.7)

| Method | Ranking gain | Best-of-n gain |
|---|---|---|
| Reason first | -0.9 [-1.8, -0.1] | -1.8 [-2.9, -0.7] |
| Stretch ×4 | +2.2 [+1.8, +2.6] | +2.3 [+1.6, +3.0] |
| Stretch ×11 | +4.3 [+3.5, +5.0] | +4.2 [+3.1, +5.3] |
| Direction | +9.8 [+8.0, +11.5] | +8.9 [+7.1, +10.7] |
| Verdict + direction | +6.5 [+5.5, +7.5] | +6.4 [+5.2, +7.8] |
| Reason first + direction | +6.3 [+5.1, +7.5] | +5.7 [+4.2, +7.3] |

## sm|bbeh|qwen3.5-4b (6 judges; verdict ranking 53.6, verdict best-of-n 50.3, random 47.5)

| Method | Ranking gain | Best-of-n gain |
|---|---|---|
| Reason first | -0.5 [-1.8, +0.8] | -1.1 [-2.9, +0.6] |
| Stretch ×4 | +1.1 [+0.5, +1.7] | +1.3 [+0.5, +2.1] |
| Stretch ×11 | +0.6 [-0.5, +1.7] | +1.4 [-0.1, +2.9] |
| Direction | +2.9 [+0.7, +5.2] | +1.9 [-0.7, +4.4] |
| Verdict + direction | +2.0 [+0.6, +3.4] | +1.8 [+0.3, +3.4] |
| Reason first + direction | +1.6 [-0.2, +3.4] | +0.7 [-1.6, +2.9] |

## sm|math|olmo2-7b (5 judges; verdict ranking 59.9, verdict best-of-n 47.1, random 36.0)

| Method | Ranking gain | Best-of-n gain |
|---|---|---|
| Reason first | -1.5 [-4.1, +1.0] | -1.5 [-5.7, +2.7] |
| Stretch ×4 | -0.3 [-1.2, +0.7] | -1.2 [-3.0, +0.5] |
| Stretch ×11 | -1.2 [-2.8, +0.5] | -1.9 [-5.3, +1.6] |
| Direction | -4.1 [-7.4, -0.7] | -4.5 [-9.9, +0.8] |
| Verdict + direction | -1.4 [-3.5, +0.6] | -2.9 [-6.2, +0.4] |
| Reason first + direction | -1.6 [-3.9, +0.8] | -2.3 [-7.0, +2.4] |

## sm|math|qwen3.5-4b (5 judges; verdict ranking 58.3, verdict best-of-n 63.6, random 56.3)

| Method | Ranking gain | Best-of-n gain |
|---|---|---|
| Reason first | -1.5 [-3.0, -0.0] | -3.8 [-6.3, -1.2] |
| Stretch ×4 | +2.2 [+1.2, +3.2] | +1.0 [-0.7, +2.7] |
| Stretch ×11 | +0.3 [-1.4, +2.2] | +0.3 [-2.6, +3.0] |
| Direction | +2.4 [-0.0, +4.8] | +0.2 [-3.3, +3.7] |
| Verdict + direction | +2.6 [+1.1, +4.0] | +0.8 [-1.4, +3.3] |
| Reason first + direction | +0.7 [-1.4, +2.9] | -0.6 [-3.6, +2.5] |

## sm|mmlu|olmo2-7b (4 judges; verdict ranking 50.8, verdict best-of-n 41.7, random 43.2)

| Method | Ranking gain | Best-of-n gain |
|---|---|---|
| Reason first | +1.9 [-0.0, +3.9] | +3.1 [+0.1, +6.0] |
| Stretch ×4 | +0.2 [-0.4, +0.9] | +0.8 [-0.5, +2.1] |
| Stretch ×11 | -0.1 [-1.5, +1.3] | -1.2 [-3.5, +1.1] |
| Direction | +0.5 [-2.2, +3.3] | +1.0 [-2.6, +4.7] |
| Verdict + direction | +0.9 [-0.7, +2.7] | +0.4 [-2.1, +3.1] |
| Reason first + direction | +1.5 [-0.6, +3.7] | +0.8 [-2.2, +4.0] |

## sm|mmlu|qwen3.5-4b (4 judges; verdict ranking 46.5, verdict best-of-n 44.4, random 48.2)

| Method | Ranking gain | Best-of-n gain |
|---|---|---|
| Reason first | +1.9 [+0.3, +3.5] | +2.3 [-0.8, +5.5] |
| Stretch ×4 | +0.3 [-0.5, +1.1] | -1.0 [-2.7, +0.8] |
| Stretch ×11 | +0.0 [-1.6, +1.6] | -1.3 [-4.0, +1.2] |
| Direction | +1.9 [-1.1, +5.1] | -0.2 [-4.3, +3.9] |
| Verdict + direction | +0.4 [-1.5, +2.3] | -2.0 [-4.7, +0.7] |
| Reason first + direction | +1.1 [-1.2, +3.4] | -0.8 [-4.0, +2.3] |

## Per set

| Set | Questions | Verdict | Reason first | Stretch ×4 | Stretch ×11 | Direction | Verdict + direction | Reason first + direction |
|---|---|---|---|---|---|---|---|---|
| pool: llama3.1-8b|mmlu | 921 | 51.1 | 52.6 | 54.8 | 58.0 | 63.7 | 59.0 | 60.2 |
| pool: llama3.2-3b|mmlu | 921 | 51.7 | 46.5 | – | 55.8 | 63.4 | 59.8 | 56.1 |
| pool: phi4-mini|mmlu | 921 | 55.0 | 52.7 | 56.6 | 58.9 | 61.1 | 59.8 | 59.0 |
| pool: mistral-7b|mmlu | 922 | 51.5 | 51.3 | 51.1 | 50.8 | 59.1 | 56.0 | 56.8 |
| pool: granite3.3-8b|mmlu | 921 | 55.4 | 51.6 | 57.3 | 57.2 | 61.9 | 59.2 | 58.9 |
| pool: llama3.2-1b|mmlu | 921 | 49.6 | 50.9 | 49.9 | 55.0 | 59.6 | 58.8 | 57.8 |
| pool: qwen2.5-7b|mmlu | 921 | 51.8 | 50.0 | 53.7 | 54.3 | 62.2 | 58.7 | 58.8 |
| pool: llama3.1-70b|mmlu | 922 | 65.0 | 62.6 | 65.6 | 64.9 | 66.8 | 65.7 | 66.0 |
| pool: llama3.1-8b|math | 600 | 54.3 | 53.0 | – | 62.5 | 66.4 | 62.5 | 63.1 |
| pool: llama3.2-3b|math | 594 | 53.5 | 52.3 | 60.0 | 59.8 | 65.1 | 60.6 | 59.5 |
| pool: phi4-mini|math | 594 | 55.9 | 56.2 | 57.6 | 62.1 | 68.7 | 63.3 | 62.5 |
| pool: mistral-7b|math | 601 | 53.4 | 53.1 | 54.6 | 55.5 | 57.8 | 56.0 | 55.9 |
| pool: llama3.2-1b|math | 594 | 51.3 | 52.5 | 55.0 | 59.1 | 64.3 | 58.6 | 58.6 |
| pool: llama3.1-70b|math | 600 | 61.8 | 62.5 | 63.6 | 62.3 | 66.3 | 64.4 | 65.7 |
| pool: llama3.1-8b|bbeh | 229 | 55.1 | 50.8 | 57.1 | 61.8 | 66.3 | 61.2 | 60.2 |
| pool: llama3.2-3b|bbeh | 229 | 50.9 | 51.4 | 53.1 | 55.6 | 60.9 | 56.6 | 61.3 |
| pool: qwen3.5-4b|bbeh | 229 | 59.5 | 63.9 | 63.0 | 64.7 | 68.7 | 65.6 | 69.4 |
| pool: phi4-mini|bbeh | 229 | 52.0 | 46.9 | 51.8 | 56.0 | 62.7 | 59.3 | 56.9 |
| pool: granite3.3-8b|bbeh | 229 | 58.8 | 53.1 | 64.4 | 65.1 | 66.2 | 65.3 | 62.0 |
| pool: llama3.2-1b|bbeh | 229 | 49.2 | 52.4 | 50.5 | 47.7 | 57.1 | 56.1 | 56.4 |
| pool: qwen2.5-7b|bbeh | 229 | 53.2 | 54.6 | 54.0 | 54.2 | 63.4 | 60.1 | 60.2 |
| pool: llama3.1-70b|bbeh | 229 | 58.6 | 57.9 | 59.6 | 60.0 | 64.6 | 63.1 | 62.6 |
| pool_unsolved: llama3.1-8b|mmlu | 512 | 47.8 | 50.4 | 51.2 | 53.8 | 58.4 | 55.0 | 55.0 |
| pool_unsolved: llama3.2-3b|mmlu | 597 | 49.0 | 45.1 | – | 53.0 | 61.9 | 57.3 | 54.4 |
| pool_unsolved: phi4-mini|mmlu | 508 | 49.4 | 47.5 | 50.4 | 53.0 | 55.4 | 53.3 | 53.2 |
| pool_unsolved: mistral-7b|mmlu | 567 | 47.9 | 47.3 | 47.3 | 46.8 | 56.1 | 52.2 | 52.9 |
| pool_unsolved: granite3.3-8b|mmlu | 513 | 48.9 | 48.0 | 50.1 | 49.9 | 55.5 | 52.1 | 52.0 |
| pool_unsolved: llama3.2-1b|mmlu | 682 | 49.3 | 50.9 | 49.7 | 54.0 | 59.1 | 58.3 | 57.6 |
| pool_unsolved: qwen2.5-7b|mmlu | 480 | 45.9 | 46.5 | 47.1 | 47.3 | 55.5 | 50.4 | 51.9 |
| pool_unsolved: llama3.1-70b|mmlu | 313 | 48.9 | 46.5 | 49.2 | 48.5 | 50.0 | 49.0 | 49.6 |
| pool_unsolved: llama3.1-8b|math | 517 | 52.6 | 52.3 | – | 61.7 | 66.0 | 61.4 | 62.4 |
| pool_unsolved: llama3.2-3b|math | 536 | 53.1 | 51.6 | 59.6 | 59.1 | 64.8 | 60.0 | 59.2 |
| pool_unsolved: phi4-mini|math | 474 | 54.4 | 55.3 | 56.5 | 61.2 | 68.6 | 62.8 | 62.7 |
| pool_unsolved: mistral-7b|math | 583 | 53.4 | 53.1 | 54.6 | 55.7 | 58.1 | 56.3 | 56.1 |
| pool_unsolved: llama3.2-1b|math | 579 | 50.9 | 52.2 | 54.8 | 59.1 | 64.4 | 58.4 | 58.5 |
| pool_unsolved: llama3.1-70b|math | 420 | 57.8 | 59.9 | 60.8 | 59.3 | 64.8 | 61.8 | 63.5 |
| pool_unsolved: llama3.1-8b|bbeh | 188 | 52.5 | 49.4 | 54.6 | 60.2 | 65.1 | 60.0 | 59.1 |
| pool_unsolved: llama3.2-3b|bbeh | 211 | 51.0 | 50.9 | 54.4 | 56.3 | 60.9 | 57.6 | 61.6 |
| pool_unsolved: qwen3.5-4b|bbeh | 128 | 48.7 | 54.2 | 51.8 | 52.6 | 59.1 | 54.8 | 58.7 |
| pool_unsolved: phi4-mini|bbeh | 213 | 51.2 | 47.0 | 51.1 | 55.7 | 62.6 | 58.8 | 56.0 |
| pool_unsolved: granite3.3-8b|bbeh | 211 | 58.6 | 53.9 | 64.3 | 64.9 | 65.9 | 64.8 | 61.9 |
| pool_unsolved: llama3.2-1b|bbeh | 217 | 49.8 | 52.4 | 50.9 | 48.0 | 56.1 | 55.7 | 56.3 |
| pool_unsolved: qwen2.5-7b|bbeh | 199 | 50.8 | 53.9 | 51.6 | 51.9 | 63.8 | 59.9 | 60.3 |
| pool_unsolved: llama3.1-70b|bbeh | 192 | 57.7 | 56.3 | 58.9 | 58.9 | 66.1 | 62.9 | 61.5 |
| sm: granite3.3-8b|bbeh|qwen3.5-4b | 335 | 50.5 | 51.3 | 53.5 | 53.9 | 56.0 | 54.6 | 54.4 |
| sm: granite3.3-8b|mmlu|qwen3.5-4b | 271 | 44.9 | 48.6 | 44.3 | 45.1 | 46.3 | 44.9 | 45.4 |
| sm: llama3.1-70b|bbeh|qwen3.5-4b | 311 | 55.2 | 58.0 | 56.1 | 54.7 | 56.1 | 57.8 | 56.6 |
| sm: llama3.1-70b|math|qwen3.5-4b | 280 | 62.9 | 63.3 | 63.7 | 63.1 | 64.0 | 64.6 | 63.8 |
| sm: llama3.1-70b|mmlu|qwen3.5-4b | 183 | 49.4 | 50.4 | 49.5 | 46.0 | 48.9 | 49.8 | 48.5 |
| sm: llama3.1-8b|bbeh|qwen3.5-4b | 303 | 54.3 | 50.1 | 54.6 | 55.4 | 55.7 | 56.6 | 53.6 |
| sm: llama3.1-8b|math|qwen3.5-4b | 350 | 58.3 | 57.4 | 62.0 | 62.2 | 60.5 | 61.8 | 60.3 |
| sm: llama3.1-8b|mmlu|qwen3.5-4b | 401 | 47.5 | 50.3 | 47.8 | 47.5 | 51.0 | 47.4 | 49.5 |
| sm: llama3.2-1b|bbeh|qwen3.5-4b | 350 | 53.7 | 53.5 | 54.2 | 49.8 | 55.3 | 54.3 | 54.9 |
| sm: llama3.2-1b|math|qwen3.5-4b | 340 | 56.2 | 54.4 | 58.3 | 59.9 | 61.8 | 59.9 | 58.8 |
| sm: llama3.2-1b|mmlu|qwen3.5-4b | 318 | 50.0 | 49.8 | 49.9 | 48.1 | 50.5 | 50.0 | 50.3 |
| sm: llama3.2-3b|bbeh|qwen3.5-4b | 341 | 53.2 | 54.1 | 55.5 | 54.5 | 55.6 | 54.9 | 55.3 |
| sm: llama3.2-3b|math|qwen3.5-4b | 327 | 62.7 | 58.8 | 65.3 | 59.4 | 61.3 | 65.3 | 60.5 |
| sm: mistral-7b|math|qwen3.5-4b | 340 | 55.8 | 55.6 | 56.4 | 55.2 | 58.2 | 57.8 | 57.4 |
| sm: phi4-mini|bbeh|qwen3.5-4b | 343 | 55.7 | 53.8 | 55.9 | 56.6 | 58.7 | 57.3 | 55.4 |
| sm: phi4-mini|math|qwen3.5-4b | 307 | 58.5 | 57.7 | 60.2 | 56.4 | 61.5 | 59.5 | 58.1 |
| sm: phi4-mini|mmlu|qwen3.5-4b | 269 | 43.6 | 45.0 | 45.2 | 45.3 | 45.8 | 45.2 | 45.0 |
| sm: qwen3.5-4b|bbeh|qwen3.5-4b | 210 | 54.4 | 56.2 | 54.8 | 55.2 | 57.9 | 56.2 | 57.8 |
| sm: granite3.3-8b|mmlu|olmo2-7b | 193 | 47.7 | 50.4 | 48.8 | 48.7 | 50.6 | 49.1 | 50.8 |
| sm: llama3.1-70b|math|olmo2-7b | 89 | 62.6 | 62.8 | 62.6 | 58.9 | 64.4 | 63.3 | 63.1 |
| sm: llama3.1-70b|mmlu|olmo2-7b | 129 | 50.6 | 46.2 | 49.4 | 48.7 | 50.5 | 49.9 | 47.2 |
| sm: llama3.1-8b|math|olmo2-7b | 154 | 58.9 | 60.5 | 58.6 | 57.9 | 58.9 | 59.0 | 61.9 |
| sm: llama3.1-8b|mmlu|olmo2-7b | 305 | 53.3 | 52.7 | 53.5 | 53.9 | 53.3 | 53.6 | 54.3 |
| sm: llama3.2-1b|math|olmo2-7b | 150 | 54.8 | 54.6 | 54.4 | 54.3 | 53.3 | 52.5 | 54.3 |
| sm: llama3.2-1b|mmlu|olmo2-7b | 241 | 51.5 | 54.6 | 51.1 | 49.5 | 49.3 | 51.9 | 52.1 |
| sm: llama3.2-3b|math|olmo2-7b | 132 | 60.5 | 58.4 | 60.2 | 60.0 | 56.8 | 60.1 | 59.5 |
| sm: mistral-7b|math|olmo2-7b | 142 | 58.2 | 57.0 | 58.6 | 56.6 | 56.3 | 57.9 | 57.2 |
| sm: phi4-mini|math|olmo2-7b | 102 | 67.0 | 61.4 | 66.0 | 64.7 | 53.3 | 62.7 | 58.6 |
| sm: phi4-mini|mmlu|olmo2-7b | 198 | 50.5 | 53.0 | 50.5 | 50.8 | 51.9 | 52.2 | 52.1 |
| sm: llama3.1-8b|math|qwen3.5-4b strict | 255 | 56.8 | 56.5 | 61.6 | 61.8 | 59.9 | 61.6 | 59.8 |