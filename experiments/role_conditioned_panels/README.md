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
| `cheapest_first.py` | forces the cheapest judge in as the first panel member, then greedy growth (`--exclude` drops judges from the pool) |
| `cascade.py` | cheap-first cascade simulated from saved verdicts |
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

### Cheapest first without gpt-oss-120b

Same run on the 7-judge pool (`python cheapest_first.py ... --exclude gpt-oss-120b`). Accuracy difference vs top-3 of the reduced pool, default greedy -> cheapest first:

| Setting | eta-hat | majority |
|---|---|---|
| BFF, no reference | -1.4 -> +0.0 [-2.0, +2.2] | -0.4 -> -1.6 |
| BFF, reference given | -0.6 -> -0.8 | -1.2 -> -0.7 |
| RewardBench-2 | +4.7 -> +4.7 (calibration) | -0.1 -> -0.9 [-1.4, -0.4] |

One of six cells reaches parity with top-3, within noise; panels grow from about 2.3 to 3 judges. This reproduces the null result.

## Cheap-first cascade

`python cascade.py --bff <bff_judgments.jsonl> --rb2 <rb2_judgments.jsonl>` simulates a cascade from the saved verdicts (no new API calls). On each split the escalation judge is the best single judge on fit+validation. The k cheapest other judges answer first; if they all agree their verdict is accepted, otherwise the escalation judge's verdict is used. Cost counts the escalation judge only on escalated items. Accuracy difference vs static top-3 (95% question-bootstrap CI):

| Setting | Strategy | Accuracy | $/item | Escalated | vs top-3 | Cost vs top-3 |
|---|---|---|---|---|---|---|
| BFF, no reference | static top-3 | 0.866 | 0.0038 | - | - | 100% |
| | best single | 0.847 | 0.0007 | - | -1.9 [-4.2, +0.4] | 19% |
| | cascade, 2 cheap judges | 0.835 | 0.0010 | 34% | -3.1 [-5.4, -1.0] | 26% |
| | cascade, 3 cheap judges | 0.853 | 0.0018 | 45% | -1.3 [-3.2, +0.4] | 47% |
| BFF, reference given | static top-3 | 0.925 | 0.0043 | - | - | 100% |
| | best single | 0.910 | 0.0021 | - | -1.5 [-3.0, -0.1] | 49% |
| | cascade, 3 cheap judges | 0.921 | 0.0020 | 27% | -0.4 [-1.3, +0.5] | 47% |
| RewardBench-2 | cascade, 3 cheap judges | 0.843 | 0.0019 | 34% | +0.6 [-0.5, +1.6] | 87% |

With the reference answer, the 3-judge cascade is within noise of top-3 at 47% of its cost, and about the same cost as the best single judge with +1.1 points higher accuracy [-0.3, +2.6]. Without a reference it is within noise of the best single judge (+0.6 [-1.3, +2.4]) but costs 2.6x as much ($0.0018 vs $0.0007), because gpt-oss-120b is already one of the cheapest judges. Two cheap judges are too few.
