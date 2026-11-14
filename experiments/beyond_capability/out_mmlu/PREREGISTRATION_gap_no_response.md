# Pre-registered prediction: a gap without a responsive verdict gives no gain (Llama-3.2-3B, Phi-4-mini, MMLU-Redux)

Written 2026-11-13 16:51 EST (saved on Cannon before stretch jobs 60351669 and 60351675 were submitted). At this point no stretch run of either judge exists and no solve labels exist for either.
What exists: the capture + shift-only screen (jobs 60326656, 60326671; stretch_pipeline.py --betas=, scored with
azure/screen_measure.py -> screen_result_round1.md on Cannon).

## Why these two judges

They were screened as candidates for a test where the gap rule predicts a gain. Neither qualifies: both have a large gap
between what the direction knows and what the verdict says, but their verdicts barely respond to pushes along the
direction. That makes them a test of the rule's other branch. A naive rule ("stretching recovers half the gap",
ignoring responsiveness) predicts a clear gain; the rule we fitted says no gain.

## The rule (unchanged from out_mmlu/qwen3.5-4b/PREREGISTRATION.md)

- GAP = KNOWS - SAYS (ranking points, x100). KNOWS = held-out ranking (within-question AUROC) of the judge direction at
  the chosen layer, from the pipeline's split; SAYS = ranking of the unedited verdict score.
- RESPONDS = share of answers accepted at shift +8 sd minus at shift -8 sd (all answers).
- If RESPONDS >= 0.10: predicted gain at x11 = 0.5 x GAP. If RESPONDS < 0.10: predicted gain < 3.

## Inputs (all answers, from the screen)

| Judge | Layer | KNOWS | SAYS | GAP | RESPONDS (accept at -8 -> +8 sd) | Same-model KNOWS / SAYS (gap) | Direction-verdict corr. |
|---|---|---|---|---|---|---|---|
| Llama-3.2-3B-Instruct | 12 of 28 | 0.632 | 0.518 | +11.4 | -0.02 (93% -> 91%) | 0.542 / 0.513 (+2.9) | -0.14 |
| Phi-4-mini-instruct | 14 of 32 | 0.624 | 0.552 | +7.2 | +0.04 (88% -> 92%) | 0.550 / 0.543 (+0.7) | 0.17 |

## Predictions

Both judges have RESPONDS < 0.10, so the rule predicts **gain < 3 points** at x11 for each.

| Judge | Group | Rule predicts | Naive rule (0.5 x GAP) would predict |
|---|---|---|---|
| Llama-3.2-3B | all answers (primary) | < 3 | +5.7 |
| Phi-4-mini | all answers (primary) | < 3 | +3.6 |
| both | solved, not solved (secondary) | < 3 | 0.5 x that group's GAP (computed when scoring) |

**What counts as the rule holding (per judge and group):** the measured gain in ranking at x11 (judge direction,
vs unedited, x100) is below 3 points. Reported with a 95% interval from resampling questions (2000 draws).

**What counts as the naive rule holding:** the measured gain lies within +/-4 points of 0.5 x GAP. Note in advance:
for Phi-4-mini the two rules overlap (naive range -0.4 to +7.6 includes values below 3), so only Llama-3.2-3B
separates them cleanly (naive range +1.7 to +9.7). A gain between +1.7 and +3 would count for both rules.

**Caveat noted in advance:** both judges' gaps mostly vanish on same-model pairs (+2.9 and +0.7), so "half the
same-model gap" also predicts little gain. This test separates "gap + responsiveness" from "gap alone on all
answers", not from "same-model gap alone".

## Strength formula (second, separate prediction, as in the Qwen3.5-4B preregistration)

SENSITIVITY = verdict change per 1 sd pushed (from +-4 sd) / verdict's within-question sd. Strength = 1 + 1/SENSITIVITY.

| Judge | SENSITIVITY | Formula strength | Stretch run will test |
|---|---|---|---|
| Llama-3.2-3B | 0.068 | x16 | x2, x4, x11, x16 (betas 1, 3, 10, 15) |
| Phi-4-mini | 0.013 | x81 | x2, x4, x11, x81 (betas 1, 3, 10, 80) |

Holds if, on all answers, the formula strength ranks within 1 point of the best strength tested and at least as well
as x11 (within 1 point). As with Qwen3.5-4B, if no strength moves the ranking this test is weak.

## Scoring plan

- Stretch: cannon_bigstretch.sh with the directions the screen already learned (each half steered with the direction
  from the other half), judge direction and random direction, suffix `stretchT` -> steer_mmlu_stretchT_h{1,2}.jsonl.
- Solved vs not solved: each judge answers every MMLU-Redux question once with vLLM (thinking off, T = 0.7, as for
  Llama-3.1-8B), final letter vs the key. Run in parallel with the stretch; used only for the secondary groups.
- Secondary (reported, not scored): the same gains using only same-model pairs, and the random-direction control.
- These judges wrote none of the candidate answers, so there is no own-answers split.
