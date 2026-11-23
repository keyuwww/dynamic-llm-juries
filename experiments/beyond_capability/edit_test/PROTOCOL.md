# Controlled-edit test (frozen 2026-11-21, before any edited answer is scored)

Purpose (strict re-review of 2026-11-21, item D3): test whether the correctness direction's gain persists when
correctness changes but the answering model, wording, formatting and length stay approximately fixed. In the main pools,
right and wrong answers differ in who wrote them and in how they are written; here they differ in one step.

## Items

- Source: the Qwen3.5-4B answers in the MATH main pool that are graded right, at most 8,000 characters, one per problem
  (the first by answer id). Problems are shuffled with seed 20261121.
- Design set: the first 40 shuffled problems. Used only to iterate on the edit prompt and filters; never scored.
- Test set: every remaining problem.
- Edit: Kimi-K3.1-Pro (high reasoning; from a family that is not a judge and not Qwen) rewrites the answer with exactly
  one wrong intermediate step, carried consistently to a different final answer, with all other text, formatting and
  tone unchanged and no words that signal an error. Up to two attempts per problem; the first attempt that passes every
  filter is used.

Design-set finding (2026-11-21, before the test set was built): the editor sometimes added trailing spaces, for
example after the final answer. Each edited line is given its original line's trailing whitespace before filtering.
During the test build, 23 editor calls stalled for over 30 minutes twice; an editor call that has not returned within
10 minutes now counts as a failed attempt (decided before any edited answer was scored). No other change was made after the design set (39 of 40 design problems passed the filters).

## Filters (automatic, all must pass)

1. The edited answer ends with a final answer line ("The answer is: ...").
2. Its final answer is wrong: not equal to the reference after canonicalisation, and GLM-5.3-Flash (the paper's MATH
   grader, same prompt) calls it DIFFERENT from the reference.
3. Same number of lines; identical counts of bold markers, `$`, the word "step", hedge, confidence and self-correction
   words, and the same final-answer-line flag (the paper's surface features); length within 5% of the original.
4. Character-level similarity (difflib ratio) at least 0.85.

## Reader check (secondary, model-based)

Claude subagents (models, not human annotators) read each test pair and record whether the edited answer contains a
single introduced error that makes its final answer wrong and whether the edit adds a visible cue (inconsistency in the
text, a comment, changed formatting). Primary analysis: all filtered pairs. Secondary: pairs the reader passes. No
human has checked the edits.

## Scoring (frozen readouts, no refitting)

Judges: the four primary-evaluation judges (Llama-3.1-8B, Qwen2.5-7B, Phi-4-mini, Granite-3.3-8B). For a problem in
outer half h, the readouts are those of the primary evaluation's fold in which h is the test half (direction, readout
layer and stretch layer fitted on the other half; out_outer/<judge>_math/outer_math.json):
  verdict    forced "VERDICT:" log-odds, unedited
  direction  projection on the fold's training direction at its readout layer
  rule       verdict stretched x11 at the fold's stretch layer if the fold is eligible, else the verdict
  stretch    verdict stretched x11 at the fold's stretch layer
  surface    the paper's surface model fitted on the fold's training half (main pool), applied to the two answers
Originals are re-scored in the same run (they must reproduce the stored primary-evaluation scores).

## Analysis

Pair accuracy: share of (original, edited) pairs where the original scores higher (ties 1/2); 50 = chance. Per judge,
and pooled as the equal-weight mean over the four judges with the synchronised question bootstrap (2,000 draws).
Primary comparison: direction minus verdict. Also reported: rule and stretch minus verdict, each readout against 50,
and the surface model (expected near 50 by construction). Every result is reported, whatever its sign.
