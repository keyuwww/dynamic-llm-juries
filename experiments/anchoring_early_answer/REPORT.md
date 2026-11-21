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
  judge reaches 7/7 times are accepted 74% of the time at the verdict; those it never reaches, 18%. The old one-sample
  match label adds nothing once belief is known. With this better measure there is a real **personal** part (+23
  points on the same wrong answer), not only a family belief. **Nov 15:** Nemotron-3-Super (NVIDIA) shows the same
  graded effect (26% → 85%, +51 points); Llama-3.1-8B has too few answers at 7/7 (5) to test.
- **How judges approve (Nov 16, Experiment 9).** With thinking on, 86–96% of approved wrong answers come with a re-solve
  that lands on the same wrong answer; thinking-off transcripts hide this. A "don't re-solve" prompt leaves believed
  answers nearly untouched.
- **Label correction (Nov 13).** 61 of 549 RB2 Math answers labelled wrong reach the same value as the right answer,
  written differently (476,000,000 vs 476,252,000 eV; 9 vs 9.02 L; 4.20 × 10¹¹ vs "420" in units of 10⁹). GLM-5.3-Flash
  checked every wrong answer against the right one (`clean_labels.py`, $0.52). They were concentrated among the answers
  the judges believe: 180 judge × answer rows dropped, more than half of the 7/7 bin. Every conclusion holds and the
  belief effect gets slightly larger; the tables in Experiments 1 (main set) and 6 now use the clean labels.
  RB2 Math now has only 10 wrong answers at 7/7, so the 7/7 bin rests mostly on BFF and JudgeBench. Those two were
  not audited this way (no right candidate to compare with on most questions). Experiments 2, 3, 7 and 8 (probes and
  steering) were run with the old labels and not redone.
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
Wrong answers only, pooled over the three Qwens, with 95% intervals (questions resampled). *Original set (BBEH, RB2
Math, JudgeBench) with the old RB2 Math labels; superseded by the main-set tables below, which use clean labels.*

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

Wrong answers only, pooled over the three Qwens (95% intervals, questions resampled). Clean labels (Nov 13): the
RB2 Math wrong answers that reach the right value are left out (`analyze.py --clean`, `out/results_clean.md`). That
leaves 12–17 matching wrong answers per judge on RB2 Math instead of 60–67.

| Benchmark | Gap at A | Gap at C | Rescue gap |
|---|---|---|---|
| **Main set** | **+26** [+18, +33] | **+35** [+28, +41] | **+26** [+16, +35] |
| RB2 Math | +20 [−2, +40] | +43 [+24, +61] | +41 [+21, +54] |
| JudgeBench | +23 [+12, +34] | +21 [+10, +32] | +15 [−2, +32] |
| BFF-Bench | +27 [+12, +38] | +41 [+27, +52] | +44 [+26, +62] |
| BBEH (contrast) | +28 [+18, +39] | +29 [+21, +38] | +7 [−6, +18] |

Same wrong candidate, three Qwens, judge + candidate fixed effects (the "is it *my* answer?" control):

| | at A | at 50% | at C |
|---|---|---|---|
| Main single-answer set (RB2 Math + BFF) | **+16** [+5, +27] | +9 [−3, +20] | +9 [−1, +18] |
| RB2 Math | +11 [−1, +31] | −2 [−33, +22] | +2 [−27, +28] |
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
the Qwens judge well, reasoning still rescues far fewer matching wrong answers (0–29%, only 5–8 per judge with clean
labels) than differing ones (29–79%).

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

**Wrong answers accepted, by belief** (main set, clean labels: 180 rows whose RB2 Math "wrong" answer reaches the
right value are left out; `belief.py --clean`, `out/belief_clean.md`):

| | 0/7 | 1–3 of 7 | 4–6 of 7 | 7/7 | 7/7 minus 0/7 (judge FE) |
|---|---|---|---|---|---|
| before reasoning (A) | 25% (n=1,741) | 28% | 42% | 65% | **+35** [+25, +43] |
| at the verdict (C) | 18% | 35% | 54% | 74% (n=101) | **+54** [+45, +63] |

It rises steadily with belief on every benchmark (at C: RB2 Math +71 but only 10 answers at 7/7, JudgeBench +44,
BFF +56). With the old labels the 7/7 row was 56% / 71% (n=211) and the slopes +28 / +52: the dropped answers were
accepted less often than really wrong ones.

**Belief, not the single sample, carries the effect.** With both measures in one regression, at C:

| | effect |
|---|---|
| old match label, belief held fixed | +3 [−6, +12] |
| belief (7/7 vs 0/7), match label held fixed | **+52** [+39, +63] |

**Same wrong candidate, three Qwens** (judge + candidate fixed effects; does *this* judge's belief matter beyond
what every Qwen believes?): +17 [+3, +31] at A, +23 [+6, +38] at C. So with a less noisy measure there **is** a
personal part, about 40% of the full belief effect. The single-sample control in Experiment 1 (+3) understated it.

**It cuts both ways.** Correct answers the judge never reaches itself (0/7) are accepted only 30% of the time at C, against
91% at 7/7 (n=102 vs 1,723). The judge rejects right answers it can't reproduce.

**Plain reading.** Anchoring is graded. The more consistently the judge produces an answer itself, the more likely it
approves that answer, right or wrong. Reasoning makes that dependence about half again as strong (+35 → +54).

### Update (Nov 15): another family — Nemotron-3-Super-120B

**What ran (Tinker, `--set nemotron`).** Nemotron-3-Super-120B (NVIDIA, 12B active, thinking off) judged every main-set
candidate in the original pool run, with the Qwens' exact prompts (0 mismatches over 2,658 items). New: its own answer
per question, 7 more own answers (6,573 of 6,580 finished), GLM matching, the A/25/50/75/C readouts, and its 57
cut-off judging transcripts regenerated from scratch (as for the Qwens). C readout = spoken verdict in 97% of
judgments. Files: `inputs/*_nemotron*`, `out_nemotron/` (`results_clean.md`, `belief_clean.md`).

**Wrong answers accepted at C, by belief** (clean labels; `make_judge_lines.py` → `out/figs_belief/fig6_belief_by_judge.png`):

| Judge | 0/7 | 1–3 of 7 | 4–6 of 7 | 7/7 |
|---|---|---|---|---|
| Qwen3.5-4B | 27% (n=567) | 39% | 57% | 64% (n=28) |
| Qwen3.5-9B | 20% (n=565) | 35% | 48% | 83% (n=36) |
| Qwen3.6-35B | 8% (n=580) | 27% | 62% | 75% (n=36) |
| Nemotron-3-Super | 26% (n=587) | 50% | 57% | 85% (n=41) |

- **Same graded effect:** 7/7 vs 0/7 = +42 [+30, +53] at A, **+51 [+39, +61]** at C. Per benchmark at C: RB2 Math +77
  (n=5 at 7/7), BFF +55, JudgeBench +27.
- **Belief explains away the one-sample label again:** old label with belief held fixed +2 [−14, +18]; belief with the
  label held fixed +48 [+30, +67].
- **Match / differ (one sample) also leans hard:** accepted at C, match vs differ: BFF 82% vs 38%, RB2 Math 88% vs 25%,
  JudgeBench 43% vs 34%.
- **Cuts both ways:** correct answers at 0/7 accepted 53%, at 7/7 87%.
- **Llama-3.1-8B is left out of the figure and the table:** only 5 of its wrong answers (of about 820 with a belief
  score) reach 7/7, too few to place the top of its curve. Below that it is flat: 54% / 54% / 57% at 0/7, 1–3 and 4–6
  (all three benchmarks; `out/belief_llama3.1-8b_clean.md`, now including BFF, spoken verdict only there). Its 7 own
  answers rarely agree, and it accepts most answers whatever it believes (Experiment 4, Finding 1).

**Plain reading.** The belief effect is not a Qwen quirk: a strong judge from another family shows it at the same size.

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

## Experiment 9 — How do judges approve the wrong answers they believe? (Nov 16)

**Transcript check (`transcript_check.py`).** GLM-5.3-Flash read each judging transcript with the question and the
graded answer and labelled: did the grader work out its own result (re-solve)? Did that result equal the graded answer?
Or did it only walk through the given steps? RB2 Math + BFF, clean labels; 4,254 thinking-off transcripts (three Qwens +
Nemotron) and 3,189 thinking-on transcripts (three Qwens, Experiment 5's generations). 8 labels checked by hand: all agree.

| Wrong answers the judge approved (Qwens) | Thinking off | Thinking on |
|---|---|---|
| Re-solves the problem itself | 26–44% | **92–100%** |
| ...and lands on the same wrong answer | 23–43% | **86–96%** |
| Only walks through the given steps | 67–86% | 18–22% |

Ranges are over the four belief levels (Qwens pooled). The rows are separate labels and can overlap ("only walks through
the steps" is the main style). Nemotron, thinking off: 15% re-solve, 81% step check.

- **With the reasoning written out, approvals of wrong answers are re-solves that land on the same wrong answer**, at
  every belief level. Rejections come with a re-solve that reaches a different answer, in both modes.
- **Thinking-off approvals only look like rubber stamps** ("the arithmetic is sound"): the short transcripts hide the
  work. An earlier reading tonight ("belief decides whether the judge bothers to check") was this artefact; withdrawn.
- **Thinking-on staircase is steeper:** wrong answers approved 3% / 24% / 50% / 79% at belief 0/7, 1–3, 4–6, 7/7
  (from the labelled set, spoken verdict after `</think>`).
- **Open:** at belief 0/7, the 44 approved wrong answers still come with a re-solve that lands on the candidate (89%),
  though the model never reaches that answer in 7 solo tries. Seeing the candidate may pull the re-solve.

**"Don't re-solve" prompt (free; beyond_capability's verify condition on the same 459 BFF items, 3 samples each).**

| Wrong BFF answers approved | 0/7 | 1–3 | 4–6 | 7/7 |
|---|---|---|---|---|
| Qwens, normal prompt | 15% | 43% | 55% | 74% |
| Qwens, "Do NOT solve the question yourself; verify the work" | 3% | 28% | 45% | 69% |
| Nemotron, normal | 35% | 62% | 83% | 85% |
| Nemotron, verify | 15% | 50% | 56% | 83% |

The prompt makes judges stricter on answers they don't believe but leaves believed ones nearly untouched: a prompt
cannot stop the model computing its own answer.

**Inside the model** (beyond_capability report, section 10): solving and judging encode correctness differently even
at a matched read position (Qwen-9B and Qwen-35B), and at the verdict the belief direction lines up with the
correctness direction (0.72–0.93 on BFF).

**Two causal tests (`causal_prep.py` → `out/causal.md`; three Qwens, thinking off, RB2 Math + BFF, every candidate,
on Tinker via the new `gen` phase of `tinker_jobs.py`).**

*Commit first:* the model's own first answer (generated earlier without any candidate, not one of the 7 belief tries)
is placed in the chat before the usual judge prompt ("Now grade another AI assistant's answer to the same question.").

| Wrong answers approved | 0/7 | 1–3 | 4–6 | 7/7 |
|---|---|---|---|---|
| Usual judge prompt | 17% (n=1,588) | 36% | 58% | 74% (n=62) |
| Own answer first | **1%** (n=1,528) | 22% | 51% | **69%** (n=61) |
| ...own answer differed from the candidate | 1% | 10% | 19% | (3) |
| ...own answer matched the candidate | (5) | 70% | 65% | 71% |

Correct answers it never reaches: 31% → 14% approved. Committing first turns the judge into an agreement checker: the
low-belief floor disappears, believed wrong answers still pass, and more unreached right answers are rejected (Lin et
al.'s self-reference trade-off, measured by belief).

*Shown the candidate, asked to solve:* the solve prompt plus "For reference, here is another AI assistant's answer …
That answer may be right or wrong. Work out the answer yourself." Share of solves whose final answer equals the
candidate's (GLM-5.3-Flash, 3,169 solves):

| Candidate | 0/7 | 1–3 | 4–6 | 7/7 |
|---|---|---|---|---|
| Wrong | **2%** | 35% | 63% | 89% |
| Right | 18% | 62% | 83% | 97% |
| Expected from belief alone | 0% | ≈ 29% | ≈ 71% | 100% |

Seeing a wrong answer barely moves what the model solves (2% at 0/7); seeing a right one helps (18%). So the 17%
approval of never-reached wrong answers comes from the grading frame (it checks along the candidate's own path), not
from a general pull on its solving.

**Plain reading.** A judge mostly asks "does this match what I get?": it re-derives the answer (visibly with thinking,
silently without) and approves when its result agrees. Belief predicts where that re-derivation lands. At low belief,
the grading frame adds approvals that committing its own answer first removes.

**Rigor checks (`rigor_checks.py` → `out/rigor_checks.md`; 95% intervals resample questions).**
- *Commit first, paired on the same 3,087 items:* wrong answers at 0/7 approved 18% → 1% (−17 [−20, −14]); at 7/7
  74% → 69% (−5 [−19, +13], not clearly changed). Right answers at 1–3 of 7: 73% → 36%. Overall balanced accuracy
  80% → **85% (+5 [+3, +6])**: a net gain on this data. (The table above uses all items; paired numbers differ by ≤1.)
- *Shown the answer, asked to solve:* landing on a wrong candidate minus the rate expected from belief: +2 [+2, +3] at
  0/7, +12 [+4, +19] at 1–3, −11 [−24, −4] at 7/7 (the "may be right or wrong" warning pushes away from the answer).
- *Different-belief juror (existing data):* when a Qwen believes a wrong answer (≥ 4/7), Nemotron-3-Super also
  believes it 77–81% of the time. Handing those verdicts to Nemotron lowers balanced accuracy (Qwen3.5-4B 76 → 74%,
  9B 80 → 77%, 35B 86 → 82%) and rejects fewer of the believed wrong answers (e.g. 9B 32% → 22%). Routing only when
  Nemotron's own belief is ≤ 3/7 is still worse (35B 86 → 84%); there Nemotron rejects 46–52%, no better than the
  Qwen. **Confident wrong beliefs are shared across these families; a peer juror does not fix them.** A much stronger
  reference (expert answer, frontier model) is the untested alternative.

---

## Experiment 10 — Does an expert reference answer remove the strong-belief errors? (Nov 16)

**Setup (`reference_test.py`).** Three Qwens, thinking off, BFF-Bench. The usual judge prompt plus BFF-Bench's own
expert-written reference answer for that question, with "use it as the ground truth" (the No Free Labels setting).
1,295 judgments (3 BFF items have no reference in the release), each paired with the same item's usual verdict from
the main runs. 95% intervals resample questions. Output: `out/reference_test.md`.

| Wrong answers approved | 0/7 | 1–3 | 4–6 | 7/7 |
|---|---|---|---|---|
| Usual judge prompt | 15% (n=337) | 36% (n=89) | 54% (n=56) | 71% (n=52) |
| **+ expert reference** | **1%** | **1%** | **5%** | **19%** |
| Change (points) | −14 [−19, −9] | −35 [−45, −24] | −48 [−62, −34] | −52 [−67, −32] |

- **The strong-belief errors mostly go away.** Wrong answers the judge believes (≥ 4/7, n=108): 62% approved
  normally, 12% with the reference (−50 [−61, −37]). This is what neither "don't re-solve", committing first, nor a
  second family (Nemotron) could do.
- **No cost on right answers; they gain.** Right answers approved rise at every belief level (e.g. 0/7: 20% → 41%).
- **Balanced accuracy 74.6% → 89.6% (+15.0 [+11.8, +18.2])**: 4B +18, 9B +14, 35B +12.
- **Not eliminated:** 7/7 still 19% (10 of 52 judgments).
- **Caveats.** One benchmark (finance), Qwens only, thinking off. The BFF labels were made by experts who also wrote
  these references, so a judge that follows the reference will agree with the labels more by construction; the
  reference is the realistic "human grounding" fix, not a free one (someone has to write it). Whether a much stronger
  model's answer works as well (no human cost) is the next test (Kimi answers exist for BFF).

**Commit first + reference (`reference_test.py --four`, `out/reference_four.md`).** Same 1,294 BFF items under four
prompts:

| Prompt | Strong-belief wrong approved (≥ 4/7, n=108) | 7/7 wrong approved | Balanced accuracy (vs usual) |
|---|---|---|---|
| Usual | 62% | 71% | 74.6% |
| Commit first | 56% | 63% | 77.8% (+3.2 [+0.5, +6.0]) |
| **+ Expert reference** | **12%** | **19%** | **89.6% (+15.0 [+11.9, +18.2])** |
| Commit first + reference | 18% | 31% | 87.0% (+12.4 [+9.2, +15.7]) |

Stacking does not help: commit first + reference is 2.6 points [−4.6, −0.7] below the reference alone. Its own (often
wrong) committed answer competes with the reference at 7/7 (19% → 31%) and costs right answers it can't reach
(0/7: 41% → 30%). The best single fix is the reference.

**A strong model's answer as the reference (`reference_test.py --kimi`, `out/reference_kimi.md`).** Kimi-K3.1-Pro's own
answer (one sample, no expert) in place of the expert reference, same 1,295 judgments. Strong-belief wrong answers
approved 62% → 34%; balanced accuracy 74.6 → 82.8% (+8.2 [+5.0, +11.4]), about half the expert's gain. Where Kimi is
right (85% of judgments) it is nearly as good as the expert (14% vs 12%); where Kimi is wrong the judge follows it
(right answers approved 19%, balanced accuracy 49.8%). About half of the strong-belief wrong answers (51 of 108) are on
questions Kimi also gets wrong.

**Rechecked on audited labels (Experiment 11).** Some BFF expert references are themselves wrong, so part of the
"fix" above was the judge rejecting answers that are actually right. Keeping only wrong answers that GLM-5.3 audits as
clearly wrong: strong-belief approvals (n=52) usual 44%, commit first 44%, **expert reference 0%**, Kimi reference 13%;
balanced accuracy 78.7 / 81.6 / 90.9 / 86.1%. On the 68 "wrong" answers GLM-5.3 audits as actually correct, approval
falls from 74% to 22% with the expert reference: the judge follows the reference, right or wrong.

---

## Experiment 11 — Are the measurements sound? Matcher check and label audit (Nov 16)

Two checks a reviewer will ask for first. Files in `validation/`. Both second readers are AI models (Claude, GLM-5.3),
not human experts.

**1. The answer matcher (GLM-5.3-Flash).** Claude re-read 50 SAME/DIFFERENT decisions (RB2 Math 20, BFF 30,
oversampling wrong answers the judge believes), deciding before looking at GLM's call (`matcher_check.md`).
- Agreement 42/47 (89%) leaving out 3 ambiguous cases; 42/50 (84%) counting them as disagreements.
- RB2 Math 19/20; BFF 23/27.
- **GLM never said SAME wrongly (24/24).** All 5 disagreements are GLM saying DIFFERENT on near-matches (4 BFF, e.g.
  WACC 5.95% vs 5.93%, or the same recommendation with one figure missing; 1 math rounding case).
- So belief is, if anything, **understated** on BFF, and the staircase is not produced by loose matching.

**2. The labels.** Claude audited all 55 wrong-labelled answers some Qwen believes 7/7 (BFF 29, JudgeBench 26;
`label_audit_7of7.md`); GLM-5.3 then audited every wrong-labelled BFF and JudgeBench answer at every belief level
(397 answers; `build_glm_audit.py`). They agree on 89% of the 7/7 "clearly wrong or not" calls.
- **Label errors pile up where judges believe the answer.** Unique wrong-labelled answers, GLM-5.3:

| Belief | Clearly wrong | Actually correct | Contested |
|---|---|---|---|
| 0/7 | 231 | 2 | 9 |
| 1–3 | 120 | 15 | 18 |
| 4–6 | 56 | 22 | 21 |
| 7/7 | 23 | 22 | 9 |

- Examples: four BFF impairment items whose expert reference copies the question's $386,000 fair value as $368,000
  (checked by hand); a portfolio return the reference weights equally when the holdings are one share each; a
  JudgeBench answer that is right but typed the letter 7 times instead of 5. Many contested JudgeBench items have a
  second defensible option among MMLU-Pro's added choices.
- Judges approve the "actually correct" ones 59–82% of the time, so the released labels inflate the top of the
  staircase.

**The staircase survives cleaning** (`clean_staircase.py`, `validation/clean_staircase.md`). Wrong answers approved,
three Qwens, thinking off; RB2 Math keeps its earlier value-match cleaning in every row:

| Labels | 0/7 | 1–3 | 4–6 | 7/7 | Gap 7/7 − 0/7 |
|---|---|---|---|---|---|
| As released | 18% (n=1,741) | 35% | 54% | 74% (n=101) | +56 [+45, +66] |
| Drop GLM-5.3 "actually correct" | 18% | 33% | 53% | 68% (n=56) | +50 [+36, +62] |
| Only GLM-5.3 "clearly wrong" | 17% | 30% | 48% | 65% (n=40) | +48 [+29, +63] |
| GLM-5.3 and Claude both "clearly wrong" | 17% | 30% | 48% | 63% (n=35) | +46 [+28, +63] |

- The rise is a little smaller and the 7/7 group is smaller, but the effect holds in every version, for every Qwen,
  and on every benchmark (cleaned 7/7: RB2 Math 90%, JudgeBench 69%, BFF 43% with n=14).
- **For the paper:** report the cleaned staircase as the main number, and the label-error pattern as a finding of
  its own: on these benchmarks, a "wrong" answer that judges strongly believe is often a label error.
- **Nemotron-3-Super survives too, and is steeper:** 25% → 51% → 61% → 88% (n=17 at 7/7) keeping only GLM-5.3
  "clearly wrong" answers (45 of its 320 BFF/JudgeBench wrong answers were not in the Qwen audit set; kept as
  released here).

**3. Inside the model, on clean labels** (`beyond_capability/dir_belief.py --audited`,
`out_dirs/belief_dirs_<key>_audited.md`). The belief arrow is built from "believed wrong minus never-reached wrong"
answers, so believed answers that are actually right would pull it toward the correctness arrow by construction.
GLM-5.3 also audited the believed wrong BBEH answers (auto-grader labels; 365 answers): 191 clearly wrong, 84 actually
correct (mostly grader misses on equivalent answers), 83 contested. Cosine of the belief and correctness arrows,
disjoint halves of the questions, best layer per role:

| Case | Believed n (released → clean) | Judging, released | **Judging, clean** | Solving after "FINAL:", clean | Solving, end of answer, clean |
|---|---|---|---|---|---|
| Qwen-9B · BBEH | 255 → 122 | 0.63 | **0.70** | 0.36 | 0.52 |
| Qwen-35B · BBEH | 250 → 122 | 0.62 | **0.80** | 0.25 | 0.31 |
| Qwen-9B · BFF | 39 → 20 | 0.80 | 0.43 | 0.10 | 0.07 |
| Qwen-35B · BFF | 32 → 12 | 0.49 | 0.11 | −0.15 | −0.03 |

- **BBEH, the biggest case, holds and gets stronger:** while judging, a believed wrong answer looks like a right one
  (0.70, 0.80), more than while solving (0.36, 0.25 after "FINAL:"; 0.52, 0.31 at the end of the answer). Removing the verdict-lean direction leaves it (0.84, 0.93).
- **The BFF numbers were mostly label errors** and now rest on 12–20 believed answers; drop them from the headline.
  RB2 Math has only 9 believed wrong answers per judge (unchanged).
- New headline for the inside-the-model slide: BBEH only, clean labels, 0.70–0.80 judging vs 0.25–0.36 solving (after "FINAL:", as in appendix A.5).

---

## Experiment 12 — More judge families: DeepSeek-V4.1-Flash and Kimi-K2.6 (Nov 16–17)

**Setup.** Same pipeline as the Nemotron replication, as its own job set (`--set deepseek`, `out_deepseek/`):
- pool verdicts on the main set (RB2 Math 732, JudgeBench 620, BFF 459; `modal_app.py --phase pooljudge`, thinking
  off, 8,192-token cap, 1 of 1,811 hit it);
- one own answer per question plus 7 more (T=0.7), GLM-5.3-Flash matching, verdict readouts at A and C;
- 14 of 6,580 extra own answers ran to the context limit (kept as is).
- Cost ≈ $28 at list prices (own answers $23, verdicts $3, readouts $2).

**Result: the staircase holds in a third and a fourth family** (`out_deepseek/belief_clean.md`, `validation/clean_staircase.md`).
Wrong answers approved, by belief:

| Judge | Labels | 0/7 | 1–3 | 4–6 | 7/7 | Gap 7/7 − 0/7 |
|---|---|---|---|---|---|---|
| 3 Qwens (Alibaba) | as released | 18% | 35% | 54% | 74% (n=101) | +56 [+46, +66] |
| 3 Qwens | clean | 17% | 30% | 49% | 65% (n=40) | +48 [+30, +63] |
| Nemotron-3-Super (NVIDIA) | as released | 26% | 50% | 58% | 83% (n=42) | +57 [+45, +68] |
| Nemotron-3-Super | clean | 26% | 55% | 62% | 88% (n=17) | +62 [+45, +76] |
| **DeepSeek-V4.1-Flash** | as released | 13% | 45% | 55% | 68% (n=50) | +55 [+41, +67] |
| **DeepSeek-V4.1-Flash** | clean | 13% | 42% | 43% | 55% (n=20) | +42 [+20, +65] |
| **Kimi-K2.6** (Moonshot) | as released | 2% | 31% | 48% | 67% (n=43) | +66 [+52, +80] |
| **Kimi-K2.6** | clean | 2% | 21% | 34% | 65% (n=17) | +63 [+40, +85] |

"Clean" = only wrong answers GLM-5.3 audits as clearly wrong (Experiment 11). Nemotron and DeepSeek rows use the C
readout, which equals the spoken verdict in every judgment checked.
- Belief again beats the one-sample "matches my answer" label: holding belief fixed, the old label adds −14
  [−33, +5]; holding the label fixed, belief adds +69 [+46, +90] (at C).
- **Kimi-K2.6 (Moonshot), a fourth family (Nov 17, `out_kimi/`):** same pipeline (`--set kimi`, model
  `moonshotai/Kimi-K2.6:peft:131072`, thinking off). Strictest at 0/7 (2%) and the steepest rise. Belief again
  beats the one-sample label (label adds −0 [−21, +21] with belief held fixed; belief adds +57 [+32, +81]).
  18 of 1,811 verdicts hit the 8,192-token cap (17 unparsed, dropped); 4 of 6,580 extra own answers ran to the
  context limit. Cost ≈ $80 at list prices (own answers ≈ $52 + their prompts, verdicts $13, readouts $7).
- Four families, four different makers, same pattern.

## Experiment 13 — Closing the review gaps (Nov 17)

### 13a. Thinking-on staircase on audited labels (`validation/think_staircase.py` → `validation/think_staircase.md`)

**What ran.** No new generation: Experiment 5's thinking-on judgments of the three Qwens (main set, every output
allowed to fill the context; the ~630 cut-off outputs replaced by their from-scratch reruns). Verdict = the spoken
verdict after `</think>` (JudgeBench: the A/B pick, mapped to "approves the target"). Belief = the usual thinking-off
belief (7 own answers). Audited labels as in Experiment 11. All 2,065 audited wrong answers × judges have a parseable
thinking-on verdict.

| Wrong answers approved (3 Qwens pooled, audited) | 0/7 | 1–3 | 4–6 | 7/7 | gap |
|---|---|---|---|---|---|
| thinking off | 17% | 30% | 49% | 65% | +48 [+30, +63] |
| thinking on | **3%** | 22% | 41% | 60% | **+57 [+38, +73]** |

- **The staircase holds with thinking on**, in every Qwen (+48, +57, +65 per judge).
- Thinking mostly makes judges stricter on answers they do *not* believe (17% → 3% at 0/7); at 7/7 it changes little.
- The difference in gaps, +9 [−6, +24], is **not significant**. The Nov 9 reading "thinking widens the gap from +37
  to +58" (Experiment 5, one-sample label, released labels) does not survive the audit; "thinking does not remove
  it" does.
- Right answers: thinking-on approves 22% / 76% / 90% / 96% by belief (thinking off 30 / 71 / 85 / 91).
- **Superseded numbers (Nov 18):** with the full audit rule below (13c), thinking off 17 / 30 / 45 / 59%
  (+43 [+20, +62]), thinking on 3 / 21 / 35 / 53% (+50 [+28, +71]); difference +8 [−9, +26].

### 13b. Is belief just difficulty? (`validation/difficulty_check.py` → `validation/difficulty_check.md`)

Belief belongs to a (judge, answer) pair; difficulty to a question. All four families pooled, full audit:
- **Same judge, same question** (judge × question fixed effects; 100 groups with wrong answers at different belief):
  the believed answer is approved more, **+47 [+26, +76]** points (0/7 → 7/7).
- **Holding the judge's own accuracy on the question fixed:** belief +57 [+8, +81]; accuracy itself −2 [−10, +5].
- Hardest questions only (judge never reaches the right answer): 15% (n=181) at 0/7 vs 100% (n=9) at 7/7.

### 13c. Label audit, complete and with a second auditor (`validation/second_auditor.py` → `validation/second_auditor.md`)

- **RB2 Math was never fully audited before** (only the value-match cleaning). GLM-5.3 and Kimi-K3.1-Pro now audited
  all 453 RB2 Math wrong answers too (`inputs/ask_labelauditrb2.jsonl.gz`, a benchmark-correct response as the
  reference): 435 / 440 clearly wrong.
- **Kimi-K3.1-Pro re-audited all 913 wrong answers** (same prompts as GLM-5.3; Moonshot, not one of the judges).
  Same clearly-wrong-or-not call as GLM-5.3 on 95% (κ = 0.75): RB2 Math 98%, BFF 96%, JudgeBench 91%.
- **One rule everywhere from now on:** keep a wrong answer only if GLM-5.3 calls it clearly wrong, on all three
  benchmarks. Main staircase (stated verdict, `validation/paper_numbers.md`): Qwens 17 / 30 / 45 / 59% (+43 [+20, +62]),
  Nemotron 25 / 49 / 59 / 86% (+61), DeepSeek 13 / 37 / 38 / 47% (+34 [+9, +58]), Kimi-K2.6 1 / 14 / 33 / 58% (+57).
  Under Kimi-K3.1-Pro's labels and under both, every family keeps a positive gap (Kimi-K2.6 under both: only 5 answers
  at 7/7, interval includes 0).
- **Human check: dropped (Nov 18).** The items were too hard to judge without domain background, so a third model
  auditor replaced it (13g). No human has checked the labels; the paper says so.

### 13g. Third auditor: Claude Opus 5.5 (`validation/build_claude_audit.py`, `validation/claude_audit.py` → `validation/claude_audit.md`)

Seven Claude Opus subagents (Claude Code, Python for arithmetic, no web), blind to the other verdicts, audited 98
answers with the exact GLM/Kimi prompts: the 60-answer blind sample (stratified 25 / 25 / 10 on GLM's verdict) and
all 43 GLM–Kimi disagreements (5 overlap). Per-answer verdicts in `validation/claude_audit_results.jsonl`.
- **Answers GLM keeps as clearly wrong (sample of 25): Opus 22 clearly wrong, 3 contested, 0 actually correct.**
- GLM "actually correct" (25): Opus 17 actually correct, 3 clearly wrong, 5 contested. GLM contested (10): 1 / 5 / 4.
- Same clearly-wrong-or-not call: with GLM 53/60 (κ 0.76), with Kimi 50/60 (κ 0.67); all three 49/60.
  Re-weighted to GLM's full verdict mix: 88% with GLM. BFF: 19/22 with GLM, 16/22 with Kimi; JudgeBench 34/38 each.
- GLM–Kimi disagreements (43): Opus sides with GLM 22, Kimi 21, and calls 18 contested — hard items, not one
  auditor's systematic error.
- Two JudgeBench items where Opus finds both the gold and the candidate wrong (hawk arc length 209.1 m; KL limit
  1.92 nats; both spot-checked numerically here). The prompt has no verdict for that; the candidate is wrong.
- Caveat: some JudgeBench responses were written by Claude models.

### 13d. Single-source recompute (`validation/paper_numbers.py` → `validation/paper_numbers.md`)

All behavioural paper numbers recomputed from raw rows with one convention (stated verdict, full audit, intervals
resampling questions). Corrections to earlier drafts:
- Table "audit by belief" had double-counted answers across bins; counted once at the highest Qwen belief:
  0/7 169 / 1 / 4, 1–3 89 / 5 / 6, 4–6 41 / 10 / 14, 7/7 23 / 23 / 9 (clearly wrong / actually correct / contested).
- **Same answer, different Qwen judges (the "not authorship" test): +17 [−2, +37]**, not +23 [+6, +38]. Suggestive only.
- Belief vs one-sample label (Qwens): label +2 [−9, +12] with belief fixed, belief +43 [+26, +57] with label fixed.
- Before reasoning (A) +22 [+7, +37] vs stated verdict +44 [+28, +56].
- Commit first (`rigor_checks.py --audited`): 0/7 17% → 1%; 7/7 50% → 56% (n=16); balanced accuracy 82 → 86% (+5 [+3, +7]).
- Reference test (`reference_test.py --audited` → `out/reference_audited.md`): strong-belief wrong 44% → 0% (expert),
  13% (Kimi-K3.1-Pro); balanced accuracy 78.7 → 90.9% / 86.1%; actually-correct answers 73% → 21% with the expert.
- Transcripts (`transcript_check.py --audited [--think]`): thinking on, approved wrong answers re-solve 99% and land on
  the graded answer 93% (n=74); thinking off 28% / 25% (n=330), rejections re-solve 97%.

### 13e. Inside the model, rechecked — the earlier strong claim does not hold

New captures on Cannon (`cannon_nano/capture_last.py`): the judge's state at "VERDICT:" **after its written
explanation** (JX) and **after its full thinking trace** (JT), BBEH, Qwen3.5-9B and Qwen3.6-35B.
- **Cosine confound** (`beyond_capability/dir_belief_robust.py`): over 20 random splits the belief–correctness cosine
  at the snap verdict is 0.80 (9B) and 0.48 (35B), but with belief labels **shuffled within question** it is 0.72 and
  0.42. Most of the alignment reflects which questions believed answers come from, not belief. The single-split,
  best-layer number for 35B moves between 0.41 and 0.80 with the split. **The paper's earlier Table 3 (0.70 / 0.80
  judging vs 0.36 / 0.25 solving) is withdrawn.**
- **Within-question test** (`beyond_capability/dir_belief_within.py`): believed vs never-reached wrong answers to the
  same question, pairwise AUROC on the correctness direction. Snap verdict 0.64 [0.51, 0.76] / 0.58 [0.48, 0.75];
  solving 0.60 / 0.54; after explanation **0.71 [0.59, 0.84] / 0.76 [0.65, 0.86]**, matching the verdict log-odds.
  Only 37–39 questions have both kinds of wrong answer. JT: 3–5 pairs, too few.
- Reading: a modest representation of belief at the snap verdict, no clear judging-vs-solving difference; after the
  judge writes its reasoning the state at "VERDICT:" mostly encodes the decision.

### 13f. Nemotron-3-Nano as a second family inside the model (running)

Tinker no longer serves Nemotron-3-Nano, so its own answers (1 + 7 per main-set question, 5 per BBEH question) run on
Cannon with vLLM (`cannon_nano/nano_gen.py`) and its hidden states with transformers (`cannon_nano/capture_last.py`,
native Nemotron-H code). Pool verdicts from when Tinker served it are reused (`cannon_nano/ingest.py`).

**Results (Nov 18, `out_nano/`, `validation/paper_numbers.md`).** 9,820 own answers (26 cut off); 1,735 verdicts.
- **Behaviour: a lenient judge with a shallow staircase.** Audited wrong answers approved 37% / 45% / 46% / 55%
  (0/7 … 7/7; gap +18 [−11, +43]). Belief slope +17 [+2, +31]; one-sample label −6 with belief fixed, belief
  +21 [+4, +37] with label fixed. Within question +47 [+8, +85] (58 groups). Right answers 50 → 83%.
- **Audit gap found and closed:** Nano's own answer matches the wrong JudgeBench response on 178 pairs no other judge
  had as a wrong target, so they had never been audited; both auditors now cover them (1,091 unique answers in all;
  GLM-5.3 vs Kimi-K3.1-Pro agreement 96%, κ 0.77).
- **Inside (BBEH, 75 believed / 617 never-reached audited wrong answers; 46 new believed answers audited,
  `inputs/ask_labelauditbbehnano.jsonl.gz`):** within-question snap verdict 0.56 [0.39, 0.68], verdict log-odds 0.47,
  solving 0.59. Cosine 0.78 at the snap verdict vs shuffled control 0.61 (95th pct 0.94) — the same confound.
- Like Llama-3.1-8B earlier, the weakest judge tracks belief least, in behaviour and inside.
- With Nano, the pooled within-question effect is +47 [+27, +71] (158 groups); accuracy control: belief +48 [+15, +72],
  accuracy +1 [−7, +8].

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
   inside the model by the absence of a causal own-answer direction. *Closest prior work (found Nov 12):* Goel et
   al. 2025 (*Great Models Think Alike*) show at the model level that judges favour models that make the same
   mistakes. Our addition is the per-question version and the inside-the-model control.
3. **The verdict ignores what the model knows about difficulty** — the hidden state ranks hard vs easy questions
   well; the verdict does not use it. That points to a cheap fix: let a probe-based difficulty score make the
   judge stricter on hard questions (a *selective* leniency dial, which steering alone was not).
4. **The own-answer lean lives in the representation in both families; it reaches the verdict only if the judge's
   reasoning uses that representation** — Qwen (reasoning amplifies it) vs Llama (reasoning discards it, along with
   most of what the hidden state knows). A judge can look "unbiased" simply because its verdict is disconnected from
   what it knows.
5. **Anchoring is graded by belief strength, and belief, not one sampled answer, is what matters.** Acceptance of
   wrong answers rises from 18% to 74% across belief 0/7 → 7/7 (clean labels). Holding belief fixed, the usual match label adds
   nothing. Correct answers the judge can't reproduce are rejected (30% accepted at 0/7). *Closest prior work (found
   Nov 12):* Wataoka et al. 2024 (judges favour text with low perplexity, i.e. text they find likely) and Zahraei et
   al. 2026 (*Prior Prejudice*, ACL Findings: judges favour claims matching their prior beliefs, behavioural, yes/no
   belief, persuasion tasks). Neither grades belief by sampling the judge's own answers on right vs wrong candidates,
   or looks inside the model. Whether one-pass answer likelihood reproduces the 7-sample result is untested.
6. **A readable signal is not a steerable fix.** Belief is linearly readable mid-network during reasoning, but pushing
   it during reasoning is a leniency dial, not a targeted correction.

## What is not new / weak spots

- The probes reproduce INSPECTOR's general claim; our addition is the within-question control showing much of it is difficulty.
- The personal own-answer effect is small with the one-sample label (+3), larger with belief strength (+23 at C,
  interval +6 to +38). Both rest on the few candidates the three Qwens believe to different degrees.
- RB2 Math labels: 61 of 549 "wrong" answers reach the right value (fixed Nov 13 in Experiments 1 and 6). BFF and
  JudgeBench labels were not audited the same way; the probe and steering experiments still use the old labels.
- Belief probes and steering were run on Qwen3.5-4B/9B with thinking off, on RB2 Math and BFF only. Their item groups
  were built before the 227 regenerated belief answers were merged; that moved only a handful of candidates between
  bins, and the belief tables above include them.
- Steering during reasoning used one way of pushing (the same push at every token, layers 14–26). A push only at
  the moment the judge checks the candidate's answer, or a fix to the re-derivation itself, is untested.
- Thinking-on results (Experiment 5) do not yet include the ~630 regenerated cut-off outputs.
- Most experiments use one family (Qwen). The belief-strength result (Experiment 6) now also holds for
  Nemotron-3-Super (NVIDIA, Nov 15 update); Llama is too weak a judge to test it (5 wrong answers at 7/7). The
  probes and steering (Experiments 2, 3, 7, 8) are still Qwen-only.
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

## Experiment 14 — Reviewer revision (Nov 18; caps: Tinker $1,000, Modal $200, Cannon free)

Handoff from an external reviewer (belief paper first). Everything below is reproducible from the named scripts.

### 14a. Fixed-effect checks (`validation/fe_checks.py` → `validation/fe_checks.md`)
- Stated verdict for every judge, 4,883 audited wrong-answer judgments, no duplicated (judge, candidate) rows; 767 of
  978 candidates are judged by 2+ families; no question id spans benchmarks.
- The paper's 60-sweep alternating projections equal an exact dummy-variable solve (to 1e-12) for judge, judge×question,
  candidate+judge and candidate+judge×question FE; they converge in 2–29 sweeps.
- Judge FE +37.6 [+26.8, +48.9]; judge×question +46.9 [+28.0, +70.2] (169 identifying groups, 88 questions; only 7% of
  belief variance left); candidate+judge +20.0 [+9.4, +31.0]; candidate+judge×question +20.6 [−6.1, +47.1].
- Leave-one-family-out: every J / JQ / CJ estimate stays positive with interval above zero. Per benchmark all positive;
  BFF candidate+judge +20.7 [−0.3, +40.1] is borderline.
- `difficulty_check.py` now uses the stated verdict for every judge (was the forced readout for non-Qwen families):
  pooled within-question +47 [+27, +70] (was +47 [+27, +71]); accuracy-controlled belief +49 [+16, +72] (was +48).
  Its "158" counts groups spanning belief BINS; 169 groups have different belief VALUES.

### 14b. How many own answers belief needs (`validation/sample_budget.py` → `validation/sample_budget.md`)
- Per-sample votes rebuilt exactly as belief.py (reproduces the paper's belief on every row). Held-out (5 folds
  grouped by question) logistic prediction of approval, judge-by-benchmark intercepts, 100 subset draws per k.
- Brier: intercepts 0.1595; separate 8th sample 0.1587 (n.s. vs intercepts); k=1 0.1572, 2 0.1561, 3 0.1556,
  5 0.1551, 7 0.1549. Every step lowers log loss with a paired interval excluding zero; 7 vs 1 −0.0022
  [−0.0037, −0.0010]; 7 vs 3 −0.0007 [−0.0012, −0.0003]. AUROC 0.70 → 0.73. Small absolute gains.
- One random sample of the seven beats the separate 8th sample (−0.0015 [−0.0026, −0.0005]); the 8th was generated
  earlier with a 4,096-token budget, so it is not exchangeable with the seven.
- JudgeBench: adding competitor belief lowers held-out log loss at every k (0.0010 at k=1, 0.0037 at k=7).

### 14c. Human-validation packages (prepared, NOT annotated): `validation/human_package/`
- `items.jsonl` (177: 60 high-belief items an auditor did not call clearly wrong, 23 GLM/Kimi disagreements,
  94 stratified retained answers with cell sizes for weighting) + `key.json`; `transcripts.jsonl` (76 thinking-on
  transcripts, verdict lines removed) + `transcripts_key.json`. Needs two human readers (finance for BFF).

### 14d. Paper wording
- Binning rule and "operational measure at one sampling configuration" stated; "authorship removed" narrowed to
  self-authorship excluded (family style can remain).

### 14e. Belief re-measured from fresh samples (`replication/reliability.py` → `replication/reliability_results.json`)
- Six original judges still on Tinker (three Qwens, Nemotron-3-Super, DeepSeek, Kimi-K2.6) answered all 459
  JudgeBench questions 7 more times, original prompt and settings ($91.77). Exact letters, so only JudgeBench's
  multiple-choice (MMLU-Pro) part counts: 237 audited wrong-answer judgments, 101 questions.
- Old vs new belief: r = 0.87; same bin 69% (7/7 → 7/7 in 15 of 21; 0/7 → 0/7 in 80 of 92).
- Approval (the ORIGINAL verdicts) on belief, judge FE: original +48 [+30, +65]; new +50 [+32, +66]; average of the
  two (14 samples) +53 [+34, +70]. Staircase by new belief 18 / 31 / 49 / 72%.
- Cap note: worst-case reservations stopped the first pass at $100 (actual $47.66); cap raised to $150 to finish.

### 14f. Fresh-question replication (`replication/`: PROTOCOL.md, SIZE.md, mmlupro.py, analyze.py → results_80_6000*.md)
- No unused questions remain in RB2 Math / JudgeBench / BFF, so JudgeBench's construction was rebuilt on MMLU-Pro
  questions not in JudgeBench. Protocol, analyses and size rule written before data. Writer Nemotron-3.5-Super
  (thinking off; GLM-5.3-Flash was dropped after a 5-question smoke test showed bare-letter answers); judges
  Qwen3.6-35B-A3B, Qwen3.5-9B, DeepSeek-V4.1-Flash, Kimi-K2.6 (no NVIDIA judge). Pilot 80 questions (not analysed);
  confirmatory questions 80..6079 → 1,336 pairs, 5,344 judgments.
- Primary (MMLU-Pro key, strict 5x-letter parsing; 4,151 judgments): 19 / 40 / 51 / 63% by bin; gap +45 [+37, +52];
  slope +47 [+41, +53]; per judge +61, +34, +50, +45 (all intervals above 0); same candidate across judges +19
  [+11, +26]; target +21 / competitor −29 [−36, −22]; one-sample label +8 [+3, +14] vs belief +40 [+34, +48].
- Kimi-K3.1-Pro audit of 361 wrong responses believed ≥ 4/7: 207 clearly wrong, 81 actually correct, 71 contested.
  Audit-filtered gap +38 [+27, +49]; Kimi-K2.6's 7/7 bin falls to 39% (n=18).
- Strict parsing dropped 1,175 judgments (Qwen3.6 593). POST-HOC lenient parser (spaced / repeated / bold / boxed /
  "answer is (X)" / last-line letter): 5,306 judgments, gap +46 [+40, +53], audit-filtered +42 [+32, +51].
- Cost $346 (writer $34, verdicts $19, own answers $229, audit $27, 13 timeouts counted at max $37).

### 14g. Ledger (Tinker, this revision): replication $346 + re-measurement $92 = $438 of the $1,000 cap. Modal $0.
Paper updated: new §6 "Replication on Fresh Questions" (+Takeaway 3), appendices "How Many Samples Belief Needs",
"Fresh-Question Replication Details", fixed-effect table; Ethics now states these costs instead of the unconfirmed
$1,500 project estimate.

## Experiment 15 — Second review: parser, audit coverage, wording, restructure (Nov 20)

Source: `Codex/.../outputs/future_paper_improvements.md`, Paper 1 items. Caps unchanged (Tinker $1,000, Modal $200).

### 15a. Complete replication audit (`replication/audit_extra.py` → `data/audit_extra.jsonl`; POST HOC)
- The pre-registered audit covered only the 361 wrong responses some judge believes ≥ 4/7 (strict parser). Kimi-K3.1-Pro
  audited the other 975 (72 high only under the lenient parser, 903 others), same prompt/settings: 842 clearly wrong,
  52 actually correct, 79 contested, 2 no verdict. All 1,336: 1,049 / 133 / 150 / 4.
- Auditor disputes (actually correct or contested) by highest belief of any judge (lenient): 0/7 9%, 1–3 19%,
  4–6 31%, 7/7 51%.
- Cost $53.24.

### 15b. Parser × label table (`replication/sensitivity.py` → `sensitivity.{json,md}`)
- Pooled slopes: strict key +47 [+41, +53]; strict high-belief audit +41; strict complete audit +43 [+35, +50];
  lenient key +48 [+43, +53]; lenient complete audit +45 [+38, +51]. Same candidate +19 to +21 throughout.
- One-sample (8th answer) label: +8 [+3, +14] on key labels, but +5 to +7 under audited labels (strict intervals
  include zero) → the paper now says the single-sample signal is reduced, not absorbed, and label-sensitive.
- Kimi-K2.6 7/7 bin under the complete audit: 39% (18) strict, 40% (25) lenient.

### 15c. Parser check (`replication/parser_check.py` → `parser_check/`)
- 134 blinded own answers read by Claude Opus 5.5 subagents (models, not humans). Lenient letter matches the reader on
  99/100 recovered answers. Of 34 answers neither parser reads, the reader finds a letter in 25 (mostly closing strings
  mixing option and non-option letters, e.g. "JKKKK"); they stay excluded (20 judgments under the lenient parser).

### 15d. Paper (`papers/judge_belief/main.tex`)
- Restructured to 4 takeaways (was 6): §4 main result + alternatives merged; §5 replication with a main-text
  parser × label table; §6 "Explanations and Hidden States" (transcripts + hidden states + verdict-before-justification,
  tables moved to appendix); §7 juries. Every experiment paragraph now opens with its motivation (citation or the
  observation that prompted it); added Simmons et al. 2011 and Verga et al. 2024.
- Wording: "persists after controlling for question identity"; "auditor from another model family"; auditor
  categories, not ground truth; transcript result described as a pattern in written explanations that cannot
  separate derivation, anchoring and rationalisation.
- Line numbers: lineno v5.7 (2026/02) misplaces right-column numbers in ACL review mode; preamble patch writes the
  column tag from `build/column/after` (also affects the stock ACL template on this TeX install).

### 15e. Ledger
Tinker this revision: $438 (Exp. 14) + $53 (complete audit) = $491 of $1,000. Modal $0. Human annotation still not done.

## Experiment 16 — Third review: self-preference contrast, math replication, human check package (Nov 20)

Self-review scored the paper ARR 3.5/5 and proposed three fixes; all three are done or prepared.

### 16a. Self-preference contrast (paper intro)
New paragraph: self-preference is about who wrote the text (and tracks familiarity / low perplexity; Panickssery et
al. 2024, Wataoka et al. 2024); belief is about what the answer concludes. Judges never grade their own text, and the
association holds where authorship cannot vary with belief (same question, same judge; same candidate, different
judges). Familiarity of a believed conclusion is counted as part of belief, not a rival explanation.

### 16b. Second pre-registered replication: open-ended math (`replication_math/`)
Why: the MMLU-Pro replication is multiple choice, and the main study's open-ended benchmarks need a model matcher.
DAPO-Math-17k problems with integer answers match exactly. Protocol (`PROTOCOL.md`) and size (`SIZE.md`) were fixed
before the confirmatory run; the parser was fixed on the pilot (questions 0-79). Confirmatory set: questions
80-1879 -> 819 pairs, 3,228 judgments (29 verdicts unparsed, 19 with < 5 own answers).

Plain-English result: judges solve 88-93% of these problems and pick the wrong response in only 4-8% of pairs, so
95% of judgments are at 0/7. Still, under the answer key the more a judge believes a wrong answer, the more it picks
it: 4% at 0/7, 19% at 1-3, 42% at 4-6, 92% at 7/7 (13 judgments). Pre-registered slope +71 [+54, +85]; every judge
above zero. Competitor belief -17 [-29, -6]. One-sample label +10 [-7, +28] beside belief +62 [+40, +83].

Differences from MMLU-Pro (reported as such):
- Same candidate across judges: -3 [-20, +17], null. Judges' beliefs about the same candidate differ for only 95 of
  819 candidates (12%; MMLU-Pro 683 of 1,333, 51%), so the test has little to work with.
- Kimi-K3.1-Pro audited all 819 wrong responses: 782 clearly wrong, 21 actually correct, 9 contested, 7 no verdict.
  Disputes by highest belief: 17/721 at 0/7, 4/66 at 1-3, 2/18 at 4-6, 7/7 at 7/7. The 7/7 disputes are specific
  derivations (e.g. power tower needs 6 levels, key says 5; divisor sum 29016, key says 2976). Not human-checked.
- Audit-filtered: no judgment left at 7/7; 3% / 14% / 22% over 0/7, 1-3, 4-6; slope +41 [+16, +70]. Qwen judges
  above zero, DeepSeek includes zero, Kimi-K2.6 approves 0 of 13 believed audited wrong responses.

Files: `math_rep.py`, `analyze_math.py`, `results_80_1800.{json,md}`, `pilot.log`, `confirm.log`, `audit2.log`. The
first audit pass stopped at the $300 cap because in-flight requests reserve their maximum cost; the 319 remaining
audits were rerun at concurrency 8. Paper: §5 "Open-ended answers", Appendix "Math Replication Details" (Table 7),
abstract, contributions, takeaway 2, limitations, ethics.

### 16c. Human label check package (MMLU-Pro replication; `replication/human_package.py`)
150 wrong-labelled responses stratified by the highest belief of any judge (7/7 50, 4-6 40, 1-3 30, 0/7 30; seed
20261120), NOT by audit verdict, so each stratum's human dispute rate compares directly with the auditor's
(9% -> 51%). Blinded items in `human_package/items.jsonl`; key with strata and auditor verdicts in `key.json`.
Annotation page: https://claude.ai/artifact/TBLySNG347bRqAbrHu1RmK (labels stored per reader). Not yet annotated;
the user will annotate. No model output may be recorded as a human label.

### 16d. Ledger
Math replication $292.59 (pilot included; writing $39.54, verdicts $19.64, own answers $178.76, audit $48.45,
timeouts $6.20). Tinker this revision total: $491 + $293 = $784 of $1,000. Modal $0.

### 16e. Independent re-review fixes (Nov 20)
A fresh reviewer checked every number against the result files (all match except three math roundings: same
candidate -2 not -3; target upper +71 not +72). Fixed after verifying each claim against code: fixed effects are
benchmark x judge (fe_checks.py, paper_numbers.py), JudgeBench falls back to the GLM matcher when an answer lacks a
letter (belief.py), the two judges that rise less are named (Nemotron-3-Nano, Qwen3.5-4B), "pre-registered" ->
"pre-specified" (protocols are written and released, not third-party registered), the math replication is described
as weaker (top bin all disputed keys; Kimi-K2.6 audited slope -7 [-14, -4]), thinking claims limited to Qwens, the
conclusion's jury claim narrowed to what was tested, reference gain "about 60%" not "half", re-measuring belief moved
to Section 4, two-replication wording throughout, metric definitions (Brier, AUROC, balanced accuracy, kappa).
Abstract 197 words; main text ends on page 8.

## Experiment 17 — Strict re-review, belief items B1–B5 (Nov 21; CPU only, $0)

Source: an outside strict review of both papers (Nov 21). This entry covers the belief paper only; the direction
items (D1–D5) were handled by the session editing the direction paper. All analyses below are post hoc, use existing
data, and made no model calls (Tinker total unchanged at about $784 of $1,000; Modal $0).

### 17a. Own belief vs other judges' belief (B2; `validation/consensus_check.py` → `consensus_check.{json,md}`)
Why: seven answers predicting approval would be unsurprising if they only marked wrong answers every model finds
attractive (shared answer popularity; Goel et al.). Test: approval ~ own belief + leave-family-out consensus (mean
belief of other-family judges in the same candidate), benchmark×judge FE, question bootstrap; plus held-out logistic
prediction (10 folds by question, 5 partitions, paired question bootstrap of log loss).
- Original (4,621 judgments): consensus alone +42 [+28, +56]; together consensus +23 [+9, +37], own +25 [+16, +35].
  Held-out log loss with own added −0.0031 [−0.0058, −0.0006]; AUROC 0.722 → 0.728. corr(own, cons) 0.69;
  identifying sample 368 judgments with |own − cons| ≥ 2/7. Consensus beyond own: −0.0021 [−0.0053, +0.0008].
- MMLU-Pro (lenient, key / complete audit): own +34 [+29, +39] / +34 [+27, +41]; log loss −0.0149 / −0.0123, both
  intervals below zero; AUROC 0.680 → 0.714.
- Math (key / audited): own +28 / +27 in-sample, but held-out log loss −0.0008 [−0.0028, +0.0010] / −0.0011
  [−0.0038, +0.0013]: not detectable, consistent with the null same-candidate test.
- Pairwise (competing response's own and consensus belief added): own +18 [+3, +33] (original JudgeBench, 563),
  +15 [+8, +22] (MMLU-Pro).
- Leave-judge-out consensus gives the same picture. Reading: part shared agreement, part judge-specific; the paper
  keeps the judge-belief framing but says so.

### 17b. Majority-vote juries at a matched budget (B4; `validation/jury_vote.py` → `jury_vote.{json,md}`)
All 1,441 original items with verdicts from all seven judges (747 right, 694 audited wrong; 81 items missing a
verdict, 82 dropped by audit). Three votes, no ties. 3 Qwens 81.5% balanced accuracy; 17 three-family juries
78.9–84.6% (mean 81.6%); Qwen3.6-35B alone 83.3%. On the 92 wrong answers the Qwens believe (mean ≥ 4/7): 3 Qwens
approve 75%, cross-family juries 76/75/73% (paired −2.2 [−12.1, +8.6] for the no-Qwen jury); each non-Qwen judge
alone approves 70%. No repeated verdicts from one model exist, so no self-consistency baseline.
**Superseded by 18a (Nov 21, later):** on JudgeBench these votes mixed frames — each judge's row targets the response
that matches its own answer, so one judge's "approve" could mean "picked the right response" and another's "picked
the wrong one" (391 of 475 pairs). The numbers above are wrong; see 18a.
Paper: Section 7 renamed "Targeted Judging Interventions"; "only an outside reference removed them" replaced by the
observed results; commit-first effect on believed answers called "undetermined" (16 judgments).

### 17c. Math as a boundary result (B3; `replication_math/boundary.py` → `boundary.{json,md}`)
Audited rates with counts: 0/7 3.0% (2,967 judgments, 780 candidates), 1–3 13.7% [5.9, 22.9] (102, 72), 4–6 22.2%
[5.9, 38.9] (18, 16), none at 7/7. Any-match vs none (judge FE): audited +11.8 [+3.9, +20.6] (Qwens clear, DeepSeek
+11.1 [−0.9, +25.3], Kimi −2.3 [−3.5, −1.2], 0 of 13 picked); key +25.7 [+15.9, +35.9]. Paper now leads with these
rates, calls the audited slope an extrapolation, states that judge-specific evidence does not replicate (same
candidate −2 [−20, +17], below MMLU-Pro's +19) without attributing it to power, and retitles Section 5
"A Replication and a Boundary Test".

### 17d. Human check for math (B1; `replication_math/human_package.py` → `human_package/`)
66 items stratified by highest belief (all 7 at 7/7, all 19 at 4–6, 20 each at 1–3 and 0/7; seed 20261121;
population sizes in key.json). Annotation page: https://claude.ai/artifact/SoM5ySwngQSWFMGFecAG8x (labels collection,
empty). The MMLU-Pro page (https://claude.ai/artifact/TBLySNG347bRqAbrHu1RmK) still has no labels. Paper: dispute rates
called provisional until human-checked; reference-answer wording now "where the auditor disputes it"; the power-tower
example is the only key error we verified by hand.

### 17e. Mechanistic material cut back (B5)
Section 6 shortened to three short paragraphs and a one-line takeaway; details stay in the appendices. Layer selection
audited (`beyond_capability/dir_belief_within.py`): the best layer is chosen by cross-fitted right-vs-wrong AUROC on
the same questions (does not use belief, but no inner split). Paper now says so and gives the top-third-of-layers
average (0.60 / 0.57 / 0.59) and the number of roles tested, with no multiplicity correction.

### 17f. Paper
Abstract 200 words (adds the consensus result and the math boundary wording). New appendices: own vs consensus
(Table `tab:consensus`), majority-vote juries (Table `tab:jury`), math observed rates. "Re-measuring belief" moved to
the robustness appendix with a pointer. Main text ends on page 8; 17 pages total; no undefined references.
Not changed: the title (the review's editorial item 1 suggests answer-agreement wording unless validated; the
consensus result supports a judge-specific component, so this is left to the authors).

---

## Experiment 18 — Strict re-review, second pass (Nov 21)

### 18a. Majority votes, corrected, with a self-consistency baseline (B4; `validation/jury_vote.py`, `validation/jury_repeat.py`; Tinker \$38.88)
**Correction.** On JudgeBench each judge's belief row targets the response matching ITS OWN one-sample answer, so the
17b votes mixed "picked the right response" and "picked the wrong response" across judges (391 of 475 pairs). Now
every pair is one unit whose candidate is the wrong response (vote = picks it; belief = each judge's belief in it,
`belief_other` when its row targets the right one). Units: 1,523 with all seven verdicts; 87 not audited clearly wrong
and 67 JudgeBench pairs never audited (no judge's own answer matched the wrong response) excluded → 434 right, 935
wrong, 755 questions. (The routing analysis was not affected: it pairs Qwen and Nemotron rows only when their targets
agree.)
**Repeats.** Each judge still on Tinker (all but Nemotron-3-Nano) graded every unit twice more with the exact original
messages (`inputs/readout_jobs*.jsonl.gz`), thinking off, T = 0.7, 32K-token budget; 18,276 draws; 14 gave no verdict
(8 ran out of tokens in repetitive reasoning, 6 Nemotron-Super outputs ended after a few tokens) and were drawn again;
every unit ends with two parsed repeats. On the 8,823 of 9,138 original transcripts in the job files that contain a
verdict (315 were cut off and regenerated in the pool run), the parser reproduces the paper's verdict every time. Cost \$38.88 (Kimi \$18.31, Qwen3.5-9B \$5.70, Qwen3.6 \$4.66, DeepSeek \$4.60,
Nemotron-Super \$3.08, Qwen3.5-4B \$2.51); the first sequential run was stopped and resumed in four parallel
processes (at most ~\$0.20 of in-flight calls lost).
**Results (balanced accuracy, %).** Singles: Qwen3.6 86.1, Kimi 85.6, DeepSeek 84.8, 9B 82.6, Nemotron-Super 81.7,
4B 79.3, Nano 65.7. Same judge ×3: Qwen3.6 86.9, DeepSeek 86.4, Kimi 86.1, 9B 85.2, Nemotron-Super 81.4, 4B 80.3
(change vs single −0.3 to +2.6; 9B +2.6 [+1.4, +3.9]). Three Qwens 85.2. Fixed cross-family juries 87.2 / 87.9 / 87.3
(mean of 17: 85.8, range 81.1–88.3): vs three Qwens +2.0 [+0.3, +3.8] / +2.7 [+0.8, +4.5] / +2.1 [+0.1, +4.1]; vs
Qwen3.6 ×3 +0.3 [−1.4, +2.3] / +1.0 [−0.3, +2.5] / +0.4 [−1.7, +2.5]. The three fixed juries leave out the weaker
judges; averaged over all 17 cross-family triples the gain over the Qwens is only 85.8 vs 85.2. **The gain over the
Qwens is mostly judge quality, not family diversity.** 34 wrong answers the Qwens believe (mean ≥ 4/7): false acceptance three Qwens 53%,
Qwen3.6 ×3 41%, fixed juries 47 / 41 / 41% (vs Qwens −5.9 [−24.2, +11.8], −11.8 [−26.5, 0.0], −11.8 [−32.4, +6.2]).
**Repeatability.** After a judge approves a wrong answer, its two repeats approve again 61.7% [57.7, 65.7] at own
belief 0/7 (653 approvals), 60.7% [54.2, 67.0] at 1–3 (149), 81.2% [73.7, 87.3] at 4–7 (128); 4–7 minus 0/7 +19.5
[+11.5, +26.6]. Approvals of believed wrong answers are reproducible decisions, not sampling noise.
**Paper.** §7 "Majority vote" rewritten (cross-family vs Qwens vs self-consistency; repeatability), Takeaway 4 and
Conclusion follow; Appendix "Majority-Vote Juries" rewritten with the new table; Limitations: repeats omit Nano.

### 18b. Hidden states: layer chosen without the test questions (B5; `validation/hidden_nested.py` → `hidden_nested.{json,md}`)
The paper's layer was the one whose correctness direction best separates right from wrong answers over ALL questions
(no belief used, but the same questions as the reported statistic). Two checks remove that choice: a nested choice
(each training half picks its layer from an inner split of its own questions; the test half is scored there; 20
halvings) and the middle captured layer fixed in advance. Snap verdict (Qwen3.5-9B / Qwen3.6-35B / Nemotron-3-Nano):
paper's selection 0.64 / 0.60 / 0.56; nested 0.62 / 0.58 / 0.59 (directions fixed, questions resampled: [0.55, 0.69],
[0.49, 0.67], [0.53, 0.68]); middle layer 0.58 / 0.61 / 0.56. Solving nested 0.59 / 0.59 / 0.56; after the
explanation 0.70 / 0.77. The nested choice is unstable (Qwen3.5-9B picks 11 different layers over 40 training
halves). Reading: layer selection does not explain the small snap-verdict effects, and they stay small.
The script also recomputes the paper's own table on the final BBEH audit (the Nano audit on Nov 18 removed 4 of the
125 Qwen3.6-35B pairs after its table was made): Qwen3.6-35B snap 0.58 → 0.60 [0.46, 0.74], log-odds 0.58 → 0.60,
solving 0.54 → 0.56, after explanation 0.76 → 0.75 (log-odds 0.77 → 0.78); Qwen3.5-9B and Nano unchanged except the
9B snap interval [0.51, 0.76] → [0.52, 0.78]. The paper's table now comes from this one script.

### 18c. Audit-by-belief table: JudgeBench belief made literal (`validation/paper_numbers.py`, T1)
The table bins each unique wrong answer by "the highest belief any Qwen has in it", but on JudgeBench it counted only
Qwen rows whose target was that wrong response; a Qwen whose row targets the right response still has a belief in the
wrong one (`belief_other`). Counting it moves 24 of 399 answers up one bin (none into 7/7). New rows (clearly wrong /
actually correct / contested): 0/7 155 / 1 / 4 (was 169 / 1 / 4), 1–3 95 / 4 / 4 (89 / 5 / 6), 4–6 49 / 11 / 16
(41 / 10 / 14), 7/7 unchanged 23 / 23 / 9. Every other number in `paper_numbers.md` is unchanged (diffed).

### 18d. Human-label analysis, ready before labels exist (B1; `validation/human_analysis.py`)
No labels yet on either annotation page (checked Nov 21: both `labels` collections empty). The script reads labels
from a page export or a JSONL file and reports reader agreement (κ), human × auditor tables per belief stratum, the
human and auditor dispute rates weighted to stratum sizes with intervals (items resampled within strata), and, for the
replications, the confirmatory slope with every sampled response relabelled by the human consensus. Plumbing tested
on SYNTHETIC labels written to a scratch folder only (`--simulate --out <scratch>`): with readers that copy the
auditor it reproduces the audited slopes (math +41 [+16, +70], MMLU-Pro +45 [+38, +51]). No synthetic output is in
the repo, and no model output may be entered as a human label.

### 18e. Paper and budget
Main text still ends on page 8 (intro results paragraph, vote setup and conclusion compressed); 17 pages; no
undefined references or overfull boxes. Wording: "predicts approval as strongly" → "with a similar slope (+50 vs +48)";
"Kimi-K2.6 reverses" (math) → "picks none of the 13 it reaches". An independent fresh-agent check of the changed
hidden-state, audit-table and wording numbers found no mismatches (one caption wording fixed); a second check of the
vote section found every number right and led to wording fixes: the mean over all 17 triples now beside the three
fixed juries, "two intervals end at zero", "almost removes", "on BFF-Bench" for the reference, 14 (not 8) redraws, and
commit-first at 4–6 (−2 [−20, +13]) added. Belief-paper Tinker spend
now about \$823 of the \$1,000 cap (this pass \$38.88); Modal \$0. Title still unchanged (authors' call).
