# Findings: order flips, confident errors and judge pairs (10/22)

All results use stored verdicts (8 Tinker judges, 1 sample at T = 0.7, every pair judged in both orders) on the
4 pairwise benchmarks: BFF pairwise, JudgeBench, AlpacaFarm, MT-Bench human. In-sample, no confidence intervals
yet. No new model calls.

Terms: a judge **flips** on a pair when it picks the same position in both orders (so exactly one of its two
verdicts is wrong). A **confident error** is a pair the judge gets wrong in both orders.

Sources: `experiments/cross_benchmark/results/order_consistency.md` (script `order_consistency.py`) and
`experiments/cross_benchmark/results/flips/judge_pairs.md` + `.json` (script `judge_pairs.py`).

## 1. Most of the best judge's errors are confident
| Benchmark | Best judge | Flip rate | Accuracy if flipped pairs are dropped | Share of its errors on its own flips |
|---|---|---|---|---|
| BFF pairwise | gpt-oss-120b | 8.0% | 85.7% → 88.8% | 28% |
| JudgeBench | Qwen3.6-35B | 7.2% | 90.6% → 93.8% | 38.5% |
| AlpacaFarm | DeepSeek-V3.1 | 21.8% | 73.0% → 79.3% | 40.2% |
| MT-Bench human | gpt-oss-120b | 6.2% | 83.8% → 86.0% | 19.2% |

The judge's own flips miss 60–80% of its errors.

## 2. Other judges' flips flag the best judge's confident errors
- Counting how many of the other 7 judges flip, AUROC for the best judge's confident errors (on pairs where it is
  consistent): **0.63** BFF pairwise, **0.77** JudgeBench, **0.66** AlpacaFarm, **0.70** MT-Bench human.
- Example, BFF pairwise: the best judge's error rate is 9% when no other judge flips and 24% when 3 do.
- Flips cluster on pairs: if one judge flips, another is 1.6–2.3x more likely to flip.
- An expert reference cuts flips for some judges (DeepSeek 16.3% → 10.0% on BFF pairwise) but not for gpt-oss.

## 3. Controls checked so far (quick, scratch run)
- Word-overlap similarity of the two answers barely relates to flips (|r| ≤ 0.16).
- Length gap does not relate to flips but predicts confident errors on MT-Bench human (AUROC 0.75); combined with
  flips 0.78. On JudgeBench, flips carry the signal (0.77) and these controls add nothing.
- The best judge's output length is a weak confidence proxy (AUROC 0.50–0.63) and barely correlates with others'
  flips (r = 0.06–0.20).

## 4. Judge pairs: who catches whom
A checker "catches" a target's confident error if it flips or is consistently right on that pair.

**Single checkers are weak; the signal comes from pooling.** One checker's flips flag the best judge's confident
errors at AUROC 0.48–0.69 (best: Nemotron-Super on JudgeBench, 0.69). Pooling all 7 gives 0.63–0.77.

**Catching a judge goes with being unlike it, but so do false alarms.**
- Across all ordered pairs, the share of a target's errors a checker flags falls with their error correlation
  (Spearman −0.73 to −0.84 on all 4 benchmarks).
- False alarms fall with checker accuracy (−0.65 to −0.92). Weak checkers flag almost everything.
- Example, BFF pairwise, target gpt-oss-120b:

  | Checker | Errors flagged | Correct pairs flagged (false alarm) | Error correlation |
  |---|---|---|---|
  | Qwen3.6-35B | 29% | 7% | 0.61 |
  | gpt-oss-20b | 30% | 10% | 0.57 |
  | DeepSeek-V3.1 | 38% | 18% | 0.46 |
  | Nemotron-Super | 44% | 26% | 0.37 |
  | Nemotron-Nano | 69% | 59% | 0.12 |

  Nemotron-Nano catches the most but is barely better than flagging at random. Qwen3.6-35B catches the fewest
  but with the fewest false alarms. This is the same accuracy-vs-overlap trade-off we saw for juries.

**Catching is largely reciprocal when flips and disagreement are combined, but not for flips alone.**
- Correlation of the "i catches j" matrix with its transpose: 0.76 BFF pairwise, 0.50 JudgeBench, 0.30 AlpacaFarm,
  0.76 MT-Bench human. If i catches j's errors, j tends to catch i's.
- For flips alone: −0.19, 0.51, −0.18, 0.02. Flip-based catching is not reciprocal, and barely tracks error
  correlation (−0.15 to +0.34) or checker accuracy. Flips behave like a property of the *pair* (hard items), not of
  the checker–target relationship.

**Good mutual pairs exist, but most top pairs lean on a noisy judge.**
- JudgeBench: Qwen3.6-35B + Nemotron-Super catch 82% and 74% of each other's confident errors at about 15% false
  alarms. This is the cleanest good pair.
- On BFF pairwise and MT-Bench human the top-ranked mutual pairs all include Nemotron-Nano, which catches a lot
  only because it flags 21–36% of correct pairs too.

## 5. What this means
1. Flips are mostly an **item-difficulty** signal. They add up across judges and do not depend much on which
   checker you use.
2. Disagreement-based catching is a **judge-relationship** signal. It follows dissimilarity, is reciprocal, and
   trades catches for false alarms in proportion to checker weakness.
3. The useful object is a **small set of checkers chosen for catch rate per false alarm**, not the most dissimilar
   judge.

## 6. Caveats
- In-sample, no CIs, 1 sample per verdict (some flips are sampling noise).
- Pair-level counts are small for strong targets (few confident errors), so single-cell numbers are noisy.
- The literature already shows cross-model disagreement catches confident errors in generation
  (see `docs/lit_review_cross_judge_error_detection.md`). What is new here is the judging setting with order
  swaps, and the split between item-level (flip) and relationship-level (disagreement) signals.
