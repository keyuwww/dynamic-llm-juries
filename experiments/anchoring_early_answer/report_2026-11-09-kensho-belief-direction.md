# Belief direction — Nov 9, 2026

**Motivation.** We looked at the mistakes LLM judges make and asked how many of them come from the judge grading an
answer that is the same as what it would have answered itself. Three Qwen judges, RB2 Math + JudgeBench + BFF:

| Judging mistake | How many | Share involving the judge's own answer | Share expected by chance |
|---|---|---|---|
| Approved a **wrong** answer | 671 | **39%** were the same wrong answer the judge gave when it solved the question itself | 19% (share of all wrong answers that match) |
| Rejected a **correct** answer | 334 | **28%** were answers that differ from the judge's own | 8% |

So a judging mistake is about **2 to 3.5 times more likely than chance** to involve the judge's own answer. It approves
wrong answers it agrees with and rejects right answers it disagrees with. Measured more carefully with belief (section
1), the picture is the same: 38% of approved wrong answers are ones the judge itself reaches in at least 4 of 7 tries,
while only 17% of all wrong answers are. On single-answer benchmarks alone, 34% of approved wrong answers match the
judge's own (RB2 Math 31%, BFF 42%).

**Question.** LLM judges approve wrong answers far more often when the wrong answer matches what they would have
answered themselves ("anchoring"). Is there an internal *belief* signal behind this, can we read it, and can we turn
it down?

**Setup.** Judges: Qwen3.5-4B, Qwen3.5-9B, Qwen3.6-35B (thinking off). Benchmarks: RB2 Math (RewardBench 2 math
problems), JudgeBench (pairwise, no coding) and BFF-Bench (finance, answers labelled by unanimous experts). Each item is
a question plus a candidate answer written by **another** model, with a label saying whether it is right. The judge never
wrote the candidates and is not told who did.

---

## 1. What "belief" is and how we measure it

**Belief = how often the judge would give that same answer itself.** There are two kinds of calls:

1. **Solve calls (7 of them, independent)**
   - Prompt: just the question, asking the model to answer it, like any normal question.
   - What it doesn't see: the candidate answer, or any of its other attempts.
   - Settings: temperature 0.7, so each attempt can come out differently.
   - Result: 7 answers we store on the side.
2. **Judging call (the normal one)**
   - Prompt: the question plus the candidate's answer, then "Is this answer correct? … VERDICT: CORRECT / INCORRECT."
   - What it doesn't see: its own 7 solutions.

**Afterwards, offline:** a different model, GLM-5.3-Flash, compares each of the judge's 7 answers with the candidate's
final answer and says SAME or DIFFERENT (JudgeBench letter answers are compared exactly). **The SAME count, out of 7,
is the belief.**
- 0/7: the judge never reaches this answer on its own.
- 7/7: it reaches it every time; it is "sure".
- 3/7: it is torn.

### Result: acceptance follows belief

Wrong answers only, all three Qwens, main set (2,440 wrong candidates):

| Belief | 0/7 | 1–3 of 7 | 4–6 of 7 | 7/7 |
|---|---|---|---|---|
| Accepted before reasoning (position A) | 25% | 29% | 41% | 56% |
| Accepted at the verdict (position C) | 18% | 36% | 54% | 71% |

- **Reasoning makes it stronger:** the 7/7-vs-0/7 difference is +28 points before reasoning and **+52** at the verdict.
- **Belief, not one sampled answer, carries it:** with both in one model, belief 7/7 vs 0/7 = **+50 [+39, +61]**,
  while the old one-sample "matches my answer" label adds +1 [−7, +10].
- **There is a personal part:** on the *same* wrong answer, a Qwen's own belief adds **+22 [+6, +38]** at the verdict
  beyond what all three Qwens share.
- **It cuts both ways:** correct answers the judge never reaches itself are accepted only 30% of the time; at 7/7, 91%.

### Belief is usually right

| Belief | 0/7 | 1–3 of 7 | 4–6 of 7 | 7/7 |
|---|---|---|---|---|
| Share of candidates at this belief that are actually correct | 5% | 34% | 70% | **89%** |

So leaning on belief is close to the best a judge can do without other information. The damage is a narrow tail:
across the three Qwens, about 150 wrong answers approved at 7/7, against about 1,570 correct ones.

![Acceptance by belief, and how often belief is right](out/figs_belief/fig1_belief_acceptance.png)

*Figure 1. Left: share of answers the judge accepts, by how often it reaches that answer itself. Wrong answers (blue
before reasoning, orange at the verdict) and correct answers (green). Right: share of candidates at each belief level
that are actually correct.*

---

## 2. How the probe works (finding the belief direction)

1. **Record what the judge is "thinking".** While the judge reads a question and a candidate answer, every layer of the
   model holds an internal state: a list of numbers (4,096 for Qwen-9B). That list is the model's working memory at that
   moment. We save it at several points:
   - **A:** just after it reads the candidate answer, before it writes anything;
   - **25%, 50%, 75%** of the way through its written reasoning;
   - **C:** right before it writes CORRECT or INCORRECT.

   We save it at every layer. That gives one 4,096-number vector per judgment, per point, per layer.
2. **Pair each vector with its belief score.** For each judgment we also have the number from section 1:

   | Judgment | Internal state (4,096 numbers) | Belief |
   |---|---|---|
   | question 1, answer A | [0.3, −1.2, 0.8, …] | 6/7 |
   | question 1, answer B | [0.1, 0.4, −0.5, …] | 0/7 |
   | … about 1,200 judgments per judge … | | |

3. **Fit a linear probe.** A linear probe is just a weighted sum: give each of the 4,096 numbers a weight, multiply, add
   up, and try to land on the belief score.

       predicted belief ≈ w₁·x₁ + w₂·x₂ + … + w₄₀₉₆·x₄₀₉₆

   We find the weights with **ridge regression**: ordinary least squares plus a penalty that stops it from overfitting,
   since there are more numbers per vector than examples. The simplicity is deliberate. If something this simple can
   recover belief, the information is sitting plainly in the state.
4. **The weights are the direction.** The 4,096 weights together form an arrow in the model's internal space. That
   arrow is the **belief direction**. (Moving along it raises the probe's predicted belief by construction, so that
   alone proves nothing; the checks are step 5 and the steering in section 4.)
5. **Check it's real, not memorized.** We train on some questions and test on **different questions** the probe never
   saw. On those, we ask: among wrong answers, can the probe tell the ones the judge believes (≥4/7) from the ones it
   never reaches (0/7)? The score is **AUROC** (0.5 = coin flip, 1.0 = perfect). We also tried every point and every
   layer, picking the best using only training data (nested cross-validation).

### Result (held-out)

| Judge, benchmark | Held-out AUROC | Usually chosen | Correctness probe / judge's verdict at the same point |
|---|---|---|---|
| Qwen3.5-9B, RB2 Math | **0.86** [0.81, 0.90] | C, layer 21 | 0.79 / 0.82 |
| Qwen3.5-9B, BFF | **0.80** [0.71, 0.87] | C, layer 25 | 0.80 / 0.74 |
| Qwen3.5-4B, RB2 Math | 0.78 [0.72, 0.83] | C | 0.73 / 0.76 |
| Qwen3.5-4B, BFF | 0.72 [0.63, 0.80] | mixed | 0.63 / 0.70 |

Belief is clearest in the middle-to-late layers, near the verdict, and on RB2 Math it grows as the judge writes
(9B: A 0.77 → C 0.88). It reads belief better than a probe trained on "is this answer right?".

![Belief readability by reasoning position](out/figs_belief/fig2_probe_by_position.png)

*Figure 2. How well the probe separates believed from never-reached wrong answers, at each point in the judge's
reasoning (best layer at each point). Legend: the honest held-out score with position and layer chosen on training
folds only.*

---

## 3. Fitted probe vs the other session's difference of means

**The other session's judge direction (difference of means):**
1. Collect the judge's internal state for many answers.
2. Average the states for right answers and, separately, for wrong answers.
3. Subtract: the right-answer average minus the wrong-answer average gives the direction.

That still needs labels (which answers are right) and data. It is a probe with no fitting step: just two averages and a
subtraction.

**Why I used a fitted probe for belief:**
- **Belief isn't yes/no.** It runs from 0/7 to 7/7, and regression uses all the levels, not just two groups.
- **I did try the subtraction first**, but only at position A (before reasoning): "believed" minus "never reached". It
  was noisy. Fitted on two different halves of the questions, the two directions barely agreed (similarity 0.24, where 1
  means identical), and it mostly pointed the same way as "is this answer right?" (similarity 0.70). Ridge regression gave
  a stable direction that separates belief from correctness better.

**Caveat.** Difference-of-means directions often *steer* better than regression directions, even when regression *reads*
better: regression can latch onto small, precise patterns that predict well but aren't what the model uses. The model
varies very little along the ridge direction, which is why large pushes were needed. Difference of means at the reasoning
positions (where belief is clearest) has **not** been tried, so it is still open.

---

## 4. Steering along the belief direction

**Done: a fixed push while the judge reasons** (Qwen3.5-9B, layers 14–26, every token; each item uses the direction
fitted on the *other* half of the questions; 418 items). Change in acceptance vs no push, both benchmarks:

| Push | Wrong, believed (68% accepted) | Wrong, never reached (21%) | Correct (85%) |
|---|---|---|---|
| belief −4 | +2 | +2 | **−7** |
| belief −6 | −5 | −1 | **−9** |
| belief without correctness −6 | −7 | −3 | **−13** |
| "is this right?" −6 | −4 | +2 | **−7** |
| random −6 (control) | +1 | +1 | −4 |
| belief **+4** | +5 | **+8** | +4 |

- The direction does change behaviour: "believe more" makes the judge accept more, and "believe less" makes it accept less.
- But it is **not selective**: correct answers drop as much as or more than the believed wrong ones. It acts as an overall
  leniency dial.
- Likely reason: adding the same push to every item can only shift everything the same way.

![Steering along the belief direction](out/figs_belief/fig3_steering.png)

*Figure 3. Change in acceptance vs no push, for each kind of push, split by item group. A selective push would move
orange (believed wrong answers) left while keeping green (correct answers) near zero; none does.*

**Done: removing belief instead of pushing it.** Here each item's *own* position along the belief direction is
multiplied by a factor, at layers 14–26 on every token. ×0 removes belief; it does not push every item the same way.
Acceptance, both benchmarks; the believed wrong answers are split by how strongly the judge believes them:

| | Wrong, believed 4–6 of 7 (n=41) | Wrong, believed 7 of 7 (n=57) | Wrong, never reached (n=160) | Correct (n=160) |
|---|---|---|---|---|
| no edit | 59% | 75% | 21% | 85% |
| belief **×0 (removed)** | 68% | 74% | 23% | 85% |
| belief ×−2 (flipped) | 61% | 77% | 24% | 84% |
| random −6 (control, additive) | 68% | 70% | 21% | 81% |

- **Removing belief changes nothing.** Answers the judge believes 7 of 7 times are still accepted 74% of the time
  (vs 75%), and correct answers are untouched (85%). The 59% → 68% move at 4–6 of 7 is within noise: n=41, and the
  random push moves it by the same amount.
- **So the direction is readable but not what drives the verdict.** The judge's tendency to accept its own answer
  survives with the belief direction projected out of the middle layers. The decision probably uses belief information
  stored elsewhere or spread across many directions. The probe finds one readable copy of it.
- **Bug, now being rerun:** the larger factors (×−5, ×5) broke every run, including the random control: 100% of
  outputs looped into junk text. Multiplying at 13 layers in a row compounds (roughly 5¹³), and ×−2 already garbled
  about 3% of outputs. ×0 is safe because removing something twice is the same as removing it once. The rerun scales at
  **one layer (21)**, with ×−1, ×−3 and ×3 plus random and correctness controls.

**Still running on Harvard's Cannon GPUs (free):**
- **Push while solving:** push the belief direction while the judge *solves* the question (no candidate shown), then
  recompute belief. This tests whether the direction changes actual belief, not just verdicts. A null result would be
  ambiguous, since the other session found solving and judging use unrelated directions.
- **Llama-3.1-8B:** the whole pipeline again (7 extra own answers, probes, steering), including BFF, which Llama never
  had.

---

## 5. Hypotheses for what comes next

- **Belief is useful when the judge's own answer is right.** Correct answers the judge believes 7/7 are accepted 91% of
  the time, which is the judge working properly. Belief only hurts when the judge is confidently wrong, and from the
  inside it can't tell those two cases apart.
- **So removing belief cuts both ways.** It would stop the judge rubber-stamping wrong answers it agrees with, but also
  stop it confirming right answers it agrees with. That is the same pattern as "Solve-and-compare" in the other
  session's report: it helps on questions the judge solves and hurts on ones it doesn't.
- **What the shrink test can still show:** whether, with belief removed, the verdict falls back on some other checking
  ability. If believed wrong answers drop a lot while correct ones drop only a little, the judge has real checking ability
  that belief was overriding.
- **On the uncertain cases (1–6/7):** belief is weaker there, so there is less to remove. The shrink results will be
  broken down by belief level.
- **A confident judge can still be wrong.** Removing belief can't give the judge the right answer.

---

## 6. Can the judge tell its wrong confident beliefs from its right ones?

**Test.** Only answers the judge believes (≥4/7). From the judge's internal state while judging, predict whether the
believed answer is actually right, on held-out questions. Compare against two baselines:
- **the judge's own verdict confidence** (how strongly it said CORRECT);
- **a question-only probe** that sees the average state over all of a question's candidates, so it carries no
  information about this particular answer.

**Among confident answers the judge accepted** (the errors that matter). AUROC for ranking right above wrong:

| | Hidden-state probe | Question-only probe | Judge's verdict confidence | Probe minus verdict |
|---|---|---|---|---|
| 9B, RB2 Math (42 wrong) | 0.69 | 0.73 | 0.65 | +0.03 [−0.09, +0.16] |
| 9B, BFF (25 wrong) | **0.84** | 0.72 | 0.66 | **+0.18 [0.00, +0.34]** |
| 4B, RB2 Math (43 wrong) | 0.62 | 0.69 | 0.63 | −0.01 |
| 4B, BFF (23 wrong) | 0.81 | 0.82 | 0.74 | +0.07 |

![Confident beliefs: right vs wrong](out/figs_belief/fig4_confident.png)

*Figure 4. Among confident answers the judge accepted, how well each signal ranks the right ones above the wrong ones.
The hidden-state probe (orange) beats the judge's own confidence (blue) clearly only for Qwen-9B on BFF, and the
question-only probe (green) is as good on RB2 Math.*

**What it means:**
- **Confident errors are partly detectable** (0.62–0.84). The judge is not completely blind to them.
- **The judge mostly already uses what it knows.** On RB2 Math the hidden state does no better than the judge's own
  confidence. There is no clear "knows but doesn't say" gap, unlike Llama in the other session.
- **On RB2 Math the signal is about the question, not the answer.** The question-only probe does as well as the
  answer-specific one, i.e. "this is the kind of question I get wrong", which is self-knowledge about difficulty.
- **One lead on BFF:** for Qwen-9B the probe beats its verdict by +0.18, but the interval touches zero and there are only
  25 wrong answers. Worth replicating, not a finding yet.
- **Belief level alone barely helps** on RB2 Math (0.57): "7/7 vs 4/7" doesn't tell you whether the belief is right.

**Bottom line.** From the inside, the most you can do is roughly "flag confident answers on questions that look hard,
and escalate them", and the judge's own confidence does nearly as well as a probe for that. Fixing confident errors needs
**outside information**: a reference answer (0.55 → 0.95 on unsolved questions in the other session), or a judge that
doesn't share the same blind spots.

---

## Files

- Belief: `belief.py` → `out/belief.md`
- Probes: `belief_probe_grid.py` → `out/belief_probe_grid.md`; `confident_probe.py` → `out/confident_probe.md`
- Steering: `belief_steer_prep.py`, `cannon_belief/steer.py` → `belief_steer_analysis.py` → `out/belief_steering.md`
- Figures: `make_belief_figs.py` → `out/figs_belief/` (needs matplotlib, e.g.
  `uv run --no-project --with matplotlib --with numpy python make_belief_figs.py`)
- Queued: `cannon_belief/solve_steer.py` (push while solving), `cannon_belief/llama_gen.py` + `capture.py` (Llama)
- Full write-up: `REPORT.md`, Experiments 5–8
