# Role-conditioned judge panels: findings

Code: `experiments/role_conditioned_panels/`. Nothing here beats a static top-3 majority vote.

## What was tested

A panel-construction method adapted from "Stopping and Routing LLM Judge Panels" (arXiv 2608.19802), run on the 8-judge Tinker pool:

1. Start with the best single judge, then add judges (in pairs, so the vote stays odd) while validation gain stays above 0.005.
2. Judges that don't help globally are checked on three text-based slices (calculation-heavy, long response, numeric prompt). If one helps on a slice it becomes a specialist, called only for those items; otherwise it is dropped.
3. Serve with majority vote over the active judges. A second version scores with a learned table over verdict patterns (the "eta-hat" rule) instead of majority vote.

This is not the certifier router that the README calls Path A.

Data: BFF-Bench judgments (459 items, 80 questions, no reference answer; 456 items, 79 questions with a reference answer) and RewardBench-2 Safety (1,800 items, 450 questions). Protocol: 20 random 50/25/25 fit/validation/test splits grouped by question (seed 0). Every baseline (best single, top-3, full jury) is re-picked on each split's fit+validation rows and scored on its test rows. Intervals are 95% question-level bootstrap CIs on test predictions pooled across repeats.

## Main result: held-out accuracy (mean over 20 splits)

| | BFF, no reference | BFF, reference given | RewardBench-2 Safety |
|---|---|---|---|
| Best single judge | 0.847 | 0.909 | 0.845 |
| Static top-3 majority | **0.865** | **0.924** | 0.838 |
| Full jury of 8, majority | 0.828 | 0.924 | 0.807 |
| Panel, majority vote | 0.846 | 0.907 | 0.842 |
| Panel, eta-hat rule | 0.839 | 0.920 | 0.890 |
| Oracle (any judge right) | 0.973 | 0.979 | 0.963 |

Panel (majority vote) minus top-3: -1.9 points [-3.1, -0.8] on BFF without reference, -1.6 [-2.7, -0.8] with reference, +0.4 [-0.7, +1.5] on RewardBench-2. In practice it ends up at roughly the best single judge.

## Per-judge results

Each judge's own accuracy against the human label (all items, not split-based), and Tinker list price per call.

| Judge | $/call | BFF, no reference | BFF, reference given | RewardBench-2 Safety |
|---|---|---|---|---|
| gpt-oss-120b | 0.00072 | **0.854** | 0.921 | 0.779 |
| gpt-oss-20b | 0.00044 | 0.826 | 0.879 | **0.847** |
| deepseek-v3.1 | 0.00261 | 0.806 | **0.930** | 0.729 |
| qwen3.6-35b-a3b | 0.00125 | 0.765 | 0.875 | 0.726 |
| qwen3.5-4b | 0.00073 | 0.745 | 0.908 | 0.732 |
| nemotron3-super-120b | 0.00095 | 0.741 | 0.928 | 0.741 |
| qwen3.5-9b | 0.00144 | 0.739 | 0.890 | 0.786 |
| nemotron3-nano-30b | 0.00029 | 0.667 | 0.792 | 0.786 |

Role each judge got from the panel method (majority-vote version): share of the 20 splits it was kept in the global panel ("kept"), made a slice specialist ("spec"), or dropped as redundant ("dropped").

| Judge | BFF, no reference (kept / spec / dropped) | BFF, reference given | RewardBench-2 Safety |
|---|---|---|---|
| gpt-oss-120b | 95% / 0% / 5% | 45% / 0% / 55% | 5% / 0% / 95% |
| gpt-oss-20b | 75% / 0% / 25% | 10% / 5% / 85% | 100% / 0% / 0% |
| deepseek-v3.1 | 45% / 10% / 45% | 80% / 0% / 20% | 5% / 0% / 95% |
| qwen3.6-35b-a3b | 20% / 10% / 70% | 15% / 0% / 85% | 0% / 15% / 85% |
| qwen3.5-4b | 10% / 20% / 70% | 25% / 0% / 75% | 0% / 0% / 100% |
| nemotron3-super-120b | 10% / 5% / 85% | 40% / 0% / 60% | 0% / 10% / 90% |
| qwen3.5-9b | 0% / 30% / 70% | 15% / 0% / 85% | 20% / 5% / 75% |
| nemotron3-nano-30b | 5% / 10% / 85% | 10% / 0% / 90% | 30% / 0% / 70% |

The judges that are kept most often are the ones that are most accurate on their own (gpt-oss-120b and gpt-oss-20b on BFF without a reference, deepseek-v3.1 with one, gpt-oss-20b on RewardBench-2). Only these are stable in the sense of being kept in at least 80% of splits (gpt-oss-120b 95%, deepseek-v3.1 80%, gpt-oss-20b 100% on RewardBench-2). The best panel found by brute force on BFF without a reference is gpt-oss-120b + gpt-oss-20b + deepseek-v3.1, which is also the static top-3. Logistic-regression weights on the 8 verdicts (BFF, no reference) rank the judges the same way: gpt-oss-120b 1.59, gpt-oss-20b 1.43, deepseek-v3.1 0.94, qwen3.6-35b-a3b 0.65, nemotron3-nano-30b 0.37, and about 0 for qwen3.5-4b, nemotron3-super-120b and qwen3.5-9b.

## Why

**The eta-hat gain on RewardBench-2 is calibration, not panel construction.** RewardBench-2 judges say "correct" on 46% of items while 25% of gold labels are correct, so a plain majority is badly miscalibrated (when 7 of 8 judges say correct, gold is correct only 47% of the time). Anything that learns a threshold fixes this: eta-hat stackers 0.890-0.896, logistic regression on the 8 verdicts 0.893, a single tuned vote-count threshold 0.896, with no panel selection at all. On BFF the verdict rate (55%) matches the gold rate (56%), and tuning does nothing.

**Greedy search was not the problem.** Brute force over all 255 panels: on BFF (no reference) the top-3 by accuracy is the best panel in-sample (rank 1/255). On RewardBench-2 the best panel is gpt-oss-20b alone. With a reference answer the best in-sample panel is 0.7 points above top-3, but panels chosen honestly on fit+validation are 0.2-1.6 points worse. Picking the best panel on the test rows themselves (optimistic) gains only about 1-1.7 points.

**The eta-hat table is too sparse on BFF.** An 8-judge table has 256 cells for roughly 345 fit+validation items (stacker over all 8: 0.815 vs 0.865 for top-3). Logistic regression over the 8 verdicts avoids this but does not beat top-3 either (0.853 / 0.929 / 0.893 on the three settings); its weights roughly reproduce the judge accuracy ranking.

**Specialists have nothing to route to.** The embedding slice (MiniLM, PCA component 5 from the learned-routing notebook) is a real difficulty split: every judge is less accurate on one side. But the best judge is the same on both sides (gpt-oss-120b on BFF, gpt-oss-20b on RewardBench-2), so routing by slice changes nothing. Hand-crafted slices behave the same way. Specialist roles flip between repeats.

**Removing the dominant judges** (7 judges without gpt-oss-120b; 6 without it and gpt-oss-20b) reproduces this on RewardBench-2. On BFF with 7 judges deepseek-v3.1 is better on conceptual items and gpt-oss-20b on calculation-heavy ones, and routed top-3 gains about 1-1.6 points on two slices (CIs barely exclude 0, from dozens of tests). The panel method still ends within noise of top-3 (-0.4 points, CI includes 0).

## One cost result

With a reference answer and the eta-hat rule, a cost penalty of lambda=10 gives accuracy +0.4 points vs top-3 [-1.4, +2.1] at 35% of top-3's cost [33%, 37%]. The accuracy edge does not hold up: reality-check p=0.52 over the 7 lambda values tried, and on three fresh split seeds the difference is 0.0, -0.9 and -0.4 points. It is more accurate than cost-aware single-judge and panel baselines (+1.6 [+0.7, +2.8] over the cost-penalized single judge, which costs about 60% as much). Without a reference answer no lambda reaches parity with top-3 (-2.0 to -3.9 points). At best this supports "within about 1.4 points of top-3 at a third of the cost", only in the setting where judges are given the reference answer.

## Controls

Shuffling labels in fit and validation collapses the panel to the class prior. Question-grouped vs item-level splits differ by about 1 point or less for the panel. A copy-stress test (duplicating a judge's verdict column) passes 20/20 for the eta-hat rule; it does not apply to majority vote, where a duplicate casts two votes.

## Caveats

- 80 questions on BFF: split-to-split sd is about 3 points, so most differences between methods are inside the noise.
- Costs are Tinker list prices per call, so only relative sizes are meaningful.
- The PC5 slice was picked from SHAP on all items in the earlier notebook, so using it here is mildly optimistic.
- Many comparisons were run (slices x pools x policies x lambdas); few of the marginal CIs would survive a multiplicity correction.

## Reproducing

Needs the judgments file (BFF: Drive, Judge Pool Results > BFF-Bench > raw_traces; the RewardBench-2 file has the same schema). VERDICTS and RewardBench-2 text are downloaded from Hugging Face on first use into `data_cache/` (git-ignored). `results/` is also git-ignored.

```bash
cd experiments/role_conditioned_panels
python run.py --data <bff_judgments.jsonl> --bench bff --rule majority --sanity --lambda-sweep
python run.py --data <bff_judgments.jsonl> --bench bff --condition human --rule eta
python explore_12.py --data <bff_judgments.jsonl> --bench bff     # all-subsets search + logistic regression
python cost_ci.py --data <bff_judgments.jsonl>                    # lambda / cost intervals
python embed.py --data <bff_judgments.jsonl> --out emb_bff        # then explore_3.py / explore_pools.py
```

Use `--bench rb2safety` for RewardBench-2 Safety, `--exclude <judge> ...` in `explore_12.py` for reduced pools.
