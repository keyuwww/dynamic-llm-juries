# Error-injection pilot: verdicts and confidence

1374 judge requests, 6870 samples, $4.77.

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
| gpt-oss-120b | human | ORIG | 58 | 0.08 | 0.92 | 0.86 | 100% |
| gpt-oss-120b | human | C2 | 50 | 0.12 | 0.88 | 0.84 | 100% |
| gpt-oss-120b | human | C1 | 12 | 0.05 | 0.95 | 0.83 | 100% |
| gpt-oss-120b | human | V1 | 30 | 1.00 | 0.00 | 0.00 | 100% |
| gpt-oss-120b | human | V2-x10 | 15 | 0.92 | 0.08 | 0.00 | 100% |
| gpt-oss-120b | human | V2-10 | 21 | 0.97 | 0.03 | 0.00 | 100% |
| gpt-oss-120b | human | V2-lead | 21 | 0.85 | 0.15 | 0.00 | 100% |
| gpt-oss-120b | human | V2-1 | 22 | 0.88 | 0.12 | 0.05 | 100% |
| gpt-oss-120b | none | ORIG | 58 | 0.14 | 0.86 | 0.83 | 100% |
| gpt-oss-120b | none | C2 | 50 | 0.13 | 0.87 | 0.82 | 100% |
| gpt-oss-120b | none | C1 | 12 | 0.13 | 0.87 | 0.75 | 100% |
| gpt-oss-120b | none | V1 | 30 | 0.96 | 0.04 | 0.00 | 100% |
| gpt-oss-120b | none | V2-x10 | 15 | 0.89 | 0.11 | 0.00 | 100% |
| gpt-oss-120b | none | V2-10 | 21 | 0.95 | 0.05 | 0.00 | 100% |
| gpt-oss-120b | none | V2-lead | 21 | 0.88 | 0.12 | 0.05 | 100% |
| gpt-oss-120b | none | V2-1 | 22 | 0.85 | 0.15 | 0.05 | 100% |
| qwen3.6-35b-a3b | human | ORIG | 58 | 0.15 | 0.85 | 0.76 | 100% |
| qwen3.6-35b-a3b | human | C2 | 50 | 0.18 | 0.82 | 0.72 | 100% |
| qwen3.6-35b-a3b | human | C1 | 12 | 0.18 | 0.82 | 0.67 | 100% |
| qwen3.6-35b-a3b | human | V1 | 30 | 0.97 | 0.03 | 0.00 | 100% |
| qwen3.6-35b-a3b | human | V2-x10 | 15 | 0.93 | 0.07 | 0.00 | 100% |
| qwen3.6-35b-a3b | human | V2-10 | 21 | 1.00 | 0.00 | 0.00 | 100% |
| qwen3.6-35b-a3b | human | V2-lead | 21 | 0.91 | 0.09 | 0.00 | 100% |
| qwen3.6-35b-a3b | human | V2-1 | 22 | 0.94 | 0.06 | 0.00 | 100% |
| qwen3.6-35b-a3b | none | ORIG | 58 | 0.25 | 0.75 | 0.67 | 100% |
| qwen3.6-35b-a3b | none | C2 | 50 | 0.25 | 0.75 | 0.64 | 100% |
| qwen3.6-35b-a3b | none | C1 | 12 | 0.30 | 0.70 | 0.50 | 100% |
| qwen3.6-35b-a3b | none | V1 | 30 | 0.97 | 0.03 | 0.00 | 99% |
| qwen3.6-35b-a3b | none | V2-x10 | 15 | 0.99 | 0.01 | 0.00 | 100% |
| qwen3.6-35b-a3b | none | V2-10 | 21 | 0.96 | 0.04 | 0.00 | 100% |
| qwen3.6-35b-a3b | none | V2-lead | 21 | 0.86 | 0.14 | 0.05 | 100% |
| qwen3.6-35b-a3b | none | V2-1 | 22 | 0.97 | 0.03 | 0.00 | 100% |
