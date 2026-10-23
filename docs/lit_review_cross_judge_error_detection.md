# Catching a judge's confident errors: literature review and gaps (10/22)

Scope: work on detecting when an LLM judge (or any LLM) is wrong, especially **confidently** wrong, using order
swaps, its own confidence, other models, and item difficulty. Written to position our order-flip study
(`docs/order_flip_difficulty_plan.md`).

**Verification level.** About 25 searches, mostly abstracts, venue pages and summaries. Full texts were not read
this session, so numbers are abstract-level unless marked. Check the paper before quoting a number.

## Bottom line
1. **Cross-model disagreement as a detector of confident errors is now an established idea for generation**, not
   for judging. Hamidieh et al. (ICLR 2026) and a NeurIPS 2025 workshop paper show that the gap between
   inter-model and intra-model agreement flags confident failures that self-consistency misses.
2. **Order swaps are well studied, but only as a judge's *own* uncertainty or as a bias to cancel**: Wang et al.
   2023, SCOPE 2026, TrustJudge 2026, JudgeLM's swap augmentation.
3. **Nobody we found combines the two for judges**, i.e. uses *other* judges' instability under order swaps to
   catch a strong judge's confident errors, or measures how that depends on the strong judge's confidence.
4. **Strong caution:** agreement is a weak and sometimes misleading confidence signal, worst for the most
   consistent frontier models, whose confident errors recur across providers (Ding 2026). Correlated errors
   (Kim 2025, Kohli 2026) set a floor that no agreement-based signal can cross.

## 1. Main research directions

### D1. Order swaps and position bias
| Paper | Finding |
|---|---|
| Zheng et al. 2023, MT-Bench (NeurIPS D&B) | Judge both orders; count inconsistent pairs as ties |
| Wang et al. 2023, *LLMs are not Fair Evaluators* (ACL 2024) | Average both orders; entropy over swapped verdicts (BPDE) picks items for human review |
| Shi et al., *Judging the Judges* (IJCNLP-AACL 2025) | 15 judges: position bias varies by judge and task and is driven mainly by the quality gap between the two answers |
| JudgeLM, Zhu et al. (ICLR 2025) | Swap augmentation in training; argues "judge twice and call it a tie" doubles cost without fixing the judge |
| Pezeshkpour & Hruschka (NAACL Findings 2024) | Option-order sensitivity appears when the model is unsure between its top choices |
| SCOPE, Badshah et al. (ICML 2026) | Bidirectional Preference Entropy from one judge's probabilities in both orders, with conformal risk control; up to 2.4x more accepted judgments at the same risk |
| TrustJudge (ICLR 2026) | Uses bidirectional preference probabilities to fix transitivity breaks (15.2% → 4.4% for Llama-3.1-70B) |
| Norman et al., *Reliability without Validity* (2026) | 21 judges, ~541K judgments: test-retest above 0.95 can coexist with position bias above 0.10; position bias spans ~100x across judges, highest for small cost-optimised models |

**Takeaway:** a flip is understood as the judge's own indecision on near-ties. It is used to cancel bias or to
measure the same judge's uncertainty, never as a signal about another judge.

### D2. A judge's own confidence
| Paper | Finding |
|---|---|
| Trust or Escalate, Jung et al. (ICLR 2025) | Simulated Annotators (agreement across prompted variants) beat token probability and stated confidence (GPT-4: 0.723 vs 0.642 vs 0.550 AUROC) |
| Tian et al. 2025, *Overconfidence in LLM-as-a-Judge* | Judges are overconfident; proposes TH-Score and an ensemble fix |
| Wang, Zhang & Choi (EMNLP Findings 2025) | The mean of the judgment distribution beats the most likely token in pointwise, pairwise and listwise settings; chain-of-thought collapses the distribution and often hurts |
| Radharapu et al. 2025 (Meta) | Linear probes on judge hidden states give calibrated uncertainty at ~10x lower cost than sampling |
| Sheng et al. (EMNLP 2025) | Conformal intervals for judge scores |

**Takeaway:** stated confidence is weak, distributions and probes are better, and all of them are blind to errors
the judge is sure about.

### D3. Cross-model disagreement to catch confident errors
| Paper | Finding |
|---|---|
| Cohen et al., *LM vs LM* (EMNLP 2023) | A second model cross-examines the first to expose factual errors; costly, needs a capable examiner |
| SAC3, Zhang et al. (EMNLP Findings 2023) | Self-consistency fails when a model is consistently wrong; cross-model checks and question perturbations catch many of these |
| Xue et al., *Verify when Uncertain* (ICML 2025) | Self-consistency is near its ceiling; a second-model verifier, called only on uncertain cases, adds detection at lower cost |
| Hamidieh et al. (ICLR 2026) | Epistemic term = inter-model minus intra-model similarity, from 5 similar 7–9B models; flags confident failures that self-consistency misses |
| *Uncovering Confident Failures* (NeurIPS 2025 workshop) | Same decomposition; the epistemic term exposes confident errors, mostly on tasks with near-unique answers |
| Feng et al., DiverseAgentEntropy (EMNLP Findings 2025) | A model can be confidently wrong on a question yet right on a knowledge-preserving rewrite; uses varied versions of the query |
| Ding 2026, *When LLMs Agree, Are They Right?* | 265K samples: agreement is a positive but weak predictor; worst for the most consistent frontier model, whose confident errors recur across providers |
| *LLMs as a Jury* (2026, arXiv 2607.10139) | Cross-model consensus can beat process reward models for selecting reasoning answers |

**Takeaway:** "other models catch what self-consistency misses" is established for generation. Its limit is
shared confident errors.

### D4. Weak models watching strong ones
| Paper | Finding |
|---|---|
| *Reliable Weak-to-Strong Monitoring of LLM Agents* (2025) | Weak monitors struggle under simple prompting; better scaffolds make them more reliable |
| *Evaluating Risks in Weak-to-Strong Alignment* (2026, arXiv 2604.25077) | Blind spots where the strong model is confidently wrong and the weak model is uncertain; strong-model variance predicts them |
| *LLM Performance Predictors* (2026, arXiv 2601.07006) | A meta-model predicting when an LLM is wrong beats standard uncertainty baselines (F1 ~81% → ~94% on one setting) |
| MetaCheckGPT (SemEval 2024) | Meta-regressor over many LLMs' signals detects hallucinations |

**Takeaway:** weak models' uncertainty on a strong model's errors is a known pattern in alignment and monitoring,
not yet in judging.

### D5. Item difficulty and meta-evaluation
| Paper | Finding |
|---|---|
| *The Progress Illusion* (EMNLP Findings 2025) | Judge-human correlation falls from ~0.8 to ~0.3 when the compared systems are close in capability |
| Choi et al., IRT for judges (ICML 2026) | Separates a judge's consistency under prompt perturbation from its human alignment |
| KCSAT-ML 2026 (arXiv 2606.10403) | Ensemble disagreement predicts item accuracy partly by construction; fit drops when measured on a different condition |
| *Counsel* (2026) | Meta-evaluation of judge critiques covers flagged errors but not missed ones |

**Takeaway:** near-tie and hard items are where judges fail, but difficulty measures built from the same
models' errors risk circularity.

### D6. Correlated errors set the floor
Kim et al. (ICML 2025): when two models both err, they often give the same wrong answer. Goel et al. (CAPA,
ICML 2025): errors converge as capability grows. Kohli 2026: 9 frontier judges carry about 2 effective votes.
Ding 2026: confident errors recur across providers.

**Takeaway:** any agreement-based alarm misses errors that every judge makes confidently.

### D7. Human disagreement vs judge ignorance
Lail 2026 splits judge uncertainty into human disagreement (labels can't fix it) and judge ignorance (labels can),
and targets expert labels at the second. Ni et al. 2025: LLMs predict human disagreement poorly, and reasoning
training makes it worse. Wang, Zhang & Choi 2025: judgment spread correlates only weakly with human disagreement.

**Takeaway:** some "errors" a flip flags are label noise on genuinely contested items. A study has to separate
these.

### D8. Selective evaluation with guarantees
Trust or Escalate, SCOPE, *Judge, Retrieve, or Abstain* (COLM 2026) and *Robust Conformal Consensus* (2026) give
finite-sample guarantees for abstaining or escalating. All calibrate a **single judge's own** confidence;
*Robust Conformal Consensus* warns that combining individually calibrated judges breaks the guarantee.

## 2. What is established vs open

| Claim | Status |
|---|---|
| Order swaps reveal a judge's own uncertainty; flips peak on near-ties | Established (D1) |
| Self-signals miss confident errors | Established (D2, D3) |
| Other models' disagreement catches some confident errors | Established for generation (D3); untested for judges |
| Weak models are uncertain where strong models are confidently wrong | Reported in weak-to-strong work (D4); untested for judges |
| Other judges' **order flips** flag a strong judge's confident errors | **Not found** |
| How detection by others depends on the strong judge's confidence | **Not found for judges** |
| Whether flips mark near-ties, unsolvable items or label noise | **Not separated** in any judge study we found |
| Guarantees from cross-judge signals | **Not found** (all use self-confidence) |

## 3. Gaps for future research (ordered by value for our project)

1. **Cross-judge order instability as an epistemic signal for judges.** Port the Hamidieh decomposition to
   pairwise judging, with order swaps as the perturbation: within-judge agreement across orders vs agreement
   across judges. Our first stored-data check gives AUROC 0.63–0.77 for other judges' flips flagging the best
   judge's confident errors.
2. **Detectability as a function of confidence.** Plot, by the strong judge's confidence (stated, token
   probability, two-order entropy), the share of its errors that other judges' flips catch. This tests whether
   cross-judge signals help exactly where self-signals fail. Ding 2026 suggests the most confident judges are the
   hardest case.
3. **Why flips mark errors.** Separate near-tie answers (Shi; *Progress Illusion*), unsolvable questions
   (No Free Labels) and contested labels (Lail) with controls and stored solve labels.
4. **Weak judges as sensors, not voters.** Bring the weak-to-strong monitoring idea to judging: are cheap, flippy
   judges the most cost-effective alarm? Compare against the disagreement flag at equal cost.
5. **Beyond order swaps.** Knowledge-preserving rewrites of the question (DiverseAgentEntropy), shuffled or
   paraphrased rubrics, reference on/off. This extends the method to single-answer grading where orders can't be
   swapped.
6. **Map the unflaggable errors.** Characterise errors that no self-signal or cross-judge signal catches (all
   judges consistent and wrong). Measure that floor per benchmark, and test whether only a reference or a human
   fixes them.
7. **Guarantees from cross-judge signals.** Calibrate escalation on other judges' instability with SCOPE /
   Learn-then-Test style bounds, recalibrating after combination (*Robust Conformal Consensus* warning).
8. **Validity checks.** Pair every flip analysis with test-retest (K ≥ 3 samples), since repeatable judges can still
   be position-biased (*Reliability without Validity*).

## 4. What this changes in our plan
- **Add baselines.** The Hamidieh inter-vs-intra epistemic score and a Verify-when-Uncertain-style second judge
  become required comparisons. Our claim must beat or complement them, not just plain disagreement.
- **A3 matters most.** If other judges' flips add nothing beyond consistent disagreement, our result is a
  judge-specific replication of D3, not a new signal.
- **Frame the contribution narrowly:** cross-judge *perturbation* signals for **judging**, their dependence on the
  strong judge's confidence, and the residual floor of unflaggable shared errors.
- **Before claiming novelty,** read the full texts of Hamidieh et al., *Uncovering Confident Failures*, Ding 2026
  and the weak-to-strong bias-variance paper (abstracts only so far).

## Sources
- Zheng et al. 2023: https://arxiv.org/abs/2306.05685
- Wang et al. 2023: https://arxiv.org/abs/2305.17926
- Shi et al.: https://arxiv.org/abs/2406.07791
- JudgeLM: https://arxiv.org/abs/2310.17631
- Pezeshkpour & Hruschka: https://arxiv.org/abs/2308.11483
- SCOPE: https://arxiv.org/abs/2602.13110
- TrustJudge: https://arxiv.org/abs/2509.21117
- Reliability without Validity: https://arxiv.org/abs/2606.19544
- Trust or Escalate: https://arxiv.org/abs/2407.18370
- Overconfidence in LLM-as-a-Judge: https://arxiv.org/abs/2508.06225
- Judgment distribution: https://arxiv.org/abs/2503.03064
- Linear probes for judges: https://arxiv.org/abs/2512.22245
- Conformal intervals for judges: https://arxiv.org/abs/2509.18658
- LM vs LM: https://arxiv.org/abs/2305.13281
- SAC3: https://arxiv.org/abs/2311.01740
- Verify when Uncertain: https://arxiv.org/abs/2502.15845
- Complementing Self-Consistency with Cross-Model Disagreement: https://arxiv.org/abs/2604.17112
- Uncovering Confident Failures: https://neurips.cc/virtual/2025/125252
- DiverseAgentEntropy: https://arxiv.org/abs/2412.09572
- When LLMs Agree, Are They Right?: https://arxiv.org/abs/2607.08065
- LLMs as a Jury: https://arxiv.org/abs/2607.10139
- Weak-to-strong monitoring of agents: https://arxiv.org/abs/2508.19461
- Weak-to-strong risks (bias-variance): https://arxiv.org/abs/2604.25077
- LLM performance predictors: https://arxiv.org/abs/2601.07006
- The Progress Illusion: https://aclanthology.org/2025.findings-emnlp.1036/
- IRT for judges: https://arxiv.org/abs/2602.00521
- KCSAT-ML: https://arxiv.org/abs/2606.10403
- Counsel: https://arxiv.org/abs/2606.21627
- Decomposing LLM-Judge Uncertainty: https://arxiv.org/abs/2609.06444
- LLMs and annotator disagreement (Ni et al.): https://huggingface.co/papers/2506.19467
- Judge, Retrieve, or Abstain: https://arxiv.org/abs/2608.17994
- Robust Conformal Consensus: https://arxiv.org/abs/2609.06367
