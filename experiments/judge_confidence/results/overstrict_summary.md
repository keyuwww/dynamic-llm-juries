# Over-strict judges: correct answers rejected with all 5 samples, even with the reference

61 cases (judge × answer) on 33 answers that all experts marked correct. Rejected by 1/2/3 judges: {1: 16, 2: 6, 3: 11}.

## Why the judge rejected it (coded by Nemotron-3 Super 120B)

| Reason | Cases | Objection valid | Partly | Invalid |
|---|---|---|---|---|
| ANSWER_FLAW | 47 | 47 | 0 | 0 |
| OMISSION | 13 | 13 | 0 | 0 |
| FORMAT_OR_EXTRA | 1 | 1 | 0 | 0 |

Answers rejected by all three judges (11): coder says objection valid 33, partly 0, invalid 0 (over judge × answer cases).

## Would a cheap signal flag these false rejections?

- **Vote share:** of 92 majority rejections of correct answers (all judges), 61 (66%) are unanimous, so a 'samples disagree' trigger can catch at most 34% of them.
- **Same judge without the reference:** accepts (vote ≥ 0.5) in 3 of 61 cases, so the strictness is not caused by the reference.

**Second judge disagrees (with the reference).** Catch = share of judge A's confident false rejections where judge B says CORRECT (majority). Escalated = share of ALL unanimous-label answers where A and B disagree. Lost = share of A's correct rejections of wrong answers where B says CORRECT (would be escalated too, so these cost a review but are not lost if a human resolves them).

| Judge A | Judge B | A's false rejections | Caught by B | Escalated (all answers) |
|---|---|---|---|---|
| deepseek-v3.1 | gpt-oss-120b | 17 | 1 (6%) | 5% |
| deepseek-v3.1 | qwen3.6-35b-a3b | 17 | 1 (6%) | 9% |
| gpt-oss-120b | deepseek-v3.1 | 14 | 2 (14%) | 5% |
| gpt-oss-120b | qwen3.6-35b-a3b | 14 | 0 (0%) | 9% |
| qwen3.6-35b-a3b | deepseek-v3.1 | 30 | 13 (43%) | 9% |
| qwen3.6-35b-a3b | gpt-oss-120b | 30 | 13 (43%) | 9% |

## Blind check (coder does not see the judge's reasoning)

Same coder, shown only the question, the reference and the answer. Control = correct answers all three judges accepted.

| Group | Answers | Conclusion matches reference | Partly | No | Substantive error found |
|---|---|---|---|---|---|
| rejected by ≥1 judge | 33 | 6 | 19 | 8 | 25 (76%) |
| rejected by all 3 judges | 11 | 0 | 6 | 5 | 11 (100%) |
| accepted by all 3 (control) | 33 | 24 | 7 | 2 | 2 (6%) |

## Examples (coder's explanation)

- **gpt-oss-120b / 3449e3bf-t1 (qwen2.5-7b)**: ANSWER_FLAW, objection valid. The answer incorrectly attributes the Pecking Order Theory to Myron S. Miller and Ferris J.文明 (Fama) instead of Stewart C. Myers and Nicholas Majluf, which is a substantive factual error about the theory's origin.
- **gpt-oss-120b / 02c3d722-t1 (llama-3.3-70b)**: ANSWER_FLAW, objection valid. The assistant incorrectly states that the maintenance margin is a fixed $60,000 (30% of the original $200,000), when in fact it is 30% of the current market value of the shares, which changes as the stock price fluctuates.
- **gpt-oss-120b / 5a0bade4-t2 (gemma-2-2b)**: OMISSION, objection valid. The answer omits key IFRS consolidation requirements such as eliminating the parent's investment and equity in the subsidiary, eliminating all intra-group assets, liabilities, equity, income and expenses, accounting for the subsidiary from the date control is obtained, and the rule that parent and subsidiaries must have the same reporting date (or a three-month-max lag with adjustments).
- **gpt-oss-120b / 00098cc2-t1 (gemma-2-2b)**: OMISSION, objection valid. The assistant's answer fails to mention that the EV tax credit is non-refundable, which is the key point in the expert reference answer that prevents the credit from creating a negative tax liability and limits the refund to the amount withheld.
- **gpt-oss-120b / 4af225fc-t2 (gemma-2-2b)**: ANSWER_FLAW, objection valid. The assistant incorrectly concluded the Fund is a defined contribution plan, but the reference answer correctly identifies it as a defined benefit plan due to Matt's constructive obligation to maintain the Fund based on his history of generous benefits and reputation, which creates an expectation of continued support regardless of its voluntary or cancellable nature.
- **gpt-oss-120b / 26e1e853-t1 (gemma-2-2b)**: ANSWER_FLAW, objection valid. The assistant incorrectly defines deferred tax liability/asset as the difference between tax and accounting depreciation expenses, rather than the temporary difference between carrying amount and tax base multiplied by the tax rate, which is a substantive error in the calculation method.
- **gpt-oss-120b / 0d9e517a-t2 (yi1.5-34b-16k)**: OMISSION, objection valid. The answer failed to subtract preferred dividends from net income when calculating both basic and diluted EPS, and incorrectly calculated shares from options exercise instead of using the treasury stock method (options proceeds / average share price).
- **gpt-oss-120b / 07415e4d-t1 (gemma-2-2b)**: ANSWER_FLAW, objection valid. The answer incorrectly states that FRS 102 uses only a historical cost model and that IFRS 9’s expected credit loss model is the same as CECL (a US GAAP concept), and falsely claims FRS 102 is a precursor to IFRS 9, which misrepresents their relationship and core measurement approaches.
- **qwen3.6-35b-a3b / 02c3d722-t1 (llama-3.3-70b)**: ANSWER_FLAW, objection valid. The assistant incorrectly treats the maintenance margin as a fixed dollar amount based on the initial stock value, when it must be recalculated as 30% of the current market value; this leads to a flawed understanding of when a margin call is triggered.
- **gpt-oss-120b / c30b3282-t1 (gemma-2-2b)**: OMISSION, objection valid. The answer omits key points from the reference: that FRS 105 does not permit fair value for PPE, intangibles, or investment properties, and that accounting policy choices in FRS 102 (e.g., expensing borrowing and development costs) are removed in FRS 105.
- **gpt-oss-120b / 5749d391-t2 (qwen2.5-7b)**: ANSWER_FLAW, objection valid. The assistant incorrectly calculated the intrinsic value of the $100-strike put as $20 when the underlying is $120; a put is only valuable when the underlying is below the strike, so its intrinsic value is max(0, strike - spot) = max(0, 100 - 120) = 0, not $20.
- **qwen3.6-35b-a3b / 00098cc2-t1 (gemma-2-2b)**: ANSWER_FLAW, objection valid. The assistant incorrectly concluded that Bob owes $1,750 after applying the credit, failing to recognize that the credit is non-refundable and that Bob's $5,100 withholding would result in a refund, not additional tax owed.
