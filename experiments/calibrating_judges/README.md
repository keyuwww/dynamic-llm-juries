# Can a judge's internal numbers tell us when to escalate its verdict?

Replication of *Calibrating LLM Judges: Linear Probes for Fast and Reliable Uncertainty Estimation* (arXiv 2512.22245), applied to the question behind our dynamic jury.

## The question

A dynamic jury should not call every judge on every item. A cheap judge grades first, and only the verdicts it is probably **wrong** about go to a stronger judge. This is called **escalation**. It only works if we can tell which of the cheap judge's verdicts to doubt.

The paper's idea: when a judge writes its reasoning and verdict, its **activations** (the internal numbers of the model) at the last token already hint at whether the verdict is right. A **probe**, a tiny trained scorer, reads that hint. We test whether it is a good way to choose what to escalate, compared with the other ways we could choose.

## The short answer

- **It works in one place:** RewardBench-2 (safety), with the Qwen judges. There the probe chooses clearly better than every other signal that costs nothing extra.
- **It does not help on BFF** (finance), where rerunning the judge 10 times, or checking whether other judges disagree, chooses much better.
- **On JudgeBench** every signal is about equally good, because most of the gain comes from one trivial rule (escalate answers that were cut off).
- **It does not carry over to a benchmark it was not trained on.** Trained on two benchmarks and tested on the third, it falls to the trivial rule's level.
- The overall gain is a few accuracy points, and the probe needs labelled data and a judge we run ourselves.

## How we tested it

1. **A cheap judge grades every item.** It writes its reasoning and its verdict. A verdict is right if it matches the human label.
2. **A signal gives each verdict a trust score.** The probe is one signal. We compare it with the others below.
3. **The 20% of items with the lowest trust go to a stronger judge,** whose verdict replaces the cheap one. Verdicts that never finished are escalated first.
4. **We measure the accuracy of the final verdicts** against the human labels.

**The one metric: accuracy points above random escalation.** Compare the accuracy of step 4 with the accuracy we would get if the same number of items (20%) were escalated **at random**. The difference, in points, is the score. A signal that knows nothing scores 0.
Real example: Qwen3.5-4B on RewardBench-2. Random escalation gives 0.814. Escalating by the probe gives 0.858. The score is **+4.4 points**.

20% is our choice. The order of the signals is the same at 10% and 30%. At 50% all gaps shrink, because everything converges toward the stronger judge.

**Judges and data.** Three cheap judges that we run ourselves (we need their activations): Qwen3.5-4B, Qwen3.5-9B, gpt-oss-20b. Three benchmarks with human labels: BFF-Bench (459 items), RewardBench-2 Safety (1,800 items), JudgeBench (620 pairs). Each judge/benchmark pair is a **setting**, so there are 9 settings. The stronger judge is the saved top-3 vote of our 8-judge pool for BFF and RewardBench-2, and another hosted judge for JudgeBench.

**The probe.** One linear layer on the judge's activations at the last token it wrote, at the paper's fixed middle layer (16 for the 32-layer Qwen models, 8 for gpt-oss). One probe per judge, trained on the three benchmarks pooled, scoring only questions it was not trained on. Training settings are the paper's. Numbers for the probe are means over 5 training seeds.

**What we compare it with**

| Signal | What gives the trust score | Extra cost |
|---|---|---|
| **Probe** | the judge's activations | none |
| Stated confidence | the judge writes "confidence 0 to 100" | none |
| Token probabilities | how confident the judge's own word choices were | none |
| Free cut-off rule | the answer was finished or cut off | none |
| 10 reruns | the share of 10 new runs that agree with the verdict (also scored by semantic entropy) | about 7 to 12x the generation |
| Other judges disagree | the share of other judges whose verdict differs | needs 2 to 7 other judges |

## Where it works and where it does not

Points above random escalation at 20%, averaged over the 3 judges within each benchmark:

| | BFF (finance) | RewardBench-2 (safety) | JudgeBench |
|---|---|---|---|
| **Probe** | 2.6 | **4.7** | 7.5 |
| 10 reruns | **5.8** | 3.5 | 7.9 |
| Other judges disagree | **6.2** | 0.9 | 6.9 |
| Token probabilities (log-prob) | 3.4 | 1.5 | 7.5 |
| Stated confidence | 2.6 | 0.5 | 8.0 |
| Free cut-off rule | 1.8 | 1.6 | 6.8 |

![By benchmark](figures/fig2_by_benchmark.png)

Each dot is one judge on one benchmark; zero means no better than random.

- **RewardBench-2:** the probe is best of all signals, including the 10 reruns (3.5). The other signals that cost nothing extra score only 0.5 to 1.6. This is the one clear win.
- **BFF:** the probe is weak. 10 reruns and other judges' disagreement are about twice as good, and token probabilities are better too.
- **JudgeBench:** all signals score between 6.8 and 8.0. 13% to 26% of answers there were cut off at 4,096 tokens, so the free cut-off rule alone already gets 6.8 of the 7.5.

Setting by setting, the probe beats 10 reruns in 3 of 9, loses in 5 and ties in 1. It beats the free cut-off rule in 7 of 9 and the best token-probability signal in 5 of 9. Its margins over the free signals are usually under a point or two. It does not beat 10 reruns, but it needs one run instead of about ten.

## What it means for accuracy

Qwen3.5-4B as the cheap judge, sending the 20% it is least sure about to the stronger judge. Accuracy of the final verdicts (one probe training run, as drawn in the curves):

| Benchmark | 4B alone | Stronger judge alone | Random 20% escalated | **Probe, 20% escalated** | 10 reruns, 20% escalated |
|---|---|---|---|---|---|
| RewardBench-2 | 0.807 | 0.841 | 0.814 | **0.858** | 0.846 |
| JudgeBench | 0.706 | 0.758 | 0.716 | **0.777** | 0.790 |
| BFF | 0.760 | 0.874 | 0.783 | 0.810 | 0.841 |

![Cascade curves](figures/fig3_cascade_curves.png)

How to read the curves: the x-axis is the share of items sent to the stronger judge, and the y-axis is the accuracy of the final verdicts. At 0% it is the cheap judge alone, and at 100% it is the stronger judge alone. The dashed line is random escalation, and the dotted line is the best possible. A good signal rises quickly above the dashed line.

- **RewardBench-2 and JudgeBench:** with the probe, sending only 20% to the stronger judge gives a better result than the stronger judge alone. The cheap judge is right on most easy items, and the stronger judge fixes its doubtful ones.
- **BFF:** it does not get there. The stronger judge is much better than the 4B on BFF (0.874 against 0.760), so you have to escalate about half the items to approach it.

## Does it carry over to a benchmark it was not trained on?

We trained the probe on two benchmarks and scored the third, which it had never seen. Points above random escalation, mean of the 3 judges:

| | Probe, same benchmark | **Probe, unseen benchmark** | 10 reruns | Free cut-off rule |
|---|---|---|---|---|
| BFF | 2.4 | 2.5 | 5.8 | 1.8 |
| RewardBench-2 | 4.7 | **0.6** | 3.5 | 1.6 |
| JudgeBench | 7.7 | 7.3 | 7.9 | 6.8 |
| **Mean of the 9 settings** | 4.9 | **3.5** | 5.7 | 3.4 |

"Same benchmark" here is one probe training run, so it differs slightly from the 5-seed means in the earlier table.

On an unseen benchmark the probe falls to the free cut-off rule's level, and on RewardBench-2, its one win, it falls to nothing (for the Qwen3.5-9B it is worse than random). So the probe needs labelled data from each new kind of task. The paper reports that training on a much broader mixture generalizes better; we did not test that.

## Which layer to read the probe from

![The probe at each layer](figures/fig4_layers.png)

The paper reads one fixed middle layer. We also trained the probe at every saved layer. Top row: how well the probe separates right from wrong verdicts at each layer. Bottom row: the validation error that an automatic layer-picking rule minimizes, and the layers it picks.

- **Qwen3.5-9B:** the ranking peaks at the paper's layer 16 on all three benchmarks, and the validation rule picks it in 4 of 5 folds.
- **Qwen3.5-4B:** on RewardBench-2 and JudgeBench the ranking is flat from layer 8 to layer 30, and on BFF it is low at every layer; the rule picks layers 28 to 30.
- **gpt-oss-20b:** the ranking is best in the earliest layers and falls to chance in deep layers (the paper's training settings probably fail to fit its raw deep-layer activations; we did not check). The rule picks layers 0 to 4.
- For the cascade, the layer barely matters for the Qwen judges: the gain differs by under a point between layers 8 and the last, about the noise of one training run.

## Is the probe's number a good probability?

The paper's main claim is that the probe's number is well calibrated: "80%" means about 80% are right. **We did not reproduce this** (Qwen3.5-4B only). On RewardBench-2 the probe ranks right above wrong verdicts well (AUROC 0.89, against 0.55 for the judge's stated confidence and 0.79 for 10 reruns), but its calibration error is 0.090 while a constant guess scores 0.012.

## Limits

- **Only for judges we run ourselves.** The probe needs the judge's activations, so it cannot be used on API-only judges. The paper states the same limit.
- **It needs labelled data** from each kind of task, and does not carry over to unseen ones.
- **Three judges from two families.** We could not read the activations of Nemotron or Qwen3.6-35B, and the largest judges are too big for our setup.
- **The stronger judges on BFF and RewardBench-2 are saved verdicts** from our earlier 8-judge pool: short answers through an API, not reasoning runs.
- **Cut-off answers on JudgeBench** count as wrong and make up 13% to 26% of the verdicts there.
- **Choices the paper leaves open:** which token is "the last token" (we use the last token the judge writes), the prompt for single-response grading, the 4,096-token cap, and the training set (the paper uses its own PPE data; we use our three benchmarks).
- **Not done:** the paper's broader training data (PPE), temperature-scaled MaxProb, Chain-of-Embedding and CoT-kinetics baselines, and the loss and rerun-count ablations.

## How the results were checked

- **Faster generation changes nothing.** Text is generated with vLLM, and the activations are read by a separate full pass of the model. Against Hugging Face's own decoding on 48 items, the two agree on 98.9% of tokens, and every difference was an exact tie in rounded numbers. On items with identical text the activations match to cosine similarity 0.9993 or better.
- **Cut-off answers cannot inflate the probe.** A probe can easily spot "this judge never finished", so every signal escalates unfinished answers first, and the free cut-off rule is reported as its own baseline.

## Files

| File | What it does |
|---|---|
| `modal_generate.py` | runs generation, activations and token statistics on Modal GPUs |
| `vllm_generate.py`, `acts_from_gen.py`, `token_stats.py` | fast generation; reading the judge's activations; token-probability signals |
| `generate_judge.py` | single-script Hugging Face version (the reference for the check above) |
| `judge_data.py`, `prompts.py` | the benchmarks and the paper's prompts |
| `evaluate.py`, `metrics.py` | probe training and the calibration table |
| `cascade_eval.py`, `summarize_cascade.py` | the escalation experiment, including the unseen-benchmark test |
| `layer_sweep.py` | trains the probe at every layer |
| `make_figures.py`, `figures/` | the plots |
| `check_equivalence.py`, `check_greedy.py` | the equivalence checks |

Generated outputs (verdicts, activations) are not in the repo. `modal_generate.py` reads the saved 8-judge verdict files and the cached VERDICTS and RewardBench-2 tables from paths set at the top of the file; adjust them to where those files live. `cascade_eval.py` imports `data.py` and `audit.py` from `../role_conditioned_panels`.
