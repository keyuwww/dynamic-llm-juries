# Advisor questions on the BFF-Bench judge results

Answers to four questions raised about the judge-pool analysis (8 Tinker judges, condition `none` = no
reference answer unless stated). Q1 and Q3 use the stored verdicts in
`experiments/judge_decisions/results/decisions.csv` (459 unanimous-label responses). Q4 adds a rerun and
a contamination probe (2026-10-16).

## Q4 first: gpt-oss-120b's no-reference κ was inflated by our label filter

**Short answer:** about half of the gap to No Free Labels comes from which responses we score. On the same
808 responses No Free Labels uses, gpt-oss-120b's no-reference κ is **0.595**, not 0.699. That is still
above their best no-reference judge (GPT-4o, 0.47). We found no sign that gpt-oss-120b memorized
BFF-Bench.

### Check 1: gold-label rule

No Free Labels (Section 3.3, Table 1) keeps a response when at least 2 of its 3 expert votes agree on
Correct or Incorrect: 808 of 960 BFF-Bench responses. All our Tinker and Jev runs instead kept only
**unanimous** responses (459). Unanimous responses are the clear-cut ones, so they are easier to judge.

We reran gpt-oss-120b (no reference, 1 sample, max 4,096 tokens) on every response with a majority label.
The 459 unanimous verdicts were reused from the original run, and 419 responses were new (cost $0.74).
Script: `experiments/tinker_pool/compare_label_rules.py`. The CI resamples whole conversations.

| Gold-label rule | n | Accuracy | κ | κ 95% CI |
|---|---|---|---|---|
| Unanimous (our runs so far) | 459 | 0.852 | 0.699 | [0.63, 0.76] |
| **No Free Labels' 2-of-3 rule** | **808** | **0.800** | **0.595** | **[0.54, 0.65]** |
| `--consensus majority` in our code (ignores Not sure) | 878 | 0.787 | 0.570 | [0.52, 0.62] |

Agreement on the split-vote responses alone is only κ 0.46 (349 responses). These responses split the
human experts too, so a judge struggles on them as well.

Our `--consensus majority` option is **not** No Free Labels' rule. It also keeps responses such as
1 Correct + 2 Not sure, which their rule drops. Use the `nfl` rule when comparing with the paper.

### Check 2: is the remaining gap plausible?

| | No Free Labels GPT-4o | Our gpt-oss-120b |
|---|---|---|
| No-reference κ, single grading | 0.47 ± 0.05 (Table 6) | 0.595 [0.54, 0.65] |
| Benchmarks pooled | BFF-Bench + (C)MT-Bench | BFF-Bench only |
| Samples per verdict | 5 (majority vote, T = 0.7) | 1 (T = 0.7) |
| Reasoning | short chain of thought | reasoning model (always reasons) |

- **The comparison is if anything conservative toward the paper.** Their 0.47 pools in (C)MT-Bench, where
  judges score higher (Table 11). Their 5-vote majority also helps them.
- **A gap remains, and it fits a newer reasoning model.** The paper reports no per-judge BFF-only κ, so we
  can't match benchmarks exactly. Our smaller modern judges sit at or below GPT-4o on the unanimous set
  (qwen3.5-4b 0.48, qwen3.5-9b 0.49), and gpt-oss-20b is 0.66.

### Check 3: bugs, leakage, contamination

- **No reference leaks into the `none` prompt.** `build_prompt` in `run_judges.py` sets the reference
  block to empty for `none`.
- **No training on test data.** Judge κ comes from zero-shot prompting; nothing is fitted. Learned routers
  are a separate experiment.
- **Verdicts match labels correctly.** Rescoring the 459 unanimous responses through a separate join on
  VERDICTS reproduced κ 0.699 exactly. 1 of 878 verdicts was unparseable and counts as Incorrect.
- **No sign of memorization.** BFF-Bench has been public since early 2025, so we probed three judges
  (`experiments/tinker_pool/probe_contamination.py`, results in `contamination_results/`, $0.54):
  - **Reference completion:** given the question and the first half of the expert answer, continue it
    word for word. gpt-oss-120b shares a median longest run of 5 words with the real continuation.
    - 8.7% of turns reach 13+ words, the same as qwen3.5-4b (9.4%).
    - Reading the matches, they are calculation tables that repeat a layout already shown in the prefix,
      or standard IAS 12 wording, not recalled answers.
  - **Masked number:** hide one number in the question and ask for it. gpt-oss-120b recovers 39%.
    - All 9 recovered numbers with 3+ significant digits are standard names (FRS 102 ×5, Form 1040 ×2)
      or sums of other numbers in the question (2).
    - The rest are years, month-end days and round amounts. None is an unexplained recall.
  - **Limit:** no verbatim recall does not prove the model never saw the data. We had no model with a
    pre-2025 training cutoff as a clean control.

### What this changes

- **Report headline κ under the 2-of-3 rule.** Every judge's κ in our tables (Tinker pool, Jev, Jeff, CLM)
  is on the unanimous subset and likely inflated the same way.
- **Rankings may hold up, but check them.** Comparisons between judges on the same 459 responses are fair
  among themselves, though the ranking could shift on split-vote responses.
- **The other 7 Tinker judges have not been rerun on the 808.** Same command with `--models all`; most of
  the cost is DeepSeek.

## Q1: are the judges' predictions correlated?

Yes, strongly, which is why majority-vote juries don't beat gpt-oss-120b.

- **Errors overlap.** Pairwise error correlation (phi) between judges averages **0.39**, ranging from
  0.12 to 0.64.
  - gpt-oss-120b and gpt-oss-20b are the most correlated pair (0.64).
  - nemotron3-nano-30b is the least correlated with anyone (0.12–0.24), but it is also the weakest judge.
- **Responses split into "everyone right" and "everyone wrong".** 42.5% of responses are judged correctly
  by all 8 judges, against 12.8% expected if errors were independent. 9.4% are missed by 6 or more
  judges, against 0.2% expected.
- **gpt-oss-120b's errors are shared.** On its 68 errors, at least 5 of the other 7 judges are also wrong
  on 39, and on only 1 are all the others right.
- **It holds with a reference too.** With the expert reference, mean phi is 0.41.

This matches Ingrid's JudgeBench SHAP finding: no anticorrelated judge pairs, so a jury has little to
correct.

## Q2: gpt-oss-120b's accuracy on the underlying task

**Not available yet.** Phase 1 (`run_answers.py` + `grade_bff_answers.py`) was set up but never run:
`bff_results_max4096/answers.jsonl` and `grades.jsonl` are empty.

No Free Labels' proxy (Appendix J in v4) is a GPT-4o judge given the human-verified reference, which agrees
closely with the expert graders. Our closest equivalent is gpt-oss-120b or DeepSeek-V3.1 *with* the
reference (κ 0.85 on unanimous labels), or Jev with the reference (κ 0.86). It would cost about $3 for
answers plus grading.

## Q3: patterns in gpt-oss-120b's grading errors (no reference, 459 responses)

- **Errors are balanced, not one-sided.** 35 wrong answers were called correct (false-positive rate 17%)
  and 33 correct answers were called wrong (false-negative rate 13%).
- **Taxation is the weak domain.** Its error rate is 30% (9/30), against 12–15% in every other domain.
  This matches GPT-4o's weakness *answering* tax questions in our annotation analysis.
- **No dependence on whose answer is graded or on the turn.** The error rate is 12–18% for every
  examinee model, and turns 1 and 2 are the same (15%).
- **Errors cluster on a few questions.** 11 questions account for 28 of the 68 errors.
- **Annotated difficulty doesn't predict errors.** Band 2 has the highest error rate (20%) and band 5 has
  none. So the difficulty and numerical-demand scores don't explain where the judge fails.
- **With the reference, it rejects correct answers.** Errors fall to 35, but 28 of them are correct answers
  called incorrect, and 15 of the 35 are on gemma-2-2b's responses.
  - In the 6 reasoning traces we read, the judge rejected answers for small rounding differences
    ($2.59 vs the reference's $2.58) or for leaving out a point the reference makes.
  - The human experts accepted those answers, so the judge holds a stricter standard than the humans.
- **Its confidence carries no signal here.** These runs took 1 sample per verdict, so there is no vote
  share to separate confident from unsure verdicts. A 5-sample run (as in No Free Labels) would allow
  that.

The judges' reasoning text is stored in `judgments.jsonl` (`raw`), so a fuller error-coding pass is
possible.
