# Pilot findings (10/23): injected vs real errors, confidence, and the reference

Judges: gpt-oss-120b, Qwen3.6-35B-A3B, DeepSeek-V3.1 on Tinker; 5 samples per verdict at T = 0.7; "confident" =
all 5 samples give the same verdict. Raw outputs: `results/raw/` (see README). Tinker cost so far: $1.28 variant
generation + $4.77 injected judging + $18.63 real judging + $0.13 coding = **$24.81**.

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

## 2. Real errors are confidently missed 4–9× more often

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
- With the reference, the main remaining confident disagreement is the opposite one: **rejecting answers the
  experts called correct** (5–12% rejected with all 5 samples). Section 5 shows most of these answers do contain a
  real error.

## What this means for the plan

1. "Numeric error injection" is not where confident judge errors live for strong reasoning judges. The confident
   misses are method/premise errors the judge shares with the answer models, which a reference fixes (the
   No Free Labels mechanism).
2. With a reference, the confident rejections of "correct" answers turned out to be mostly real flaws the expert
   label missed (section 5), so the reference-plus-strong-judge setup has very few confident errors left that are
   the judge's fault. The next useful step is a human check of the 33 disputed answers.
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

## 5. The "over-strict" rejections are mostly real flaws the expert label missed

Cases: correct answers (all experts said correct) that a judge rejects with all 5 samples even with the
reference: 61 (judge × answer) on 33 answers; 11 answers rejected by all three judges; 35 of the 61 on gemma-2-2b
answers. Script `overstrict.py`, full tables in `overstrict_summary.md`, coder Nemotron-3 Super 120B (not one of the
three judges; $0.13).

**Blind check.** The coder sees only the question, the reference and the answer (not the judge's reasoning), and
says whether the conclusion matches the reference and whether there is a substantive error anywhere. Control =
33 correct answers all three judges accepted.

| Group | Answers | Conclusion fully matches reference | Substantive error found |
|---|---|---|---|
| Rejected by ≥ 1 judge | 33 | 6 | 25 (76%) |
| Rejected by all 3 judges | 11 | 0 | 11 (100%) |
| Accepted by all 3 (control) | 33 | 24 | 2 (6%) |

Hand-checked 4 (10/23), all with a real error: a put's intrinsic value given as $20 when the stock is above the
strike; the Pecking Order Theory credited to "Myron S. Miller and Ferris J.文明 (Fama), 1987"; "a negative tax
liability means he owes the government money"; maintenance margin computed on the purchase value instead of the
current value. A coder that sees the judge's reasoning agrees with the judge in all 61 cases, so only the blind
numbers should be used.

What this means:
1. **Most of the remaining confident "errors" with the reference are label problems, not judge problems.** The
   expert "correct" label often accepts an answer whose conclusion is roughly right while a step, definition or
   fact is wrong; the judges grade the whole answer. Judge accuracy against BFF's unanimous labels is therefore
   understated, and the 11 answers all three judges reject are likely mislabelled.
2. **Cheap flags would not (and should not) overturn these rejections.** 66% of rejections of "correct" answers
   are unanimous across the 5 samples. A second judge agrees with gpt-oss-120b's and DeepSeek's rejections 86–94%
   of the time. Only Qwen3.6's rejections are often idiosyncratic: another judge accepts 43% of them (13 of 30)
   at a 9% escalation rate.
3. The coder is an LLM too; a human check of the 33 answers (about 1 hour) should confirm before we report any
   label-error rate.
