# Pre-registered prediction: stretching the judge direction on RewardBench 2 Safety (Qwen3.5-9B, Llama-3.1-8B)

Written 2026-11-09 19:24 EST, right after submitting jobs 59357761 (Qwen) and 59357763 (Llama), before either
has produced any output.

**Data.** RewardBench 2 Safety: 450 human-labelled requests, each with 1 appropriate and 3 inappropriate responses
(1,800 answers). There is no "solved" notion for a safety request, so all answers form one group.

**Rule (same as the Qwen3.5-4B pre-registration, fitted on 8 earlier cases):**

- GAP = KNOWS - SAYS, in ranking points (x100). KNOWS = held-out ranking of the judge direction; SAYS = ranking of
  the unedited verdict score.
- RESPONDS = share of answers accepted at shift +8 sd minus at shift -8 sd.
- If RESPONDS >= 0.10: predicted gain from stretching x11 (change in the verdict's ranking, x100) = 0.5 x GAP.
  If RESPONDS < 0.10: predicted gain < 3.

**What counts as the rule holding:** the measured gain lies within +/-4 points of the prediction, and its 95% interval
excludes zero when the prediction is >= 5 and includes zero when it is <= 2.

**Procedure.** Each job runs shifts and stretches together. The predicted numbers are computed first from the shift and
unedited columns only (prereg_measure.py) and written below, before the stretch columns are analysed.

**Update 19:5x EST:** the two cluster jobs were cancelled before they started, and the same pipeline runs instead on Modal H100s (stretch_modal.py, app ap-A7U0TirqUxvxBFjyU5XXke). Nothing else changed.

## Predicted numbers (filled in from prereg_measure.json before analysing the stretches)

### Llama-3.1-8B (layer 14) — written 2026-11-09 21:36 EST, before analysing the stretch columns

- KNOWS 0.987, SAYS 0.959, GAP +2.8 points; correlation 0.91
- RESPONDS: accepted 0% at -8 sd, 38% unedited, 99% at +8 sd -> 0.99 (>= 0.10)
- **Predicted gain from x11: +1.4 points** (<= 2, so the 95% interval should include zero; measured gain should lie in [-2.6, +5.4])
- Note: Llama already ranks safety answers almost perfectly (SAYS 0.96), so there is little room to gain.

### Qwen3.5-9B (layer 14) — written 2026-11-09 21:37 EST, before analysing the stretch columns

(Its measurement step failed inside the first Modal run because both containers wrote the same helper file; it was re-run alone on the saved hidden states and shift columns.)

- KNOWS 0.977, SAYS 0.964, GAP +1.3 points; correlation 0.74
- RESPONDS: accepted 38% at -8 sd, 38% unedited, 37% at +8 sd -> -0.02 (< 0.10: the verdict does not respond)
- **Predicted gain from x11: below 3 points**, with a 95% interval that includes zero.

## Outcome (analysed after both predictions above were written)

| Judge | Predicted gain at x11 | Measured gain at x11 [95% CI] | Rule holds? |
|---|---|---|---|
| Qwen3.5-9B | below 3, interval includes 0 | +0.1 [-0.6, +0.7] | **yes** |
| Llama-3.1-8B | +1.4, within [-2.6, +5.4], interval includes 0 | **-6.3 [-9.5, -3.5]** | **no** |

- Llama at gentler stretches: x2 +0.6 [-0.3, +1.8], x4 +1.0 [-0.4, +2.7], consistent with the prediction. x11 overshoots.
- Random direction: flat for both (within +/-0.1).
- Both judges are near the ceiling on this benchmark (ranking about 0.96), so there was little to gain.
- Likely reason for the failure (post hoc, not tested): Llama's verdict is extremely sensitive to this layer here (a +/-8 sd shift moves acceptance from 0% to 99%), so a fixed x11 stretch distorts it. The rule says nothing about strength, so it needs a third condition, or the strength must be tuned per benchmark on held-out data.
