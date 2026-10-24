# The UNSURE option (real BFF answers)

Same judges, same 5 samples, but the prompt allows "VERDICT: UNSURE ... should be checked by a human expert". Errors = the judge's binary-prompt majority verdict vs the unanimous expert label. Escalated = share of answers sent to a human by each rule.

## No reference

| Judge | Uses UNSURE (any sample) | Majority UNSURE | Escalated by UNSURE | Errors caught by UNSURE | Escalated by split vote | Errors caught by split vote | UNSURE on expert-split answers | on clear answers |
|---|---|---|---|---|---|---|---|---|
| deepseek-v3.1 | 0% | 0% | 0% | 0% of 51 | 16% | 29% | 0% | 0% |
| gpt-oss-120b | 0% | 0% | 0% | 2% of 64 | 13% | 39% | 0% | 0% |
| qwen3.6-35b-a3b | 0% | 0% | 0% | 1% of 95 | 17% | 39% | 0% | 0% |

Accuracy on the answers the judge did decide (UNSURE prompt) vs the binary prompt on all answers:

- deepseek-v3.1: 82% vs 80%
- gpt-oss-120b: 86% vs 86%
- qwen3.6-35b-a3b: 80% vs 79%

## With reference

| Judge | Uses UNSURE (any sample) | Majority UNSURE | Escalated by UNSURE | Errors caught by UNSURE | Escalated by split vote | Errors caught by split vote | UNSURE on expert-split answers | on clear answers |
|---|---|---|---|---|---|---|---|---|
| gpt-oss-120b | 0% | 0% | 0% | 0% of 32 | 8% | 44% | 0% | 0% |
| qwen3.6-35b-a3b | 0% | 0% | 0% | 0% of 57 | 10% | 33% | 0% | 0% |

Accuracy on the answers the judge did decide (UNSURE prompt) vs the binary prompt on all answers:

- gpt-oss-120b: 93% vs 93%
- qwen3.6-35b-a3b: 87% vs 88%

Cost of the UNSURE runs: $14.70.
