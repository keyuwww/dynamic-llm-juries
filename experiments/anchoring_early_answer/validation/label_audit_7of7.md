# Label audit of the 7/7-belief wrong answers (BFF-Bench and JudgeBench)

**Auditor: Claude (an AI model, Anthropic's Claude Opus 5.5), not a human expert.** Every verdict below comes from Claude solving the question itself and comparing its answer with the benchmark label. The verdicts have not been checked by a finance expert or a domain specialist. Treat them as a careful second opinion, not ground truth.

Scope: the 55 items where at least one Qwen judge reaches the wrong-labelled answer in all 7 of its own 7 attempts ("belief 7/7"). There are 29 BFF-Bench items and 26 JudgeBench items. Per-item verdicts are in `label_audit_7of7_results.jsonl`.

Verdicts:
- **LABEL_OK**: the wrong-labelled answer really is wrong in a substantive way.
- **LABEL_WRONG**: the wrong-labelled answer is actually correct, or equivalent to the reference, so the benchmark label is wrong.
- **CONTESTED**: reasonable experts could disagree. Examples: more than one option is correct, the gold is debatable, or the answer reaches the right conclusion but has real errors in its working.

## Counts

| Bench | Items | LABEL_OK | LABEL_WRONG | CONTESTED |
|---|---:|---:|---:|---:|
| BFF-Bench | 29 | 11 (38%) | 15 (52%) | 3 (10%) |
| JudgeBench | 26 | 13 (50%) | 1 (4%) | 12 (46%) |
| **Total** | **55** | **24 (44%)** | **16 (29%)** | **15 (27%)** |

Items are not independent questions. Several BFF items are different candidate answers to the same question. For example, 7 of the 15 BFF LABEL_WRONG items come from one equipment-impairment question.

## LABEL_WRONG and CONTESTED cases

### BFF-Bench

| Item | Verdict | Wrong-labelled answer | Reference | Reason |
|---|---|---|---|---|
| 040f5fc5-t2 | LABEL_WRONG | $98.86M split 35/35/30 | $118.4M split | The reference charges the fee on pre-trading-cost AUM and skips the stated 18% tax. Applying the question's own rules gives the candidate's $98.86M. |
| 10e382d2-t2 | LABEL_WRONG | add ~$530M | add ~$536M | $530M is the exact solution. The reference plugs in the rounded WAM (255 instead of 255.22). |
| 1bd216d5-t1 | LABEL_WRONG | IFRS loss $116,550 | $134,550 | The question gives fair value $386,000. The reference uses $368,000 (digit swap). The candidate has small slips in value in use (VIU) that don't change the result. |
| 37d78983-t1 | LABEL_WRONG | IFRS loss $116,550 | $134,550 | Same digit swap in the reference. The candidate miscomputes VIU, but VIU stays below fair value less costs to sell (FVLCD), so the answer is unaffected. |
| 6a2988d1-t1 | LABEL_WRONG | IFRS loss $116,550 | $134,550 | Fully correct as the question is stated. |
| e38c46dc-t1 | LABEL_WRONG | IFRS loss $116,550 | $134,550 | Fully correct as stated. Its VIU differs from the exact figure by $16. |
| 68b7b17a-t2 | LABEL_WRONG | US GAAP loss $114,000 | $140,294 | ASC 360: the asset fails the recoverability test, so the loss is carrying amount minus fair value ($500k − $386k). The reference uses discounted cash flows in place of the quoted fair value. |
| 898bf424-t2 | LABEL_WRONG | US GAAP loss $114,000 | $140,294 | Textbook ASC 360 two-step. Same reference error. |
| c9062f23-t2 | LABEL_WRONG | US GAAP loss $114,000 | $140,294 | Textbook ASC 360 two-step. Same reference error. |
| 20c6d543-t2 | LABEL_WRONG | Yes (8.19% vs 7.62%) | Yes (10.48% vs 9.46%) | Same conclusion. With one share of each stock the portfolio is value-weighted, so the candidate's figures are right and the reference's equal weights are not. |
| dd06c3be-t2 | LABEL_WRONG | Yes ($68.75 vs $64) | Yes (10.48% vs 9.46%) | Same conclusion. Dollar returns on the same $840 base are equivalent to percentage returns. |
| f54bc9dc-t1 | LABEL_WRONG | price return 7.62% | 9.46% | The portfolio goes from $840 to $904, which is +7.62%. The reference wrongly gives the three stocks equal weights. |
| 30d09bef-t2 | LABEL_WRONG | Amazon (inventory/sales) | Amazon (turnover) | Same conclusion. Inventory-to-sales is a valid metric and the candidate computes it correctly. |
| bab23e40-t2 | LABEL_WRONG | tax shield −0.83 pp | −1.31 pp | Correct: 0.4118 × 5% × 40% = 0.82 pp. The reference uses the 8% cost of equity as the cost of debt. |
| e8c203c1-t2 | LABEL_WRONG | payback 4.78 yrs | "by end of year 5" | The exact discounted payback is 4.78 years, consistent with the reference. The reference itself has arithmetic slips. |
| 55bb3129-t2 | CONTESTED | retained earnings, then debt | same, plus cost of debt and equity | Same recommendation, but no cost-of-capital numbers and a muddled tax remark. |
| c3796724-t2 | CONTESTED | net EPS effect zero | EPS down, then up | Both answers agree on a $200k write-down and a $200k reversal. The candidate reports the net effect (zero), the reference the two separate moves. |
| f12d7cf0-t2 | CONTESTED | PNC | PNC | Right choice, but the candidate applies PNC's rate tiers wrongly and miscomputes the Chase payment. |

### JudgeBench

| Item | Verdict | Wrong-labelled choice | Gold | Reason |
|---|---|---|---|---|
| gpt-5d50e41f | LABEL_WRONG | 27 (E), written "EEEEEEE" | 27 (E), "EEEEE" | Both responses get the right answer. The "wrong" one only wrote 7 letters instead of 5. |
| claude-182a216b | CONTESTED | C (grapefruit juice price up) | F (higher expected income) | Both shift orange-juice demand right. |
| claude-2417995a | CONTESTED | B (minor role: contracts and property) | C (no government role) | Textbook definitions of pure capitalism keep a minimal role for government. |
| claude-6101a179 | CONTESTED | F (Earth not the centre) | C (infinite universe/multiverse) | F is the conclusion that actually follows from the observations. The gold overreaches. |
| claude-851b5544 | CONTESTED | C | B | B, C, D and E are all incorrect statements, but the question wants exactly one. |
| claude-c2028682 | CONTESTED | I (3 methods) | H (4 kinds) | Both lists of verbal-learning methods appear in textbooks. |
| claude-e82d2ea3 | CONTESTED | D (muscles) | J (flexible chitin joints) | Muscles drive the movement and the joints allow it. Both are defensible. |
| gpt-49c0f568 | CONTESTED | D (muscles) | J (flexible chitin joints) | Same question as above. |
| claude-f474b24e | CONTESTED | J (grapheme) | D (phoneme) | The written letter "c" is strictly a grapheme. |
| gpt-0a347026 | CONTESTED | I (128 Hz fork) | D (same tract as light touch) | D, G and I are all true. |
| gpt-5b13ebd9 | CONTESTED | D (hinders difficult tasks) | H (helps easy tasks) | Social facilitation research supports both. |
| gpt-a1b1ff8a | CONTESTED | H (lysis) | I (apoptosis) | Which mechanism is "most common" is debatable. |
| gpt-cc8d0d03 | CONTESTED | A (predicts future or past performance) | J (predicts behaviour in set situations) | A is at least as good a definition of criterion-related validity. |

## What this means for the 7/7 result

In plain terms: for the strongest cases, where a judge reaches the wrong-labelled answer in all 7 of its own attempts, only **24 of 55 (44%) are clearly wrong answers**. Another 16 (29%) look actually correct, and 15 (27%) are debatable.

**BFF-Bench:** the problem is mainly bad expert references. 15 of 29 items (52%) are answers that look right, and only 11 (38%) are clearly wrong. Most of the LABEL_WRONG cases trace to a handful of questions whose expert reference has an error:
- a digit swap in the fair value ($368k vs the stated $386k)
- discounted cash flows used where US GAAP requires fair value
- equal weights used for a one-share-each portfolio
- a missing tax step, a wrong cost of debt, and a rounded intermediate value

So a large part of the "judges approve wrong answers they believe" effect on BFF at 7/7 is the judges agreeing with answers that are actually right.

**JudgeBench:** the problem is mainly ambiguity rather than wrong gold answers. Only 1 of 26 is a real label error, and that one is a formatting slip on an otherwise correct answer. But 12 (46%) are contested, mostly because MMLU-Pro's added distractor options include a second correct or equally defensible option. Half (13 of 26) are clearly wrong.

**How to use this:** the 7/7 result should be reported only on the LABEL_OK subset (24 items), or with that subset as a robustness check. Any headline example drawn from 7/7 should be checked against this audit first. Because these verdicts come from an AI model, the LABEL_WRONG BFF cases deserve a quick look from a finance expert before they are cited as benchmark errors. They are mostly simple arithmetic or a misread input, so they should be quick to confirm.
