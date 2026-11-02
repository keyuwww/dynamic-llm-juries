# Confident, intermediate and unsure verdicts, right and wrong: plan (11/02)

**Question.** Does a judge's state differ between right and wrong verdicts **at the same confidence level**,
and does a confident error look like a confident right answer, an unsure error, or something else?
Two studies: **A** how similar errors are across judges, by confidence level (no new calls), **B** probes on
judges' hidden states (Modal GPU).

## Conditions: 3 confidence levels × 3 outcomes
Per judge × pair, from the confidence run (verdict and confidence from the same calls, both orders).

**Outcome:** right in both orders · wrong in both orders · flip (right in one order only; kept as its own outcome,
since correctness is undefined).

**Confidence level:** low / intermediate / high = the judge's own lower, middle and upper third of mean stated
confidence, cut **within each judge × benchmark**. Ties stay in one cell (confidence is coarse: 85, 90, 95, 100), so
cells are not exactly equal in size; we report their sizes.

| | Right | Wrong | Flip |
|---|---|---|---|
| **High** | HR: confidently right | **HW: confidently wrong** | HF |
| **Intermediate** (control) | MR | MW | MF |
| **Low** | LR: unsure but right | LW: unsure and wrong | LF |

Pooled counts with tertiles (all 8 judges, 4 benchmarks): high 3,499 R / 337 W / 428 F; intermediate 2,836 / 562 /
859; low 1,961 / 841 / 1,466. Error rate on consistent pairs: 8.8% high, 16.5% intermediate, 30.0% low.

**Main contrasts.**
1. **Right vs wrong at the same level** (HR–HW, MR–MW, LR–LW): does anything besides stated confidence separate
   errors? At high, this is the hidden-doubt test.
2. **Wrong across levels** (HW–MW–LW): is a confident error a different kind of error from an unsure one?
3. **Intermediate as control:** effects should be graded (low → intermediate → high). An effect only at the high
   level, absent at intermediate, is specific to confident errors and not a general confidence trend.
4. **Flips vs consistent** at each level: is order instability a separate kind of uncertainty from low confidence?

### Why not fixed 70 / 90?
They were my ad hoc choice: 90 sits near most judges' median, and 70 is where earlier calibration showed error rates
rising. They don't work across judges. Qwen and Nemotron-Nano put 79–86% of their answers at ≥ 90 and only 1–2% below
70, while gpt-oss-120b puts 45% at ≥ 90 and 10% below 70. A fixed "unsure" bin would be nearly empty for Qwen and
would mostly contain flips. Within-judge thirds compare each judge to its own scale, which also matches how the
other signals were built (ranked within each judge). **Robustness:** rerun A1–A5 with the fixed cuts
(< 70 / 70–89 / ≥ 90) and with quartiles; claim only results that hold under both.

### Threshold rule (from the confidence distributions)
Stated confidence is coarse: almost all values are 100, 95, 90, 85, 80, 70 or 60, and the two-order mean adds half
steps. So exact thirds are impossible; cuts are **snapped to the judge's value grid** (high = at or above its
67th-percentile value, low = below its 33rd-percentile value, ties never split).

| Judge | Low | Intermediate | High | Error rate low / int. / high |
|---|---|---|---|---|
| gpt-oss-120b | < 80 (31%) | 80–92.5 (36%) | ≥ 93 (33%) | 49% / 22% / 5% |
| gpt-oss-20b | < 87.5 (30%) | 87.5–94 (36%) | ≥ 94.5 (34%) | 53% / 38% / 15% |
| DeepSeek-V3.1 | < 85 (30%) | 85–97 (36%) | ≥ 97.5 (35%) | 54% / 33% / 10% |
| Nemotron-Super | < 85 (24%) | 85–94.5 (39%) | ≥ 95 (38%) | 61% / 40% / 19% |
| Qwen3.6-35B | < 95 (28%) | 95–99.5 (29%) | 100 (43%) | 51% / 31% / 10% |
| Qwen3.5-9B | < 90 (25%) | 90–97 (33%) | ≥ 97.5 (42%) | 56% / 44% / 15% |
| Qwen3.5-4B | < 95 (28%) | 95–99.5 (38%) | 100 (34%) | 58% / 42% / 15% |
| Nemotron-Nano | < 91 (32%) | 91–94.5 (19%) | ≥ 95 (48%) | 69% / 57% / 50% |

(Pooled over benchmarks for display; error = wrong in either order. The analysis cuts within judge × benchmark.)

- **Primary:** within-judge snapped thirds, as above. Each level means "relatively sure for this judge", which is
  the right reference for the probes (B), since they read the judge's own state.
- **Second lens, for cross-judge comparisons (A1, A2):** calibrated risk. Map each judge's confidence to its
  empirical error rate with isotonic regression, cross-fitted by question (no item labels its own level), then use
  common cuts: expected error < 15% / 15–35% / > 35%. "High" then means the same risk for every judge. Nemotron-Nano
  gets almost no high cell, which is accurate.
- **Robustness:** fixed 70 / 90 and quartiles.
- **Not used:** cuts tuned to maximise the error-rate gap on the same data. That would be circular for the
  right-vs-wrong contrasts and would leak labels into the probe cells.
- **Nemotron-Nano** is reported separately: even its high level is 50% wrong, so its confidence barely tracks
  correctness.

## A. Do judges share errors, and does it depend on confidence? (≈ 1.5 days, no calls)

**Hypotheses.** A1: errors are shared across judges more than chance, and HW more than LW (confident errors come
from shared misconceptions or bad labels). A2: shared HW items are mostly contested labels or near-ties.
A3: other judges' doubt catches LW and one-judge HW, not shared HW.

| Step | What | Output |
|---|---|---|
| A0 Cells | 3×3 counts per judge × benchmark; error rate and flip share by level. | count table |
| A1 Overlap | For each level, judge × judge co-occurrence of wrong verdicts (phi; observed / expected under independence). Permutation test within benchmark; same vs different family. | heat map per level |
| A2 Sharing spectrum | Per wrong verdict: how many other judges are also wrong on the item, by level of the focal judge, vs a Poisson-binomial null. | histogram vs null, by level |
| A3 Item correlates | Across all 9 cells: human vote margin (MT-Bench human, AlpacaFarm), answer similarity and length gap, same final number, BFF solve labels, aspect tags. Logistic within benchmark, level × outcome interaction. | effect plot by cell |
| A4 Hidden doubt | Verdict-token probability vs stated confidence: right vs wrong within each level. | AUROC per level |
| A5 Cross-judge catch | AUROC of others' doubt / disagreement for this judge's errors, within each level, and split by sharing level. | bar per level |
| A6 Qualitative coding | 120 items: 20 per cell for HW, MW, LW, HR, LR, HF, stratified by benchmark. Read question, both answers, gold, the judge's reasoning (`raw_full`). **Contrast pairs:** for HW items, put the reasoning next to a judge that was HR on the same item. Claude codes blind to cell labels; Janys codes 30 → Cohen's κ. | coded sheet, κ, 5–8 worked examples |

**A6 codebook (draft).**
- **Error type** (wrong cells only): missed factual error · arithmetic or logic slip · misread question or
  constraint · preferred length or style · preferred confident tone · near tie · gold label questionable · other.
- **For all cells:**
  - Noticed the decisive difference: yes / no.
  - Hedging or self-correction in the reasoning: yes / no.
  - Reasoning length.
  - Says the answers are close: yes / no.

The test is whether coders blind to the cell can tell HW from HR, and LW from LR, from the reasoning alone.

## B. Hidden-state probes (≈ 2.5 days, about $40–80 Modal)

**Hypotheses.** B1: right vs wrong is separable in hidden states at **each** confidence level, above a text
baseline. At high, that means hidden doubt; if it isn't separable, the confident error is a real belief.
B2: the separation is graded across levels, with intermediate in between. B3: HW sits closer to HR than to LW in
activation space (real belief) for shared errors, and closer to LW for one-judge errors. B4: the signal exists
before reasoning (end of prompt).

**Models (open weights, in our judge pool).**
- Qwen3.5-4B, Qwen3.5-9B: probes already run on Modal.
- gpt-oss-20b.
- Nemotron-3-Nano.
- Qwen3.6-35B-A3B: JudgeBench expert; H100.
- gpt-oss-120b: BFF / MT-Bench expert; H100, native 4-bit weights.

Start with gpt-oss-20b and Qwen3.5-9B. **Labels come from the model we read:** each model regenerates its own
verdicts on Modal, and levels are cut within that model.

| Step | What |
|---|---|
| B0 Setup | Check Modal auth (no `~/.modal.toml` found; may be env vars). Extend `experiments/judge_confidence/probe_modal.py` into `probe_states_modal.py`: pairwise confidence-run prompt, both orders, vLLM generation + HF forward pass. Smoke test on 20 pairs. |
| B1 Forced verdict (cheap) | Prefill the verdict with no reasoning; levels from within-model thirds of P(verdict). Residual stream at: end of question, end of answer B, verdict position. All 1,614 pairs. |
| B2 With reasoning | Generate reasoning + verdict + confidence (K = 1, temp 0.7), then forward pass. Levels from stated confidence. Activations at: end of prompt, verdict token, confidence token. |
| B3 Probes | Right-vs-wrong probe **trained and tested within each level**, plus one probe across levels with level as a covariate. Per layer, grouped 5-fold CV by question; layer chosen on inner folds. Text baseline (answer model, lengths, similarity, benchmark); report probe minus baseline. Leave-one-benchmark-out transfer. |
| B4 Geometry | Centroids of the 9 cells per layer. Distance of HW to HR vs to LW; the same for MW (control). Split HW by sharing level from A. |
| B5 Belief or item difficulty? | Apply model X's within-level probe to **other** judges' errors on the same items. If it transfers equally well, it reads item difficulty, not X's own belief. |
| B6 Logit lens (optional) | Layer at which the A/B preference settles, by cell. |

**Power.** About 10 HW per judge × benchmark on average, fewest for the strongest judges. Pool benchmarks per
model, use bootstrap CIs over questions, and below ~40 cases in a cell report direction and CI only.

## Storage
- Code: `experiments/cross_benchmark/confident_errors.py` (A0–A5);
  `experiments/judge_confidence/probe_states_modal.py`, `analyze_state_probes.py` (B).
- Tables and figures: `experiments/cross_benchmark/results/confident_errors/` (committed).
- A6 sheet: `results/confident_errors/coding.csv`; codebook in this doc.
- B generations and `index.jsonl` (key, cell, positions, P(verdict)) committed. Activations (`.npy`, GBs)
  git-ignored in `experiments/judge_confidence/results/raw/activations_states/<model>/`, on disk and the Modal
  volume, never only in the scratchpad.
- Write-up: `docs/results_confident_errors.md`; report section in `reports/difficulty-awareness.html`.

## Order and time
1. A0–A5 (≈ 4 h) → A6 coding (≈ 6 h incl. Janys's 30 items).
2. B0 + B1 on gpt-oss-20b and Qwen3.5-9B (≈ 1 day) → B3–B5 (≈ 4 h).
3. B1 on the two experts and B2 (≈ 1 day), if B1 shows a signal.

## Caveats
- K = 1: a single verdict can be lucky; B2 can add K = 5 for a subset.
- The confidence prompt changes 12–20% of verdicts, so cells come from the confidence run, not the stored run.
- AlpacaFarm and MT-Bench labels are crowd votes; a "wrong" verdict there may be a defensible minority view (A6
  codes this).
- Probes can read correlates (length, answer model); the text baseline and B5 guard against this.

## Prior work (check before citing)
- Orgad et al. 2024, *LLMs Know More Than They Show*: error signal at answer tokens; error types from resampling.
- Kossen et al. 2024: semantic-entropy probes.
- Simhi et al. 2025: high-certainty hallucinations.
- Kadavath et al. 2022: P(True) vs P(IK).
- Ding 2026; Kim 2025: correlated errors across providers.
- Shi et al., *Judging the Judges*: position bias driven by the quality gap.
