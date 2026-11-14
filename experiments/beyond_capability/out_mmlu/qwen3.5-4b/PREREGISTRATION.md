# Pre-registered prediction: stretching Qwen3.5-4B's judge direction on MMLU-Redux

Written 2026-11-09 14:14 EST, before job 59257916 (shift-only) has produced any output and before any
stretching of Qwen3.5-4B has been run.

**Rule (fitted on 8 earlier cases: Qwen-9B and Llama-8B x MMLU-Redux and MATH x solved / not solved):**

- GAP = KNOWS - SAYS, in ranking points (x100). KNOWS = held-out ranking of the judge direction; SAYS = ranking of
  the unedited verdict score.
- RESPONDS = share of answers accepted at shift +8 sd minus at shift -8 sd (all answers).
- If RESPONDS >= 0.10: predicted gain from stretching x11 (change in the verdict's ranking, x100) = 0.5 x GAP.
  If RESPONDS < 0.10: predicted gain < 3.
- Scored per group: solved, not solved (by Qwen3.5-4B's own majority-of-3 answers), with and without its own
  candidate answers.

**What counts as the rule holding:** in each group, the measured gain lies within +/-4 points of the prediction,
and the gain's 95% interval excludes zero when the prediction is >= 5 and includes zero when it is <= 2.

Inputs: prereg_measure.json (from the shift-only run). Outcome: the x11 stretch run, analysed with stretch_analyze.

## Addendum: stretch-strength formula (written 2026-11-10 22:09 EST, job 59257916 still pending, no Qwen3.5-4B output exists)

The rule above is unchanged. This adds a second, separate prediction: which stretch strength is best.

- SENSITIVITY = mean verdict change per 1 sd pushed along the direction (from shifts +4 and -4 sd), divided by the
  verdict score's within-question standard deviation (unedited). All answers.
- Predicted best strength = 1 + 1/SENSITIVITY; if SENSITIVITY <= 0, predicted best is x1 (no stretch).
- Found after looking at 8 judge x benchmark cases (strength_select.py, out_strength_select.md); this is its first
  fresh test.
- The stretch job will run x2, x4, x11 plus the formula's strength (rounded to the nearest integer), computed from
  prereg_measure inputs before the stretch job is submitted.

**What counts as the formula holding:** on all answers, the formula's strength ranks within 1 point of the best
strength tested, and is at least as good as fixed x11 (within 1 point).

## Predictions filled in (written 2026-11-11 09:41 EST, after the shift-only job finished, before any stretch is run)

Inputs: prereg_measure.json and steer_mmlu_h{1,2}.jsonl from job 59257916 (judge-direction layer 18, shifts only).

**Gap rule.** RESPONDS = 0.791 - 0.511 = 0.28 (>= 0.10), so predicted gain at x11 = 0.5 x GAP.

| Group | KNOWS | SAYS | GAP | Predicted gain (x11) | Rule holds if |
|---|---|---|---|---|---|
| with own answers, all | 0.622 | 0.609 | +1.3 | +0.6 | gain in [-3.4, +4.6] and 95% CI includes 0 |
| with own answers, solved | 0.716 | 0.704 | +1.2 | +0.6 | gain in [-3.4, +4.6] and CI includes 0 |
| with own answers, not solved | 0.533 | 0.520 | +1.3 | +0.6 | gain in [-3.4, +4.6] and CI includes 0 |
| without own answers, all | 0.552 | 0.577 | -2.5 | -1.3 | gain in [-5.3, +2.7] and CI includes 0 |
| without own answers, solved | 0.665 | 0.699 | -3.4 | -1.7 | gain in [-5.7, +2.3] and CI includes 0 |
| without own answers, not solved | 0.428 | 0.441 | -1.3 | -0.6 | gain in [-4.6, +3.4] and CI includes 0 |

In plain words: the rule predicts that stretching does **not** help Qwen3.5-4B anywhere, because its verdict already
says about as much as its direction knows.

**Strength formula.** Verdict change per 1 sd pushed = 0.234; verdict's within-question sd = 1.795;
SENSITIVITY = 0.130; predicted best strength = 1 + 1/0.130 = 8.7, rounded to **x9**.
The stretch job runs x2, x4, x9, x11 (betas 1, 3, 8, 10), judge direction and random direction.
Note: because the gap rule predicts no gain, "best strength" may be decided by noise; the formula check is
still scored as written above.

**Added secondary analysis (decided before the stretch run, not part of the original rule):** repeat every gain
using only pairs of answers to the same question written by the same model (removes the "which model wrote it" clue,
check_same_source.py). Reported alongside, not used to score the rule.

## Outcome (scored 2026-11-12, after the stretch run; nothing above was changed)

Stretch run: job 59930641, an identical copy of 59736975 submitted to gpu_test (A100 MIG slice) because 59736975
waited over a day in the queue; 59736975 was cancelled once the copy completed. Outputs:
steer_mmlu_stretchT_h{1,2}.jsonl. The unedited verdict matches the earlier shift-only run on 99.1% of accept/reject
decisions. Scoring: prereg_score_4b.py -> prereg_outcome.md.

**Gap rule: holds in 6 of 6 groups.** Measured gains at x11: -0.4, -0.4, -0.4 (with own answers: all, solved, not
solved) and -2.5, -3.1, -1.7 (without own answers); every one inside its range and every 95% interval includes 0.
Stretching does not help Qwen3.5-4B, as predicted.

**Strength formula: holds, but the test is weak.** Rankings at x2, x4, x9, x11 are 61.1, 61.3, 60.6, 60.7 (unedited
61.0); x9 is within 1 point of the best (x4) and of x11. Because no strength changes the ranking by more than
0.4 points, every strength would have passed, so this says little about the formula (as anticipated above).

**Secondary, same-model pairs (not scored):** gains -1.3 [-3.1, +0.5] (all), 0.0 [-2.5, +2.5] (solved),
-2.7 [-5.7, 0.0] (not solved). These pairs are almost all two of Qwen3.5-4B's own answers; without its own answers
no question has a same-model pair.
