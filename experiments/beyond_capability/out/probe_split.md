| Judge | Benchmark | Questions | n | pairs | spoken verdict: within-Q AUROC | probe: within-Q AUROC | spoken: balanced acc | probe: balanced acc (same leniency) |
|---|---|---|---|---|---|---|---|---|
| qwen3.5-4b | BBEH (layer 25) | solved | 220 | 50 | 0.62 | 0.68 | 0.63 | 0.60 |
| qwen3.5-4b | BBEH (layer 25) | unsolved | 330 | 57 | 0.53 | 0.58 | 0.47 | 0.66 |
| qwen3.5-4b | RB2 Math (layer 32) | solved | 624 | 468 | 0.79 | 0.86 | 0.79 | 0.77 |
| qwen3.5-4b | RB2 Math (layer 32) | unsolved | 104 | 78 | 0.73 | 0.79 | 0.73 | 0.63 |
| qwen3.5-4b | JudgeBench (layer 22) | solved | 361 | 32508 | 0.75 (verdict at A) | 0.70 | 0.68 | 0.64 |
| qwen3.5-4b | JudgeBench (layer 22) | unsolved | 186 | 8288 | 0.64 (verdict at A) | 0.63 | 0.59 | 0.60 |
| qwen3.5-9b | BBEH (layer 19) | solved | 291 | 75 | 0.73 | 0.68 | 0.72 | 0.60 |
| qwen3.5-9b | BBEH (layer 19) | unsolved | 273 | 37 | 0.47 | 0.54 | 0.51 | 0.69 |
| qwen3.5-9b | RB2 Math (layer 31) | solved | 612 | 459 | 0.83 | 0.87 | 0.83 | 0.78 |
| qwen3.5-9b | RB2 Math (layer 31) | unsolved | 116 | 87 | 0.72 | 0.85 | 0.72 | 0.71 |
| qwen3.5-9b | JudgeBench (layer 28) | solved | 437 | 47190 | 0.76 (verdict at A) | 0.72 | 0.67 | 0.65 |
| qwen3.5-9b | JudgeBench (layer 28) | unsolved | 110 | 3009 | 0.58 (verdict at A) | 0.57 | 0.58 | 0.55 |
