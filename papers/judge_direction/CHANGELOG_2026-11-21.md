# Direction paper: response to the strict re-review of November 21

What each direction-paper item in `strict_re_review_2026-11-21.md` led to. Every number in the paper comes from
`build.sh`, and the numbers below come from the same files. The belief-paper items (B1–B5) were handled in the belief
paper's own session; this change log covers only the direction paper.

New result files (all in `experiments/beyond_capability/`):

- `out_paper/primary_scope.json`: from `primary_scope_modal.py` (Modal CPU, recomputed from stored hidden states).
- `out_paper/primary_scope_check.json`: from `primary_scope_analyze.py`.
- `edit_test/`: protocol, edits, scores and results of the controlled-edit test.

## D1: the explanatory analyses now use the primary, unselected population

**Done.** Every explanatory analysis in §4.2–4.3 now uses the 12 primary pairs. These are 4 judges × 3 benchmarks,
fixed before running and including the pairs without a gap. Each analysis uses the same two folds and the same readout
layer per fold, with every fit on the training half.

- **Reproducing the primary scores.** The direction was refitted from the stored hidden states. The test scores it
  gives match the stored primary-evaluation scores: largest difference 1e-5, except 0.04 for Llama-3.1-8B on MATH,
  whose hidden states were captured twice.
- **Same-model vs different-model gain, as a paired difference.** This uses the 8 primary pairs on MMLU-Redux and
  MATH, the only benchmarks where one model wrote several answers to a question.

  | Readout | Different-model pairs | Same-model pairs | Difference |
  |---|---|---|---|
  | Direction | +11.4 [+9.7, +13.1] | +1.2 [−1.4, +3.6] | +10.2 [+7.6, +12.8] |
  | Rule (stretch) | +4.4 [+3.6, +5.3] | +0.5 [−1.0, +1.9] | +4.0 [+2.4, +5.4] |

  The text says the same-model intervals still allow gains of a few points.
- **Surface model vs direction.** Over the 12 pairs, surface minus direction is −0.3 [−1.9, +1.4]: no difference was
  detected. This average hides opposite signs by benchmark:

  | Benchmark | Surface minus direction |
  |---|---|
  | MMLU-Redux | +2.7 [+0.4, +4.9] |
  | MATH | +3.6 [+1.0, +6.1] |
  | BBEH | −7.2 [−10.9, −3.4] |

  On BBEH the surface model does not beat the verdict (−0.7 [−5.4, +4.2]). This benchmark dependence is new and is now
  in the abstract.
- **Residualization on the 12 pairs.** It removes 35% [21, 49] of the gain (65% kept). Per benchmark it keeps 64% on
  MMLU-Redux, 43% on MATH and 97% on BBEH. On the 19 selected pairs it kept 69%.
- **Projecting out the authorship directions on the primary pairs.** This removes 58% [46, 75] of the gain on
  MMLU-Redux and 19% [4, 37] on MATH. On the selected pairs the figures were 65% and 11%.
- **Analysis-scope table.** A new appendix table (Table 4, `tab:scope`) lists every analysis with its judges,
  benchmarks, pairs, how the pairs were selected, and where the layer was chosen. The same-model, failed-question and
  scale analyses are labelled as using the exploratory selected pairs.
- **Selected-pair results moved.** The 19-pair results now sit in an appendix section called "Exploratory Protocol and
  Selected Pairs", described as conditional and descriptive.
- **Reasoning first on the primary pairs.** On the 10 primary pairs that have a reasoning run, it gives
  −2.1 [−3.3, −1.0]. Qwen2.5-7B and Granite-3.3-8B on MATH have no reasoning run.

## D2: residualization is no longer read as a share of information

**Done.**

- **Wording.** The text now says "linear residualization … reduces its ranking gain over the verdict by 35% [21, 49]
  under this procedure: about two thirds of the gain survives". It also says AUROC is not additive, so the percentage
  is not a share of the direction's information.
- **New incremental-prediction test (nested).** Pairwise logistic models are fitted on the right-vs-wrong pairs of the
  training questions and scored on held-out pairs.

  | Comparison | Ranking gain | Held-out log loss per pair |
  |---|---|---|
  | Add the direction to the surface features | +2.3 [+1.2, +3.4] | 0.626 → 0.607 (−0.020 [−0.024, −0.015]) |
  | Add the surface features to the direction | +2.5 [+1.5, +3.5] | not separately reported |
  | Add the direction to the surface features, same-model pairs only | +0.2 [−1.7, +2.2] | not separately reported |

- **Error overlap.** Of the test pairs, 47% are ranked correctly by both scores, 16% only by the surface model, 16%
  only by the direction, and 21% by neither. The two scores' correctness indicators correlate at 0.31. So the surface
  model and the direction do not make the same errors.

## D3: content checking vs population shortcuts (new controlled-edit experiment)

**Done: a new experiment, with a result that narrows the paper's claim.** The protocol was written before anything
was scored: `experiments/beyond_capability/edit_test/PROTOCOL.md`.

**Items.**

- **Source answers.** One right Qwen3.5-4B MATH answer per problem.
- **Design/test split.** The first 40 problems formed a design set, used only to tune the prompt and filters; it is
  never scored.
- **Edits.** On the other 348 problems, Kimi-K3.1-Pro changed one intermediate step to a wrong value and carried it
  through to a wrong final answer, keeping all other text the same.
- **Filters.** GLM-5.3-Flash must confirm the new final answer is wrong, and the surface features, line counts,
  length (within 5%) and character similarity (≥ 0.85) must match the original. 342 pairs pass, with median
  similarity 0.997.

**Two rules added during the build, both before any scoring.**

- The design set showed that the editor added trailing spaces, so each edited line now keeps its original line's
  trailing whitespace.
- An API call that has not returned within 10 minutes counts as a failed attempt. This hit two grading calls.

**Scoring.**

- **Judges and readouts.** The 4 primary judges, each scored with frozen readouts from the fold in which the problem is
  held out.
- **Reproduction check.** The original answers reproduce their stored primary scores to within bf16 rounding.

**Result.** The table gives the share of pairs where the original scores above the edit (50 = chance):

| Score | Share of pairs | Against the verdict |
|---|---|---|
| Verdict | 71.0 [68.0, 74.0] | — |
| Direction | 67.2 [64.0, 70.3] | −3.8 [−6.3, −1.5] |
| Rule (stretch) | 69.5 [66.4, 72.6] | −1.5 [−3.1, +0.1] |
| Surface model | 49.4 | — |

The surface model sits at chance by construction. Every judge's direction ranks below its own verdict. When
correctness changes in one checkable step and little else changes, the verdicts detect it and the direction adds
nothing.

- **Where it is reported.** The abstract, the introduction, §4.3, Takeaway 3, the conclusion and the limitations all
  report this. They also state its limits:
  - The errors are visible single-step mistakes, often arithmetic slips, which may be easier to catch than natural
    errors.
  - The direction has to transfer from natural answers to a new kind of error.
  - The test covers one benchmark, one answering model and one editing model.
- **Reader check (models, not humans).** Six Claude subagents read every pair as a diff, without seeing any scores:
  - 0 edits leave the answer correct.
  - 2 add a visible cue: a spurious failed check, and a misquoted figure code.
  - 24 leave an unchanged line that still uses the original value. These are kept, because the self-contradiction is
    still a content error.

  Dropping the 2 cue pairs gives the same result: direction −3.8 [−6.2, −1.5].
- **Appendix.** A new section "Controlled Edits" with a per-judge table (Table 8).

## D4: verdict + direction is now scaled without test-set statistics

**Done.**

- **The fix.** `outer_analyze.py` now divides each score by its within-question SD on the fold's *training* answers.
  These scales are computed in `primary_scope_modal.py` from the training projections.
- **Effect.** Verdict + direction gains +5.8 [+4.9, +6.8] held out. The earlier version used the pooled test answers
  and gave +5.4 [+4.6, +6.2]. The paper reports both.
- **Unchanged.** The direction and rule results do not change.

## D5: utility and uncertainty scope

**Done.**

- **New paragraph in §4.2, "When is stretching worth it?".** It covers:
  - Cost: the readout is a dot product on the verdict's own forward pass, while stretching needs about one extra
    token step.
  - The direction beats the rule on ranking, on best-of-n (+7.6 vs +1.8) and on a fixed review budget.
  - When stretching is still useful: only where a pipeline must consume the judge's own verdict.
- **Review budget (new Table 6 in the appendix).** When 10% of answers are flagged, the share of wrong answers caught
  is:

  | Score | Wrong answers caught | Gain over the verdict |
  |---|---|---|
  | Verdict | 11.8% | — |
  | Direction | 15.2% | +3.4 [+2.1, +4.6] |
  | Rule | 12.8% | +1.0 [+0.3, +1.7] |

  Budgets of 20% and 30% are also in the table. The comparison follows Gulati & Wunder's fixed-budget framing.
- **Uncertainty wording.** The Setup now says the intervals resample stored test scores. They are conditional on the
  fitted directions, the chosen layers and the judges studied, and do not cover refitting or other model families.
- **Split stability.** We ran five more random outer splits, direction only. The pooled gain ranges from +7.2 to
  +8.6, against +8.0 on the primary split. The stretch would need new GPU runs and was not repeated; the appendix says
  so.

## Editorial items

1. **Belief title and claims:** belief paper, not handled here.
2. **"Supervised readout–verdict gap" replaces "know–say".**
   - New title: *The Readout–Verdict Gap of Small LLM Judges: Most of the Gain Is on Answers by Different Models*.
   - The introduction says that whether the gap reflects unexpressed knowledge or cues in the answer pool is a
     separate question.
3. **The nested protocol is now the default methods description.**
   - Setup has a "Primary protocol" paragraph.
   - The in-sample layer selection, the layer-rule history, the layer figure and the pooling history have moved to the
     appendix section on the exploratory protocol.
   - Figure 1 and Table 3 are labelled exploratory.
4. **Status file:** the direction lines of `papers/REVISION_STATUS.md` were updated with dates and file links. The
   belief lines are maintained by the belief session.
5. **No equivalence claims.**
   - "Ranks as well" is replaced with "no detected difference" (interval −1.9 to +1.4) everywhere, including the
     abstract, introduction, section headings, takeaway and conclusion.
   - Same-model intervals are described as allowing small positive effects.

## Validation status

- **Human validation: none.** No human has checked the controlled edits or any label in this paper. The edit filters
  are automatic (GLM-5.3-Flash grading plus text checks), and the reader check is done by Claude subagents (models).
  The paper says so in §4.3, Appendix F and the Limitations.
- **MATH grading.** MATH correctness labels come from GLM-5.3-Flash against the reference, as before.

## Cost

- **Modal: about $5.** This covers the CPU primary-scope job and the H100 edit scoring (4 judges, about 10
  minutes each), out of the $100 direction cap; the direction paper's total is about $33.
- **Tinker:** about $37 at list prices for the Kimi-K3.1-Pro edits and GLM-5.3-Flash grading, out of the $1K
  direction cap. The token counts are 0.64M in and 1.30M out for Kimi. If the ~23 calls that stalled and were
  restarted were also billed, add up to about $14.
- Cannon was not used. Nothing was committed.
