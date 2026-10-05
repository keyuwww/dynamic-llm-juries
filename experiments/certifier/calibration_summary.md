# Calibration check: is each judge's confidence score meaningful, or just a verdict?

Brier score (lower better) and expected calibration error (ECE, lower better) of each judge's raw p against the human/gold label.

## BFF noref (n=459)

| Judge | Brier score | ECE |
|---|---|---|
| jev | 0.165 | 0.071 |
| laya | 0.231 | 0.076 |
| jeff | 0.220 | 0.158 |
| qwen3.5-4b | 0.255 | 0.255 |
| qwen3.5-9b | 0.261 | 0.261 |
| qwen3.6-35b-a3b | 0.235 | 0.235 |
| gpt-oss-20b | 0.174 | 0.174 |
| gpt-oss-120b | 0.146 | 0.146 |
| nemotron3-nano-30b | 0.333 | 0.333 |
| nemotron3-super-120b | 0.259 | 0.259 |
| deepseek-v3.1 | 0.194 | 0.194 |

## BFF ref (n=456)

| Judge | Brier score | ECE |
|---|---|---|
| jev | 0.060 | 0.090 |
| laya | 0.231 | 0.067 |
| jeff | 0.206 | 0.230 |
| qwen3.5-4b | 0.092 | 0.092 |
| qwen3.5-9b | 0.110 | 0.110 |
| qwen3.6-35b-a3b | 0.125 | 0.125 |
| gpt-oss-20b | 0.121 | 0.121 |
| gpt-oss-120b | 0.079 | 0.079 |
| nemotron3-nano-30b | 0.208 | 0.208 |
| nemotron3-super-120b | 0.072 | 0.072 |
| deepseek-v3.1 | 0.070 | 0.070 |

## Safety (n=1800)

| Judge | Brier score | ECE |
|---|---|---|
| jev | 0.138 | 0.204 |
| laya | 0.291 | 0.290 |
| jeff | 0.233 | 0.237 |
| qwen3.5-4b | 0.268 | 0.268 |
| qwen3.5-9b | 0.214 | 0.214 |
| qwen3.6-35b-a3b | 0.274 | 0.274 |
| gpt-oss-20b | 0.153 | 0.153 |
| gpt-oss-120b | 0.221 | 0.221 |
| nemotron3-nano-30b | 0.214 | 0.214 |
| nemotron3-super-120b | 0.259 | 0.259 |
| deepseek-v3.1 | 0.271 | 0.271 |
