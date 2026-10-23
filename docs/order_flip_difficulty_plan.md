# Order flips, confidence and difficulty: detailed plan (updated 10/22)

## 1. Question
Every pairwise item is judged in both orders. A judge "flips" when it picks the same *position* both times, so
exactly one of its two verdicts is wrong. The best judge's own flips only reveal its unsure errors; most of its
errors are **confident** (wrong in both orders: 72% on BFF pairwise for gpt-oss-120b).

We ask:
1. Do **other judges' flips** catch the best judge's confident errors, after controlling for obvious features?
2. How does that depend on the best judge's **confidence** (stated, and from token probabilities)?
3. Why do flips mark errors: near-tie answers, unsolvable questions, noisy labels, or surface cues?
4. Are flip counts a better, label-free **difficulty** measure, and can cheap judges supply them?

## 2. What we already have (stored, no new calls)
From `experiments/cross_benchmark/results/order_consistency.md` (in-sample, no CIs yet):
- Other judges' flips flag the best judge's confident errors: AUROC 0.63 BFF pairwise, 0.77 JudgeBench,
  0.66 AlpacaFarm, 0.70 MT-Bench human (0.5 = chance).
- Flips cluster on items: if one judge flips, another is 1.6–2.3x more likely to flip.
- Quick control check (scratch run, not saved): word-overlap similarity of the two answers barely relates to flips
  (|r| ≤ 0.16). Length gap does not relate to flips but predicts confident errors on MT-Bench human (0.75);
  combined with flips 0.78 there. The best judge's output length is a weak confidence proxy (0.50–0.63).

Prior work and the gap are in Section 9.

## 3. Data and where everything is stored
Rule: every raw model output and every derived table goes in the repo, never only in the scratchpad.
Raw `*.jsonl` caches are large and stay uncommitted unless we decide otherwise; derived tables and reports are committed.

| What | Path | Status |
|---|---|---|
| Stored pairwise verdicts (8 judges, both orders, condition none/human) | `experiments/cross_benchmark/data/{bffpair,judgebench,alpacafarm,mtbhuman}_decisions.pkl` | exists |
| Raw judge outputs for those | `experiments/tinker_pool/bffpair_results_max4096/`, `experiments/cross_benchmark/results/<bench>/judgments.jsonl` | exists (final text only, no reasoning traces) |
| BFF solve labels (8 judges' own answers, graded) | `experiments/tinker_pool/bff_results*/answers.jsonl`, `grades.jsonl` | exists |
| Order-consistency script and table | `experiments/cross_benchmark/order_consistency.py`, `results/order_consistency.md` | exists, uncommitted |
| Confidence run script | `experiments/cross_benchmark/run_confidence.py` | written, not yet run |
| Confidence raw outputs (verdict, stated confidence, verdict-token probability, full output incl. reasoning) | `experiments/cross_benchmark/results/confidence/<bench>/judgments.jsonl` | to create |
| Pair feature table (controls) | `experiments/cross_benchmark/data/pair_features_<bench>.parquet` + `results/flips/features.md` | to create |
| Analysis outputs (tables, figures, JSON) | `experiments/cross_benchmark/results/flips/` | to create |
| Analysis code | `experiments/cross_benchmark/flip_analysis.py` (one module, one function per analysis) | to create |
| Write-up | this file, then a short HTML report | to update |

## 4. Control features (one row per pair)
Built once by `flip_analysis.py features`, from stored text only.

| Group | Features |
|---|---|
| How close the two answers are | word-overlap similarity (TF-IDF cosine); length gap and ratio; whether the final numeric answers match (BFF pairwise, JudgeBench); similarity of each answer to the expert reference (BFF) and the difference |
| Surface cues | which answer is longer; counts of headers, bullets, tables, numbers, code blocks; hedging and confidence words; refusal markers |
| Item | question length; category; stored aspect codes (knowledge, reasoning, constraints, open-endedness, context load, risk) |
| Who wrote the answers | answer models; strong vs weak; same family as the best judge |
| Label quality | human vote margin (AlpacaFarm, MT-Bench human); `gold_questionable` codes |
| Later (needs approval) | sentence-embedding similarity from a small open embedding model downloaded locally |

## 5. Experiments and analyses

### Stage A: stored data only (no cost, about 4 days)

**A1. Does the flip signal survive the controls?**
- Target: the best judge's confident error, on pairs where the best judge is consistent (avoids the
  built-in "one of two verdicts is wrong" artifact).
- Models: logistic regression, (i) controls only, (ii) controls + number of other judges that flip. Grouped 5x5 CV
  by question; bootstrap CIs on the AUROC gain; Holm across 4 benchmarks.
- Output: `results/flips/a1_incremental.md`.
- Pass: flips add ≥ 0.03 AUROC with CI above 0 on ≥ 3 of 4 benchmarks.

**A2. Matched comparison.**
- Bin pairs on length gap, similarity, category and human margin; within bins compare the error rate for
  0–1 vs ≥ 2 other-judge flips.
- Output: `results/flips/a2_matched.md` + one figure.

**A3. Flips vs plain disagreement.**
- For each pair, count other judges that agree with the best judge in both orders, disagree in both orders,
  or flip. Test whether flips add beyond the consistent-disagreement count.
- Output: `results/flips/a3_flip_vs_disagree.md`.
- Decides whether flips are a new signal or disagreement in another form.

**A4. Whose flips carry the signal.**
- 8x8 matrix: AUROC of judge i's flips for judge j's confident errors; summaries for weak vs strong flippers and
  same vs different family.
- Output: `results/flips/a4_matrix.md` + heat map.

**A5. Item or question.**
- BFF pairwise (several pairs per question): do flips on one pair predict the best judge's errors on other pairs
  of the same question? Same-pair vs sibling-pair AUROC.
- Output: `results/flips/a5_item_vs_question.md`.

**A6. Flips and solvability (BFF pairwise).**
- Join BFF solve labels: are a judge's flips concentrated on questions it could not solve? Are the best judge's
  confident errors on questions no judge solved?
- Output: `results/flips/a6_solvability.md`.

**A7. Flips as label-free difficulty.**
- Leave-one-judge-out: does the flip count from the other 7 predict a held-out judge's errors as well as
  "share of other judges wrong" (needs labels) or a simple IRT difficulty? Does it predict human splits
  (AlpacaFarm, MT-Bench human)?
- Output: `results/flips/a7_difficulty.md`.
- Pass: within 0.03 AUROC of the label-based measure; human-split AUROC ≥ 0.65.

**A8. Cheap judges as difficulty sensors.**
- Greedy choice of 1–3 checker judges on training folds, maximising errors caught per dollar (per-call cost is
  logged). Compare with the 1-checker disagreement flag (18% flagged, 39% caught) at equal flag rate and cost.
- Output: `results/flips/a8_cheap_sensors.md`.

### Stage B: confidence and token probability (new calls)

**B0. Smoke test (pennies).** 3 pairs x 3 judges on BFF pairwise. Check that verdicts, confidence lines and
verdict-token probabilities parse, and that the full output with reasoning is saved.

**B1. Pilot (about $5).** gpt-oss-120b (best judge) plus two checkers (gpt-oss-20b, Nemotron-Nano, the most
flippy), on BFF pairwise and MT-Bench human, both orders.
- Check 1: how often does asking for confidence change the verdict vs the stored run? Report results both ways.
- Check 2: is stated confidence informative or flat (everything 80–95)? Is the token probability better?
- Gate: continue to B2 only if parse rate ≥ 95% and at least one confidence measure has AUROC ≥ 0.6 for the
  best judge's errors.

**B2. Full run (about $30–45).** All 8 judges, all 4 pairwise benchmarks, both orders.

**Analyses on B data** (output `results/flips/b_*.md`):
- **B-a Own confidence vs own flips:** do judges report lower confidence (stated and token) on pairs they flip?
- **B-b Confidence vs confident errors:** is the best judge sure of itself when it is wrong in both orders?
  Calibration curves per judge; does calibration worsen for weaker judges?
- **B-c Confidence x detectability:** bin pairs by the best judge's confidence (two-order average, SCOPE-style
  entropy). Per bin: error rate, share of errors flagged by ≥ 2 other-judge flips, AUROC.
- **B-d Combined alarm:** best-judge confidence + other judges' flips (+ controls) in one grouped-CV model.
  Pass: beats each signal alone by ≥ 0.05 AUROC on ≥ 3 of 4 benchmarks, and at 18% flagged catches more than 39%.
- **B-e Others' confidence vs others' flips:** is low confidence from other judges a better alarm than their flips?
- **B-f Reasoning traces:** with full outputs now saved, code a sample of the best judge's confident errors
  (did it solve the problem and reach the same wrong answer?).

### Stage C: optional follow-ups
- **C1 Noise floor (about $10–20):** resample checkers 3–5 times per order; are repeatable flips better alarms
  than one-off flips?
- **C2 Controlled pairs (about $10):** same answer in both slots (pure position bias); a correct BFF answer vs
  the same answer with one injected numeric error of varying visibility; padded vs plain correct answers; an
  explicit "tie" option. Do flips rise as the quality gap shrinks?
- **C3 Embeddings:** semantic similarity features and a text-only model predicting flip counts (can we skip the
  checker calls?). Needs approval to download a small embedding model.
- **C4 Single-answer benchmarks:** if confidence tracks flips, use other judges' low confidence as the alarm on
  BFF, Safety and BBEH, where orders can't be swapped.

## 6. Shared analysis rules
- Measure confident errors only on pairs where the target judge is consistent.
- Grouped CV by question (pairs of the same question never split across folds); bootstrap CIs; Holm across benchmarks.
- Leave-one-judge-out whenever a judge's errors are predicted from flips, so a judge never predicts itself.
- Report the one-sample (K = 1) noise caveat until C1 is done.
- Every number in a write-up must come from a saved output file.

## 7. Schedule and cost

| When | Stage | Cost |
|---|---|---|
| 10/23–10/24 | Build feature table; A1–A3 | $0 |
| 10/27–10/28 | A4–A8 | $0 |
| 10/23 (parallel) | B0 smoke test, then B1 pilot | under $5 |
| 10/29–10/30 | B2 full run, if the pilot passes its gate | about $30–45 |
| 10/31–11/03 | B analyses; short HTML report | $0 |
| later | C1–C4 as results justify | about $20–30 |

## 8. Decisions this plan needs from the team
1. OK to spend about $5 on the pilot now, and about $30–45 on the full run if it passes?
2. OK to download a small open embedding model for C3?
3. Commit raw confidence outputs to git, or keep them on disk only (and back them up elsewhere)?

## 8b. Improvements after the literature review and judge-pair findings (10/22)
Findings: `docs/findings_order_flips.md`. Review: `docs/lit_review_cross_judge_error_detection.md`.

1. **Required baselines for every alarm.** (a) plain consistent-disagreement count; (b) the Hamidieh et al.
   (ICLR 2026) epistemic score, inter-judge minus intra-judge agreement; (c) a single second-judge verifier
   (Verify when Uncertain); (d) after Stage B, the best judge's SCOPE-style two-order entropy. Our signal has to
   beat or add to all four.
2. **Model the two signals separately.** The judge-pair results suggest flips are an item-level signal (they pool
   across judges and barely depend on the checker), while disagreement is a relationship-level signal
   (reciprocal, follows dissimilarity). A3 now fits both terms together and reports each one's gain.
3. **Score alarms by catches per false alarm and by cost, not AUROC alone.** Report errors caught at fixed flag
   rates (10%, 18%, 30%) and per dollar. Nemotron-Nano shows why: it flags 69% of gpt-oss-120b's errors but also
   59% of its correct pairs.
4. **New A9: checker portfolios and mutual pairs.** Choose 1–3 checkers on training folds by the catch vs
   false-alarm frontier; test on held-out folds and on a held-out benchmark. Test whether mutual pairs (two judges
   checking each other, e.g. Qwen3.6-35B + Nemotron-Super on JudgeBench: 82% / 74% at ~15% false alarms) hold up
   out of sample.
5. **Report the unflaggable floor.** For each benchmark, the share of the best judge's confident errors that no
   checker flags. Inspect a sample, and test whether the expert reference fixes them.
6. **Move the noise check earlier.** Run K = 3 samples in the B1 pilot so flips can be split into repeatable vs
   one-off before the full run.
7. **Perturbations beyond order.** For single-answer benchmarks, use knowledge-preserving rewrites of the question
   (DiverseAgentEntropy) or reference on/off as the perturbation, so the method is not limited to pairwise data.
8. **Uncertainty everywhere.** Bootstrap CIs grouped by question for every cell of the pair matrices; drop cells
   with fewer than 20 confident errors.
9. **Novelty check before any write-up.** Read the full texts of Hamidieh et al., *Uncovering Confident
   Failures*, Ding 2026 and the weak-to-strong risk paper (arXiv 2604.25077).
10. **Fix pass/fail rules before running B2.** Write the thresholds in this file and keep them.

## 9. Prior work and the gap

| Work | What it does | What it leaves open for us |
|---|---|---|
| Wang et al. 2023, *LLMs are not Fair Evaluators* (ACL 2024) | Swap orders and average; entropy over swapped verdicts picks items for humans | Uses the same judge's swaps only |
| Zheng et al. 2023, MT-Bench | Run both orders; inconsistent pairs become ties | Discards the flip as information |
| Shi et al., *Judging the Judges* (ICLR 2025) | 15 judges; position bias is driven mainly by the quality gap | Implies flips mark near-ties; not used to catch another judge's errors |
| Pezeshkpour & Hruschka (NAACL Findings 2024) | Order sensitivity appears when the model is unsure between its top choices | Single model, multiple choice |
| SCOPE, Badshah et al. (ICML 2026) | One judge's probabilities in both orders → uncertainty, with conformal risk control | Own uncertainty only; needs probabilities |
| Trust or Escalate, Jung et al. (ICLR 2025) | Agreement across prompted variants of one judge as confidence; stated confidence weak (AUROC 0.55 for GPT-4) | Own-model variants; misses confident errors |
| SAC3, Zhang et al. (EMNLP Findings 2023) | Self-consistency misses consistently wrong answers; cross-model checks catch many | Hallucination detection, not judging |
| Lail 2026, *Decomposing LLM-Judge Uncertainty* | Splits uncertainty into human disagreement vs judge ignorance | One judge, uses labels |
| KCSAT-ML 2026 (arXiv 2606.10403) | Ensemble disagreement predicts item accuracy partly by construction | Warns against circular difficulty measures |
| orq.ai blog (not peer-reviewed) | Own flips miss about 3/4 of hard-item errors, which are stable | Motivates using other judges' flips |
| Kohli 2026; Kim et al. ICML 2025 | Judges share errors (about 2 effective votes) | Shared confident errors may show no flips at all |

**Gap (in what we found):** prior work uses a judge's own order flips or own samples as its confidence. We found
no work that uses other judges' order flips to catch a strong judge's confident errors, or that measures how this
depends on the strong judge's confidence.

Sources: https://arxiv.org/abs/2305.17926 · https://arxiv.org/abs/2406.07791 · https://arxiv.org/abs/2308.11483 ·
https://arxiv.org/abs/2602.13110 · https://arxiv.org/abs/2407.18370 · https://arxiv.org/abs/2311.01740 ·
https://arxiv.org/abs/2609.06444 · https://arxiv.org/abs/2606.10403 ·
https://orq.ai/blog/llm-as-a-judge-alignment-with-humans
