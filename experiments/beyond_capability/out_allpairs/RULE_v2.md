# Fresh test of the score-based layer rule (written before running)

Written 2026-11-16 02:48 PST. New judges never used before in this study: Llama-3.2-1B-Instruct and
Qwen2.5-7B-Instruct (thinking off), on MMLU-Redux, MATH and BBEH (same answers and labels as out_allpairs/RULE.md).

- **Gap check:** unchanged (GAP = best layer's KNOWS - SAYS; stop if <= 5).
- **Response (changed):** on 400 random answers, push -8 and +8 sd along the direction at every candidate layer.
  Sensitivity = mean over answers of (verdict score at +8 minus at -8) / 16, divided by the within-question sd of the
  unedited verdict score. A layer *responds* if sensitivity >= 0.05. (The accept-rate rule of RULE.md is also recorded.)
- **Layer:** highest KNOWS among responding layers; if none, the highest-KNOWS layer ("no layer responds").
- **Stretch:** x4, x11, x21 along the judge direction and x11 along a random direction, at that layer only.
- **Predictions:** for every pair with a gap and a responding layer, the x11 gain on all pairs is > 0 (95% CI above 0)
  and the random direction is within +-1. On same-model pairs (sm_*_items, questions the judge cannot solve), the gain
  at x4 is >= 0 on MATH and BBEH and about 0 on MMLU.
