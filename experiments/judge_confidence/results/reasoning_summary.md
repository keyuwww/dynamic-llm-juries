# How judges reason when they are confidently wrong (real BFF, no reference)

Coder: Nemotron-3 Super 120B, blind to the label and to whether the judge was right. Control = an equal number of confident correct verdicts per judge and expert label. Rows split by what the judge said.

## Judge said CORRECT (missed errors vs correct accepts)

| Group | n | Recomputed | Checked inputs | Named an issue | Hedged | Median tokens |
|---|---|---|---|---|---|---|
| confident error | 73 | 42% | 93% | 4% | 0% | 214 |
| confident correct | 88 | 41% | 70% | 2% | 1% | 156 |

Focus of the reasoning:

- confident error: final_answer 42, method 22, numbers 6, definitions 3
- confident correct: final_answer 44, definitions 18, method 17, completeness 6, numbers 3

## Judge said INCORRECT (false rejections vs correct rejections)

| Group | n | Recomputed | Checked inputs | Named an issue | Hedged | Median tokens |
|---|---|---|---|---|---|---|
| confident error | 88 | 26% | 94% | 99% | 0% | 363 |
| confident correct | 73 | 55% | 95% | 97% | 1% | 418 |

Focus of the reasoning:

- confident error: definitions 42, method 32, numbers 6, final_answer 6, completeness 2
- confident correct: method 52, numbers 13, completeness 6, final_answer 2

Coder cost $0.13.
