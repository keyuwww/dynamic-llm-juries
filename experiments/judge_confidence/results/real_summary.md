# Real BFF answers: verdicts and confidence

4248 requests, $18.63. Gold = unanimous label; 'split' = annotators disagreed. Confident = all 5 samples agree.

| Judge | Ref | Gold | n | Says INCORRECT | All 5 agree | Confidently wrong (all 5 agree, wrong) |
|---|---|---|---|---|---|---|
| deepseek-v3.1 | human | correct | 255 | 0.10 | 0.94 | 0.07 |
| deepseek-v3.1 | human | incorrect | 201 | 0.94 | 0.89 | 0.01 |
| deepseek-v3.1 | none | correct | 256 | 0.14 | 0.88 | 0.10 |
| deepseek-v3.1 | none | incorrect | 203 | 0.72 | 0.80 | 0.19 |
| deepseek-v3.1 | none | split | 501 | 0.43 | 0.78 |  |
| gpt-oss-120b | human | correct | 255 | 0.10 | 0.91 | 0.05 |
| gpt-oss-120b | human | incorrect | 201 | 0.96 | 0.93 | 0.02 |
| gpt-oss-120b | none | correct | 256 | 0.13 | 0.89 | 0.08 |
| gpt-oss-120b | none | incorrect | 203 | 0.84 | 0.85 | 0.09 |
| gpt-oss-120b | none | split | 501 | 0.49 | 0.79 |  |
| qwen3.6-35b-a3b | human | correct | 255 | 0.18 | 0.86 | 0.12 |
| qwen3.6-35b-a3b | human | incorrect | 201 | 0.93 | 0.94 | 0.04 |
| qwen3.6-35b-a3b | none | correct | 256 | 0.25 | 0.81 | 0.16 |
| qwen3.6-35b-a3b | none | incorrect | 203 | 0.85 | 0.85 | 0.08 |
| qwen3.6-35b-a3b | none | split | 501 | 0.62 | 0.79 |  |
