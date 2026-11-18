# Related-work notes

These notes go with `refs.bib` (26 entries). Each entry was checked on 2026-11-16 against its arXiv record and, if published, against the venue's own page: the ACL Anthology .bib export, the NeurIPS or ICLR proceedings index, the iclr.cc poster page, or the OpenReview venue record.

Terms used below:
- **Direction:** our linear correctness direction, the difference of class means read from the judge's hidden state.
- **Verdict:** the judge's stated grade.
- **Same-author pairs:** a right and a wrong answer written by the same model.
- **Can't-solve questions:** questions the judge gets wrong when it answers them itself.

## Read first: overlap risks and surprises

1. **The claim that a probe beats the verdict now has concurrent work.** `gulati2026auditing` (arXiv, 2026-11-10) trains a correctness probe on a judge's attention-head activations. It compares the probe with the judge's verdict-token score on GSM8K and MATH, using open 7–12B models. The probe catches 1.3 to 22.5 more percentage points of errors when 5% of answers are reviewed. It is the same headline comparison as ours, on one of our benchmarks.
   - What it does not do: no same-author control, no can't-solve split, no steering, and no comparison with fact recall. It also reports that the probe transfers poorly across datasets.
   - It was posted after the mid-2026 window you gave, so treat it as concurrent work, but reviewers will expect it to be cited. Its arXiv comment names an IEEE TPS-ISA 2026 paper. I could not confirm that on a proceedings page, so the entry is an arXiv `@article`.
2. **Reading a judge's hidden state is already published at ACL.** `radharapu-etal-2026-calibrating` (ACL 2026 Industry Track) trains linear probes on reasoning judges' hidden states. It gets better-calibrated confidence than verbalized or multi-sample methods. So "use the judge's hidden state instead of its verdict" cannot be our novelty. What is still ours:
   - the split into authorship versus correctness;
   - the same-author, can't-solve condition;
   - the reasoning-versus-recall contrast;
   - steering.
3. **The internal-beats-external measure is close to ours.** `gekhman2025insideout` defines knowledge as the fraction of correct–incorrect answer pairs in which the correct answer is ranked higher. It compares that ranking from hidden states (internal) with the ranking from token probabilities (external). Internal beats external by about 40% on average.
   - That pairwise measure is close to our pairwise ranking metric, and their setting is closed-book fact recall.
   - They grade the model's own answers to its own questions. They do not grade other models' answers or split by solvability.
   - We find no gain on MMLU in the same-author, can't-solve setting. That may look like a contradiction with their result, so the paper should explain why it is not one.
4. **Our main premise is a published finding.** `krumdick2026nofreelabels` (COLM 2026) finds that, without a reference answer, judges agree with experts mainly on questions the judges can answer themselves. `tan2025judgebench` (ICLR 2025, ablation in Section 5) also states that a judge's ability to verify is "highly correlated with its ability to solve the problem itself". The paper should present the can't-solve split as building on these two results, not as a new observation.
5. **Authorship directions are already known.** `ackerman2025inspection` finds a residual-stream vector in Llama3-8B-Instruct that tracks "I wrote this" and steers authorship claims. `panickssery2024llm` ties self-recognition to self-preference. Our finding that most of the signal tracks who wrote the answer fits both papers, so cite them as support rather than presenting it as a surprise.
6. **Probe advantages can come from calibration.** `liu-etal-2023-cognitive` finds that when probes beat model outputs, the edge often comes from better calibration on uncertain items, not from more confident correct answers. Ranking metrics such as AUROC reward calibration. We should check whether the direction's lead holds at the verdict's operating point, not only in ranking.
7. **Steering a judge's hidden state is already done, but for bias.** `xu2026unfair` steers judges along bias subspaces in both directions, and a linear projection predicts judge failures. That is the closest work on steering judge activations. It targets bias, not correctness, and does not compare against letting the judge reason first.

I found nothing, by mid-2026 or in the concurrent paper above, that tests the direction-versus-verdict gap on same-author pairs, or on questions the judge cannot solve. That remains the most defensible new claim.

## Corrections to the citation details you gave

- **Rimsky et al. 2024 (CAA):** the ACL version lists the author as **Nina Rimsky** and the last author as "Alexander Turner". The arXiv record now shows "Nina Panickssery". The bib uses the ACL form. Key: `rimsky-etal-2024-steering`.
- **Turner et al.:** arXiv only. It was submitted to ICLR 2025 and rejected (per OpenReview). Earlier arXiv versions were titled "Activation Addition: Steering Language Models Without Optimization". The current title is "Steering Language Models With Activation Engineering".
- **Burns et al.:** the venue is ICLR **2023** (iclr.cc poster page). The arXiv record is from December 2022.
- **Marks & Tegmark:** COLM 2024 is confirmed by the OpenReview venue record. It was rejected at ICLR 2024 and shown as a poster at the NeurIPS 2023 ATTRIB workshop.
- **Krumdick et al.:** accepted at **COLM 2026** (OpenReview venue record), so it is cited as 2026, not 2025. The arXiv record now has four versions; the latest is from September 2026.
- **Xu et al. 2026:** it exists. The full title is "Inside the Unfair Judge: A Mechanistic Interpretability Account of LLM-as-Judge Bias". Authors: Zixiang Xu, Sixian Li, Huaxing Liu, Xiang Wang, Shuai Li, Zirui Song, Xiuying Chen. arXiv only, no venue.
- **Zou et al., Kadavath et al., Cobbe et al.:** arXiv only. I found no peer-reviewed version.

## Entries

### The 17 papers you listed

| bibkey | What it shows | How it relates to our paper |
|---|---|---|
| `li2023iti` | Shifts activations along "truthful" directions in a few attention heads at inference time. On TruthfulQA this raises Alpaca's truthfulness from 32.5% to 65.1%. | Prior work we build on: inference-time steering along a truth direction found from a few hundred labels. Our "stretch" is the same idea applied to a judge's grading. |
| `orgad2025llms` | Truthfulness information sits at specific answer tokens. Error detectors do not transfer across datasets. Models can encode the right answer yet still generate a wrong one. | Prior work: the hidden state knows more than the output. The finding that detectors do not transfer supports our per-benchmark, cross-fit directions and our caution about one general "correctness" axis. |
| `burns2023discovering` | Contrast-Consistent Search finds a truth direction without labels, using logical consistency. It beats zero-shot accuracy by about 4% and holds up when prompts push toward wrong answers. | Prior work on latent knowledge versus stated output. A contrast: our direction is supervised (difference of class means), not unsupervised. |
| `azaria-mitchell-2023-internal` | A classifier on hidden activations (SAPLMA) labels statements as true or false with 71–83% accuracy, depending on the base model. The paper compares it with methods based on the probability the model assigns to the sentence. | An early "probe beats output" result on true/false statements. We test the same gap for a judge grading other models' answers. |
| `marks2024geometry` | True/false statements are linearly separable at scale. Mass-mean probing (difference of means) generalizes better and has a stronger causal effect than other probes. | Direct precedent for our method: our difference-of-class-means direction is mass-mean probing. Cite it for the choice of estimator. |
| `zou2023representation` | Representation engineering: read and control high-level concepts (honesty, harm, and others) through population-level directions in hidden states. | Prior work for the read-then-steer workflow we use. |
| `turner2023steering` | Activation Addition: add a steering vector, computed from a pair of contrasting prompts, to the residual stream to change model behavior without any optimization. | Prior work on activation steering, and the method family our stretch belongs to. |
| `rimsky-etal-2024-steering` | Contrastive Activation Addition: steering vectors from the mean difference of activations on contrasting behavior pairs, added at chosen layers in Llama 2 Chat. | The closest steering precedent: a mean-difference vector added at a layer. Our stretch of the direction at a layer the verdict reads is the same operation. |
| `kadavath2022language` | Large models are mostly calibrated on multiple-choice questions and can be trained to predict whether they know an answer (P(IK)). | Background on models judging their own correctness. A contrast: our judges grade other models' answers, often on questions they cannot solve. |
| `zheng2023judging` | Introduces MT-Bench and Chatbot Arena. Strong LLM judges match human preferences more than 80% of the time, and the paper names position, verbosity and self-enhancement biases. | The standard LLM-as-a-judge reference. Our "verdict" baseline is this kind of prompted judge. |
| `panickssery2024llm` | LLM evaluators can tell their own outputs apart. Self-recognition ability correlates linearly with how strongly they prefer their own outputs. | Supports our finding that much of the hidden signal tracks authorship. It motivates the same-author control. |
| `krumdick2026nofreelabels` | With expert labels on 1,200 finance and MT-Bench responses: judges without a reference agree with experts mainly on questions they can answer themselves, and expert references largely fix this. | The premise we build on: judges fail where they cannot solve. We ask whether the hidden state still carries signal there. See surprise 4. |
| `gema-etal-2025-done` | Finds many errors in MMLU and releases MMLU-Redux, a set of 5,700 re-annotated questions. | Benchmark used (fact recall). |
| `hendrycks2021math` | MATH: 12,500 competition math problems with step-by-step solutions. | Benchmark used (reasoning). |
| `kazemi-etal-2025-big` | BBEH swaps each BIG-Bench Hard task for a much harder one. The best models score well below the ceiling. | Benchmark used (reasoning). |
| `xu2026unfair` | Judge biases appear as low-dimensional, type-specific subspaces in hidden state. Steering along them causes or removes biased scoring, and a linear projection predicts judge failures on unseen benchmarks. | The closest work on reading and steering judge activations. It targets bias, not correctness. See surprise 7. |
| `cobbe2021training` | Introduces GSM8K. Training verifiers to rank sampled solutions beats fine-tuning alone and scales better with data. | Background: verification as a separate skill from generation. Our verdict versus direction is a prompted judge versus a read-out verifier. |

### Additional papers (I found and verified these)

| bibkey | Area | What it shows | How it relates to our paper |
|---|---|---|---|
| `radharapu-etal-2026-calibrating` | (a) probing judges | Linear probes with a Brier-score loss on reasoning judges' hidden states give calibrated confidence at about one-tenth the compute of multi-sample methods. They transfer to unseen domains but are conservative on easy data. | The closest peer-reviewed work on probe-based judging. Our novelty has to rest elsewhere. See surprise 2. |
| `gulati2026auditing` | (a)/(d) concurrent | Compares a judge's verdict-token score with a correctness probe on attention heads, on GSM8K and MATH with open 7–12B models. The probe catches more errors at a fixed review budget but transfers poorly across datasets. | Concurrent work with the same headline comparison and no authorship or solvability controls. Posted 2026-11-10, after your mid-2026 window. See surprise 1. |
| `song2025mind` | (b) generator–verifier gap | Defines the generation–verification gap that governs self-improvement. A variant of the gap grows steadily with pre-training compute. | The standard reference for the gap. Our can't-solve split asks whether the judge's hidden state verifies where its generation fails. |
| `tan2025judgebench` | (b) | JudgeBench: hard response pairs labeled by objective correctness, on which many strong judges score near chance. An ablation finds that verifying ability is "highly correlated" with solving ability. | Supports the premise that judges fail on what they cannot solve. Also a possible extra evaluation set. |
| `west2024generative` | (b) | The "Generative AI Paradox": models can generate better than they understand, which is the reverse of humans. | The opposite direction of the gap. We look for the case where verification, as read from the hidden state, exceeds generation. |
| `ackerman2025inspection` | (c) authorship | Llama3-8B-Instruct, but not the base model, recognizes its own text. A residual-stream vector tracks self-authorship and can steer authorship claims. | Shows that authorship is linearly encoded and steerable in a model family we use. Supports the authorship finding. See surprise 5. |
| `liu-etal-2023-cognitive` | (d) probes vs outputs | Probes often beat model outputs because they are better calibrated on uncertain items, not because they are more often correct with confidence. The two can be combined for higher accuracy. | A warning about our AUROC comparison. It also suggests combining direction and verdict as a baseline. See surprise 6. |
| `gekhman2025insideout` | (d) | LLMs encode about 40% more factual knowledge internally than they express, measured by how they rank correct–incorrect answer pairs. Some answers are known internally but never generated, even in 1,000 samples. | Closest in measurement design: pairwise ranking from hidden states versus outputs, on fact recall. See surprise 3. |
| `zhang2025reasoning` | (d) | A probe on a reasoning model's hidden states verifies its own intermediate answers with good calibration. Using it to stop reasoning early saves 24% of tokens. | Same idea applied to self-verification on math. Ours is third-party grading, with authorship and solvability controls. |

## Considered but left out

- **Chen et al. 2025, "Do LLM Evaluators Prefer Themselves for a Reason?"** (arXiv 2504.03846). Real and relevant to self-preference (area c), but not peer-reviewed. It was rejected at ICLR 2026 and is listed as an ICLR 2027 submission on OpenReview. Add it as an arXiv citation if you want a second self-preference paper.
- **Wataoka et al. 2024, "Self-Preference Bias in LLM-as-a-Judge"** (arXiv 2410.21819). Workshop paper only (NeurIPS 2024 Safe Generative AI Workshop).
- **Eshuijs et al. 2025, "But what is your honest answer? Aiding LLM-judges with honest alternatives using steering vectors"** (arXiv 2505.17760). It steers models to build alternatives for a judge to compare against. I found no venue.
- **Ribeiro et al. 2025, "On LLMs' Internal Representation of Code Correctness"** (arXiv 2512.07404). It finds a correctness direction for code. The arXiv comment says ICSE'26, but I did not check that on a proceedings page, and it is software-engineering work.

Unverified papers: none. All 17 papers you listed were found and checked. I left nothing out for lack of verification. The four papers above were left out only because they lack a peer-reviewed venue or are less relevant.
