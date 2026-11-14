*Cross-model held-out validation: does the model "know better" internally than it says?*

Tested all 7 feasible pool models (deepseek-v3.1 excluded — Tinker-hosted only, no local HF weights) × 3 benchmarks (BFF, BiGGen, HealthBench) × 2 conditions (standard, rubric) = 42 cells, all complete and verified on disk.

*Method:* `held_out_gap` = κ(best interior layer, held-out half) − κ(model's own final answer, held-out half), averaged over 200 random 50/50 splits, with bootstrap CI + sign-permutation p-value. Positive = interior layer beats the final answer (model "knows better" internally than it says out loud).

*Headline answer:* Not consistent. 6 of 21 (benchmark, model) pairs show the rubric *strengthening or creating* an interior-layer win, 8 show it *weakening or creating* a final-answer win, 7 show no real effect either way. Real, non-random effect (most cells p<1e-5), but direction is model- and benchmark-specific — no universal rule.

*Models where the effect is real and fairly consistent:*
• *gpt-oss-120b* — interior-layer wins in 5 of 6 cells (BFF ✅✅, BiGGen ✅✅, HealthBench-rubric ✅; only HealthBench-standard flips negative)
• *qwen3.5-4b* — interior-layer wins in 4 of 6 cells (BFF ✅✅ — rubric *sharpens* it, 0.172→0.347; BiGGen ✅✅; HealthBench negligible)

*Models where it's inconsistent or absent:*
• *nemotron3-nano-30b*, *qwen3.6-35b-a3b* — show it in 2–3 of 6 cells, but flips on/off between standard and rubric within the same benchmark
• *nemotron3-super-120b* — only 1 of 6 cells (BFF-standard); mostly negligible/negative elsewhere
• *gpt-oss-20b* — no effect anywhere, gap ≈ 0 across the board (known degenerate/constant-prediction model)
• *qwen3.5-9b* — opposite pattern: final answer beats interior layer almost everywhere, never shows an interior-layer win

*Bottom line:* "rubric → better internal answers" is real but not universal. gpt-oss-120b and qwen3.5-4b are the two models where it's robust; everywhere else it's absent, flips with the rubric, or reversed.

Not yet folded into `mech_interp_findings.html` or `manuscript.md` — pending a separate decision on whether/how to include it.
