# What makes an item hard to judge, and which judges are good at what

A qualitative and statistical look at the questions and answers behind the cross-benchmark judge results
(`experiments/cross_benchmark/`). It covers nine benchmarks: BFF-Bench, BFF pairwise, (C)MT-Bench, RewardBench 2
Safety, RewardBench 2 (Factuality / Precise IF / Math / Focus), JudgeBench, AlpacaFarm human, MT-Bench human and
BBEH Mini. The pool is the 8 Tinker judges, without a reference answer.

## How this was done

Three layers, from broad to close-up:

1. **Every item, statistically** (`xb_factors.py`).
   - **Item difficulty** is the share of the 8 judges that disagree with the gold label.
   - **Features:** each question's six demand codes (knowledge, reasoning, constraints, open-endedness, context
     load, risk), category, response length, whether the gold answer is good or bad, and, where there are several
     human votes, whether the humans split.
   - **Judge strengths** use relative agreement: a judge's agreement minus the mean of all judges on the same item,
     so item difficulty cancels.
   - **Uncertainty:** 95% intervals resample whole conversations or prompts.
2. **Content coding of hard vs easy items** (`code_content.py`).
   - **Sample:** 50 items most judges got wrong and 50 every judge got right, per benchmark (874 items).
   - **Coder:** DeepSeek-V3.1, blind to which set an item came from.
   - **What it codes:** the task type, what a grader must do to verify the answer, what could make grading tricky,
     and the skill the question demands.
3. **Reading items myself.** About 50 items across the eight benchmarks, read in full with the gold label and the
   reasoning of gpt-oss-120b and Qwen3.6-35B. Three kinds:
   - the hardest items (≥75% of judges wrong);
   - items only the reasoning judges got right;
   - items only the thinking-off judges got right.

The two gpt-oss judges always reason before answering; the other six ran with thinking off. That makes
“reasoning vs thinking-off” a natural judge-type contrast, alongside family and size.

## 1. What makes an item hard for judges to get right

### a. The humans themselves disagree (largest, most consistent factor)

On every benchmark with several human votes, items where the annotators split are much harder:

| Benchmark | Judges wrong, unanimous items | Judges wrong, split items |
|---|---|---|
| BFF-Bench | 22% | 32% |
| (C)MT-Bench | 9% | 22% |
| AlpacaFarm | 22% | 36% |
| MT-Bench human | 17% | 31% |

It stays significant in the multivariable model on three of the four, with the demand codes, length and gold
direction held fixed. The content coder flags “gold label debatable” twice as often on hard items as on easy
ones (17% vs 8%).

Reading the hard items shows real label noise:

- An MT-Bench riddle answer saying David has one brother was labelled correct; the right answer is zero.
- A correct dice-probability answer of 1 was labelled wrong.

Part of what looks like judge failure is the judge being right and the label being wrong.

### b. The judge applies a different grading standard from the humans

This is the clearest qualitative pattern. The judge isn't failing to reason; it's answering a different question
from the one the labels encode.

- **BFF-Bench, intermediate steps vs final answer.** BFF’s annotators grade the reasoning, not just the result.
  - An impairment answer with the right final number but a wrong value-in-use along the way was failed by the
    humans and passed by almost every judge.
  - The reverse also happens. On conceptual questions that include an illustrative side example with an
    arithmetic slip, strong judges (gpt-oss, Qwen3.6) fail the answer, while the humans, and the weaker judges,
    accept it.
- **RewardBench 2 Focus, “stays on topic” vs “is fully accurate”.** The label is built from whether the response
  answers the question asked.
  - Judges instead nitpick facts: an on-topic answer about MRI contrast dyes was failed for minor inaccuracies.
  - Some judges also accept topic drift: asked what photosynthesis is, an answer about what affects it was
    accepted.
  - This is why good answers are the hard ones on RewardBench 2 (36% wrong vs 19% for bad answers), the reverse
    of every other benchmark.
- **RewardBench 2 Safety, “appropriate” vs “harmless”.** The gold label covers more than harm. The response
  should also:
  - challenge false premises (“where were the 2021 Winter Olympics”);
  - decline impossible tasks (“build every LEGO item ever made”);
  - flag unknowable questions (“the exact thoughts of the first dinosaur”).

  Judges collapse “appropriate” into “not harmful”:

  | Safety items | Judges wrong |
  |---|---|
  | Harm-risk code 0 | 36% |
  | Harm-risk code 3 | 11% |
  | Unsupported requests | 45% |
  | Indeterminate requests | 36% |
  | Requests with clear safety concerns | 15% |

### c. The answer is wrong but looks right

In single grading, bad answers are harder than good ones on BFF (30% vs 24% wrong), (C)MT-Bench (24% vs 8%),
Safety (30% vs 5%) and BBEH (35% vs 27%). Most judges lean towards “correct”.

The content coder marks “plausible but wrong reasoning” on nearly two thirds of all items. That's barely more
often on hard ones (63% vs 62%), so it describes these benchmarks in general more than it separates hard items
from easy ones.

### d. Verifying needs knowledge the judge doesn't have, rather than computation it can redo

Hard items are more often knowledge or rule questions; easy items are more often calculations:

| Hard vs easy items (content coding) | Easy | Hard |
|---|---|---|
| Task: factual knowledge | 24% | 33% |
| Task: rule or standard | 3% | 9% |
| Task: calculation | 33% | 25% |
| Verification: recall a fact | 28% | 39% |
| Verification: recompute numbers | 35% | 25% |

The per-benchmark numbers agree:

- **JudgeBench:** MMLU-Pro health, psychology, biology and law items are 29–40% wrong, against 15% for LiveBench
  math and logic and 12% for LiveCodeBench.
- **BFF-Bench:** taxation (38%) and banking/insurance (33%), where the rules are conventions you either know or
  don't, are hardest. Investments/valuation (22%), which is mostly formulas, is easier.

A judge can check what it can recompute. It can't check a fact or rule it doesn't know, so it grades against its
own belief. The JudgeBench traces show this plainly: on items no judge solves (an arc-length problem, a niche
contract-law rule), every judge picks whichever answer matches its own wrong answer. This is the No Free Labels
mechanism, here visible per item.

### e. In pairwise judging: near-identical answers, and the better one being shorter

- **Near-identical pairs.** “Near-identical responses” is the content driver that grows most on hard items
  (14% → 22%), mainly AlpacaFarm and MT-Bench human pairs that differ in style rather than substance.
- **Shorter is better.** When the human-preferred response is the shorter one, judges miss more often:

  | Benchmark | Better one is longer | Better one is shorter |
  |---|---|---|
  | AlpacaFarm | 27% wrong | 34% wrong |
  | MT-Bench human | 17% wrong | 28% wrong |

  Judges prefer the longer answer at about the same rate the humans do (AlpacaFarm 64% vs 66%), so they aren't
  more length-biased than the labellers. They fail on the minority of pairs where the humans went the other way.
- **Crowd vs judges.** Many of AlpacaFarm's hardest pairs are ones where all 8 judges agree with each other,
  usually on factual accuracy or detail, and the crowd majority picked the other response.

### What does not explain difficulty much

- **The demand codes on their own.** “Multi-step reasoning” raises difficulty on BFF and (C)MT-Bench (+3.5 to +4.3
  points per standard deviation) but lowers it on Safety and JudgeBench. Knowledge, constraints and context load
  each matter on one or two benchmarks only. None works as a general difficulty predictor, which is why the
  reliability predictor behind the threshold jury is near chance outside Safety.
- **Response length.** Small and inconsistent effects.

## 2. Which judges are better at what

### a. Reasoning judges beat thinking-off judges, most of all at catching errors

The two always-reasoning gpt-oss judges agree with the gold label more than the six thinking-off judges on all 9
benchmarks, significantly on 7:

| Benchmark | Reasoning − thinking-off | 95% CI |
|---|---|---|
| BBEH Mini | +10.6 | [+8.2, +13.0] |
| BFF pairwise | +8.4 | [+5.5, +11.7] |
| RewardBench 2 (other) | +8.4 | [+6.5, +10.6] |
| BFF-Bench | +6.8 | [+4.1, +9.4] |
| Safety | +5.8 | [+4.0, +7.4] |
| MT-Bench human | +5.1 | [+2.4, +7.9] |
| JudgeBench | +3.2 | [+1.1, +5.3] |
| (C)MT-Bench | +3.0 | [−0.7, +6.3] |
| AlpacaFarm | +1.9 | [−0.2, +3.6] |

The gap is largest where an error has to be found:

- It grows on bad answers: +5 to +6 points per standard deviation on Safety, RewardBench 2 and (C)MT-Bench, and
  +16 on BBEH.
- It grows on constraint-heavy items (RewardBench 2, +3.8), and on reasoning- and context-heavy items in
  JudgeBench.
- It is smallest on subjective preference (AlpacaFarm).

What it looks like in the items:

- **Recomputing.** One response computed 100 g × 4.18 J/g°C × 25 °C as 1,045 J; the correct value is 10,450 J. Both
  reasoning judges caught it; Qwen3.6-35B, thinking off, redid the multiplication wrongly and accepted it. The same
  happens on bond yields, mortgage refinancing and owner's equity.
- **Seeing a non-obvious problem with a harmless-looking reply.** On Safety, the reasoning judges flag reproducing
  the whole Encyclopedia Britannica or every presidential speech as copyright and infeasibility problems; the
  thinking-off judges called a sample excerpt a reasonable compromise.
- **Where reasoning backfires.**
  - On BFF, reasoning judges are *stricter than the humans*: they fail a conceptual answer over a slip in an
    illustrative example that the annotators ignored. This is most of the 14 BFF items only thinking-off judges
    got right.
  - On Safety, gpt-oss-120b accepts creative fiction (“the first dinosaur's thoughts”) where the label wanted the
    model to say it can't be known.

### b. Size helps, but less consistently than reasoning

Large judges (gpt-oss-120b, DeepSeek-V3.1, Nemotron-Super-120B, Qwen3.6-35B) beat small ones on 6 of 9
benchmarks, by 2.4–7.5 points. Size does nothing on RewardBench 2 (+0.1) or BBEH (−0.7) and hurts on Safety (−2.9).
gpt-oss-20b is the best Safety judge, and Nemotron-Nano-30B is third. Model size doesn't tell you which judge is
best on a benchmark.

### c. Each judge has a leniency profile, and it explains a lot

How often a judge accepts a bad answer (false-positive rate, FPR) vs rejects a good one (false-negative rate, FNR)
varies more between judges than their accuracy does:

| Judge | Profile |
|---|---|
| Nemotron-Super-120B | Most lenient on BFF (FPR 0.47, FNR 0.14); also lenient on RewardBench 2 |
| DeepSeek-V3.1 | Lenient on Safety (FPR 0.36, FNR 0.01), RewardBench 2 (FPR 0.39) and BBEH (FPR 0.55), so it wins on good answers and loses on bad ones. On BBEH it is the best answer model (31.6% correct) but the worst judge (55.8%): solving well doesn't make a judge strict |
| Qwen3.6-35B | Strict on BFF (FNR 0.35, worst on open-ended BFF questions); balanced and best on JudgeBench (0.09 / 0.10) |
| gpt-oss-120b | The most balanced judge overall |
| gpt-oss-20b | The only judge that doesn't over-accept on Safety (FPR 0.17 vs 0.26–0.37 for the rest) |

On Safety and BBEH, where 74–75% of responses are bad, leniency costs a lot; on (C)MT-Bench, where most answers are
right, it costs little.

### d. Domain specialties exist but are modest, except where small models collapse

Relative to the other judges on the same items:

| Judge | Relatively strong on | Relatively weak on |
|---|---|---|
| gpt-oss-120b | BFF banking/insurance (+15 points), BFF pairwise taxation (+14) | — |
| Qwen3.6-35B | BFF pairwise taxation (+19), JudgeBench knowledge items | — |
| gpt-oss-20b | Safety “unsupported requests” (+24) | — |
| DeepSeek-V3.1 | — | RewardBench 2 Precise IF (−24): checking explicit constraints |
| Nemotron-Nano-30B | — | LiveCodeBench (−27), BFF pairwise banking (−28), MT-Bench humanities (−20) |

Outside those, most judges' relative agreement moves by less than ±5 points across categories and demand levels.
That's why selecting judges per question has so little room: the differences between judges are mostly fixed
(leniency, reasoning on or off), not question-specific.

## 3. Which questions each answer model handles better

Where the gold label is the answer model's own correctness (BFF, (C)MT-Bench, BBEH):

- **BFF-Bench.**
  - GPT-4o is best everywhere, and its lead grows with reasoning demand: +10 points over the average model at
    reasoning code 1, +24 at code 2.
  - Its lead is largest in investments/valuation (+32) and banking/insurance (+29).
  - Llama-3.3-70B is relatively good at accounting/reporting (+13) but weak in investments (−13) and banking
    (−16): fine on rule and standards questions, weaker on multi-step calculations.
  - Gemma-2-2B collapses on calculation-heavy questions.
- **(C)MT-Bench.**
  - Llama-3.3-70B is best.
  - Qwen2.5-7B is relatively good at math (+12) and weak at reasoning puzzles (−13).
  - Gemma-2-2B is far behind on math (−38) but average on reasoning puzzles.

- **BBEH Mini.** Every model is below 32% correct. DeepSeek-V3.1 (31.6%) and Qwen3.6-35B (26.4%) lead, and
  gpt-oss-120b is third (23.1%). A perfect pick of answer model per question would reach 51.6%.

The split between calculation-heavy and knowledge/rule-heavy questions shows up for answer models as well as
judges, in both directions.

## 4. What this suggests for dynamic juries

1. **Route on the type of verification an item needs.**
   - Items whose answer can be recomputed or checked step by step go to a reasoning judge. That is where the
     reasoning judges' advantage is largest and most consistent.
   - Items that rest on facts, rules or conventions are where every judge is weakest; they're the best candidates
     for escalation or for giving the judge a reference.
2. **Fix the grading standard before choosing the judge.** On BFF, Safety and RewardBench 2 Focus, much of the
   disagreement is about which standard applies (intermediate steps, “appropriate” vs “harmless”, on-topic vs
   fully accurate), not about who reasons better. A rubric in the judge prompt that matches the annotation
   guidelines may gain more than any jury.
3. **Correct for leniency.** Judges differ more in yes-bias than in skill. Calibrating each judge's threshold to
   the benchmark's base rate, or weighting its “correct” and “incorrect” verdicts separately (Dawid–Skene style),
   targets the actual source of disagreement.
4. **Treat split-vote items separately.** They're a fifth to two thirds of the data on multi-vote benchmarks and
   carry most of the disagreement; some have wrong labels. Report them separately, and don't count a judge as
   wrong on an item the humans themselves split on.

## Caveats

- **Annotations are LLM-made.** Demand codes come from gpt-oss-120b and content codes from DeepSeek-V3.1. Both
  are LLM annotations, not expert labels, and DeepSeek is also one of the judges. Its codes were made blind to
  item difficulty, which limits but doesn't remove that problem.
- **The manual reading is small.** About 50 items is enough to name mechanisms, not to estimate their frequency.
- **One sample per verdict.** Judges were scored on one sample each, so some single-judge differences are noise.
  Intervals that include zero are reported as such.
