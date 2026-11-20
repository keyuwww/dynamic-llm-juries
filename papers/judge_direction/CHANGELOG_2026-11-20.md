# Direction paper: response to the November 20 review

What each item in `future_paper_improvements.md` (direction paper) led to. Every number in the paper comes from
`build.sh`; the numbers below come from the same files.

## Priority 1

**Check the complete residualization pipeline: done. The result changed.**
- `experiments/beyond_capability/nested_surface_modal.py` (Modal CPU) and `nested_surface_analyze.py` produce
  `out_paper/nested_surface.json` and `out_paper/nested_surface_check.json`.
- Outer folds are the paper's two question halves. Everything is fitted on the training half: the layer (by an inner
  split), the direction, the feature scaling, the surface model, and a residualizer trained on inner cross-fitted
  direction scores. The test answers are scored by the same inner directions.
- **Removing the surface features now keeps 69% [58, 81] of the direction's gain**, against 49% [34, 61] in the
  earlier composed version. So the features statistically account for about a third of the advantage
  (31% [19, 42]), not half.
- If the test answers are scored with the direction fitted on the whole training half instead, 75% [64, 87] is kept.
- On same-model pairs the residualized direction falls below the verdict: −3.5 [−5.8, −1.1]. The direction itself
  shows no advantage there: +0.1 [−2.2, +2.6].
- The surface-only model uses no direction scores, so it is unaffected. The appendix (Surface Features) explains
  both versions.

**Paired surface-versus-direction comparison: done.**
- On identical questions and answers, with the synchronized question bootstrap, surface minus direction is
  +0.7 [−1.0, +2.5]. The in-sample-layer version is −0.8 [−2.8, +1.2].
- On same-model pairs the surface model ranks higher: +3.4 [+0.5, +6.4].
- The wording is now "about as well" and "no detected difference". The claims "ranks as well" and "leaves none on
  same-model pairs" are gone.

**Nested evaluation as the primary performance result: done.**
- Table 1 now has two blocks:
  - top (primary): every choice made on training questions and evaluated on held-out questions, 12 pairs;
  - bottom (descriptive): the 19 selected pairs, with choices made on the evaluated answers.
- Primary results: direction +8.0 [6.5, 9.6] in ranking and +7.6 [5.8, 9.5] in best-of-n; verdict + direction
  +5.4 [4.6, 6.2]; the rule +3.1 [2.2, 4.0], which is 39% [30, 47] of the direction's gain.
- The abstract, intro, §4.2 and Takeaway 2 lead with these numbers.
- The text says this is a nested re-analysis of data we had already studied, not a prospective test. The Limitations
  section says it too.
- The scope keeps the pairs without a gap (Granite-3.3-8B MATH) and the failed-rule case (Qwen2.5-7B MATH, −1.4).

**Statistical adjustment vs causal explanation: done.**
- §4.3 says residualization measures overlapping predictive information, not that formatting causes the judge's
  signal.
- It says a bare final line, or a long answer full of self-corrections, can reflect a real failure of reasoning.
- It ties this caution to the one already stated for removing the authorship subspace.

## Priority 2

**Inability and reasoning claims narrowed: done.**
- "Cannot solve" is now "failed on a sampled attempt" in the main text, captions, tables, figure and related work.
- The nine-attempt set is described by its observed criterion: failed all nine of its own attempts.
- "Own ability removed" is gone, and §4.4 is retitled "Checking Answers to Questions the Judge Failed".
- The reasoning claims are qualified by the brief-reasoning prompt: in 6 of 19 pairs the judge writes almost no
  reasoning (median ≤ 5 tokens).

**Figures and final editing: done.**
- Figure 3 now uses 95% intervals from the synchronized question bootstrap, and the caption says they reflect
  question sampling, not variation between judges.
- The repeated "pairs" in Limitations is fixed.
- The conclusion now says "every choice is made on training questions and evaluated on held-out questions".
- The matched scale result is unchanged: 70B is above 8B, and its difference from 3B is called inconclusive, not
  equivalence.

## Not done

- No new GPU experiments: none of the items needed them.
- The belief-paper items belong to the other session's paper and were left alone.

## Cost

Modal: about $0.06 for this round (CPU). Total for the direction-paper revision: about $28 on Modal, $0 on Tinker.
Cannon was not used.
