# role_conditioned_panels

Role-conditioned judge-panel construction on the 8-judge Tinker pool (BFF-Bench, RewardBench-2 Safety), plus the control experiments. Results and discussion: `docs/findings_role_conditioned_panels.md`.

| File | What it does |
|---|---|
| `data.py` | loads judgments into verdicts `Z`, gold `Y`, question groups; joins prompt/response text from Hugging Face |
| `audit.py` | the only place the match matrix (`Z == Y`) is built; descriptive stats and the baselines |
| `splits.py`, `slices.py` | question-grouped fit/val/test splits; hand-crafted slices with fit-only thresholds |
| `oracle_risk.py`, `construct.py`, `evaluate.py` | eta-hat table, panel construction, serving, repeats, bootstrap, copy stress test |
| `majority.py` | the same construction and serving using majority vote only (no eta-hat table) |
| `run.py` | main CLI (`--rule eta|majority`, `--condition none|human`, `--sanity`, `--lambda-sweep`) |
| `explore_12.py` | brute-force search over all panels and logistic regression over the verdicts |
| `explore_3.py`, `explore_pools.py`, `embed.py` | embedding (PC5) slice and reduced-pool specialization tests |
| `cost_ci.py`, `subsample.py`, `calibration.py` | cost/accuracy intervals, subsampling test, verdict-rate vs gold-rate check |
| `cheapest_first.py` | forces the cheapest judge in as the first panel member, then greedy growth |
| `make_chart.py`, `plot_chart.py` | accuracy comparison figure |

`data_cache/` and `results/` are git-ignored; no raw judgment files are committed.

## Cheapest judge first

Suggested in discussion: force the cheapest judge (nemotron3-nano-30b, $0.00029/call) to be the first panel member, then grow greedily (`first_judge` in `run_all_repeats` / `run_all_repeats_mv`; `python cheapest_first.py --bff <bff_judgments.jsonl> --rb2 <rb2_judgments.jsonl>`). It does not help. Accuracy difference vs static top-3 majority, same 20 splits (95% CI):

| Setting | Rule | Default greedy | Cheapest first | Panel size (default -> cheapest first) |
|---|---|---|---|---|
| BFF, no reference | eta-hat | -2.7 [-4.3, -1.1] | -2.4 [-3.9, -0.8] | 2.1 -> 2.9 |
| BFF, no reference | majority | -1.9 [-3.1, -0.8] | -4.0 [-5.9, -2.0] | 2.6 -> 4.4 |
| BFF, reference given | eta-hat | -0.4 [-2.4, +1.2] | -0.8 [-2.7, +0.8] | 1.8 -> 2.7 |
| BFF, reference given | majority | -1.6 [-2.7, -0.8] | -0.8 [-1.9, +0.3] | 2.4 -> 3.8 |
| RewardBench-2 | eta-hat | +5.2 | +5.1 | 3.4 -> 3.5 |
| RewardBench-2 | majority | +0.4 [-0.7, +1.5] | -0.3 [-0.9, +0.2] | 1.6 -> 3.0 |

Panels get larger and cost more (BFF, no reference, majority: $0.0048 vs $0.0032 per item). The RewardBench-2 eta-hat gain is the calibration effect described in the findings doc, not panel construction. Excluding the strongest judge and trying other benchmarks were done earlier (see the findings doc).
