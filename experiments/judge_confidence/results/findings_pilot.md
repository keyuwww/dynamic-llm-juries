# Pilot findings (10/23): injected vs real errors, confidence, and the reference

Judges: gpt-oss-120b, Qwen3.6-35B-A3B, DeepSeek-V3.1 on Tinker; 5 samples per verdict at T = 0.7; "confident" =
all 5 samples give the same verdict. Raw outputs: `results/raw/` (see README). Tinker cost so far: $1.28 variant
generation + $4.77 injected judging + $18.63 real judging = **$24.68**.

## 1. Injected numeric errors are caught; confident misses are rare

173 edited BFF answers that passed the automatic checks (one numeric error or a harmless control edit; tables in
`pilot_summary.md`).

| Text | Says INCORRECT, no reference | With reference |
|---|---|---|
| Still correct (ORIG, rounding, paraphrase) | 12–30% (false alarms) | 3–18% |
| Final result contradicts the working (V1) | 73–97% | 85–100% |
| Consistent error: 1%, 10%, ×10, leading digit (V2) | 85–100% | 81–100% |

- Edits to numbers copied from the question are caught a little more often (0.95–0.97) than edits to computed
  numbers (0.86–0.88), but both are high.
- Of 218 (error text, reference condition) pairs, only 13 were accepted with all 5 samples by any judge; 1 by
  all three.
- Size and digit place barely matter at this level: the leading-digit variant is the hardest (81–91%).

Contrast with the Validation Gap paper (consistent errors caught 3–45% by ≤70B models without reasoning): our
reasoning judges recompute and catch them.

## 2. Real errors are confidently missed 3–8× more often

All 960 real BFF answers, no reference. Gold = unanimous expert label (256 correct, 203 incorrect).

| Judge | Injected errors: accepted with all 5 | Real errors: accepted with all 5 | AUROC of vote share on real items |
|---|---|---|---|
| gpt-oss-120b | 2% | 9% | 0.90 |
| Qwen3.6-35B | 1% | 8% | 0.85 |
| DeepSeek-V3.1 | 5% | 19% | 0.83 |

- Vote share is a useful confidence signal: when all 5 agree, accuracy is 84–90%; when samples are mixed, 53–63%.
  The verdict-word probability adds little (after reasoning it is almost always ~0 or ~1).
- 8 real wrong answers were confidently accepted by all three judges. In all 8 the arithmetic is internally right;
  the error is in the method or premise (e.g. the IFRS impairment question, where three answer models gave the
  same $116,550 and all three judges agreed with it). These look like misconceptions the judges share with the
  answer models, not numeric slips.
- Judges are about as confident on items where the experts split (78–79% of verdicts unanimous) as on clear
  items (80–89%), so their confidence does not track human ambiguity.

## 3. The expert reference removes most confident misses on real errors

Same 459 unanimous items, with the expert reference.

| Judge | Confident misses of real errors: none → reference | Confident false alarms on correct answers: none → reference |
|---|---|---|
| gpt-oss-120b | 9% → 2% | 8% → 5% |
| Qwen3.6-35B | 8% → 4% | 16% → 12% |
| DeepSeek-V3.1 | 19% → 1% | 10% → 7% |

- Real wrong answers confidently accepted by all three judges: 8 → 0 (most of the 8 are now caught by 2–3
  judges).
- With the reference, the main remaining confident error is the opposite one: **rejecting correct answers**
  (5–12% of correct answers rejected with all 5 samples). This matches the earlier finding that judges hold a
  stricter standard than the experts (rounding, a point the reference makes that the answer leaves out).

## What this means for the plan

1. "Numeric error injection" is not where confident judge errors live for strong reasoning judges. The confident
   misses are method/premise errors the judge shares with the answer models, which a reference fixes (the
   No Free Labels mechanism).
2. The open confident-error problem with a reference is **over-strict rejection of correct answers**. That is the
   next target: code those cases and test whether a probe or a second judge can flag them.
3. The local probe (section 4) finds only a small "knows but doesn't say" gap, and only without the reference.

## 4. Local probe: Qwen3.5-4B, verdict forced without reasoning

Same 229 texts (ORIG + passing variants), each with and without the reference; one forward pass with the
assistant turn pre-filled with "VERDICT:". Linear probes per layer, 5-fold cross-validation grouped by answer;
the best layer is chosen on the same folds, so probe numbers are slightly optimistic. Full numbers:
`results/probe_qwen3.5-4b.json`.

| | No reference | With reference |
|---|---|---|
| Verdict P(INCORRECT): AUROC, error vs still-correct texts | 0.89 | 0.94 |
| Probe at the verdict position (best layer 20–21) | 0.93 | 0.94 |
| Probe at the end of the answer (layer 18) | 0.89 | 0.89 |
| Probe at the edited number (last layer) | 0.98 | 0.98 |

- **Even without reasoning, the 4B judge's verdict catches most injected errors** (says INCORRECT on 77–100% of
  error texts, 16–20% of paraphrased correct texts).
- **The hidden state adds little beyond the verdict.** At the verdict position the probe gains +0.04 AUROC without
  the reference (largest for V1 0.85→0.90 and V2-lead 0.86→0.92) and nothing with it. This matches Opening LLM
  Judges, which found no internal advantage on objective-correctness benchmarks.
- **The 0.98 at the edited number is not clean evidence of error detection.** The same probe also flags the
  harmless rounding edits (C1: 0.81 vs ORIG), so at that position it partly detects "this number was edited"
  rather than "this is wrong". A fair test needs edits that are matched in form (e.g. swap in another plausible
  number that is still correct).
- So for injected numeric errors, missed errors are mostly not present-but-unused: when the verdict misses, the
  hidden state mostly misses too.
