# BFF-Bench contamination probe

Reference completion: longest run of words the model's continuation shares with the real second half of the expert reference (`verbatim13` = share of turns with a 13+ word exact match). Masked number: share of turns where the model recovers the exact masked number from the question.

Exact recall counts any recovered number, including ones derivable from the rest of the question (totals, tax owed) or easy to guess (years, round amounts). `Specific` restricts to numbers with 3+ significant digits that are not years. Check recovered specific numbers by hand for derivability.

| Model | Ref turns | Mean longest run | Median | Share ≥13 words | Masked-number turns | Exact recall | Specific numbers | Specific recall | Cost |
|---|---|---|---|---|---|---|---|---|---|
| gpt-oss-120b | 149 | 6.2 | 5 | 0.087 | 104 | 0.394 | 21 | 0.429 | $0.244 |
| gpt-oss-20b | 149 | 4.1 | 2 | 0.047 | 104 | 0.144 | 21 | 0.190 | $0.137 |
| qwen3.5-4b | 149 | 6.1 | 4 | 0.094 | 104 | 0.298 | 21 | 0.381 | $0.154 |

## Specific numbers recovered (check whether each is derivable from the question)

| Model | Turn | Number |
|---|---|---|
| gpt-oss-120b | b7559f23-t1 | 102, |
| gpt-oss-120b | b7559f23-t2 | 102 |
| gpt-oss-120b | 0e7c0684-t1 | 102 |
| gpt-oss-120b | 9be15d66-t1 | 42,237,000 |
| gpt-oss-120b | ce6d2523-t1 | 102 |
| gpt-oss-120b | 91fd499c-t1 | 102 |
| gpt-oss-120b | 1bb784ce-t2 | 1040 |
| gpt-oss-120b | c67c5f87-t1 | $5,750 |
| gpt-oss-120b | 1bb784ce-t1 | 1040 |
| gpt-oss-20b | 0e7c0684-t1 | 102 |
| gpt-oss-20b | c67c5f87-t1 | $5,750 |
| gpt-oss-20b | 1bb784ce-t1 | 1040 |
| qwen3.5-4b | b7559f23-t1 | 102, |
| gpt-oss-20b | b525b226-t1 | 61,838.1 |
| qwen3.5-4b | b7559f23-t2 | 102 |
| qwen3.5-4b | 9be15d66-t1 | 42,237,000 |
| qwen3.5-4b | ce6d2523-t1 | 102 |
| qwen3.5-4b | 91fd499c-t1 | 102 |
| qwen3.5-4b | 1bb784ce-t1 | 1040 |
| qwen3.5-4b | 1bb784ce-t2 | 1040 |
| qwen3.5-4b | b525b226-t1 | 61,838.1 |

## Longest verbatim matches

| Model | Turn | Longest run (words) |
|---|---|---|
| gpt-oss-20b | 2245e388-t1 | 41 |
| gpt-oss-120b | 2245e388-t1 | 38 |
| qwen3.5-4b | 2245e388-t1 | 38 |
| gpt-oss-120b | c104f63a-t2 | 30 |
| gpt-oss-120b | 97d2048d-t2 | 28 |
| qwen3.5-4b | 2acf7cbd-t2 | 27 |
| gpt-oss-20b | 51de7010-t1 | 26 |
| qwen3.5-4b | 51de7010-t1 | 26 |
| gpt-oss-120b | 51de7010-t1 | 25 |
| gpt-oss-120b | 2acf7cbd-t2 | 25 |
