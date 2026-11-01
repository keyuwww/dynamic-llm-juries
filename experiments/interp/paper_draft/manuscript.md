---
title: "Rubrics Change What LLM Judges Know, Not Just What They Say: A Logit-Lens and Causal Study Across Five Benchmarks"
author: "Team 10 (Kensho / AC297r, Harvard SEAS)"
date: "October 2026"
---

# Abstract

We study a specific failure mode in LLM-as-judge pipelines: a judge model's own interior
representations can already agree with human gold labels better than the verdict it actually
outputs. Using logit-lens probing (reading each transformer layer's hidden state through the
model's own final norm and unembedding) and same-pass causal activation patching on gpt-oss-120b,
we show this "best-layer-beats-final" effect is (1) real and reproducible across five
benchmarks of unrelated format and domain — BFF-Bench (finance/accounting correctness),
JudgeBench (pairwise response comparison), RewardBench2-Safety (binary appropriateness),
BiGGen Bench (multi-capability instance-level rubrics), and HealthBench (physician-written
medical-response rubrics) — with every held-out gap significant at p < 1e-5 across 200
random splits; (2) causally real, not an artifact of logit-lens readout, confirmed by
same-pass activation patching that recovers the gold verdict in 98-100% of flip items on
every benchmark tested; (3) model-specific rather than a property of the probing method,
since Qwen3.5-9B shows zero or negative gaps on all five benchmarks and gpt-oss-20b shows
a degenerate, content-blind pattern on three; and (4) sharpened or qualitatively changed by
a genuine, human-authored, benchmark-specific grading rubric on three of three benchmarks
where one exists (BFF, BiGGen, HealthBench), including one case where a rubric flips a
*significant null* (HealthBench standard) into a *significant positive* effect. A direct
logit attribution (DLA) analysis finds the degradation is driven roughly 2-4x more by MLP
writes than attention writes across every benchmark, but that naive per-layer attribution is
an unreliable localizer of the true causal layer specifically under BiGGen's per-instance
rubric condition (median mislocalization: 17 layers), where head-level ablation shows neither
candidate layer has a single responsible component — a genuinely diffuse, non-head-localized
mechanism, unlike BFF's locally recoverable "active override" pattern.

# 1. Introduction

LLM-as-judge pipelines are increasingly used to grade, rank, and reward model outputs at scale,
often as a drop-in replacement for human annotation. A judge model's *stated* verdict is usually
treated as the ground truth signal for downstream training or evaluation. This paper asks a
narrower, mechanistic question: does the model's own internal computation actually agree with
that stated verdict, or does the final output discard information that an earlier layer already
had right?

We build on activation-patching methodology from Wang et al. (2025), "When Truth Is Overridden:
Internal Origins of Sycophancy" (arXiv:2508.02087), which shows that a truthful internal
representation can be causally overridden by later computation under social pressure. We ask an
analogous question under a different pressure: a *grading rubric*. Does giving a judge model an
explicit, detailed rubric to follow change whether its final verdict reflects what it "knows"
internally?

**Contributions.**

1. A reusable logit-lens-plus-causal-patching pipeline, applied to five benchmarks spanning
   finance, safety, general capability, and medicine.
2. A policy for what counts as a legitimate "rubric" condition: we require the rubric text to be
   verbatim (or a documented, clearly-labeled derivation) from a human-authored source tied to
   that benchmark's own annotation process — never researcher-invented. This ruled out one
   initially-used condition (RewardBench2-Safety's CoCoNot-derived rubric) from our strict
   comparisons, kept as a broader replication case instead.
3. Formal significance testing (200-split bootstrap confidence intervals, sign-permutation
   p-values) for every benchmark/condition pair, and cross-model replication establishing the
   phenomenon is specific to gpt-oss-120b rather than an artifact of the probing method.
4. A novel application of direct logit attribution (DLA) to this setting, which (a) replicates
   the ablation-based active-override/passive-forgetting distinction via an independent,
   non-interventional method, and (b) uncovers and fully dissects — down to the individual
   attention head — a case where naive attribution is a reliable localizer everywhere except one
   specific benchmark/condition.

# 2. Related Work

**Internal vs. stated judgment.** Wang et al. (2025, arXiv:2508.02087) show sycophantic judges
can have the correct answer latent in an earlier layer, which is then causally overridden.
Halawi et al. (2024, arXiv:2307.09476), "Overthinking the Truth," find an analogous late-layer
degradation under false few-shot demonstrations driven by a small number of attention heads
that actively reintroduce the wrong answer — a localized, head-level mechanism. Our setting
differs from both: we use a single forward pass per condition (no need for a paired
clean/corrupted run), and rather than a social or demonstration-based pressure, our manipulation
is the presence or absence of a rubric.

**Attribution reliability.** "Opening LLM Judges: Recovering Preference Signals Beyond the Final
Verdict" (arXiv:2609.32407) reports that naive attribution correlates only ρ=0.31 with true
causal effect from patching, and that causal decision depth is typically earlier than where the
logit lens appears to "decide." Our DLA-vs-causal-layer comparison (Section 5.4) directly
replicates this warning within our own data, and extends it by showing the mismatch is
*benchmark/condition-specific* rather than a blanket property of the method: four of five
tested cases show accurate attribution, and the one exception is itself causally dissected.

**Benchmarks and rubrics.** BFF-Bench's rubric is reused verbatim from Setlur et al.'s "No Free
Labels" (arXiv:2503.05061, Appendix A.4), originally written for human annotators. BiGGen Bench
(Kim et al., 2024, arXiv:2406.05761) supplies a genuine per-instance scoring rubric for every
evaluation item. HealthBench (OpenAI, arXiv:2505.08775) supplies physician-written rubric
criteria with physician binary agreement labels, released via `openai/simple-evals`.
RewardBench2's Safety category (used as a broader replication benchmark, not a strict rubric
pair) names CoCoNot (Brahman et al., 2024) as its taxonomy source but does not reproduce its own
annotators' rubric text verbatim.

# 3. Method

## 3.1 Logit-lens probing

For a forced-choice judge prompt ending in a single CORRECT/INCORRECT token, we read the hidden
state at every layer through the model's own final RMSNorm and unembedding matrix, giving a
layer-wise probability $p_\text{correct\_norm} = p_\text{CORRECT} / (p_\text{CORRECT} +
p_\text{INCORRECT})$. This is compared against the model's actual final-token answer and against
the human gold label.

## 3.2 Held-out validation and formal significance

Picking "the best of N layers" and comparing it to the final layer is a multiple-comparisons
problem. For each benchmark/condition/model, we run 200 random 50/50 item splits: the winning
layer is chosen by Cohen's κ against gold on half A only, then scored *only on that fixed layer*
against the held-out half B. We report the mean gap across splits, a percentile bootstrap 95%
CI (10,000 resamples of the 200 split-level gaps), a two-sided Monte Carlo sign-permutation
p-value (100,000 permutations, H0: each split's gap sign is a fair coin flip), and a "layer
stability" statistic — the fraction of the 200 splits whose winning layer falls within ±2 of the
modal winner.

## 3.3 Causal confirmation: same-pass activation patching

Correlation between an interior layer and gold is not causation. For every "flip" item (an
interior layer agrees with gold at layer L but the model's spoken answer does not), we run a
*second* forward pass, hook the fixed layer L to capture its hidden state during a first pass,
then overwrite a later candidate layer K's output with that captured value (last token only),
scanning K from L+1 to the final layer. The earliest K that recovers the gold verdict is the
item's causal rescue layer. This requires no paired clean/corrupted prompt, since the correct
signal is already present earlier in the same prompt.

## 3.4 Mechanism classification: active override vs. passive forgetting

At the causal rescue layer, we zero-ablate the *whole* attention-sublayer or MLP-sublayer
output (no patched-in value). If ablation alone recovers the verdict, that computation is
actively overriding a correct signal ("active override" — a "false induction head"-style
mechanism). If ablation does not help, but the self-patch does, the later computation is merely
failing to preserve, rather than actively erasing, the earlier signal ("passive forgetting").

## 3.5 Direct logit attribution (DLA)

For each flip item, in a single ordinary forward pass (no intervention), we hook every decoder
layer's attention and MLP submodules to capture their raw write vectors to the residual stream
at the last token. Each write is projected onto the forced-choice unembedding direction $u =
W_U[\text{tok}_\text{pos}] - W_U[\text{tok}_\text{neg}]$, scaled by the final RMSNorm's learned
gain and divided by the final residual's RMS norm — the standard linear approximation used
throughout the attribution literature to rank per-sublayer contributions to the output logit
difference. This gives a cheap, continuous, per-layer, per-item signal generalizing the binary
ablation test, letting us compare the *loudest* layer under naive attribution against the *true*
causal rescue layer from Section 3.3, and slice by item subject/category.

## 3.6 Head-level dissection

Where DLA and the true causal layer disagree, we zero-ablate one attention head at a time (of
64) at both the DLA-flagged layer and the true causal-layer cluster, to test whether either
location has a single, dominant responsible head.

# 4. Benchmarks and the rubric-provenance policy

We adopt a strict rule: a benchmark's "rubric" condition is included in our rubric-vs-standard
comparison only if the rubric text is verbatim from, or a clearly-labeled derivation of, a
human-authored source tied to that specific benchmark's own annotation process. Researcher-
invented rubrics, or rubrics borrowed from an upstream/analogous taxonomy, are excluded from
this comparison (though may still be used for the broader "does the layer-vs-final effect exist
at all" question).

| Benchmark | Domain | Rubric source | Strict pair? |
|---|---|---|---|
| BFF-Bench | Finance/accounting correctness | Setlur et al. 2025, Appendix A.4 (human annotator guidelines, verbatim) | Yes |
| BiGGen Bench | Multi-capability (8 categories) | Per-instance, human-authored scoring rubric (verbatim, one per item) | Yes |
| HealthBench | Medical response quality | OpenAI physician-written rubric criteria, verbatim, physician binary gold | Yes |
| JudgeBench | Pairwise response comparison | No rubric exists (algorithmic gold) | N/A — standard only |
| RewardBench2-Safety | Binary appropriateness | CoCoNot (Brahman et al. 2024) taxonomy — upstream, not RB2's own annotator text | No (replication only) |

This policy caused us to drop an initially-used RewardBench2-Safety rubric condition from the
strict comparison after an internal review identified it as a borrowed, not verbatim, rubric —
documented here as a methodological correction rather than omitted silently.

HealthBench specifically: we use OpenAI's public meta-evaluation release (29,511 rows, each a
(conversation, completion, physician-written rubric criterion) triple with 2+ physician binary
judgments), keeping the 77.5% of rows with unanimous physician agreement as gold, consistent
with this project's BFF `consensus=unanimous` policy elsewhere.

# 5. Results

## 5.1 The held-out layer-vs-final gap is real and significant everywhere tested

Table 1 reports, for gpt-oss-120b, the held-out κ gap (best interior layer minus final answer)
for all nine benchmark/condition combinations, with 200-split bootstrap CIs and permutation
p-values.

**Table 1. Held-out layer-vs-final κ gap, gpt-oss-120b.**

| Benchmark | Condition | Gap (κ) | 95% CI | p | Modal layer (depth) | Stability |
|---|---|---|---|---|---|---|
| BFF-Bench | standard | +0.161 | [0.150, 0.170] | <1e-5 | 28% | 94.5% |
| BFF-Bench | real rubric | **+0.167** | [0.159, 0.175] | <1e-5 | 89% | 97.0% |
| BiGGen Bench | standard | +0.111 | [0.103, 0.119] | <1e-5 | 83% | 84.5% |
| BiGGen Bench | per-instance rubric | **+0.105** | [0.097, 0.113] | <1e-5 | 11% | 87.0% |
| HealthBench | standard | **-0.011** | [-0.014, -0.009] | <1e-5 | 100% (literal final) | 75.0% |
| HealthBench | physician rubric | **+0.025** | [0.023, 0.027] | <1e-5 | 94% | 73.0% |
| JudgeBench | — | +0.052 | [0.041, 0.062] | <1e-5 | 97% | 93.0% |
| RewardBench2-Safety | standard | +0.209 | [0.202, 0.216] | <1e-5 | 78% | 99.5% |
| RewardBench2-Safety | CoCoNot rubric* | +0.197 | [0.189, 0.205] | <1e-5 | 50% | 83.5% |

\* Not a strict pair; retained for the broader causal-replication question only.

Every row is significant at p < 1e-5 with ≥73% layer stability. HealthBench-standard is the
single case in this entire study with a significant, negative gap — its own final layer
(literally the last layer, 100% of winning splits) is the single best layer available. Its
rubric condition flips this to a significant positive effect: the rubric does not merely change
the *size* of the effect here, it changes its *sign*.

## 5.2 The effect is model-specific, not a probing artifact

We replicated BiGGen and HealthBench on two additional models already established in this
project as reference points: Qwen3.5-9B (a model that never shows this effect on any other
benchmark) and gpt-oss-20b (a model with documented content-blind, constant-prediction behavior
on other benchmarks).

**Table 2. Cross-model replication.**

| Model | Benchmark | Condition | Gap (κ) | p | Modal layer |
|---|---|---|---|---|---|
| Qwen3.5-9B | BiGGen | standard | -0.002 | 0.33 (n.s.) | 81% depth |
| Qwen3.5-9B | BiGGen | rubric | -0.131 | <1e-5 | 100% (final) |
| Qwen3.5-9B | HealthBench | standard | -0.015 | <1e-5 | 100% (final) |
| Qwen3.5-9B | HealthBench | rubric | -0.067 | <1e-5 | 100% (final) |
| gpt-oss-20b | BiGGen | standard | -0.005 | <1e-5† | 100% (final) |
| gpt-oss-20b | BiGGen | rubric | -0.006 | <1e-5† | 0% depth |

† Significant but near-zero, driven by a content-blind constant prediction (identical full-sample
κ = 0.0054 in both conditions), the same degeneracy previously documented for gpt-oss-20b on
RewardBench2-Safety and JudgeBench.

Qwen3.5-9B now shows zero or significantly *negative* layer-vs-final gaps on five of five
benchmarks tested in this project. This cross-model evidence supports treating the
best-layer-beats-final phenomenon as a genuine property of gpt-oss-120b's computation, not an
artifact that any forced-choice logit-lens probe would find in any sufficiently large model.

## 5.3 The effect is causally real, and its mechanism bifurcates into two types

Same-pass activation patching recovers the gold verdict in 98-100% of flip items on every
benchmark/condition tested (BFF: 100%, 137/137; RewardBench2-Safety: 100%, 245/245; BiGGen-
rubric: 98.5%; HealthBench-rubric: 100%, 181/181) — whenever a correlational gap exists, it is
essentially always causally confirmed.

Whole-sublayer ablation at the causal layer classifies each benchmark/condition into one of two
mechanisms:

- **Active override** (BFF, JudgeBench): deleting the sublayer's output alone recovers the
  verdict in 83-87% of items — a small number of computations are actively reintroducing the
  wrong answer.
- **Passive forgetting** (RewardBench2-Safety-rubric, BiGGen-rubric, HealthBench-rubric):
  deletion alone recovers almost nothing (89%, 98.5%, and 89.5% of items respectively require
  the actual earlier hidden state to be restored) — later computation is not actively erasing
  the signal, merely failing to carry it forward.

## 5.4 Direct logit attribution: MLP-dominant, and usually (but not always) a reliable localizer

Across every benchmark tested, MLP sublayer writes dominate attention writes in pushing toward
the incorrect verdict (ratio 1.4-3.8x), and this dominance is uniform across all eight of
BiGGen's capability categories even though *flip frequency* varies sharply by category
(reasoning/tool-use/refinement: 23-26% of items flip; safety: 1.8%; instruction-following: 5%).

**Table 3. DLA peak-push layer vs. true causal layer, across all eight pairs run.**

| Benchmark/condition | Best layer L (of 37) | MLP-dominant items | Median (DLA peak − causal layer) | Attribution reliable? |
|---|---|---|---|---|
| JudgeBench (no rubric) | 35 | 17% | 0 | Yes |
| HealthBench (rubric) | 34 | 76% | -1 | Yes |
| BFF (rules) | 31 | 55% | +1 | Yes |
| BiGGen (standard) | 30 | 80% | 0 | Yes |
| RewardBench2-Safety (standard) | 28 | 40% | -3 | Yes |
| **RewardBench2-Safety (CoCoNot rubric)** | **18** | **95%** | **+12** | **No** |
| **BFF (standard)** | **10** | **23%** | **+21** | **No** |
| **BiGGen (rubric)** | **4** | **96%** | **+17** | **No** |

This table went through two working hypotheses before this one. The first (Section 6)
was that mislocalization tracks *per-instance* rubrics specifically; it was rejected once
RewardBench2-Safety's reused, non-per-instance CoCoNot rubric also mislocalized. The second
was that mislocalization tracks >90% MLP dominance — true of both mislocalizing cases known at
the time, with all five accurate cases below 80%. Adding the eighth pair, BFF's standard
(no-rubric) condition, rejected this too: BFF-standard is only 23% MLP-dominant (mostly
attn-dominant, the *opposite* of the signature) yet mislocalizes worse than anything else in the
project (median +21 layers). Across all eight pairs, MLP-dominance and attribution error are
essentially uncorrelated (Pearson r=0.13, R²=0.02).

What predicts it instead is **how early the true best layer L is**: r(L, median diff)=-0.93,
R²=0.87. DLA's own peak-push layer clusters in a narrow, nearly fixed late band (30-36 of 37)
regardless of benchmark — including BFF-standard (70/93 flip items peak at layer 32) and
BiGGen-rubric (64/68 at layer 31) — while the true causal layer tracks L itself (BFF-standard's
causal layer clusters at 11-13, just after its L=10; BiGGen-rubric's at 13-15, just after its
L=4). When L is already late (L≥28 here), DLA's fixed late-band bias happens to land near the
true cause and attribution looks reliable; when L is early, the same bias overshoots by however
far L is from that band. This reads as a genuine DLA artifact — raw per-layer writes project more
strongly onto the readout direction merely by being closer to the final unembedding, independent
of which layer's computation is actually causally responsible — now pinned to a concrete,
falsifiable predictor (L) rather than a mechanism-type guess that didn't survive an eighth data
point.

## 5.5 Head-level dissection: neither candidate layer has a single responsible head

Zero-ablating one attention head at a time (of 64) at both candidate layers:

| Layer(s) | Role | Items with any single head recovering the verdict |
|---|---|---|
| Layer 31 | DLA's (false) peak | 1 / 70 (1.4%) |
| Layers 13, 14, 15 | True causal cluster | 2-6 / 70 per layer (3-9%), no head repeats more than 3× |

Layer 31 is a red herring: it dominates naive attribution but zero-ablating any single head
there recovers almost nothing, confirming it is downstream noise rather than the mechanism —
exactly the failure mode arXiv:2609.32407 describes. Layers 13-15 are causally real (same-pass
patching rescues ~100% of items there) but have no dominant head either. Combined with the
passive-forgetting result (Section 5.3), this rules out a Halawi-et-al-style "a few heads
actively reintroduce the wrong answer" mechanism for BiGGen's rubric condition specifically: the
effect is genuinely diffuse, distributed across many heads/dimensions, and recoverable only by
literally replaying the earlier computation forward.

# 6. Discussion

The central empirical finding is that a judge model's final, spoken verdict can be a strictly
worse predictor of human agreement than a fixed interior layer, that this gap is model-specific
rather than universal, and that a genuine human-authored rubric does not uniformly fix or break
this — it can sharpen an existing effect, shift where in the network it is computed, or (in
HealthBench's case) flip a null into a real effect. Practically, for the one model studied
closely (gpt-oss-120b), reading a fixed, pre-calibrated interior layer rather than the model's
own final token would simultaneously reduce inference cost and increase agreement with human
labels on at least seven of nine tested benchmark/condition pairs — though the right layer is
benchmark- and model-specific and would need held-out calibration before any deployment use.

The dissociation between "active override vs. passive forgetting" (an ablation property) and
"is naive attribution a reliable localizer" (a DLA property) is, to our knowledge, a novel
observation: these are not two readings of the same underlying fact. RewardBench2-Safety-standard
and HealthBench-rubric are both passive-forgetting (89%, 89.5%) *and* attribution-accurate, while
BiGGen-rubric and RewardBench2-Safety-rubric are both passive-forgetting (98.5%, 89%) *and*
attribution-inaccurate, and BFF-standard (mostly active-override, 75%) is *also*
attribution-inaccurate — confirming the two axes are genuinely orthogonal rather than a
coincidence of the first seven points. What actually predicts attribution-inaccuracy went through
two rejected guesses before the current one (Section 5.4): *per-instance rubrics* (falsified by
RewardBench2-Safety's reused CoCoNot rubric mislocalizing), then *>90% MLP dominance* (falsified
by BFF-standard mislocalizing worst of all at only 23% MLP-dominant). The current best-supported
predictor — how early the true best layer L sits (r=-0.93, R²=0.87 across all eight pairs) — is a
depth artifact of DLA itself, not a property of the benchmark's rubric or mechanism type. We
report this trajectory explicitly, including the two rejected hypotheses, because each one looked
well-supported on five-to-seven points and broke on the next; the current account should be read
as hypothesis-generating, not confirmed, and we would not be surprised if a ninth pair breaks it
too.

# 7. Limitations and future work

- All causal and mechanistic results (Sections 5.3-5.5) are reported for gpt-oss-120b only;
  cross-model evidence (Section 5.2) establishes that the *size and direction* of the
  correlational effect is model-specific, but we have not run the causal/mechanistic pipeline on
  a second model that *does* show the effect, since none of the other models tested show it
  reliably enough to generate a large flip-item set.
- Both the per-instance-rubric hypothesis and the >90%-MLP-dominance hypothesis for attribution
  mislocalization (Section 6) were tested and rejected in sequence as more data arrived; the
  current best-layer-depth account (Section 5.4) is drawn from only eight benchmark/condition
  pairs on one model and has not been tested by directly manipulating L (e.g. a model or prompt
  designed to put L at a different depth) — it remains an observed correlation across benchmarks
  that differ in many other ways at once, and a ninth pair could break it exactly as the eighth
  broke the previous guess.
- The DLA approximation treats RMSNorm's denominator as a near-constant scalar, a standard but
  imperfect linearization; it is used here only to rank and localize contributions, not to
  reconstruct exact logit values.

# References

- Wang et al. 2025. "When Truth Is Overridden: Internal Origins of Sycophancy." arXiv:2508.02087.
- Setlur et al. 2025. "No Free Labels." arXiv:2503.05061.
- Kim et al. 2024. "The BiGGen Bench." arXiv:2406.05761.
- OpenAI. 2025. "HealthBench." arXiv:2505.08775. Data: github.com/openai/simple-evals.
- Brahman et al. 2024. "CoCoNot." (RewardBench2-Safety's cited taxonomy source.)
- Halawi et al. 2024. "Overthinking the Truth." arXiv:2307.09476.
- Anonymous. "Opening LLM Judges: Recovering Preference Signals Beyond the Final Verdict."
  arXiv:2609.32407.
