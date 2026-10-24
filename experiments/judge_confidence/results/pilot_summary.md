# Error-injection pilot: verdicts and confidence

4234 judge requests, 21170 samples, $12.75.

Detection = share of samples with verdict INCORRECT. For ORIG/C1/C2 the answer is still correct, so detection there is a false alarm. P(CORRECT) = probability on the verdict word, averaged over samples. Confident = all 5 samples agree.

| Judge | Reference | Text | n | Detected (INCORRECT) | Mean P(CORRECT) | All 5 say CORRECT | P read for |
|---|---|---|---|---|---|---|---|
| deepseek-v3.1 | human | ORIG | 58 | 0.07 | 0.93 | 0.86 | 100% |
| deepseek-v3.1 | human | C2 | 50 | 0.07 | 0.93 | 0.86 | 100% |
| deepseek-v3.1 | human | C1 | 12 | 0.03 | 0.97 | 0.83 | 100% |
| deepseek-v3.1 | human | V1 | 30 | 0.85 | 0.15 | 0.03 | 100% |
| deepseek-v3.1 | human | V2-x10 | 15 | 0.84 | 0.16 | 0.07 | 100% |
| deepseek-v3.1 | human | V2-10 | 21 | 0.93 | 0.07 | 0.05 | 100% |
| deepseek-v3.1 | human | V2-lead | 21 | 0.81 | 0.19 | 0.14 | 100% |
| deepseek-v3.1 | human | V2-1 | 22 | 0.81 | 0.19 | 0.00 | 100% |
| deepseek-v3.1 | none | ORIG | 58 | 0.12 | 0.88 | 0.84 | 100% |
| deepseek-v3.1 | none | C2 | 50 | 0.14 | 0.86 | 0.80 | 100% |
| deepseek-v3.1 | none | C1 | 12 | 0.15 | 0.85 | 0.83 | 100% |
| deepseek-v3.1 | none | V1 | 30 | 0.73 | 0.27 | 0.13 | 100% |
| deepseek-v3.1 | none | V2-x10 | 15 | 0.96 | 0.04 | 0.00 | 100% |
| deepseek-v3.1 | none | V2-10 | 21 | 1.00 | 0.00 | 0.00 | 100% |
| deepseek-v3.1 | none | V2-lead | 21 | 0.90 | 0.10 | 0.05 | 100% |
| deepseek-v3.1 | none | V2-1 | 22 | 0.93 | 0.07 | 0.00 | 100% |
| gpt-oss-120b | human | ORIG | 248 | 0.09 | 0.91 | 0.85 | 100% |
| gpt-oss-120b | human | C2 | 223 | 0.10 | 0.90 | 0.86 | 100% |
| gpt-oss-120b | human | C1 | 52 | 0.06 | 0.94 | 0.88 | 100% |
| gpt-oss-120b | human | V1 | 125 | 0.94 | 0.06 | 0.02 | 100% |
| gpt-oss-120b | human | V2-x10 | 50 | 0.86 | 0.14 | 0.02 | 100% |
| gpt-oss-120b | human | V2-10 | 84 | 0.94 | 0.06 | 0.02 | 100% |
| gpt-oss-120b | human | V2-lead | 76 | 0.89 | 0.11 | 0.01 | 100% |
| gpt-oss-120b | human | V2-1 | 86 | 0.74 | 0.26 | 0.12 | 100% |
| gpt-oss-120b | none | ORIG | 248 | 0.13 | 0.87 | 0.81 | 100% |
| gpt-oss-120b | none | C2 | 223 | 0.13 | 0.87 | 0.82 | 100% |
| gpt-oss-120b | none | C1 | 52 | 0.08 | 0.92 | 0.85 | 100% |
| gpt-oss-120b | none | V1 | 125 | 0.95 | 0.05 | 0.02 | 100% |
| gpt-oss-120b | none | V2-x10 | 50 | 0.89 | 0.11 | 0.02 | 100% |
| gpt-oss-120b | none | V2-10 | 84 | 0.94 | 0.06 | 0.01 | 100% |
| gpt-oss-120b | none | V2-lead | 76 | 0.92 | 0.08 | 0.03 | 100% |
| gpt-oss-120b | none | V2-1 | 86 | 0.78 | 0.22 | 0.09 | 100% |
| qwen3.6-35b-a3b | human | ORIG | 248 | 0.16 | 0.84 | 0.77 | 100% |
| qwen3.6-35b-a3b | human | C2 | 223 | 0.18 | 0.82 | 0.75 | 100% |
| qwen3.6-35b-a3b | human | C1 | 52 | 0.12 | 0.88 | 0.77 | 100% |
| qwen3.6-35b-a3b | human | V1 | 125 | 0.94 | 0.06 | 0.02 | 100% |
| qwen3.6-35b-a3b | human | V2-x10 | 50 | 0.92 | 0.08 | 0.02 | 100% |
| qwen3.6-35b-a3b | human | V2-10 | 84 | 0.97 | 0.03 | 0.00 | 100% |
| qwen3.6-35b-a3b | human | V2-lead | 76 | 0.93 | 0.07 | 0.01 | 100% |
| qwen3.6-35b-a3b | human | V2-1 | 86 | 0.85 | 0.15 | 0.08 | 100% |
| qwen3.6-35b-a3b | none | ORIG | 248 | 0.24 | 0.76 | 0.65 | 100% |
| qwen3.6-35b-a3b | none | C2 | 223 | 0.25 | 0.75 | 0.64 | 100% |
| qwen3.6-35b-a3b | none | C1 | 52 | 0.23 | 0.77 | 0.58 | 100% |
| qwen3.6-35b-a3b | none | V1 | 125 | 0.94 | 0.06 | 0.01 | 100% |
| qwen3.6-35b-a3b | none | V2-x10 | 50 | 0.96 | 0.04 | 0.00 | 100% |
| qwen3.6-35b-a3b | none | V2-10 | 84 | 0.99 | 0.01 | 0.00 | 100% |
| qwen3.6-35b-a3b | none | V2-lead | 76 | 0.93 | 0.07 | 0.03 | 100% |
| qwen3.6-35b-a3b | none | V2-1 | 86 | 0.91 | 0.09 | 0.03 | 100% |
