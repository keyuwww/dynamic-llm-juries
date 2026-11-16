# Llama-3.2-3B layer sweep on MMLU-Redux: predictions written before the results

Written 2026-11-15 22:39 PST, while the Modal run was still steering; no sweep output had been pulled or seen.

## Why this run
On MATH, Llama-3.1-8B's verdict ignored pushes at layers 8-14 and responded strongly from layer 16 on (accept rate
~44% -> ~98% for -8 -> +8 sd). The pipeline had picked layer 14 by "knows" alone. Llama-3.2-3B was steered at layer 12 of
28 (same relative depth) in the preregistered test, where its accept rate barely moved (93% -> 91%) yet x11 still gained
+4.1 overall; on same-model pairs +3.0 [-0.5, +6.5] (solved +3.8 [-1.7, +9.3], not solved +2.6 [-1.8, +7.1]).

## Decision rule (fixed now)
- A layer "responds" if the accept rate rises by at least 10 points from a -8 sd push to a +8 sd push.
- Primary layer: among layers that respond, the one whose direction ranks held-out answers best ("knows").
  If no layer responds, the primary layer is 12 (the preregistered one).
- Primary readout: gain at x11 on **same-model pairs, questions the judge cannot solve**, 95% CI resampling questions.
  Secondary: gain on all pairs (all / solved / not solved), and the random-direction control (should be ~0).

## Scenarios
1. **Later layers respond, gain grows on all pairs, same-model not-solved gain CI includes 0.** (my prediction:
   +1 to +3 point estimate) -> the "no response" was the layer choice, as on MATH; the extra gain is again mostly
   "which model wrote it". Bottom line unchanged: stretching helps within the judge's ability, not beyond it.
2. **A responding layer gives a same-model not-solved gain with CI above 0.** -> first sign that stretching recovers
   checking beyond solving, in a small model. Not believed until replicated (Phi-4-mini or a second benchmark),
   because the primary layer was chosen from 12 candidates.
3. **No layer responds.** -> layer choice is not the explanation for this judge; its verdict is a near rubber stamp
   at every depth, and the +4 at layer 12 came from reordering scores without moving accept rates. Supports the
   score-based responsiveness measure (margin sensitivity) over the accept-rate one.
4. **Layers respond but the gain does not grow, or turns negative (overshoot).** -> responding is necessary but not
   sufficient; the small model's direction carries little beyond surface clues (its same-model gap was only +3).

## Outcome (added after scoring; layer_sweep.md)
- **No layer responds in the preregistered sense** (accept rate *rising* >= 10 points from -8 to +8 sd). So the primary
  layer is 12, as preregistered: x11 gain +4.0 [+2.1, +5.6] overall, +4.0 [+1.9, +6.3] on unsolved questions;
  same-model pairs, unsolved: **+3.3 [-0.9, +7.7]** (CI includes 0). Random direction ~0 everywhere.
- **Not anticipated by any scenario:** from layer 14 on, the verdict responds strongly but *backwards*: pushing toward
  "right" makes it reject (accept 98% at -8 sd -> 44% at +8 sd from layer 18 on), and stretching there hurts
  (-4 to -5 overall). The verdict reads the correctness direction with the opposite sign at those layers.
- Reading: closest to scenario 3 (layer choice does not rescue this judge); bottom line unchanged (nothing clearly
  beyond the judge's ability on same-model pairs).
