# Plan: when are judges unsure, and when are they confidently wrong?

Two linked experiments. Direction 1 measures the judge's confidence on real items and asks what drives it.
Direction 2 controls the cause: it injects one numeric error into a correct answer and varies how visible the
error is. Both use the same confidence measures and the same probes, so they share most of the code.

Updated 10/22 after reading the full texts of the six closest papers (section "What the papers already show").

**Why.** Our routers and juries fail on errors that every judge makes with full confidence (error φ 0.30–0.48,
about 2 effective votes out of 8). Confidence predicts judge errors only moderately (AUROC 0.60–0.76), and drops to
chance where judges cannot solve the item.

**What we have now.** The 8 Tinker judges stored 1 vote per verdict and no log-probs, so they have no confidence
signal. Only Jev, CLM, Laya and Jeff store a probability (`p`). No judge prompt allows "unsure".

## What the papers already show (full texts read 10/22)

| Paper | Already shown | Not done |
|---|---|---|
| **The Validation Gap** (Bertolazzi et al., 2502.11771) | Models validating *someone else's* written arithmetic catch an inconsistent error (60–99%) but miss a consistent one (3–41%; Llama-70B ~45%). Mechanism: middle-layer "consistency heads" check that digits match; the correct sum is only computed in later layers, after the check | Toy word problems (one-digit + one-digit); only the units digit ever wrong; no size axis; no reference; no confidence; ≤3.8B models analysed |
| **Opening LLM Judges** (Mukherjee & Sitaram, 2609.32407) | For 64 judges, a probe at the verdict beats the verdict on 8/8 pairwise benchmarks (+0.12). The gain is predicted by surface confounding (ρ 0.90) and is **near zero on JudgeBench** (objective correctness). Internal confidence beats verdict margin for abstention | No numeric errors, no injected errors, no finance/math breakdown; no gain on single-answer rubric tasks |
| **FBI** (Doddapaneni et al., 2406.13439) | GPT-4-written single errors (CALCULATIONS, FINAL ERRORS, COPYING NUMBERS). GPT-4-Turbo misses 19–53% of calculation errors without a reference, **4% with a reference**. Explanations sometimes name the error while the score stays high | No severity levels, propagation unspecified, no confidence, no internals |
| **Probing for Arithmetic Errors** (Sun et al., 2507.12379) | Probes flag the model's *own* addition errors at >90% (Gemma-2B) | Never probes reading someone else's error; no comparison with the model's own judgement |
| **Calibrating LLM Judges with probes** (Radharapu et al., 2512.22245) | Probes are well calibrated, but error AUROC on JudgeBench is only 0.52–0.71 | No error types, no perturbations |
| **Classifying probes** (Maiya et al., 2503.17755) | Probes beat generated preferences on text-quality and commonsense tasks | No numeric or correctness tasks |

**Consequences for this plan**
1. "The judge's hidden state registers the error but the verdict misses it" is **not new as a general claim**
   (Opening LLM Judges). And for objective correctness that paper finds **no** internal advantage, so we should
   expect the signal may simply be absent.
2. V1 (inconsistent) vs V2 (consistent) is a **replication** of the Validation Gap, moved from toy sums to
   expert finance answers and larger judges.
3. The open question is sharper: *when a judge misses a numeric error in a realistic answer, is the error absent
   from its hidden states (a perception failure), or present but not used (a readout failure)?* The Validation Gap
   predicts readout for consistent errors (the right value is computed late); Opening LLM Judges predicts
   perception on objective tasks. Our design tests which one holds, and how this depends on size, digit place and
   the reference.

## Shared setup

| | |
|---|---|
| Output judges (Tinker) | gpt-oss-120b, Qwen3.6-35B-A3B, DeepSeek-V3.1 |
| Internal judges (laptop, M3 Pro 18 GB) | Qwen3.5-4B; Jeff (Qwen3.5-0.8B fine-tune) and its base. Qwen3.5-9B only 8-bit locally |
| Larger internal judges | Modal (gpt-oss-20b, Qwen3.5-9B full precision). **Modal is not logged in on this laptop** (needs `uv run modal setup`) |
| Confidence signals | (a) vote share over 5 samples; (b) probability of the verdict word from Tinker's top-k sample log-probs; (c) choosing UNSURE when offered |
| Internal signals | residual stream at the injected number's tokens, at the end of the answer, and at the verdict position; linear probes and logit lens |

### Storage (every model output kept for reuse)

All code and outputs live in `experiments/judge_confidence/`:

| Path | Contents | In git? |
|---|---|---|
| `results/raw/variants.jsonl` | One row per variant: source item, variant type, full original and new answer text, the exact edits, check results | No (large; on laptop only) |
| `results/raw/generator_calls.jsonl` | Every DeepSeek call that wrote a variant: prompt, raw output, tokens, cost | No |
| `results/raw/judgments.jsonl` | One row per (judge, text, condition): full prompt, all 5 sampled texts, parsed verdicts, top-k log-probs at the verdict token, tokens, cost, model id, renderer, sampling settings | No |
| `results/raw/activations/<model>/` | Hidden states for chosen layers and positions (float16 `.npy`) plus an index table | No |
| `results/*.md`, `results/*.json` | Summaries and figures | Yes |

`results/raw/` is git-ignored, so it exists only on this laptop. Back it up (e.g. Google Drive) before deleting
the folder.

## Direction 1: what makes a judge unsure?

**Questions**
1. Which item features predict low confidence, and which predict errors? A feature that predicts errors but not low
   confidence is a cause of confident errors.
2. If a judge may say UNSURE, does it use it on the items it gets wrong, or on the items where humans split?
3. Is "humans disagree" (ambiguity) represented differently from "I am wrong on a clear item" (ignorance)?
   A black-box version exists (2609.06444); probes are reported to fail under ambiguity (2511.04418), so ours tests
   that claim.

**Items.** BFF, MT-Bench human, AlpacaFarm, including the human-split items we dropped (152, 79, 147); JudgeBench
and BBEH.

| # | Step | Cost / time |
|---|---|---|
| 1.1 | Rerun the 3 output judges with 5 samples and verdict-word probability | ~$8 · 1.5 h |
| 1.2 | Same with a third option, `VERDICT: UNSURE` | ~$8 · 1.5 h |
| 1.3 | Item features → low confidence vs → error | $0 · 1 h |
| 1.4 | Code the reasoning of confident errors (recomputed? hedged? length?) | ~$1 · 1 h |
| 1.5 | Local probes on Qwen3.5-4B: error, human split, and "can I solve this" on the question alone | $0 · 1 day |
| 1.6 | Same probes on Jeff vs its base | $0 · 0.5 day |

Compare against disagreement escalation at the same escalation rate (catches 23–48% of errors at 10–23%).

## Direction 2: inject one numeric error, vary its visibility

**Items.** The 256 BFF answers all three experts marked correct (110 question turns). DeepSeek proposes the edits;
a script applies them and checks that only the intended numbers changed.

**Variants of each answer**

| Code | Change | Literature anchor |
|---|---|---|
| ORIG | Unchanged (baseline) | |
| V1 | Final stated result wrong; working left intact, so the answer contradicts itself | Validation Gap "answer error"; FBI FINAL ERRORS |
| V2-10 | One intermediate number off by ~10%, every later number recomputed consistently | Validation Gap "consistent error" |
| V2-1 | Same, ~1% | New: size |
| V2-x10 | Same, ×10 | New: size |
| V2-lead | Same, but only the leading digit changed (vs V2-10, where typically a later digit changes) | New: digit place (Validation Gap only tested the units digit) |
| C1 | Harmless rounding change; still correct | New: tests our judges' over-strictness on rounding |
| C2 | Paraphrase of one sentence, no number changed | Control |

Each text is judged without and with the expert reference. Hypothesis from the Validation Gap: a reference turns a
consistent error into an inconsistent one (the answer now disagrees with the reference), which would explain why
references help so much (FBI: 4% missed with a reference).

| # | Step | Cost / time |
|---|---|---|
| 2.1 | Pilot: 30 answers × 8 texts; generation, automatic checks, hand-check 20 variants; judge with 3 judges × 2 conditions × 5 samples | ~$9 · 1.5 h |
| 2.2 | Full run on all 256 answers | ~$60 · 3 h (decide after the pilot; could use 2 judges) |
| 2.3 | Local Qwen3.5-4B: does an "error present" probe fire at the injected number, at the end of the answer, and at the verdict? Logit lens for the verdict by layer | $0 · 1 day |
| 2.4 | Apply the probe to BFF's real incorrect answers | $0 · 2 h |

**Main figure.** For each variant and condition: detection by verdict, by confidence, and by the probe at each
position. Probe high + verdict low = readout failure. Both low = perception failure.

## Order and decision points

1. 2.1 pilot. Stop and fix the generator if fewer than ~80% of variants pass the checks.
2. 1.1 → 1.3.
3. Local probes (2.3, 1.5) on Qwen3.5-4B. If the pilot shows the 4B judge is near chance on V1, stop: there is
   nothing for the probe to explain.
4. 2.2 full run and 1.2 UNSURE only if the pilot results are clear.

## Risks

- Constructed errors are easier to catch than natural ones, so 2.4 is required before claiming anything about real
  errors.
- Probes transfer poorly across tasks; train and test on different items/benchmarks.
- Models we can probe locally (≤4B at full precision) are weaker than our best judges.
- Finance answers mix numbers in text, tables and code; one edit can leave a stale copy of the old number. The
  checker must catch this.
