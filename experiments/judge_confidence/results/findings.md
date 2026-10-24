# Findings (10/23): when judges are confidently wrong, and what could flag it

Judges: gpt-oss-120b, Qwen3.6-35B-A3B, DeepSeek-V3.1 on Tinker; 5 samples per verdict at T = 0.7; "confident" =
all 5 samples give the same verdict. Open models for hidden-state probes: Qwen3.5-0.8B, Jeff (Qwen3.5-0.8B fine-tune),
Qwen3.5-4B, Qwen3.5-9B on Modal GPUs. Raw outputs: `results/raw/` (see README; git-ignored, on the laptop only).

Tinker cost: $4.87 variant generation + $12.75 planted-error judging + $18.63 real judging + $14.70 UNSURE runs +
$0.26 coding = **$51.21**. Modal GPU time is billed separately (see the Modal dashboard).

**DeepSeek-V3.1 stopped being served by Tinker on 10/23 during the runs.** Its planted-error results cover the
pilot subset (109 error texts), and its UNSURE run covers 511 of 960 answers without the reference and none with it.

## 1. Planted numeric errors are caught; confident misses are rare

696 edited answers passed the automatic checks (one numeric error or a harmless control edit) on 255 expert-approved
BFF answers. Per-type tables: `pilot_summary.md`.

| Text (gpt-oss-120b and Qwen3.6 pooled) | n | Says INCORRECT, no reference | With reference |
|---|---|---|---|
| Unchanged answer | 248 | 19% (false alarm) | 13% |
| Paraphrase / harmless rounding | 223 / 52 | 19% / 16% | 14% / 9% |
| Final result contradicts the working (V1) | 125 | 94% | 94% |
| Consistent error ~10% / ×10 / leading digit | 84 / 50 / 76 | 96% / 93% / 93% | 95% / 89% / 91% |
| Consistent error ~1% | 86 | 84% | 80% |

- Planted errors accepted with all 5 samples: gpt-oss-120b 3.3%, Qwen3.6 1.4%, DeepSeek 4.6% (pilot subset).
- Size matters only at the small end: a 1% change is caught 80–84% of the time, other errors 89–96%.
- Contrast with the Validation Gap paper (consistent errors caught 3–45% by ≤70B models without reasoning): our
  reasoning judges recompute and catch them.

## 2. Real errors are confidently missed 3–6× more often

All 960 real BFF answers, no reference. Gold = unanimous expert label (256 correct, 203 incorrect).

| Judge | Planted errors: accepted with all 5 | Real errors: accepted with all 5 | AUROC of vote share on real items |
|---|---|---|---|
| gpt-oss-120b | 3.3% | 8.9% | 0.90 |
| Qwen3.6-35B | 1.4% | 8.4% | 0.85 |
| DeepSeek-V3.1 | 4.6% | 18.7% | 0.83 |

- Vote share is a useful confidence signal: when all 5 agree, accuracy is 84–90%; when samples are mixed, 53–63%.
  The verdict-word probability adds little (after reasoning it is almost always ~0 or ~1).
- 8 real wrong answers were confidently accepted by all three judges. In all 8 the arithmetic is internally right;
  the error is in the method or premise (e.g. the IFRS impairment question, where three answer models gave the
  same $116,550 and all three judges agreed). These look like misconceptions the judges share with the answer
  models, not numeric slips.
- Judges are about as confident on items where the experts split (78–79% of verdicts unanimous) as on clear
  items (80–89%).

## 3. The expert reference removes most confident misses on real errors

| Judge | Confident misses of real errors: none → reference | Confident false alarms on correct answers: none → reference |
|---|---|---|
| gpt-oss-120b | 9% → 2% | 8% → 5% |
| Qwen3.6-35B | 8% → 4% | 16% → 12% |
| DeepSeek-V3.1 | 19% → 1% | 10% → 7% |

Real wrong answers confidently accepted by all three judges: 8 → 0. With the reference, the main remaining
confident disagreement is rejecting answers the experts called correct (section 5).

## 4. Item features barely predict errors; long answers and weak answer models hide them

`features.py`, `features_summary.md`. Six coded question aspects, answer length, turn and answer model; logistic
models, CV grouped by question.

- Without the reference, item features hardly predict a judge's error (AUROC 0.52), low confidence (0.57) or
  confident error (0.58).
- Some features raise errors without lowering confidence: answer length (+0.42 for confident error vs +0.11 for
  low confidence) and gemma-2-2b answers (confident-error rate 20%, the highest, with the lowest uncertainty, 12%).
- Reasoning-heavy and open-ended questions raise uncertainty (+0.23) about as much as they raise errors, so judges
  are appropriately unsure there.

## 5. The "over-strict" rejections are mostly real flaws the expert label missed

61 cases (judge × answer) on 33 expert-approved answers rejected with all 5 samples even with the reference; 11
answers rejected by all three judges. Blind coder (Nemotron-3 Super 120B, sees question, reference and answer only):

| Group | Answers | Conclusion fully matches reference | Substantive error found |
|---|---|---|---|
| Rejected by ≥ 1 judge | 33 | 6 | 25 (76%) |
| Rejected by all 3 judges | 11 | 0 | 11 (100%) |
| Accepted by all 3 (control) | 33 | 24 | 2 (6%) |

Hand-checked 4, all real errors (a put valued at $20 above its strike; Pecking Order Theory misattributed; "a
negative tax liability means he owes the government money"; maintenance margin on purchase value). The expert
"correct" label often accepts a roughly right conclusion with a wrong step; the judges grade the whole answer. A
human check of the 33 is still needed before quoting a label-error rate.

## 6. Judges never use an UNSURE option

`judge_real.py --unsure`, `unsure_summary.md`. Same prompt plus "VERDICT: UNSURE if you cannot tell with confidence
... should be checked by a human expert".

| Judge, condition | UNSURE used (any of 5 samples) | Errors caught by UNSURE | Split vote: escalated / errors caught |
|---|---|---|---|
| gpt-oss-120b, no reference | 0.2% of answers | 2% of 64 | 13% / 39% |
| Qwen3.6, no reference | ~0% | 1% of 95 | 17% / 39% |
| DeepSeek, no reference (511 answers) | 0% | 0% of 51 | 16% / 29% |
| gpt-oss-120b, reference | 0% | 0% of 32 | 8% / 44% |
| Qwen3.6, reference | 0% | 0% of 57 | 10% / 33% |

Offering UNSURE does not change accuracy on the answers they decide (86% vs 86%, 80% vs 79%, 93% vs 93%). A
self-reported "I don't know" is useless here; disagreement among samples is the usable signal.

## 7. Confident errors look like confident correct verdicts in the reasoning

`reasoning_codes.py`, `reasoning_summary.md`. Blind coder on the first sample's reasoning, confident errors vs an
equal-size set of confident correct verdicts.

| Judge said | Group | n | Recomputed | Named an issue | Hedged | Median tokens |
|---|---|---|---|---|---|---|
| CORRECT | missed a real error | 73 | 42% | 4% | 0% | 214 |
| CORRECT | rightly accepted | 88 | 41% | 2% | 1% | 156 |
| INCORRECT | rejected an approved answer | 88 | 26% | 99% | 0% | 363 |
| INCORRECT | rightly rejected | 73 | 55% | 97% | 1% | 418 |

- Missed errors are indistinguishable from correct acceptances: same recomputation rate, no hedging.
- Rejections of approved answers recompute less and argue about definitions (42 of 88, vs 0 of 73).

## 8. Inside small judges: they know more than they say, and the gap shrinks with size

`probe_modal.py`, `analyze_probes.py`, `probes_modal.md`. Each open model sees the grading prompt with "VERDICT:"
pre-filled (no reasoning); linear probes on one layer, 5-fold CV grouped by question, best layer chosen on the same
folds (slightly optimistic).

| Model | Planted errors: verdict → probe (at verdict, no ref) | Real errors: verdict → probe, within answer model (no ref) | Real errors with reference: verdict → probe |
|---|---|---|---|
| Qwen3.5-0.8B | 0.61 → 0.85 | 0.64 → 0.87 | 0.81 → 0.98 |
| Jeff (0.8B, decision-trained) | 0.60 → 0.90 | 0.67 → 0.87 | 0.80 → 0.98 |
| Qwen3.5-4B | 0.88 → 0.93 | 0.82 → 0.86 | 0.97 → 0.99 |
| Qwen3.5-9B | 0.86 → 0.94 | 0.83 → 0.88 | 0.97 → 0.99 |

- **The smaller the model, the bigger the gap** between what its hidden state holds and what its verdict says
  (+0.20 to +0.30 AUROC at 0.8B, +0.04 to +0.08 at 4B–9B). This is the "knows but doesn't say" pattern, and it is
  mostly a small-model effect.
- **Confound check.** Answer model + answer length alone predict which real answers are wrong at AUROC 0.80, so the
  real-error column is computed within each answer model; the probe advantage survives. The planted-error column has
  no such confound (each variant is compared with the same answer unedited), and paraphrase edits stay at 0.48, so
  the probe does not just react to any edit.
- **Jeff vs its base:** decision training barely moves the verdict (0.60 vs 0.61 planted, 0.67 vs 0.64 real) and
  slightly sharpens the internal signal on planted errors (0.90 vs 0.85).
- **Experts splitting is barely encoded:** a probe for "humans disagreed on this answer" reaches only 0.59–0.61 in
  every model.
- **Before reading the answer:** a probe on the question alone predicts the model's own verdict error at 0.64–0.66
  and gpt-oss-120b's error at 0.60–0.62. A weak pre-routing signal.

## 9. The strong judges' blind spots are shared by small models

Among the 203 answers all experts marked wrong: do the ones a strong judge confidently accepted also look more
correct to a small model? (AUROC of the small model's "looks correct" score; 0.5 = unrelated, higher = shared blind
spot.)

| Small model | gpt-oss-120b's misses | Qwen3.6's misses | DeepSeek's misses |
|---|---|---|---|
| Qwen3.5-0.8B (probe / verdict) | 0.72 / 0.61 | 0.57 / 0.55 | 0.66 / 0.68 |
| Qwen3.5-4B (probe / verdict) | 0.75 / 0.82 | 0.73 / 0.82 | 0.71 / 0.85 |
| Qwen3.5-9B (probe / verdict) | 0.84 / 0.87 | 0.79 / 0.84 | 0.78 / 0.91 |

The answers strong judges confidently miss are the ones small models find most convincing too, and more so as the
small model gets larger. A small model's hidden state cannot be used to catch the big judges' confident misses.

## What this means

1. Planted numeric slips are not where strong reasoning judges fail. Their confident failures without a reference
   are method and premise errors they share with the answer models, and with smaller models too.
2. A reference fixes most of those; the confident disagreements left are mostly lenient expert labels.
3. For a router: escalate on split votes and always supply a reference when one exists. Self-reported UNSURE,
   the verdict-word probability, hedging language and item features are all near-useless; a small model's hidden
   state adds information mainly for very small judges and does not see the big judges' blind spots.
