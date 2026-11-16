# All (judge, benchmark) pairs: the rule, fixed before any result

Written 2026-11-15 23:00 PST, before the run (azure/pair_pipeline.py, allpairs_modal.py).

- **Gap check.** KNOWS = held-out within-question ranking of the question-centred judge direction (learned on one half
  of the questions, scored on the other), at each layer; SAYS = ranking of the unedited verdict. GAP = 100 x (best
  layer's KNOWS - SAYS). Pairs with GAP <= 5 stop here.
- **Push test (no labels).** On 400 random answers, accept rate at -8 sd and +8 sd along the direction, at every
  2nd layer (not 0, not the last). A layer *responds* if the accept rate rises by >= 10 points.
- **Layer.** Highest KNOWS among responding layers; if none responds, the highest-KNOWS layer ("no layer responds").
- **Stretch.** x11 at that layer along the judge direction, and along a random direction (control). Nothing else is
  stretched, so the layer cannot be picked by its gain.
- **Readouts.** Gain = ranking after x11 minus unedited, x100, 95% CI resampling questions; all / solved / not solved;
  and on same-model pairs (right vs wrong answers from the same answering model), the honest "beyond ability" test.
- **Solve labels.** The judge's own answer (thinking off, T = 0.7, one sample; MMLU <= 4096 new tokens, MATH and BBEH
  <= 8192; hitting the cap = wrong). Existing labels are reused where they exist (Llama-3.1-8B, Llama-3.2-3B and
  Phi-4-mini on MMLU, Qwen3.5-4B on MATH and BBEH, Llama-3.1-8B on BBEH).

Amendment, 23:27 PST, still before any full-run result: the final pass also records x4 and x21 along the judge
direction at the chosen layer (secondary readouts, for choosing a strength). x11 stays the primary readout.
