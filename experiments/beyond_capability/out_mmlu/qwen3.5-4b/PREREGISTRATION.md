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
