# Can a judge's activations tell us when to escalate its verdict?

Replication of *Calibrating LLM Judges: Linear Probes for Fast and Reliable Uncertainty Estimation* (arXiv 2512.22245), applied to the question behind our dynamic jury.

## The question

A dynamic jury should not call every judge on every item. A cheap judge grades first, and only the verdicts it is probably **wrong** about go to a stronger judge. This is called **escalation**. It only works if we can tell which of the cheap judge's verdicts to doubt.

The paper's idea: when a judge writes its reasoning and verdict, its **activations** at the last token already hint at whether the verdict is right. Activations are the vectors the model computes inside itself as it reads and writes. A **probe**, a tiny trained scorer, reads that hint. We test whether it is a good way to choose what to escalate, compared with the other ways we could choose.

## The short answer

Every number is for one cheap judge on one benchmark; nothing is averaged.

- **It works in one place:** RewardBench-2 (safety) with the Qwen judges. The probe gets 85.8% (Qwen3.5-4B) and 88.7% (Qwen3.5-9B), ahead of 10 reruns (84.6%, 86.2%) and of the other signals that cost nothing extra (80.5% to 84.3%).
- **It does not help on BFF** (finance): for all three judges, rerunning the judge 10 times or checking whether other judges disagree chooses better. The gap is large for the 4B and 9B (for the 9B: 85.8% and 86.3%, against 82.3% for the probe) and 1.5 to 2 points for gpt-oss.
- **On JudgeBench** every signal is about equally good. 13% to 26% of the answers were cut off, and every signal escalates those first, so the signals differ only on the rest.
- **It does not carry over where it matters.** Trained on two benchmarks and scored on the third, the probe loses 1.5 to 6.9 points on RewardBench-2, its one win, and ends at about random escalation (4B) or below it (9B). On BFF and JudgeBench it loses about a point or less, but it was not better than the alternatives there either.
- The probe needs labelled data and a judge we run ourselves, and the gains are a few accuracy points.

## How we tested it

1. **A cheap judge grades every item.** It writes its reasoning and its verdict. A verdict is right if it matches the human label.
2. **A signal gives each verdict a trust score.** The probe is one signal. We compare it with the others below.
3. **The 20% of items with the lowest trust go to a stronger judge,** whose verdict replaces the cheap one. Verdicts that never finished are escalated first.
4. **We measure the accuracy of the final verdicts** against the human labels, and compare it with the accuracy we would get if the same 20% were escalated **at random**.

Real example: Qwen3.5-4B on RewardBench-2 gets 81.4% with random escalation and 85.8% when the probe chooses. 20% is our choice. At 10%, 20% and 30% the probe beats 10 reruns in 2, 3 and 3 of the 9 settings.

**Judges and data.** Three cheap judges that we run ourselves (we need their activations): Qwen3.5-4B, Qwen3.5-9B and gpt-oss-20b. Three benchmarks with human labels: BFF-Bench (459 items), RewardBench-2 Safety (1,800 items) and JudgeBench (620 pairs). Each judge on each benchmark is one **setting**, so there are 9.

**The stronger judge.** On BFF and RewardBench-2 it is the majority vote of the three best *other* judges in our 8-judge pool; the cheap judge's own model is never in it. On JudgeBench it is one other judge we ran ourselves.

| Cheap judge | BFF: stronger panel | RewardBench-2: stronger panel | JudgeBench: stronger judge |
|---|---|---|---|
| Qwen3.5-4B | gpt-oss-120b, gpt-oss-20b, DeepSeek-V3.1 | gpt-oss-20b, Nemotron-3-Nano, Qwen3.5-9B | Qwen3.5-9B |
| Qwen3.5-9B | gpt-oss-120b, gpt-oss-20b, DeepSeek-V3.1 | gpt-oss-20b, Nemotron-3-Nano, gpt-oss-120b | gpt-oss-20b |
| gpt-oss-20b | gpt-oss-120b, DeepSeek-V3.1, Qwen3.6-35B | Nemotron-3-Nano, Qwen3.5-9B, gpt-oss-120b | Qwen3.5-9B |

**The probe.** One linear layer on the judge's activations at the last token it wrote, at the paper's fixed middle layer (16 for the 32-layer Qwen models, 8 for gpt-oss). One probe per judge, trained on the three benchmarks pooled and scoring only questions it was not trained on. Training settings are the paper's. The probe's accuracies are means over 5 training seeds of the same setting.

**What we compare it with**

| Signal | What gives the trust score | Extra cost |
|---|---|---|
| **Probe** | the judge's activations | none |
| Stated confidence | the judge writes "confidence 0 to 100" (a second run) | none |
| Token log-prob | how confident the judge's own word choices were (the average log-probability of the words it wrote) | none |
| 10 reruns | the share of 10 new runs that agree with the verdict (also scored by semantic entropy) | about 7 to 12x the generation |
| Other judges disagree | the share of other judges whose verdict differs | needs 2 to 7 other judges |

## Where it works and where it does not

![Accuracy by judge and benchmark](figures/fig1_by_judge_and_benchmark.png)

Each panel is a benchmark and each group of dots is one cheap judge. Dashed line: the cheap judge alone. Dotted: random 20% escalation. Solid: the stronger judge alone.

- **RewardBench-2:** for the two Qwen judges the probe is the best signal: 85.8% (4B) and 88.7% (9B), above 10 reruns (84.6%, 86.2%), above the stronger judge alone (84.1% for both) and well above random (81.4%, 84.1%). For gpt-oss-20b the probe (88.6%) is level with 10 reruns (88.9%) and ahead of token log-prob (87.1%); there the stronger panel (81.6%) is below the cheap judge itself (83.9%).
- **BFF:** the probe (81.5%, 82.3%, 82.2% for the 4B, 9B and gpt-oss) is behind 10 reruns (84.1%, 85.8%, 83.7%) and behind other judges' disagreement (85.2%, 86.3%, 84.3%) for all three judges. For gpt-oss, stated confidence (85.2%) is also above it.
- **JudgeBench:** the probe (77.5%, 79.2%, 72.6%) is within 1.5 points of the best signal for every judge. For gpt-oss every signal except stated confidence ends at exactly 72.6%: 26% of its answers were cut off, and escalating those first leaves little to rank. For the 9B the stronger judge (gpt-oss) is weaker than the 9B itself (59.2% against 75.8%).

Setting by setting, the probe beats 10 reruns in 3 of 9, loses in 5 and ties in 1. It beats token log-prob in 5 of 9 (loses 3, ties 1) and stated confidence in 5 of 9 (loses 4).

<details><summary>Full table: every judge on every benchmark (accuracy %, 20% escalated)</summary>

The best of the five signals in each row is in bold. Stated confidence comes from its own second run of the cheap judge.

| Benchmark | Cheap judge | Cheap alone | Random 20% | Probe | 10 reruns | Other judges | Token log-prob | Stated conf. | Stronger alone |
|---|---|---|---|---|---|---|---|---|---|
| BFF | Qwen3.5-4B | 76.0 | 78.3 | 81.5 | 84.1 | **85.2** | 81.3 | 79.7 | 87.4 |
| BFF | Qwen3.5-9B | 77.8 | 79.7 | 82.3 | 85.8 | **86.3** | 83.2 | 83.2 | 87.4 |
| BFF | gpt-oss-20b | 79.3 | 80.4 | 82.2 | 83.7 | 84.3 | 84.3 | **85.2** | 84.7 |
| RewardBench-2 | Qwen3.5-4B | 80.7 | 81.4 | **85.8** | 84.6 | 83.1 | 81.8 | 80.5 | 84.1 |
| RewardBench-2 | Qwen3.5-9B | 84.1 | 84.1 | **88.7** | 86.2 | 83.2 | 84.3 | 83.3 | 84.1 |
| RewardBench-2 | gpt-oss-20b | 83.9 | 83.4 | 88.6 | **88.9** | 83.4 | 87.1 | 86.1 | 81.6 |
| JudgeBench | Qwen3.5-4B | 70.6 | 71.7 | 77.5 | **79.0** | 77.9 | 76.8 | 78.5 | 75.8 |
| JudgeBench | Qwen3.5-9B | 75.8 | 72.5 | 79.2 | 78.7 | 76.9 | **79.8** | 79.7 | 59.2 |
| JudgeBench | gpt-oss-20b | 59.2 | 62.5 | **72.6** | **72.6** | **72.6** | **72.6** | 71.1 | 75.8 |

</details>

## What it means for accuracy

![Cascade curves](figures/fig2_cascade_curves.png)

Qwen3.5-4B as the cheap judge. x-axis: the share of items sent to the stronger judge (0% = the 4B alone, 100% = the stronger judge alone). Dashed: random escalation. Dotted: the best possible.

Accuracy (%) of the final verdicts with 20% escalated:

| | 4B alone | Stronger judge alone | Random 20% | **Probe, 20%** | Stated confidence, 20% | 10 reruns, 20% |
|---|---|---|---|---|---|---|
| RewardBench-2 | 80.7 | 84.1 | 81.4 | **85.8** | 80.5 | 84.6 |
| JudgeBench | 70.6 | 75.8 | 71.7 | 77.5 | 78.5 | **79.0** |
| BFF | 76.0 | 87.4 | 78.3 | 81.5 | 79.7 | **84.1** |

The probe's numbers are means over 5 training seeds; the curves show one training run, so they can differ by up to about half a point. The stated-confidence curve starts at a different height at 0% because it comes from its own second run of the 4B, whose verdicts differ slightly.

- On RewardBench-2 and JudgeBench, escalating only 20% with the probe beats the stronger judge alone: the cheap judge keeps the items it is sure about, and the stronger judge handles the doubtful ones.
- On BFF it does not: the stronger judge is much better there (87.4% against 76.0%), and the probe's cascade only reaches it when about 80% of the items go up (10 reruns: about 94%).
- On RewardBench-2 the 4B's stated confidence does no better than random escalation (80.5% against 81.4%).

## Does it carry over to a benchmark it was not trained on?

Accuracy (%) with 20% escalated. In the "unseen" column the probe was trained on the other two benchmarks only. "Same benchmark" is one training run.

| Benchmark | Cheap judge | Random 20% | Probe, same benchmark | **Probe, unseen benchmark** | 10 reruns |
|---|---|---|---|---|---|
| BFF | Qwen3.5-4B | 78.3 | 81.0 | **81.5** | 84.1 |
| BFF | Qwen3.5-9B | 79.7 | 82.8 | **81.7** | 85.8 |
| BFF | gpt-oss-20b | 80.4 | 81.9 | **81.9** | 83.7 |
| RewardBench-2 | Qwen3.5-4B | 81.4 | 85.8 | **81.8** | 84.6 |
| RewardBench-2 | Qwen3.5-9B | 84.1 | 88.8 | **81.9** | 86.2 |
| RewardBench-2 | gpt-oss-20b | 83.4 | 88.6 | **87.1** | 88.9 |
| JudgeBench | Qwen3.5-4B | 71.7 | 77.7 | **77.4** | 79.0 |
| JudgeBench | Qwen3.5-9B | 72.5 | 79.4 | **78.5** | 78.7 |
| JudgeBench | gpt-oss-20b | 62.5 | 72.6 | **72.6** | 72.6 |

- **RewardBench-2, the probe's one win, does not carry over:** unseen, it drops by 4.0 points (4B), 6.9 (9B) and 1.5 (gpt-oss) compared with being trained on RewardBench-2's own questions. For the 4B it ends at about random escalation (81.8% against 81.4%) and for the 9B below it (81.9% against 84.1%).
- **BFF and JudgeBench:** the unseen-benchmark probe is within 1.1 points of the same-benchmark probe in all six settings.
- So the probe needs labelled data from each new kind of task.

## Which layer to read the probe from?

![The probe at each layer](figures/fig3_layers.png)

Top: how well the probe separates right from wrong verdicts at each layer. Bottom: the validation error that an automatic layer-picking rule minimizes, and the layers it picks. Dotted line: the paper's fixed layer.

- **Qwen3.5-9B:** the ranking peaks at the paper's layer 16, and the rule picks it.
- **Qwen3.5-4B:** flat from layer 8 to 30 on RewardBench-2 and JudgeBench; the rule picks 28 to 30.
- **gpt-oss-20b:** best in the earliest layers, near chance in deep layers; the rule picks 0 to 4.

## Is the probe's number a good probability?

The paper's main claim is that the probe's number is well calibrated: "80%" means about 80% are right. **We did not reproduce this** (Qwen3.5-4B only). On RewardBench-2 the probe ranks right above wrong verdicts well (AUROC 0.89, against 0.55 for the judge's stated confidence and 0.79 for 10 reruns), but its calibration error is 0.090 while a constant guess scores 0.012.

## Limits

- Only for judges we run ourselves (it needs their activations), and it needs labelled data per kind of task.
- Three judges from two families. Nemotron and Qwen3.6-35B could not be read.
- The stronger judges on BFF and RewardBench-2 are saved verdicts from our earlier 8-judge pool (short API answers, not reasoning runs).
- 13% to 26% of JudgeBench answers were cut off at 4,096 tokens and count as wrong.
- Choices the paper leaves open: which token is "the last token" (we use the last token the judge writes), the prompt for single-response grading, the 4,096-token cap, and the training set (the paper uses its own PPE data; we use our three benchmarks).
- Not done: the paper's broader training data (PPE), temperature-scaled MaxProb, Chain-of-Embedding, CoT-kinetics, and the loss and rerun-count ablations.

## How the results were checked

Generation uses vLLM and the activations come from a separate full pass. Against Hugging Face's own decoding on 48 items they agree on 98.9% of tokens, and every difference was an exact tie; on identical text the activations match to cosine similarity 0.9993 or better. Every signal escalates unfinished answers first, so cut-off answers cannot inflate the probe.

## Files

| File | What it does |
|---|---|
| `modal_generate.py` | runs generation, activations and token statistics on Modal GPUs |
| `vllm_generate.py`, `acts_from_gen.py`, `token_stats.py` | fast generation; the judge's activations; token-probability signals |
| `generate_judge.py` | single-script Hugging Face version (reference for the check) |
| `judge_data.py`, `prompts.py` | the benchmarks and the paper's prompts |
| `evaluate.py`, `metrics.py` | probe training and the calibration table |
| `cascade_eval.py`, `summarize_cascade.py` | the escalation experiment, including the unseen-benchmark test |
| `layer_sweep.py` | trains the probe at every layer |
| `make_figures.py`, `figures/` | the plots |
| `check_equivalence.py`, `check_greedy.py` | the equivalence checks |

Generated outputs (verdicts, activations) are not in the repo. `modal_generate.py` reads the saved 8-judge verdict files and the cached VERDICTS and RewardBench-2 tables from paths set at the top of the file. `cascade_eval.py` imports `data.py` and `audit.py` from `../role_conditioned_panels`.

