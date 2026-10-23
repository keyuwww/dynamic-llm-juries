# Stage A results: do other judges' order flips catch the best judge's confident errors? (10/23)

**Setup.** Stored verdicts only (no new calls): 8 judges, every pair judged in both orders, 4 pairwise benchmarks.
Target = each benchmark's best judge. Outcome = its **confident error** (wrong in both orders), on the pairs where
it is consistent: 6.5–20.7% of pairs (17–79 errors per benchmark). AUROC: 0.5 = chance; 95% CIs by bootstrap over
questions; learned models are cross-validated by question.
Full tables: `experiments/cross_benchmark/results/flips/stage_a.md` (+ `stage_a.json`, `features_<bench>.csv`).
Code: `experiments/cross_benchmark/flip_analysis.py`. Plan: `docs/order_flip_difficulty_plan.md`.

## Conclusions
1. **Other judges' flips do flag the best judge's confident errors, and not only because of obvious features.**
   They survive length, similarity, formatting and item controls on 3 of 4 benchmarks, and a matched comparison
   shows a higher error rate with more flips on all 4.
2. **Flips are best used together with plain disagreement, and that combination is essentially the known
   "cross-model disagreement" signal.** Neither beats the other by much on its own; a simple pooled score of both
   is the best label-free alarm. This limits how new our result is (see Section 3).
3. **Our three "why" hypotheses mostly failed.** Flips are not explained by the judge's ability to solve the
   question, are not a good label-free difficulty measure, and are question-level on one benchmark but pair-level
   on another.
4. **Hand-picked checkers don't beat pooling all judges.** Pooling flips from all 7 other judges matches or beats
   checkers chosen on training data on 3 of 4 benchmarks.
5. **A small floor of errors is invisible to every judge**: 0–18% of the best judge's confident errors have no
   other judge flipping or disagreeing.

## Results by hypothesis

| # | Hypothesis | Verdict | Evidence |
|---|---|---|---|
| H1 (A1) | Flips add beyond controls | **Supported, 3 of 4** | AUROC gain: JudgeBench +0.08 [0.03, 0.14], AlpacaFarm +0.06 [0.01, 0.10], MT-Bench human +0.05 [0.01, 0.10], BFF pairwise +0.01 [−0.03, 0.04] |
| H2 (A2) | More flips → more errors within matched strata | **Supported, 4 of 4** | +3.8 (BFF), +9.1 (JudgeBench), +18.9 (AlpacaFarm), +26.1 (MT-Bench human) points |
| H3 (A3) | Flips add beyond consistent disagreement | **Partly** | Flips alone ≥ disagreement alone on all 4. Gain over controls + disagreement: significant only on JudgeBench (+0.07 [0.02, 0.13]); borderline on MT-Bench human (+0.03 [0.00, 0.07]); none on the other two |
| H4 (A5) | Flips reflect the question, not the pair | **Mixed** | BFF pairwise: flips on other pairs of the same question predict as well (0.67 vs 0.63). MT-Bench human: only the same pair predicts (0.70 vs 0.52) |
| H5 (A6) | Flips happen on questions the judge can't solve | **Not supported** | BFF pairwise flip rates are similar whether a judge solved the question or not (e.g. gpt-oss-120b 7% vs 8%); the best judge's confident-error rate is 10.6% vs 11.1% |
| H6 (A7) | Flip counts are a good label-free difficulty measure | **Not supported** | For a held-out judge's errors: others' flips 0.67–0.78 vs others' labelled errors 0.91–0.96. Human vote splits: 0.59–0.61 (target was ≥ 0.65) |
| H7 (A9) | A few chosen checkers beat pooling all judges | **Not supported** | Chosen sets match pooled flips on JudgeBench and AlpacaFarm, beat them on BFF (2–3 checkers: 50–57% vs 42–45% caught) and lose on MT-Bench human (1 checker: 23% vs 41%) |

## Best alarm per benchmark (AUROC, 95% CI)

| Signal | BFF pairwise | JudgeBench | AlpacaFarm | MT-Bench human |
|---|---|---|---|---|
| Controls only (length, similarity, formatting, item aspects) | **0.72** [0.61, 0.82] | 0.63 [0.47, 0.79] | 0.55 [0.47, 0.62] | 0.72 [0.62, 0.80] |
| Others' flip count | 0.63 [0.51, 0.72] | 0.77 [0.66, 0.86] | 0.66 [0.59, 0.73] | 0.70 [0.63, 0.78] |
| Others' consistent disagreement | 0.58 [0.49, 0.66] | 0.67 [0.53, 0.80] | 0.61 [0.55, 0.68] | 0.66 [0.58, 0.75] |
| Pooled score (disagreement + half-weighted flips) | 0.63 [0.52, 0.74] | **0.78** [0.69, 0.87] | **0.69** [0.62, 0.75] | 0.76 [0.68, 0.84] |
| Controls + disagreement + flips | **0.72** [0.62, 0.81] | 0.71 [0.59, 0.82] | 0.64 [0.58, 0.71] | **0.81** [0.73, 0.88] |

- **The controls are strong on their own where length matters.** On BFF pairwise and MT-Bench human, a small
  length gap between the two answers and open-ended questions mark the best judge's errors (single-feature AUROC
  up to 0.75).
- **In practical terms:** at an 18% flag rate, pooled flips catch 27–49% of the best judge's confident errors
  (random flagging would catch 18%).

## What this means for the research
- **Novelty is narrower than hoped.** The working signal is cross-judge disagreement, with order flips counted as
  half-disagreement. That is close to the published inter-model vs intra-model disagreement score (Hamidieh et al.,
  ICLR 2026), applied to judging with order swaps. Our defensible contribution is the judging-specific evidence:
  it survives controls, it catches errors the strong judge makes in both orders, and there is a measurable floor
  of errors no judge flags.
- **The "why" is still open.** Solvability and label-free difficulty didn't explain flips. Remaining candidates are
  near-tie answers (length gap was the strongest control) and genuinely contested labels (AlpacaFarm, where human
  votes split on 60% of pairs).
- **Confidence (Stage B) is the next real test.** The open question is whether the strong judge's own confidence
  and others' flips are complementary. That needs new calls.

## Caveats
- Small numbers of confident errors (17 on JudgeBench, 39–79 elsewhere), so the CIs are wide.
- One sample per verdict, so some flips are sampling noise.
- The target is the best judge on the full data (in-sample choice).
- Cross-validated combinations of two count features are unstable with so few errors. The pooled score needs no
  fitting and is the more reliable combined number.
- BFF solve labels come from the 1,024-token answer run, graded by two judges; pairs where the graders disagreed
  were dropped.

## Next steps
1. **Stage B pilot (about $5, needs your OK):** gpt-oss-120b plus 2 checkers on BFF pairwise and MT-Bench human,
   with stated confidence, verdict-token probability and 3 samples per order.
2. **No-cost follow-ups on stored data:**
   - Hand-inspect the 23 "unflaggable" errors across benchmarks.
   - Split AlpacaFarm results by human vote margin to separate contested labels from real errors.
