# Do weaker judges sense how hard an item is for the expert judge? (10/29)

Stored verdicts and the existing confidence run, no new calls. Code: `experiments/cross_benchmark/difficulty_awareness.py`;
full tables: `experiments/cross_benchmark/results/flips/difficulty_awareness.{md,json}`.

**Setup.** On 4 pairwise benchmarks, the "expert" is the most accurate judge on each benchmark. Its error = wrong
in at least one answer order (all pairs). A weaker judge's **doubt** = its low stated confidence (0–100,
confidence run, mean of both orders). AUROC 0.5 = chance. 28 points = 7 weaker judges × 4 benchmarks.

## Answer
**Yes. Weaker judges' doubt tracks how hard an item is for the expert, not just whether the weaker judge itself
fails.** Excluding the weakest judge (Nemotron-Nano), the signal is clear on every benchmark.

## Results

| Test | Question | Result |
|---|---|---|
| T1 | On pairs the weak judge gets **right**, does its doubt still flag the expert's errors? | **Yes.** AUROC 0.72 on average (0.74 without Nemotron-Nano, minimum 0.65); significant on 26 of 28 points. The two exceptions are Nemotron-Nano on JudgeBench and MT-Bench human. |
| T1 | On pairs the weak judge gets **wrong**? | **Much weaker:** 0.55. When the weak judge is itself wrong, its doubt says little about the expert. |
| T1 | Does doubt add beyond the weak judge's own correctness? (logistic, within benchmark) | **Yes on 19 of 28 points.** Both terms matter: the weak judge being wrong is the stronger predictor (median log-odds +2.1), and doubt adds +0.36 per standard deviation. |
| T2 | Does doubt predict the expert's errors better than other weak judges' errors? | **Slightly.** +0.02 AUROC on average, higher on 22 of 28 points (Wilcoxon p < 0.001). It predicts **stronger** peers' errors better than weaker peers' (0.72 vs 0.68, p = 0.001). The signal is general item difficulty, aimed at the errors of capable judges, rather than at noise. |
| T4 | Within a model family, do bigger models sense difficulty better? | **Mostly.** Awareness rises with size in 7 of 10 family-benchmark comparisons. It always rises from Nemotron-Nano to Super; Qwen 4B → 9B → 35B is flat or mixed. |
| T5a | Does doubt track independent difficulty (share of the other 6 judges wrong)? | **Moderately:** Spearman ρ 0.42 on average (0.30–0.61; Nemotron-Nano 0.07–0.24). |
| T5b | Does doubt flag items where human annotators split? | **Somewhat:** AUROC 0.66 on MT-Bench human (0.66–0.71 without Nemotron-Nano; 182 pairs with several votes), 0.59 on AlpacaFarm. |
| T5c | Does doubt track whether the expert, or the judge itself, could **solve** the question (BFF)? | **No:** 0.54 for the expert, 0.50 for itself. Doubt reflects how hard the comparison is, not how hard the underlying finance problem is. |
| T5d | Controlled pairs: does confidence drop on built-in ties? | **For some judges.** With the same answer in both slots, DeepSeek drops from 93 to 50, Nemotron-Super from 92 to 60 and gpt-oss-120b from 89 to 77. Qwen and Nemotron-Nano barely move (85–96). A single +10% changed figure lowers confidence only slightly (87–89 vs 89–93 on real pairs). |

## What this means
- **Weaker judges sense difficulty even when they get the item right.** That's the strongest evidence that they
  sense difficulty, not only their own failure.
- **The difficulty they sense is about the comparison**: near-ties, contested human labels, items capable judges
  get wrong. It is not about whether the underlying problem is solvable.
- **Model differences matter.** Qwen judges almost never lower their confidence, even on identical answers, yet their
  doubt still ranks items well. Nemotron-Nano's confidence carries little information.

## Caveats
- One sample per verdict. Asking for confidence changed 12–20% of verdicts; confidence comes from the new run,
  correctness from the stored run.
- The expert is chosen on the full data. The same 7 judges appear on all 4 benchmarks, so the 28 points are not
  independent.
- T1 conditional AUROCs rest on few expert errors where the weak judge is right (4–20% of 112–358 pairs).
- Solve labels come from the 1,024-token BFF answer run, graded by two judges; pairs where the graders disagree
  are dropped.

## Test 3: ask the judges directly (10/30, new calls)
Each of the 6 judges still on Tinker was asked how likely a strong expert judge is to pick the better answer
(0–100), told not to judge the item itself. Two prompts: **question only** (no answers shown) and **with both
answers** (first order only, one sample). 16.9K calls plus retries, $23.62. 98–100% parsed after re-running items that ran out of
tokens (mostly JudgeBench, where judges tried to solve the problem). Code: `run_difficulty.py`, `analyze_difficulty.py`;
raw outputs: `results/difficulty/<bench>/judgments.jsonl`; tables: `results/flips/difficulty_prediction.{md,json}`.
Same outcome as above (expert wrong in either order); all three scores are compared on the same pairs.

| Question | Result |
|---|---|
| Can a judge predict the expert's errors **from the question alone**? | **No.** AUROC 0.53 on average. Only slightly above chance on BFF and JudgeBench (pooled 0.61–0.63), and at chance on AlpacaFarm and MT-Bench human (0.49–0.52). |
| **With the answers shown**, does the explicit prediction work? | **Yes.** AUROC 0.69 on average for single judges (0.61–0.78); pooled over the weaker judges 0.71–0.83. |
| Is it better than the judge's implicit doubt (its own low confidence)? | **No, slightly worse:** 0.69 vs 0.72 (Wilcoxon p = 0.001). Pooled, the two are about equal (0.71–0.83 vs 0.70–0.82). The two scores are moderately correlated (ρ 0.57), so they partly measure the same thing. |
| Does it work on pairs the judge itself gets right? | **Yes:** 0.70, the same as on all pairs. It is not just the judge flagging its own failure. |
| Can the expert predict its own errors this way? | **Yes, about as well as by confidence:** gpt-oss-120b 0.75–0.79 explicit vs 0.80–0.81 implicit. |

**What this means.** Weaker judges sense difficulty from how close the two answers are, not from the question.
Asking them about the expert adds nothing over asking for their own confidence, so the cheaper signal (confidence,
which comes free with a verdict) is the one to use.

**Caveats.** The implicit score averages two answer orders, the explicit one is a single call, which favours the
implicit score. Most judges are over-optimistic (mean predicted expert accuracy 74–96%), but only ranking matters for AUROC.

## Selective judging: what to do with the flags (10/30, no new calls)
Code: `selective_judging.py` (tables `results/flips/selective_judging.{md,json}`), `sensor_router.py`
(`results/flips/sensor_router.{md,json}`), `cascade_quicklook.py`.

| Question | Result |
|---|---|
| Can a router pick the right judge per item from each judge's skill at spotting others' errors? | **No.** Ties with the best single judge (−0.023 to +0.014, grouped CV) and needs every judge's confidence. Trusting the most confident judge is worse (−0.03 to −0.13). |
| Does a cheap judge answering first and escalating its doubts save money? | **Only on AlpacaFarm** (gpt-oss-120b, 20% escalated: same accuracy at 55% of the cost; in-sample thresholds). |
| If the 20% most-doubted items go to a human, how many expert errors are caught? | **43–61%** on BFF, JudgeBench and MT-Bench human; 29–33% on AlpacaFarm (random: 20%). Expert accuracy on the kept items rises 4–5 points. |
| Which doubt is best for this? | The expert's own confidence and the pooled weaker judges are about equal; single good weak judges come close (gpt-oss-20b catches 26–45%). |
| Would escalating flagged items to another model help? | **No.** On them the expert drops to 0.61–0.72 (0.76–0.95 elsewhere) and no other judge beats 0.66, yet some judge is right 89–94% of the time. |

**What this means.** Doubt marks items that are hard for every judge, so it can't say which judge is right. Its use
is selective judging: send flagged items to a human or a reference answer, not to a bigger model. This runs against
the escalate-to-a-stronger-model design of Trust or Escalate and model cascades.
