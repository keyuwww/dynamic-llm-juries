# Confident, intermediate and unsure errors: Study A results (11/02)

Plan: `docs/confident_errors_plan.md`. Code: `experiments/cross_benchmark/confident_errors.py`; tables:
`experiments/cross_benchmark/results/confident_errors/` (`summary.md`, CSVs). No new calls.

**Setup.** 8 judges × 4 benchmarks × 1,614 pairs, confidence run (verdict and confidence from the same calls).
Outcome: R right in both orders, W wrong in both, F flip. Level: low / intermediate / high third of each judge's own
stated confidence within each benchmark (ties kept together). Pooled cells: high 4,479 R / 452 W / 612 F,
intermediate 2,203 / 555 / 831, low 1,614 / 733 / 1,310. Error rate on consistent pairs: 9% / 20% / 31%.

## Answer
**Confident errors look like real, shared false beliefs, not hidden doubt.** They are shared with more judges than
unsure errors are. They sit on items where human annotators disagreed or where the judge could not solve the
problem. The judge's own token probability shows almost no doubt.

## Results

| Step | Question | Result |
|---|---|---|
| A2 | When a judge is wrong in both orders, how many of the other 7 judges are also wrong in both orders? | **More for confident errors, graded:** 3.1 (low) → 3.5 (intermediate) → **4.0 (high)** of 7, vs about 1.0 if judges erred independently. CIs for high (3.6–4.4) and low (2.8–3.4) do not overlap. Only 13–15% of errors at any level are unique to one judge. |
| A2 | Same, counting any error by the others (including flips)? | Flat: 5.4–5.6 of 7 at every level (null 2.5). Almost every error sits on an item where most judges stumble at least once. |
| A1 | Overlap between judge pairs (lift of the other judge's error rate)? | 2.4–2.5× at every level; same family slightly higher (2.6–2.8× vs 2.4–2.5×). |
| A3 | What kind of item is a confident error on? (W minus R, z within benchmark, 95% CI) | **Contested labels:** the human split rises with level (+0.19 n.s., +0.40, **+0.63** SD). **Unsolved by the judge (BFF):** high-confidence errors are on problems the judge itself could not solve (**−0.59** SD vs right; −0.48 vs low-confidence errors). Intermediate and low errors are tied to surface cues instead: the two answers are similar (+0.12, +0.18), share a final number (+0.22 intermediate), or the longer answer is the worse one (−0.26 intermediate). High-confidence errors also have bigger length gaps than low-confidence errors (+0.37). |
| A4 | Does anything inside a confidence level separate errors from right answers? | **Very little.** Verdict-token probability: AUROC 0.53–0.60 (highest at the high level); remaining differences in stated confidence: 0.55–0.56. Token probability is saturated (76–86% at ≥ 0.999). |
| A5 | Do other judges catch this judge's errors, within each level? | **Others' doubt catches confident errors best:** AUROC 0.72 (high) vs 0.67 (intermediate) vs 0.59 (low). Others' disagreement: 0.72–0.76 at every level. Even errors shared by 4+ other judges are caught at 0.62–0.72 by others' doubt: the others are wrong, but less sure. |

**Robustness.** The A2 gradient holds under all three level schemes:
- within-judge thirds: 3.1 / 3.5 / 4.0;
- calibrated risk: 3.1 / 4.1 / **4.8**, with only 5% of calibrated high-confidence errors unique to one judge;
- fixed 70 / 90 cuts: 2.9 / 3.4 / 3.7.

A5 also holds: others' doubt for high vs low is 0.75 vs 0.63 under risk and 0.74 vs 0.44 under fixed cuts.

## What this means
- **Two kinds of error.** Unsure and intermediate errors come from near-ties and surface cues (similar answers,
  length). Confident errors come from contested labels and problems the judge can't solve, and many judges share
  them.
- **The judge's own signals can't see confident errors.** Its token probability is saturated, and within a level it
  barely separates right from wrong. Other judges' doubt is the better alarm, and it works best exactly at the high
  level.
- **Some "confident errors" are probably label noise.** That is most likely on AlpacaFarm and MT-Bench, where the
  human split is large. The A6 coding checks this item by item.
- **For Study B (probes):** the behavioural evidence predicts that HW will sit near HR in activation space (a real
  belief). If a probe still separates them, the model holds doubt that its output doesn't show.

## Caveats
- One sample per verdict. Levels and outcomes come from the confidence run, which changed 12–20% of verdicts relative
  to the stored run.
- Human split exists only for AlpacaFarm and MT-Bench human; solve labels only for BFF.
- A5 split by sharing level: disagreement is near 1 by construction when the other judges are right, so only the
  doubt signal and the "all W" and "4+" rows are informative. Few errors are unique to one judge (4–6 judge ×
  benchmark cells), so "one-judge vs shared" catch rates can't be compared reliably.
- Judges are counted over the same items, so the 8 × 4 points aren't independent; CIs bootstrap over question groups.

## A6 qualitative coding (11/02)
120 verdicts, 20 per cell, coded blind to confidence and flips by four parallel Claude coders, each given the
codebook only. Code: `confident_errors_sample.py`, `confident_errors_coding.py`; codes and summary in
`results/confident_errors/` (`claude_codes.json`, `coded.csv`, `coding_summary.md`). 18 verdict-only records are
excluded from the reasoning codes.

| | HW | MW | LW | HF | HR | LR |
|---|---|---|---|---|---|---|
| Gold label questionable | **55%** | 45% | 35% | 10% | 0% | 10% |
| Error: gold questionable / near tie | **45% / 20%** | 35% / 25% | 15% / **45%** | 0 / 12% (n = 8) | | |
| Error: the judge's own mistake (missed fact, slip, misread, style) | 30% | 40% | 35% | **88%** (half arithmetic slips) | | |
| Noticed the decisive difference | 65% | 73% | 31% | 50% | 95% | 89% |
| Hedges or self-corrects | 18% | 27% | 62% | 31% | 25% | 72% |
| Says the answers are close | 12% | 60% | 81% | 19% | 10% | 78% |
| Reasoning reads highly confident | **88%** | 73% | 12% | 56% | **90%** | 33% |

- **About two thirds of confident errors are label problems, not judge failures.** 45% have a questionable gold
  label and 20% are near ties; only about 30% are clear judge mistakes. Unsure errors are mostly near ties (45%).
- **A confident error reads exactly like a confident right answer.** A blind reader can't tell HW from HR by how
  confident the reasoning sounds (AUROC 0.49), but easily tells HW from LW (0.88). There is no hidden doubt in the
  text either, consistent with A4.
- **Confident errors often see the decisive difference (65%) but weigh it differently from the gold label.** This
  fits contested labels. Unsure errors mostly miss it (31%).
- **Flips at high confidence are the judge's own slips** (arithmetic, misreading) in one order, not label problems.
  These are the errors that order swaps catch.

**Caveats.**
- The coders are LLMs, one coder per record, and n = 20 per cell.
- "Gold questionable" is the coder's own judgement and may side with the judges. Janys's 30-item check
  (`janys_sheet.csv`, 5 per cell, without Claude's codes) gives Cohen's κ, especially for this code.
- 9 reasonings were cut at 6,000 characters for the coders.
