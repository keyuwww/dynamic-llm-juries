# Why judges approve wrong answers they agree with — report (Nov 8–9, 2026)

## The question, in one paragraph

Your starting point was the interpretability finding that a judge's *interior* layers sometimes know the right
verdict when its *spoken* verdict is wrong, and the broader question of why some LLMs judge well and others
don't. Our BBEH data showed one consistent failure: **judges approve wrong answers far more often when the
wrong answer is the same one they would have given themselves** (7 of 8 pool models). You asked whether that
happens *before* the judge reasons (it reads the problem and already "knows" its answer) or *during* the
reasoning. Overnight we tested that, then tried the two papers' ideas — an internal "is this right?" signal
(INSPECTOR, Li et al. ICLR 2026) and steerable bias directions (Inside the Unfair Judge, Xu et al. 2026) — on
open models, to see whether they are feasible here and what they add.

**Short answer.** The lean toward the judge's own answer is already there before it reasons, and reasoning
roughly doubles it instead of correcting it. But most of it is not about the judge's *own* answer: it is a
belief shared by the whole Qwen family about which wrong answers look right. Inside the model, the
"is this right?" signal is real and causally controls the verdict, but it acts as a leniency dial, not as a
detector of which answer is wrong; and there is no separate "this is my answer" direction to steer.

**Llama-3.1-8B (a different family, added this morning)** shows *no* lean toward its own answer in what it says —
but only because its spoken verdict barely tracks anything: it accepts right and wrong answers at almost the same
rate. Its hidden state at position A separates right from wrong far better than its words, and that hidden signal
*does* lean toward its own wrong answers, by about the same amount as in the Qwens. Llama also does not accept the
wrong answers the Qwens believe, so the "shared belief" from Experiment 1 is mostly Qwen-family-specific.

**Nov 9 additions (Experiments 5–8).**
- **Belief strength.** Measured with 7 fresh own answers instead of one, the lean is graded. Wrong answers the
  judge reaches 7/7 times are accepted 71% of the time at the verdict; those it never reaches, 18%. The old one-sample
  match label adds nothing once belief is known. With this better measure there is a real **personal** part (+22
  points on the same wrong answer), not only a family belief.
- **Thinking on.** The gap gets *larger* (about +58 points vs +37 with thinking off).
- **Inside the model.** Belief is readable from the hidden state (held-out AUROC up to 0.86), better than an
  "is this right?" probe, and more readable as the judge writes.
- **Steering.** Pushing along the belief direction while the judge reasons only shifts overall leniency. It does not
  selectively remove the anchored wrong answers.

---

## Terms used below

- **Position A**: the moment after the judge has read the question and the candidate answer, before it writes
  anything. **C**: right before it writes its verdict word. **50%**: halfway through its reasoning.
- **Reading the verdict at a checkpoint**: cut the judge's transcript there, append `VERDICT:`, and see whether
  the model's next word would be CORRECT or INCORRECT.
- **Match / differ**: the wrong candidate answer is the same as / different from the answer the judge gave
  when it solved the question itself (a separate call; the judge never sees it while judging).
- **AUROC**: how well a score ranks right answers above wrong ones. 0.5 = coin flip, 1.0 = perfect.
- **Within-question AUROC**: the same, but only comparing candidates to the *same* question, so "this question
  is hard" can't help. This is the fair test.

## Benchmarks

| Benchmark | Format | Items per Qwen judge |
|---|---|---|
| BBEH Mini | single answer, judge says CORRECT / INCORRECT | 920 |
| RewardBench 2 Math | single answer, CORRECT / INCORRECT | 732 |
| JudgeBench (no coding) | pairwise, judge picks A or B | 547 |

Judges: qwen3.5-4b, qwen3.5-9b, qwen3.6-35b (Tinker, thinking off, their original pool transcripts). Probes
and steering: Qwen3.5-4B, Qwen3.5-9B and Llama-3.1-8B on Modal GPUs. No gpt-oss anywhere.

---

## Experiment 1 — When does the lean toward its own answer appear? (Tinker, 3 Qwens)

### Data fixes made tonight
- **Cut-off answers rerun from scratch** with the whole 64K context: about half of the Qwens' BBEH solves had
  stopped at 16K tokens with no final answer; 924 of 1,006 reruns now finish. 503 judging transcripts that
  stopped before their verdict line were rerun too (all but 21 now reach a verdict; RB2 judging had been run
  with only 1,024 tokens).
- **Answer matching** (does the judge's answer equal the candidate's?) is done by **GLM-5.3-Flash** (high
  reasoning). Checked against exact letter answers: 99.2% agreement. Nemotron was dropped.
- Every rebuilt prompt matches the original run's token count (6,597 / 6,597); the reading at C equals the
  judge's actual spoken verdict 99.9% of the time.

### Result
Wrong answers only, pooled over the three Qwens, with 95% intervals (questions resampled):

| | Before reasoning (A) | At the verdict (C) | Reasoning rescues a wrong accept less often when it matches |
|---|---|---|---|
| Extra acceptance when the wrong answer matches the judge's own | **+24 points** [+18, +31] | **+36 points** [+30, +41] | **+23 points** [+16, +30] |

Per benchmark, rescue = "accepted at A, rejected by C":

| | matching wrong answers rescued | differing wrong answers rescued |
|---|---|---|
| RB2 Math (3 Qwens) | 0–21% | 28–77% |
| JudgeBench | 30–41% | 47–65% |
| BBEH | 11–16% | 5–29% |

**Plain reading:** on first read the judge already leans toward answers that agree with what it believes;
reasoning then fixes wrong answers it *disagrees* with but almost never ones it agrees with (on RB2 Math the
35B Qwen rescues 77% of disagreeing wrong answers and 21% of agreeing ones).

### Update (Nov 8): the main benchmark set — RB2 Math + JudgeBench + BFF-Bench

BBEH turned out to be beyond the Qwens' ability (see below), so the main set is now RewardBench 2 Math, JudgeBench
and **BFF-Bench** (finance questions; the candidates are labelled correct/incorrect by unanimous human experts). For
BFF, each Qwen answered exactly the conversation the candidate answered (full 64K budget; 893/894 finished), its 62
judging transcripts that had hit the old 2,048-token cap were rerun from scratch, and GLM-5.3-Flash compared final
answers (BFF answers are prose, so matching is fuzzier than on math; spot checks looked right).

Wrong answers only, pooled over the three Qwens (95% intervals, questions resampled):

| Benchmark | Gap at A | Gap at C | Rescue gap |
|---|---|---|---|
| **Main set** | **+23** [+17, +30] | **+37** [+31, +43] | **+29** [+21, +37] |
| RB2 Math | +18 [+6, +30] | +44 [+33, +53] | +39 [+30, +48] |
| JudgeBench | +23 [+12, +34] | +21 [+10, +32] | +15 [−2, +32] |
| BFF-Bench | +27 [+12, +38] | +41 [+27, +52] | +44 [+26, +62] |
| BBEH (contrast) | +28 [+18, +39] | +29 [+21, +38] | +7 [−6, +18] |

Same wrong candidate, three Qwens, judge + candidate fixed effects (the "is it *my* answer?" control):

| | at A | at 50% | at C |
|---|---|---|---|
| Main single-answer set (RB2 Math + BFF) | **+14** [+5, +23] | +4 [−6, +15] | +6 [−3, +15] |
| RB2 Math | +9 [−6, +22] | −8 [−26, +11] | −2 [−19, +17] |
| **BFF-Bench** | **+17** [+5, +31] | +12 [−1, +25] | **+11** [0, +23] |

**Plain reading.**
- The pattern holds on all three main benchmarks: the lean is there before reasoning and reasoning grows it, except
  on JudgeBench, where it stays about the same.
- On BFF there is a **personal** own-answer effect even on the same wrong answer: a Qwen that gave that wrong answer
  itself accepts it 17 points more often at A, and 11 more at the verdict, than a Qwen that did not. On math it is
  mostly the family-shared belief.
- On BFF the 35B also **rejects correct answers that disagree with its own**: it accepts 56% of them at A but only
  19% at the verdict. Reasoning argues it out of right answers it disagrees with.

### Is BBEH simply too hard for the Qwens?

Partly, yes. As judges, the Qwens are competent on RB2 Math (they accept 87–89% of right answers and only 13–34%
of wrong ones) but struggle on BBEH (right / wrong accepted: 4B 65% / 57%, 9B 81% / 57%, 35B 78% / 51%); they solve
only about half of BBEH themselves. Splitting BBEH by difficulty (share of the pool's candidates that are right):

| BBEH questions | Wrong answer accepted at the verdict: matches own / differs | Gap |
|---|---|---|
| Hard (≤25% of candidates right) | 82% / 50% | **+32 points** [+22, +42] (+34 already at A) |
| Medium (25–60%) | 58% / 44% | +14 [−5, +33] |
| Easy (≥60%) | 83% / 62% | +22 [−7, +48] (only 52 wrong answers) |

**Plain reading:** the lean toward the judge's own answer is strongest exactly where the judge cannot verify the
answer — it falls back on "does this match what I think?". It is not only a BBEH artefact, though: on RB2 Math, where
the Qwens judge well, reasoning still rescues far fewer matching wrong answers (0–21%) than differing ones (28–77%).

### The control that matters
A wrong answer the judge also gave may just be a *convincing* wrong answer to everyone. Comparing the three Qwens
on the **same** wrong answer, and removing each judge's overall leniency:

| | At A | At 50% | At C |
|---|---|---|---|
| Effect of "this matches *my* answer" | +7 points [−2, +16] | −1 | +3 |

So most of the effect is **shared belief within the model family** (all Qwens find the same wrong answers
plausible), not the individual judge's own answer. The personal part is small and not significant with the
final data (it was +13 with an earlier, noisier matching).

---

## Experiment 2 — Is there an internal "is this right?" signal? (INSPECTOR idea) — feasible, smaller than it first looks

A linear probe reads the hidden state at position A (every layer) and predicts whether the candidate is correct.
Whole questions held out. Candidates that never wrote a final answer are dropped (always wrong, too easy).

**Within-question AUROC (the fair test):**

| Model | Benchmark | Judge's own verdict at A | Hidden-state probe (best layer) |
|---|---|---|---|
| Qwen3.5-4B | BBEH | 0.58 | 0.64 (layer 25) |
| Qwen3.5-9B | BBEH | 0.65 | 0.65 (layer 19) |
| Llama-3.1-8B | BBEH | 0.57 | **0.68** (layer 29) |
| Qwen3.5-4B | RB2 Math | 0.81 | 0.83 |
| Qwen3.5-9B | RB2 Math | 0.84 | 0.85 |
| Llama-3.1-8B | RB2 Math | 0.74 | **0.79** |
| all | JudgeBench | 0.58–0.73 | lower than the verdict |

- Over all candidates the probe looked dramatic (BBEH 0.73 vs the judge's 0.49), but **most of that is the
  probe recognising which questions are hard** — something the hidden state encodes and the verdict ignores.
  That itself is a finding: the judge's verdict does not use what the model knows about question difficulty.
- Within a question, the hidden signal beats the verdict only a little for Qwen, not at all for Qwen-9B, and the
  most for **Llama (+5 to +10 points)**.
- **How anchored is the hidden signal?** Holding leniency equal to the spoken verdict, the 4B/9B probe accepts
  matching wrong answers 10–13 points more than differing ones — about the same as the verdict at A (16–19), and
  far less than the spoken verdict at C (31–43). **The anchoring in the representation is already there at A;
  most of the extra comes from reasoning.**

**RB2 Math alone (where the Qwens judge well)** — same-leniency comparison, wrong answers only:

| Judge | Matching wrong answers accepted: verdict at A / spoken / probe | Differing wrong answers: verdict at A / spoken / probe | Lean (match − differ): spoken vs probe |
|---|---|---|---|
| Qwen3.5-4B (n = 67 / 442) | 42% / 63% / 45% | 25% / 30% / 35% | **+33 vs +10** |
| Qwen3.5-9B (n = 61 / 450) | 41% / 69% / 33% | 27% / 21% / 29% | **+48 vs +4** |
| Llama-3.1-8B (n = 78 / 418) | 60% / 65% / 55% | 63% / 67% / 66% | −2 vs −11 |

On RB2 Math the hidden state at A is barely anchored (Qwen-9B: +4 points), while the spoken verdict is strongly
anchored (+48). So on a benchmark the judge can solve, **most of the anchoring is created during the written
reasoning, not present in the first read**; at the same overall leniency the probe accepts about half as many of the
matching wrong answers as the spoken verdict. Caveats: the probe is trained on correctness labels (a best linear
reading, not the model's own opinion), and there are only ~60–70 matching wrong answers per judge.

## Experiment 3 — Steering (Unfair Judge idea) — "is this right?" is causal but only a leniency dial; "my answer" is not causal

Push the hidden state at position A along a direction by ±4 or ±8 standard deviations; read the verdict at A.

| Direction | Qwen3.5-4B | Qwen3.5-9B | Random direction (control) |
|---|---|---|---|
| "is this right?" (correct − wrong) | accept rate 0% at −8 → 93–97% at +8 | 0% → 84–98% | moves ≤ ±20 points |
| "matches my answer" (match − differ, wrong only) | −10 on matching wrong, but −19 on correct | −8 / −10 | same size as random |

- The correctness direction really **causes** the verdict, but it moves right and wrong answers together, so it
  makes the judge stricter or more lenient everywhere — it does not fix anchoring specifically.
- There is **no causal "this is my answer" direction** at position A, consistent with the weak probe
  (0.70–0.74 vs a text-only baseline of 0.64–0.66) and with Experiment 1's control.

---

## Experiment 4 — Llama-3.1-8B: a judge from another family

**What ran.** Llama answered all 1,102 questions itself and judged the same 2,199 candidates the Qwens judged (vLLM
on an H100, T = 0.7, each output allowed to fill the 64K context; 1,047 of its own answers and 2,187 of its judging
transcripts finished). Llama often ignores the requested format ("The assistant's answer is CORRECT." instead of
`VERDICT: CORRECT`), so GLM-5.3-Flash read the verdict in the 187 transcripts with no verdict line (it found one in
101; the rest never gave a verdict, e.g. Llama solved the question instead of grading it) and compared the 230 BBEH
answers that lacked "The answer is". Position A for Llama is the GPU readout (same `...VERDICT:` setup).

**Finding 1 — Llama barely judges.** Share of candidates accepted in its spoken verdict:

| | right answers | wrong answers | for comparison, Qwen-35B (right / wrong) |
|---|---|---|---|
| BBEH | 52% | 55% | 78% / 51% |
| RB2 Math | 83% | 67% | 89% / 13% |
| JudgeBench (picks the target) | 56% | 46% | 98% / 47% |

It is also a weak solver: its own answer equals the correct one on about 19% of BBEH and 34% of RB2 Math questions
(Qwens: 50–65% and 82–86%).

**Finding 2 — no own-answer lean in what Llama says.** Wrong answers only, Llama's own answer matches vs differs
(95% intervals, questions resampled):

| | Gap at A | Gap at C | Rescue gap |
|---|---|---|---|
| all three benchmarks | −2 points [−10, +6] | +2 [−6, +10] | +1 [−8, +9] |
| RB2 Math (where Llama does tell right from wrong) | −3 [−15, +9] | −2 [−13, +10] | −4 [−16, +8] |

(Qwens: +24 at A, +36 at C.) Reasoning also barely moves Llama: its accept rates at A and C are nearly the same.

**Finding 3 — but the lean is there inside Llama.** The position-A probe, held to the same overall leniency as Llama's
spoken verdict:

| Candidates | Llama's spoken verdict accepts | hidden-state probe accepts |
|---|---|---|
| correct | 64% | **85%** |
| wrong, Llama's own answer matches | 64% | 61% |
| wrong, Llama's own answer differs | 63% | 48% |

- The probe leans toward Llama's own wrong answers by **+13 points**, the same size as the Qwen probes (+10 to +13).
- The probe separates right from wrong far better than Llama's words. Within a question (the fair test): BBEH 0.68 vs
  0.49, RB2 Math 0.79 vs 0.58.
- **Llama's reasoning loses information.** Its own gut verdict at A ranks answers better than its verdict after
  reasoning (BBEH 0.57 vs 0.49; RB2 Math 0.74 vs 0.58). For the Qwens, reasoning helps.

**Finding 4 — the cross-family test: Llama does not buy the Qwens' wrong answers.** When Llama's own answer differs,
it accepts wrong answers that 2–3 Qwens also produced about as often as wrong answers no Qwen produced: +1 point
[−12, +13] at A, −4 [−17, +8] at C. On RB2 Math alone there is a borderline +12 [0, +23] at C. So the wrong answers
that "convince the whole Qwen family" in Experiment 1 mostly do not convince Llama.

**Plain reading.** Both families carry a lean toward their own answer *inside*, at first read, of similar size. Whether
it reaches the verdict depends on whether the verdict actually uses that internal state. Qwen's reasoning connects
the two: it amplifies the lean and also fixes answers it disagrees with. Llama's reasoning disconnects them: it loses the
lean along with most of the useful signal. So **"no anchoring" in Llama is a symptom of a judge that isn't really
judging, not of a good judge.** And the Qwens' "shared belief" is mostly a Qwen-family belief.

Caveats:
- Llama's insensitivity to the Qwens' wrong answers is partly insensitivity to everything (Finding 1).
- The probe's +13 can also mean "Llama's own wrong answer is a common, plausible wrong answer", the same caveat as for
  the Qwen probes.
- Pooling Llama with the Qwens in the same-candidate control gives +8 [+1, +15] at A and +13 [+6, +20] at C. I would
  not read this as a personal own-answer effect: in that pool, "believes this wrong answer" is almost always "is a
  Qwen", and Llama judges everything alike, so the number mixes own belief with family.

**Steering Llama (same setup as Experiment 3)** gives the same picture as the Qwens:
- **Correctness direction (layer 21):** the accept rate goes from 0% at −8 to 96–99% at +8 for right and wrong
  answers alike. It is a leniency dial again.
- **"Matches my answer" direction (layer 15):** at −8 it lowers acceptance of matching wrong answers by 18 points,
  differing wrong answers by 20 and correct answers by 13. That is not specific to own answers; a random direction
  moves things by up to 11.

So in both families the lean shows up in a probe, but no steerable "my answer" direction exists at position A.

---

## Experiment 5 — Thinking-on Qwens (Nov 9, preliminary)

**What ran.** The same three Qwens with thinking switched on, each output allowed to fill the context, on all four
benchmarks (Tinker). Besides A, 25/50/75% and C we read the verdict at **E** (the end of the hidden thinking, before
the written answer starts).

**Result** — main set (RB2 Math + JudgeBench + BFF), wrong answers only, own answer matches minus differs:

| Judge | Gap at A | Gap at E | Gap in spoken verdict | Same wrong candidate, judge + candidate FE, at C |
|---|---|---|---|---|
| Qwen3.5-4B | +19 [+10, +28] | +57 [+48, +65] | +57 | +7 [0, +14] |
| Qwen3.5-9B | +21 [+11, +30] | +59 [+50, +67] | +59 | +9 [+2, +15] |
| Qwen3.6-35B | +27 [+17, +36] | +58 [+48, +66] | +58 | +4 [−3, +10] |

(Thinking off, pooled: +23 at A, +37 at C.)

**Plain reading.**
- Thinking makes the judges better at rejecting wrong answers they *disagree* with: on RB2 Math the 9B accepts only
  2% of those at the end, against 70% of the wrong answers that match its own.
- So thinking **widens** the gap from about +37 to about +58. Long reasoning is not a cure; it makes the judge more
  certain of whatever it already believes.
- The whole gap is in place by E. Nothing changes between the end of thinking and the spoken verdict.
- The personal "it's *my* answer" part on the same candidate stays small (+4 to +9), as with thinking off.

**Not final.** About 630 cut-off outputs (own answers and judgments) were regenerated from scratch afterwards. They are
not merged yet, because their new answers still need GLM matching (Tinker money, so I'll estimate first). Roughly 280
of them still hit the limit.

---

## Experiment 6 — Belief strength: does acceptance follow how often the judge itself reaches the answer?

**Why.** "Match / differ" comes from a single own answer, a noisy yes/no. **Belief** = in how many of **7 fresh own
answers** (same prompt, temperature 0.7) the judge reaches the candidate's final answer: 0/7 = never, 7/7 = always.
These 7 are separate from the answer that defined match/differ, so the two measures are independent. GLM-5.3-Flash
compared answers; the 227 answers that ran out of room were regenerated from scratch. Thinking off, three Qwens, main
set.

**Wrong answers accepted, by belief** (main set):

| | 0/7 | 1–3 of 7 | 4–6 of 7 | 7/7 | 7/7 minus 0/7 (judge FE) |
|---|---|---|---|---|---|
| before reasoning (A) | 25% (n=1,758) | 29% | 41% | 56% | **+28** [+19, +36] |
| at the verdict (C) | 18% | 36% | 54% | 71% (n=211) | **+52** [+44, +59] |

It rises steadily with belief on every benchmark (at C: RB2 Math +52, JudgeBench +44, BFF +56).

**Belief, not the single sample, carries the effect.** With both measures in one regression, at C:

| | effect |
|---|---|
| old match label, belief held fixed | +1 [−7, +10] |
| belief (7/7 vs 0/7), match label held fixed | **+50** [+39, +61] |

**Same wrong candidate, three Qwens** (judge + candidate fixed effects; does *this* judge's belief matter beyond
what every Qwen believes?): +14 [+1, +27] at A, +22 [+6, +38] at C. So with a less noisy measure there **is** a
personal part, about 40% of the full belief effect. The single-sample control in Experiment 1 (+3) understated it.

**It cuts both ways.** Correct answers the judge never reaches itself (0/7) are accepted only 30% of the time at C, against
91% at 7/7 (n=102 vs 1,723). The judge rejects right answers it can't reproduce.

**Plain reading.** Anchoring is graded. The more consistently the judge produces an answer itself, the more likely it
approves that answer, right or wrong. Reasoning nearly doubles that dependence (+28 → +52).

---

## Experiment 7 — Where is belief readable inside the judge? (probes, all positions × all layers)

**What ran.** Qwen3.5-4B and 9B on RB2 Math and BFF (thinking off), on Harvard's Cannon GPUs. For every judgment we saved
the hidden state at every layer at five points: A, 25/50/75% of the written reasoning, and C. A ridge probe
predicts belief from one (position, layer) cell.

- **Score:** AUROC among wrong answers, believed (≥4/7) vs never reached (0/7). 0.5 = chance, 1 = perfect.
- **Choosing the cell:** inside each training fold only (nested cross-validation, whole questions held out), so the
  held-out score is honest.

| Judge, benchmark | Held-out score | Cell usually chosen | Same cell: belief probe / correctness probe / judge's own verdict |
|---|---|---|---|
| Qwen3.5-9B, RB2 Math | **0.86** [0.81, 0.90] | C, layer 21 | 0.87 / 0.79 / 0.82 |
| Qwen3.5-9B, BFF | **0.80** [0.71, 0.87] | C, layer 25 | 0.84 / 0.80 / 0.74 |
| Qwen3.5-4B, RB2 Math | 0.78 [0.72, 0.83] | C, layers 17–29 | 0.78 / 0.73 / 0.76 |
| Qwen3.5-4B, BFF | 0.72 [0.63, 0.80] | mixed (A / 75 / C) | 0.79 / 0.63 / 0.70 |

- **Belief is clearly readable**, and better than a probe trained on "is this answer right?" or the judge's own
  verdict.
- On RB2 Math it **grows as the judge writes**: 9B best layer A 0.77 → 25% 0.79 → 50% 0.81 → 75% 0.87 → C 0.88. On BFF
  it is about as readable at A (0.83) as at C (0.84).
- Middle-to-late layers (17–28) are best. The last layer is not the best.

---

## Experiment 8 — Steering belief *during* reasoning (Nov 9) — moves leniency, not the anchored answers

**What ran.** Qwen3.5-9B, thinking off, greedy decoding, 418 items:
- RB2 Math: 59 wrong & believed (≥4/7), 80 wrong & never reached, 80 correct.
- BFF: 39 / 80 / 80.

While the judge wrote its whole judgment (prompt and every generated token), we added a push at layers 14–26.
- **Direction:** at each layer, the belief direction learned from the reasoning-position hidden states. It was
  fitted on the *other* half of the questions, so these items are held out from it.
- **Same length for every direction:** each push has the size of the belief direction at that layer.
- **Paired:** decoding is greedy, so each condition judges exactly the same items as "no push".

**Controls:**
- **"Is this right?"**: the correctness direction.
- **"Belief without correctness"**: the belief direction with the correctness part removed.
- **A random direction.**
- **A positive push:** "believe more", the opposite sign.

Pushes of ±16 broke every output, and ±8 started to, so the run used 4 and 6.

Change in acceptance vs no push, both benchmarks (95% intervals, questions resampled). **Selectivity** = change on
wrong & believed minus change on correct. Negative would mean the push removes anchored errors more than it hurts
right answers.

| Push | Wrong, believed (68% accepted) | Wrong, never reached (21%) | Correct (85%) | Selectivity | Broke* |
|---|---|---|---|---|---|
| belief −4 | +2 [−5, +9] | +2 | **−7** [−12, −2] | +9 [0, +18] | 1% |
| belief −6 | −5 [−13, +3] | −1 | **−9** [−15, −4] | +4 [−5, +14] | 5% |
| belief without correctness −6 | −7 [−17, +2] | −3 | **−13** [−20, −7] | +6 [−6, +17] | 5% |
| "is this right?" −6 | −4 [−12, +4] | +2 | **−7** [−13, −1] | +3 [−8, +12] | 3% |
| random −6 | +1 [−7, +9] | +1 | −4 [−10, +2] | +5 [−4, +15] | 5% |
| belief **+4** | +5 [−3, +13] | **+8** [+2, +14] | +4 [0, +9] | +1 [−8, +9] | 3% |

\*Broke = looped until the 8,192-token cap (about 4× the longest normal judgment) or gave no verdict. It counts as not
accepting.

**Plain reading.**
- **The direction has a sign.** Belief +4 flipped 40 verdicts toward "accept" and 14 toward "reject". The −4/−6 pushes
  lean the other way. The random push flips as many verdicts (84 of 418), but evenly both ways (33 / 31).
- **It is not selective.** Pushing belief down lowers acceptance of *correct* answers (−7 to −13) at least as much as
  of the wrong answers the judge believes (+2 to −7, all within noise). Selectivity is never reliably negative.
  Removing the correctness part does not help.
- RB2 Math was clean (≤1% broke). BFF was noisier (6–11% broke at size 6), and no BFF condition was selective.
- **Interpretation:** belief can be read out well (Experiment 7), but nudging it does not undo anchoring on specific
  answers. Our best guess is that the judge approves a believed wrong answer because it **re-derives that same wrong
  answer in its written reasoning**. A nudge along "belief" doesn't change that computation; it only shifts how
  willing the judge is to say CORRECT overall. This matches Experiment 3 (correctness = leniency dial) and the missing
  "my answer" direction at A, now tested during reasoning too.

---

## Feasibility verdict on the two papers' ideas

| Idea | Works here? | What we learned |
|---|---|---|
| Hidden "is this right?" signal (INSPECTOR) | Yes, but mostly as "is this question hard?" | Item-level gain over the verdict is small for Qwen, moderate for Llama |
| Bias as a direction you can steer (Unfair Judge) | Yes for correctness, no for own-answer agreement | Steering correctness = leniency dial; no own-answer direction |
| Predicting failures from activations | Not tried yet | Natural next step: does the difficulty signal predict anchoring errors? |
| Same tools on a second family (Llama) | Yes | Hidden signal is strongest relative to the verdict in the weakest judge |
| Probing belief (how often the judge reaches this answer) | Yes | Held-out AUROC 0.72–0.86; beats the correctness probe and the verdict |
| Steering belief during reasoning | Causal for leniency only | Moves verdicts in the expected direction, but hurts correct answers as much as anchored wrong ones |

## What looks genuinely new (neither paper does this)

1. **Anchoring is set at first read and amplified by reasoning, not created by it** — checkpoint readouts (A,
   50%, C) on three benchmarks × three Qwens, with the cut-off outputs fixed.
2. **It is mostly a family-shared belief, not "my answer"** — the same-candidate control across judges, backed
   inside the model by the absence of a causal own-answer direction.
3. **The verdict ignores what the model knows about difficulty** — the hidden state ranks hard vs easy questions
   well; the verdict does not use it. That points to a cheap fix: let a probe-based difficulty score make the
   judge stricter on hard questions (a *selective* leniency dial, which steering alone was not).
4. **The own-answer lean lives in the representation in both families; it reaches the verdict only if the judge's
   reasoning uses that representation** — Qwen (reasoning amplifies it) vs Llama (reasoning discards it, along with
   most of what the hidden state knows). A judge can look "unbiased" simply because its verdict is disconnected from
   what it knows.
5. **Anchoring is graded by belief strength, and belief, not one sampled answer, is what matters.** Acceptance of
   wrong answers rises from 18% to 71% across belief 0/7 → 7/7. Holding belief fixed, the usual match label adds
   nothing. Correct answers the judge can't reproduce are rejected (30% accepted at 0/7).
6. **A readable signal is not a steerable fix.** Belief is linearly readable mid-network during reasoning, but pushing
   it during reasoning is a leniency dial, not a targeted correction.

## What is not new / weak spots

- The probes reproduce INSPECTOR's general claim; our addition is the within-question control showing much of it is difficulty.
- The personal own-answer effect is small with the one-sample label (+3), larger with belief strength (+22 at C,
  interval +6 to +38). Both rest on the few candidates the three Qwens believe to different degrees.
- Belief probes and steering were run on Qwen3.5-4B/9B with thinking off, on RB2 Math and BFF only. Their item groups
  were built before the 227 regenerated belief answers were merged; that moved only a handful of candidates between
  bins, and the belief tables above include them.
- Steering during reasoning used one way of pushing (the same push at every token, layers 14–26). A push only at
  the moment the judge checks the candidate's answer, or a fix to the re-derivation itself, is untested.
- Thinking-on results (Experiment 5) do not yet include the ~630 regenerated cut-off outputs.
- Tinker judges are one family (Qwen). Llama is the only other family, and it is a weak judge, so the cross-family
  test can't fully separate "family-specific belief" from "Llama ignores everything". A stronger non-Qwen judge
  (e.g. Llama-3.3-70B or Gemma) would settle it.
- Llama's verdicts and some of its BBEH answers were read by GLM because Llama ignored the format; the Qwens' were
  parsed exactly.

## Next steps (my priority order)

1. **A stronger second family** (Llama-3.3-70B, Gemma-3-27B or Mistral) for the cross-family test, since
   Llama-3.1-8B barely judges.
2. **Difficulty-gated strictness**: use the probe's difficulty signal to scale the correctness direction (or the
   threshold) per item; check if it removes anchoring errors without hurting correct answers.
3. ~~Steer during reasoning~~ (done, Experiment 8: leniency only).
4. ~~Thinking-on Qwen run~~ (done, Experiment 5). Left: GLM-match the ~630 regenerated cut-off outputs and redo the
   tables (Tinker cost to estimate first).
5. ~~Belief strength~~ (done, Experiment 6).
6. **Why the anchored answers survive:** check in the transcripts whether the judge re-derives the candidate's wrong
   answer before approving it. If so, the fix is in the reasoning (e.g. make it check the candidate's steps instead of
   re-solving), not in a single direction.
7. **OLMo-3 training stages** (paused Nov 9 to free GPUs; restart steps in `cannon_olmo/PAUSED.md`).

## Files and cost
- Code: `build_jobs.py`, `build_extend.py`, `tinker_jobs.py`, `modal_app.py` (Tinker), `analyze.py`;
  `probe_steer.py`, `probe_modal.py`, `probes.py`, `steer_analysis.py` (GPU probes/steering);
  `llama_gen_modal.py` (Llama generation), `llama_ingest.py`, `llama_analysis.py` (Llama anchoring + cross-family).
- Results: `out/results.md` (anchoring tables), `out_llama/results.md` (Llama + cross-family),
  `out_probe/<model>/probes.md`, `out_probe/<model>/steering.md`.
- Llama this morning: one H100 run for generation (~4 h), one for steering (~15 min); GLM fill/matching ≈ $5.
- Tinker cost tonight ≈ $110 readouts + ~$60 reruns + ~$10 matching (estimates from token counts). Modal GPU:
  H100 for ~2 hours total.
- Nov 9 code:
  - `think_split.py` (thinking-on run → `out_open/<qwen>-think/results.md`)
  - `belief.py` → `out/belief.md`
  - `belief_ckpt_jobs.py` + `cannon_belief/capture.py` (hidden states, Cannon)
  - `belief_probe_grid.py` → `out/belief_probe_grid.md`
  - `belief_steer_prep.py` + `cannon_belief/steer.py` → `belief_steer_analysis.py` → `out/belief_steering.md`
- Nov 9 cost:
  - Tinker for this work: ≈ $770 at list prices. Thinking-on generation ~$280, its readouts ~$240, reruns ~$100,
    belief solves ~$80, GLM matching ~$70.
  - Probes and steering ran on Harvard Cannon GPUs (free).
- Nothing is committed.
