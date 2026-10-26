# Order flips, confidence and catching a judge's confident errors: final results (10/23)

**Question.** When the best judge is wrong in both answer orders (a *confident error*), can other judges' order flips,
their disagreement, or confidence (the judge's own or others') flag it? And why do flips mark errors?

**Data.** 8 Tinker judges. 4 pairwise benchmarks (BFF pairwise, JudgeBench, AlpacaFarm, MT-Bench human), every pair
judged in both orders. Plus 236 controlled BFF pairs and RewardBench 2 "other" as a single-answer benchmark.
- New calls: 41,858 judgments with stated confidence (0–100) and verdict-token probability. Total logged cost **$55.89**.
- Confidence signals come from the new runs; the outcome is always the best judge's confident errors in the stored run.
- AUROC: 0.5 = chance. 95% CIs by bootstrap over questions.

Stage A (stored data only) is in `docs/results_stage_a_order_flips.md`. Plan: `docs/order_flip_difficulty_plan.md`.
Literature: `docs/lit_review_cross_judge_error_detection.md`.

## Conclusions
1. **The best alarm is the strong judge's own stated confidence, plus other judges' signals.**
   - Stated confidence alone flags its confident errors at AUROC 0.65–0.84 (pilot runs: 0.78–0.80). It is
     reasonably calibrated: on BFF pairwise, pairs rated 95–100 are wrong 3.9% of the time, pairs rated 80–90 are
     wrong 25.8%.
   - Adding other judges' pooled flips and disagreement helps on 3 of 4 benchmarks: combined 0.70–0.86, e.g.
     MT-Bench human 0.76 → 0.80.
   - This contradicts the literature's expectation that stated confidence is weak (0.55 for GPT-4 in Trust or
     Escalate). Our judges reason first and then state confidence.
2. **Other judges' low stated confidence beats their flips as an alarm.** Using checkers' low confidence: 0.65–0.83
   AUROC. Using the same checkers' flips: 0.62–0.73. Confidence also works where orders can't be swapped.
3. **On single-answer grading, plain disagreement is the best signal.** On RewardBench 2 other, the number of other
   judges disagreeing with gpt-oss-120b flags its errors at AUROC 0.73. Its own stated
   confidence gets 0.61; its token probability is at chance (0.47).
4. **Flips mark near-tie pairs, and the default under a tie is the first-shown answer.**
   - With the same answer in both slots, 93–100% of strong judges' picks go to the first position.
   - When one figure of an answer is changed by 10%, the gpt-oss judges flip 2–4x more often than on real BFF
     pairs (gpt-oss-120b 18% vs 4%; gpt-oss-20b 27% vs 12%). DeepSeek and Nemotron-Super flip about 1.5x more;
     the Qwen judges about the same or less. Judges other than Nemotron-Nano almost never pick the corrupted
     answer in both orders (0–3%): the small error becomes a flip or is caught, not a confident error.
   - This is the mechanism behind order bias on near-ties. It also explains why other judges' flips point at
     hard-to-separate pairs.
5. **Token probability is a poor confidence measure for reasoning judges.** After reasoning, the verdict token is
   near-certain (gpt-oss 0.42–0.64 AUROC for its own flips). Stated confidence carries the signal instead.
6. **Some caveats change how to read the numbers.** Asking for confidence changed 12–20% of verdicts relative to the
   stored run. About half of the strong judges' flips do not repeat across samples. Neither the pooled-flip signal
   nor single cross-judge signals beat the strong judge's own confidence by itself.

## Results by hypothesis

| # | Hypothesis | Verdict | Key numbers |
|---|---|---|---|
| H1 | Others' flips add beyond text controls | Supported, 3 of 4 | Gain +0.05 to +0.09 (JudgeBench, AlpacaFarm, MT-Bench human), also after semantic-embedding controls |
| H2 | More flips → more errors within matched strata | Supported, 4 of 4 | +3.8 to +26.1 points |
| H3 | Flips add beyond plain disagreement | Partly | Flips ≥ disagreement alone; extra gain significant only on JudgeBench |
| H4 | Flips are question-level, not pair-level | Mixed | BFF pairwise yes (0.67 vs 0.63), MT-Bench human no (0.52 vs 0.70) |
| H5 | Flips happen on questions the judge can't solve | Not supported | gpt-oss-120b flips 7% (solved) vs 8% (unsolved) |
| H6 | Flip counts are a good label-free difficulty measure | Not supported | 0.67–0.78 vs 0.91–0.96 for labelled errors |
| H7 | A few chosen checkers beat pooling all judges | Not supported | Pooling matches or wins on 3 of 4 |
| H8 | Flips can be predicted from the text alone | Not supported | Correlation with real flips −0.05 to 0.29 |
| B1 | A judge is less confident on pairs it flips | **Supported** | Stated confidence AUROC 0.79–0.86 for gpt-oss-120b; 0.56–0.65 for Nemotron-Nano |
| B2 | The strong judge's own confidence flags its confident errors | **Supported** | 0.65–0.84 (stated) |
| B3 | Own confidence and others' flips are complementary | Partly | Correlation +0.41 to +0.53; combining adds +0.02 to +0.05 on 3 of 4, none on BFF pairwise |
| B4 | Others' flips catch errors where the strong judge is most confident | Mixed | High-confidence tercile: AUROC 0.58 (BFF), 0.71–0.72 (AlpacaFarm, MT-Bench human), but only 0–15 errors there |
| B5 | Others' confidence beats others' flips | **Supported** | 0.65–0.83 vs 0.62–0.73 |
| C1 | Repeatable flips are a better alarm than one-off flips | Not supported | Checkers' flips: single run 0.57, repeatable only 0.53–0.64 |
| C2 | Flips rise as the quality gap shrinks | Partly | Corrupted pairs vs real pairs: gpt-oss 2–4x more flips, DeepSeek and Nemotron-Super ~1.5x, Qwen no rise; identical answers: 93–100% of strong judges' picks go to the first position |
| C2 | Judges prefer a padded copy of the same answer | **Supported** | Strong judges pick the padded version in both orders 40–52% vs 7–12% for the shorter one |
| C4 | Cross-judge signals work without order swaps | **Supported** | Disagreement 0.73; others' low confidence 0.65 (RewardBench 2 other) |

## Alarm comparison (AUROC for the best judge's confident errors)

| Signal | BFF pairwise | JudgeBench | AlpacaFarm | MT-Bench human |
|---|---|---|---|---|
| Text controls only | 0.72 | 0.63 | 0.55 | 0.72 |
| Others' flips (stored) | 0.63 | 0.77 | 0.66 | 0.70 |
| Others' pooled score (flips + disagreement) | 0.63 | 0.78 | 0.69 | 0.76 |
| Best judge's stated confidence | **0.74** | 0.84 | 0.65 | 0.76 |
| Stated confidence + others' pooled score | 0.73 | **0.86** | **0.70** | **0.80** |
| Others' low stated confidence | **0.74** | 0.83 | 0.65 | 0.78 |

Signals are compared by AUROC across all thresholds, so no single flag rate is chosen in advance.

## What this means
- **For routing:** ask the strong judge for a confidence and escalate low-confidence items. Add other judges'
  disagreement or low confidence where they are cheap. Order swaps are mainly useful for exposing near-tie pairs.
- **For novelty:** the cross-judge signal works and survives controls, but it is close to the published
  inter-model vs intra-model disagreement idea. More distinctive findings:
  - Stated confidence from reasoning judges is informative, against the literature's expectation.
  - Other judges' confidence beats their flips.
  - Controlled pairs show the mechanism: near-ties default to the first-shown answer, and padded copies win.
- **For data quality:** many errors no judge flags look like wrong gold labels (AlpacaFarm 3–1 votes, MT-Bench
  human). The flip signal is much stronger on unanimous AlpacaFarm pairs (0.76 vs 0.61).

## Caveats
- **Asking for confidence changed 12–20% of verdicts** relative to the stored run. Confidence signals come from the
  new run, the outcome from the stored run.
- **The full run used one sample per verdict.** In the 3-sample pilot, only 46–80% of a judge's flips repeat.
- **JudgeBench parse rate was 92.6%.** The 4,096-token cap cut some reasoning (the stored run used 8,192).
- **Few confident errors per benchmark** (17–79), so CIs are wide; JudgeBench has only 17.
- **The best judge was chosen on the full data** (in-sample).
- **Controlled pairs are small** (72–82 per type) and use the human-preferred BFF answer as "correct".
- **The RewardBench 2 single-answer outcome** uses the new run's own verdicts.

## Files
- Code (in `experiments/cross_benchmark/`):
  - `flip_analysis.py`, `flip_followups.py`, `flip_embeddings.py`, `judge_pairs.py`, `order_consistency.py`
  - `run_confidence.py`, `conf_analysis.py`, `build_ctrl_pairs.py`, `stage_c.py`
- Raw outputs, including full reasoning text:
  - `results/confidence/<bench>/judgments.jsonl`
  - `results/confidence_pilot/<bench>/judgments.jsonl`
  - `data/bffctrl_items.json`
- Tables: `results/flips/` (`stage_a.md`, `stage_b_confidence.md`, `stage_b_confidence_pilot.md`, `stage_c.md`,
  `c3_embeddings.md`, `judge_pairs.md`, `unflaggable.md`, `alpaca_margin.md`)

## Next steps
1. **Re-score the outcome on the new run.** Use the new run's own confident errors so confidence and outcome come
   from the same verdicts, and check that the conclusions hold.
2. **Build an escalation policy with a guarantee.** Use the strong judge's stated confidence plus others'
   disagreement, calibrated on held-out data (Trust-or-Escalate style), and report errors caught per dollar.
3. **Audit the suspected wrong gold labels.** Have someone check the unflaggable AlpacaFarm and MT-Bench human items
   by hand, and report results with and without them.
