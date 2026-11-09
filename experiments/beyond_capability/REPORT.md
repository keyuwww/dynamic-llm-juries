# Judging questions you cannot solve: can an LLM judge still judge, and what helps? (Nov 8, 2026)

## The question

The anchoring study found that judges lean toward wrong answers that match their own belief, and that the lean is
strongest on BBEH questions the judge cannot solve. This project asks the broader question: **when a question is beyond
a judge's ability to solve, can it still tell right answers from wrong ones, and what makes it better at that?**

## Short answer

1. **Mostly no.** On BBEH (hard reasoning puzzles), the three Qwen judges are close to a coin flip on questions they
   cannot solve themselves (balanced accuracy 0.49–0.55, against 0.68–0.77 on questions they solve). Even the strongest
   model available, Kimi-K3.1-Pro with reasoning, drops from 0.93 to 0.63 on the questions it gets wrong itself.
2. **Part of this is plain difficulty, but not all of it.** Hard questions defeat every judge. Holding the answer
   being judged fixed (the same answer judged by a judge that solved the question and one that did not), solving still
   adds **+6 points** [+3, +10] to the chance of a correct verdict.
3. **How bad it gets depends on the benchmark.** Where checking an answer is easier than producing it (RB2 Math,
   BFF-Bench finance), judges keep balanced accuracy of 0.62–0.74 on questions they cannot solve. On BBEH and
   JudgeBench they fall to 0.49–0.68.
4. **The stronger the judge, the bigger the drop.** Qwen-35B and Kimi have the largest gaps (+28 to +30 points on
   BBEH, +43 on JudgeBench). On questions they cannot solve, strong and weak judges end up in the same 0.5–0.7 band:
   a stronger judge's advantage comes almost entirely from the questions it can solve.
5. **On unsolved questions the verdict collapses into "does this match what I believe?"** Qwen judges accept 68–90% of
   wrong answers that equal their own wrong answer, but only 44–54% of other wrong answers, and only 62–69% of right
   answers. Answers they never produced themselves: right ones accepted 42–59%, wrong ones 37–49%.
6. **What helps is outside information, not more effort from the judge.**
   - The official answer as a reference lifts unsolved questions from 0.55 to **0.95** (BBEH) and 0.69 to 0.85 (BFF).
   - A stronger model's answer as a reference: **+20 points** on BBEH unsolved, +8 on BFF. It hurts when that answer
     is itself wrong.
   - The simplest version works as well: accept only answers that match the stronger model's answer (+23), or let the
     stronger model judge (+22).
   - A cascade that sends only the cheap judge's uncertain cases to Kimi (about 40–55% of them) recovers most of
     Kimi's accuracy.
7. **What does not help:** a "verify the steps" prompt (−2 to +1), giving the judge its own earlier answer as the
   reference (**−17 points** on BBEH unsolved, −10 on BFF), a majority vote of the four weak judges (+4), thresholds
   that adapt to difficulty (+1 to +5), and the hidden-state probe (it mostly recognises hard questions; small gain
   within a question).
8. **Inside the model, solving and judging encode "this is right" in different places** (Step 3). Show Qwen-9B or
   Llama-8B the same answer as its own response vs as someone else's to grade: the two "right minus wrong" directions
   are near-orthogonal (cosine −0.05 to 0.11), and a probe trained in one role does not work in the other. Steering the
   judge along the solving direction does nothing. Stretching along the judge's own direction gives Llama +7 points
   [+1, +14] on questions it cannot solve and Qwen nothing — so steering is not a route to a good judge.
9. **Telling the judge an answer is its own does not help, and it shifts leniency** (Step 4). On BBEH, presenting
   someone else's answer as the judge's own makes it accept more wrong answers (58% → 70% on unsolved questions):
   claimed authorship alone is enough to trigger self-preference. On BFF-Bench the "own reply, then 'is your answer
   correct?'" version makes the two small Qwens reject a third of the right answers instead, apparently the
   "are you sure?" back-down effect; Qwen-35B is unaffected and Nemotron becomes more lenient there too.
   Turning thinking on helps a little (Qwen-9B +5 points [+0, +10] on unsolved BBEH questions).

---

## Terms

- **Judge**: a model asked whether a candidate answer is correct; it reasons briefly and ends with
  `VERDICT: CORRECT` or `VERDICT: INCORRECT`. Judges run with thinking **off**, as in the earlier pool runs.
- **Candidate**: one model's answer to a question, the thing being judged.
- **Solved (BBEH)**: the judge answered the question itself 5 times (thinking off, a separate call it never sees while
  judging); *solved* = the most common of its 5 final answers is correct (official BBEH auto-grader).
- **Solved (BFF-Bench)**: the judge answered 3 times; GLM-5.3-Flash graded each answer against the expert reference;
  *solved* = at least 2 of 3 correct.
- **Solved (RB2 Math, JudgeBench)**: from the anchoring study's single solve per Qwen judge, matched to the candidates
  by GLM-5.3-Flash.
- **TPR** (true positive rate): share of right answers the judge accepts. **FPR** (false positive rate): share of
  wrong answers it accepts.
- **Balanced accuracy**: (TPR + (1 − FPR)) / 2. 0.5 = coin flip, 1.0 = perfect. Used throughout because unsolved
  questions have far more wrong candidates than right ones, and plain accuracy would reward "reject everything".
- **κ (Cohen's kappa)**: agreement with the gold label beyond chance. 0 = chance, 1 = perfect.
- **Within-question AUROC**: over every pair of one right and one wrong answer to the *same* question, how often the
  judge scores the right one higher (score = share of 3 verdict samples saying CORRECT). 0.5 = chance. Question
  difficulty cancels out.
- **Δ (points)**: change in balanced accuracy × 100 versus the no-reference baseline, on the same candidates.
- **[a, b]**: 95% interval from resampling whole questions.

## Benchmarks

| Benchmark | What it is | Gold label | Used here |
|---|---|---|---|
| **BBEH Mini** | 460 hard reasoning puzzles (BIG-Bench Extra Hard, 23 task types) with short exact answers | official auto-grader | main testbed: 2,244 candidates = every pool model's answer that reaches a final answer; each judge skips its own model's answers |
| **BFF-Bench** | 80 two-turn finance/accounting conversations (160 questions), expert reference answers | unanimous expert label (VERDICTS) | 459 expert-labelled responses from six 2024 models |
| **RB2 Math** | RewardBench 2 Math: maths problems, 1 correct + 3 incorrect responses each | algorithmic | existing Qwen judgments only (no new runs) |
| **JudgeBench** | pairs of responses (knowledge, reasoning, maths); pick the better one | algorithmic | existing Qwen judgments only (no new runs) |

## Models

| Model | Role |
|---|---|
| Qwen3.5-4B, Qwen3.5-9B, Qwen3.6-35B-A3B | judges (thinking off) |
| Nemotron-3-Super-120B | judge (thinking off) — caveat: with thinking off it answers BBEH with no reasoning (median 8 tokens), so its "solved" label means "its gut answer is right". With its thinking-on answer as the label it shows the same gap as the Qwens (0.71 vs 0.50). |
| Kimi-K3.1-Pro (high reasoning) | the "stronger model": its own answer as a reference, and as a judge to route to. A different family from every judge. |
| GLM-5.3-Flash (high reasoning) | grader of BFF answers against the expert reference; reads verdicts that are not in the requested format |

DeepSeek-V3.1 and Nemotron-3-Nano are no longer on Tinker; gpt-oss is not used. Every generation got the whole context
window as its budget (64K for the judges, 262K for Kimi/GLM); outputs that still hit the limit were rerun from scratch
up to 3 times.

---

## Step 1 — How judging quality depends on whether the judge can solve the question

### 1a. Across benchmarks (no reference)

Balanced accuracy (JudgeBench: plain accuracy of picking the better response).

| Benchmark | Judge | solved (n) | **not solved** (n) | gap (points) |
|---|---|---|---|---|
| BBEH | Qwen3.5-4B | 0.68 (845) | **0.55** (1,187) | +13 |
| BBEH | Qwen3.5-9B | 0.69 (1,036) | **0.51** (982) | +17 |
| BBEH | Qwen3.6-35B | 0.77 (1,194) | **0.49** (818) | +28 |
| BBEH | Nemotron-Super* | 0.65 (462) | **0.61** (1,546) | +4 |
| BBEH | Kimi-K3.1-Pro (reasoning) | 0.93 (1,368) | **0.63** (876) | +30 |
| BFF-Bench | Qwen3.5-4B | 0.73 (239) | **0.68** (217) | +5 |
| BFF-Bench | Qwen3.5-9B | 0.77 (293) | **0.72** (163) | +5 |
| BFF-Bench | Qwen3.6-35B | 0.82 (333) | **0.62** (123) | +20 |
| BFF-Bench | Nemotron-Super | 0.74 (316) | **0.70** (140) | +3 |
| BFF-Bench | Kimi-K3.1-Pro (reasoning) | 0.85 (384) | **0.48** (72) | +37 |
| RB2 Math | Qwen3.5-4B | 0.79 (624) | **0.73** (104) | +6 |
| RB2 Math | Qwen3.5-9B | 0.83 (612) | **0.72** (116) | +10 |
| RB2 Math | Qwen3.6-35B | 0.91 (600) | **0.74** (128) | +17 |
| JudgeBench | Qwen3.5-4B | 0.86 (361) | **0.68** (186) | +18 |
| JudgeBench | Qwen3.5-9B | 0.86 (437) | **0.62** (110) | +25 |
| JudgeBench | Qwen3.6-35B | 0.97 (454) | **0.54** (93) | +43 |

\*Nemotron-Super's BBEH "solved" is a no-reasoning answer (see Models). With its thinking-on answer as the label it
shows a clear gap: 0.71 vs 0.50.

**Plain reading:** every judge on every benchmark judges worse on the questions it cannot solve. The drop is largest
for the strongest judges, and on BBEH the Qwens fall to a coin flip.

### 1b. BBEH in detail (no reference)

| Judge | Questions | right / wrong answers | TPR | FPR | Balanced acc. [95% CI] | κ | Within-Q AUROC |
|---|---|---|---|---|---|---|---|
| Qwen3.5-4B | solved | 581 / 264 | 0.83 | 0.46 | 0.68 [0.65, 0.72] | 0.37 | 0.71 |
| Qwen3.5-4B | **not solved** | 389 / 798 | 0.64 | 0.54 | **0.55** [0.51, 0.58] | 0.09 | 0.58 |
| Qwen3.5-9B | solved | 716 / 320 | 0.90 | 0.52 | 0.69 [0.65, 0.72] | 0.41 | 0.74 |
| Qwen3.5-9B | **not solved** | 236 / 745 | 0.69 | 0.66 | **0.51** [0.47, 0.56] | 0.01 | 0.58 |
| Qwen3.6-35B | solved | 797 / 397 | 0.92 | 0.38 | 0.77 [0.74, 0.81] | 0.57 | 0.84 |
| Qwen3.6-35B | **not solved** | 162 / 656 | 0.62 | 0.63 | **0.49** [0.44, 0.55] | −0.01 | 0.50 |
| Kimi-K3.1-Pro | solved | 860 / 508 | 0.98 | 0.13 | 0.93 [0.90, 0.95] | 0.87 | 0.92 |
| Kimi-K3.1-Pro | **not solved** | 217 / 659 | 0.76 | 0.50 | **0.63** [0.57, 0.69] | 0.18 | 0.58 |

It is graded, not all-or-nothing. Balanced accuracy by how many of its own 5 answers were right:

| Judge | 0 of 5 | 1–2 of 5 | 3–4 of 5 | 5 of 5 |
|---|---|---|---|---|
| Qwen3.5-4B | 0.52 | 0.60 | 0.67 | 0.75 |
| Qwen3.5-9B | 0.44 | 0.60 | 0.66 | 0.75 |
| Qwen3.6-35B | **0.39** | 0.62 | 0.72 | 0.83 |

On questions the 35B never gets right in 5 tries, it is *worse* than a coin flip.

### 1c. Is it solving ability, or just that unsolved questions are harder?

Both. Outside difficulty = share of the 8 earlier pool models that answered the question correctly.

| Outside difficulty (pool models right) | judge solved it | judge did not |
|---|---|---|
| 0–1 of 8 (hardest) | 0.65 | 0.44 |
| 2–3 of 8 | 0.65 | 0.56 |
| 4–5 of 8 | 0.70 | 0.62 |
| 6–8 of 8 (easiest) | 0.77 | 0.72 |

At every difficulty level, solving helps. A linear fit with both (balanced weights) gives an effect of solving of +9
[+4, +14] (4B), +13 [+8, +19] (9B), +27 [+19, +34] (35B) points (Nemotron −2, consistent with its no-reasoning solve
label); going from hardest to easiest adds +32 to +51.

The strongest control holds the answer itself fixed: the same candidate judged by a judge that solved the question and
another that did not, with an intercept per candidate and per judge. **Solving adds +6 points [+3, +10]** to the chance
of a correct verdict (4,547 judgments; Qwens only +8).

Using the thinking-on solve (1 sample, from the pool runs) as the definition of solved gives the same split (Qwens
0.69–0.77 vs 0.51–0.54); the two labels agree on 75–78% of questions.

### 1d. On unsolved questions, what does the judge accept?

| Judge | right answers | wrong answers equal to its own (wrong) answer | other wrong answers |
|---|---|---|---|
| Qwen3.5-4B | 0.64 | 0.68 | 0.46 |
| Qwen3.5-9B | 0.69 | **0.85** | 0.54 |
| Qwen3.6-35B | 0.62 | **0.90** | 0.44 |

The cleanest test of "can it verify beyond solving": answers that differ from **all 5** of the judge's own attempts, on
questions it did not solve.

| Judge | right accepted | wrong accepted | gap (points) [95% CI] |
|---|---|---|---|
| Qwen3.5-4B | 0.59 | 0.43 | +16 [+6, +27] |
| Qwen3.5-9B | 0.57 | 0.49 | +8 [−6, +21] |
| Qwen3.6-35B | 0.42 | 0.37 | +5 [−10, +20] |

**Plain reading:** when the judge holds a wrong belief, it approves answers that share it. Faced with answers it never
produced, the 9B and 35B cannot reliably tell right from wrong; the 4B has a small, real signal.

---

## Step 2 — Interventions on unsolved questions

### 2a. BBEH, pooled over the 4 judges

Balanced accuracy; Δ in points vs no reference on the same candidates. "Rules" use no extra LLM call at judging time.

| Method | solved | Δ | **not solved** | Δ [95% CI] |
|---|---|---|---|---|
| No reference (baseline) | 0.71 | — | 0.55 | — |
| **Official answer as reference** (ceiling) | 0.93 | +22 | **0.95** | **+40** [+37, +42] |
| **Stronger model's answer as reference** (Kimi's final answer) | 0.86 | +15 | **0.76** | **+20** [+17, +24] |
| Rule: accept iff it matches the stronger model's answer | 0.86 | +15 | 0.78 | +23 [+18, +27] |
| Route everything to the stronger judge (Kimi) | 0.86 | +15 | 0.77 | +22 [+18, +25] |
| Defer to the Kimi judge when the judge's own 5 answers disagree (<4 of 5 agree) | 0.80 | +9 | 0.71 | +15 [+12, +18] |
| Use the stronger model's reference only when own answers disagree | 0.80 | +9 | 0.70 | +15 [+12, +18] |
| Rule: match the most common answer among all candidates | 0.82 | +11 | 0.65 | +10 [+6, +13] |
| Rule: match the most common answer of the 4 weak judges (20 attempts) | 0.92 | +21 | 0.63 | +7 [+3, +12] |
| Majority vote of the 4 judges | 0.77 | +6 | 0.59 | +4 [+2, +6] |
| Verify-the-steps prompt (don't re-solve; check conditions and each step) | 0.74 | +3 | 0.54 | −2 [−3, +0] |
| Rule: solve-and-compare only when own 5 answers agree (≥4/5), else own verdict | 0.85 | +14 | 0.51 | −4 [−6, −2] |
| **Own earlier answer as reference** | 0.87 | +16 | **0.39** | **−17** [−19, −14] |
| Rule: solve-and-compare (accept iff it matches own majority answer) | 1.00 | +29 | 0.33 | −22 [−25, −20] |

Per judge, the stronger model's reference adds +17 to +21 points on unsolved questions (4B 0.76, 9B 0.73, 35B 0.67,
Nemotron 0.80); the own-answer reference costs −16 to −17.

**When the stronger model's answer is itself wrong** (Kimi solves 63% of BBEH), the reference stops helping or hurts:

| Judge, unsolved questions | Kimi right: none → Kimi reference | Kimi wrong: none → Kimi reference |
|---|---|---|
| Qwen3.5-4B | 0.58 → 0.88 | 0.59 → 0.58 |
| Qwen3.5-9B | 0.56 → 0.92 | 0.50 → 0.41 |
| Qwen3.6-35B | 0.58 → 0.94 | 0.43 → 0.34 |

So the gain from a stronger model's reference is exactly the stronger model's own solving ability, passed on. The judge
adds little checking of its own.

### 2b. BFF-Bench (finance, expert labels), pooled over the 4 judges

| Method | solved | Δ | **not solved** | Δ [95% CI] |
|---|---|---|---|---|
| No reference (baseline) | 0.77 | — | 0.69 | — |
| **Expert reference** | 0.92 | +15 | **0.85** | **+15** [+10, +20] |
| Stronger model's answer as reference | 0.88 | +11 | 0.77 | +8 [+2, +14] |
| Route to the stronger judge (Kimi) | 0.84 | +7 | 0.75 | +5 [−1, +12] |
| Verify-the-steps prompt | 0.83 | +6 | 0.70 | +1 [−4, +6] |
| **Own earlier answer as reference** | 0.86 | +8 | **0.59** | **−10** [−17, −4] |

Same pattern as BBEH, with smaller numbers because the judges already do better on unsolved BFF questions. On BFF, Kimi
gets 88% of questions right, but its judging on the 12% it gets wrong is at chance (0.48).

### 2c. Cascades: decide cheaply when it is safe, ask the stronger judge otherwise

Each rule decides, without gold labels, which candidates go to Kimi. Balanced accuracy over all candidates.

| Judge | cheap judge alone | Kimi alone | route if own 5 answers disagree | route if the 3 verdict votes split, or own answer ≠ most common candidate answer |
|---|---|---|---|---|
| Qwen3.5-4B | 0.62 | 0.80 | 0.74 (56% routed) | 0.76 (68% routed) |
| Qwen3.5-9B | 0.61 | 0.80 | 0.73 (47%) | 0.75 (54%) |
| Qwen3.6-35B | 0.67 | 0.81 | 0.75 (41%) | 0.78 (49%) |

Routing about half the candidates closes 55–80% of the gap to Kimi alone.

### 2d. Signals that did little

- **Self-consistency as a warning light.** How often the judge's own 5 answers agree predicts whether it solved the
  question (AUROC 0.68–0.72), but the baseline verdict is only a little better when they all agree (0.61–0.68) than
  when they disagree (0.57–0.64). Confidently wrong beliefs are common, which is why solve-and-compare fails.
- **Difficulty-aware thresholds.** Choosing the vote threshold separately for each level of own agreement
  (cross-fitted by question): unsolved 0.52 → 0.57 (4B), 0.49 → 0.52 (9B), 0.49 → 0.50 (35B); no change on solved.
- **Hidden-state probe as the verdict** (the anchoring study's position-A captures, before the judge writes anything;
  probe trained with whole questions held out):

| Judge | Benchmark | questions | spoken verdict: within-Q AUROC | probe: within-Q AUROC | spoken: balanced acc. | probe: balanced acc. (same leniency) |
|---|---|---|---|---|---|---|
| Qwen3.5-4B | BBEH | not solved | 0.53 | 0.58 | 0.47 | 0.66 |
| Qwen3.5-9B | BBEH | not solved | 0.47 | 0.54 | 0.51 | 0.69 |
| Qwen3.5-4B | RB2 Math | not solved | 0.73 | 0.79 | 0.73 | 0.63 |
| Qwen3.5-9B | RB2 Math | not solved | 0.72 | **0.85** | 0.72 | 0.71 |
| Qwen3.5-9B | JudgeBench | not solved | 0.58 (verdict at A) | 0.57 | 0.58 | 0.55 |

  On BBEH the probe's balanced-accuracy gain is mostly it recognising *hard questions* (where most candidates are
  wrong), not telling answers to the same question apart (+5 to +7 within a question, on only 37–57 pairs). The one
  clear item-level gain is Qwen-9B on RB2 Math (0.85 vs 0.72), a benchmark where the judge's own checking already partly works.

### 2e. Cost (tokens per judgment, BBEH)

| Condition | mean input | mean output (Qwens) |
|---|---|---|
| No reference | ~2,100 | 1,900–2,600 (×3 samples) |
| Official / stronger-model reference | ~2,100 | 1,150–2,000 |
| Own answer as reference | ~6,000 | 480–920 |
| Verify-the-steps prompt | ~2,200 | 3,100–3,600 |
| Kimi as judge | ~2,000 | 1,300 (including its thinking) |

A reference makes judging *cheaper* (shorter reasoning). The stronger-model reference costs one Kimi solve per
question (460 calls), shared by every candidate and every judge.

---

## Step 3 — Inside the model: are "solving" and "judging" the same signal, and can steering help?

**Question.** Could a weak model be steered into a good judge on questions it cannot solve? That depends on how the
model represents "this answer is right" when it *writes* an answer versus when it *grades* one.

**Design.** Qwen3.5-9B and Llama-3.1-8B (open weights, on an H100; thinking off). The **same answer text** is shown in
three roles, so only the role changes, not the content:

| Role | What the model sees | Hidden state taken at |
|---|---|---|
| **Judge** | "Grade this answer" prompt containing someone else's answer | the token after `VERDICT:` |
| **Generate** | the question, then the answer as *its own* response | the last token of the answer |
| **Self-check** | the question, the answer as its own, then "Is your answer correct?" | the token after `VERDICT:` |

Answers: the 2,244 BBEH pool answers and the 732 RB2 Math responses (the model's own pool answers excluded). Every 2nd
layer is kept. Probes are logistic regressions with whole questions held out. Directions are "right minus wrong"
averages of question-centred states (each answer minus its question's average), so only differences between answers
to the same question count.

### 3a. Each role carries some signal, more than the spoken verdict uses

Within-question AUROC (best layer per role):

| Model | Benchmark | Questions | judge probe | generate probe | self-check probe | spoken verdict (judge) |
|---|---|---|---|---|---|---|
| Qwen-9B | BBEH | not solved | 0.63 | 0.64 | 0.67 | **0.50** |
| Qwen-9B | BBEH | solved | 0.68 | 0.77 | 0.75 | 0.68 |
| Qwen-9B | RB2 Math | not solved | 0.82 | 0.74 | 0.75 | 0.78 |
| Llama-8B | BBEH | not solved | 0.69 | 0.67 | 0.70 | **0.53** |
| Llama-8B | RB2 Math | not solved | 0.75 | 0.74 | 0.81 | 0.72 |

On BBEH questions the model cannot solve, its hidden state ranks answers at 0.63–0.70 while its verdict is at chance.

### 3b. But it is a different signal in each role

Cosine between the "right minus wrong" directions (1 = same direction, 0 = unrelated; two random directions ≈ 0.016).
Split-half ceiling = cosine between the same role's direction from two random halves of the questions, i.e. the
highest value noise allows.

| Model | Benchmark | judge · generate | judge · self-check | ceiling (judge / generate) |
|---|---|---|---|---|
| Qwen-9B | BBEH | **−0.05** | 0.76 | 0.94 / 0.64 |
| Qwen-9B | RB2 Math | **0.05** | 0.93 | 0.99 / 0.82 |
| Llama-8B | BBEH | **0.04** | 0.67 | 0.82 / 0.80 |
| Llama-8B | RB2 Math | **0.11** | 0.64 | 0.98 / 0.70 |

The same holds at every layer (judge · generate between −0.05 and 0.16 throughout; table in
`out_dirs/dirs_tables_<model>.md`).

A probe trained in one role and tested in another (within-question AUROC on unsolved questions):

| Model | Benchmark | judge → judge | generate → judge | judge → generate | self-check → judge |
|---|---|---|---|---|---|
| Qwen-9B | BBEH | 0.63 | 0.51 | 0.48 | 0.57 |
| Qwen-9B | RB2 Math | 0.82 | 0.39 | 0.67 | 0.72 |
| Llama-8B | BBEH | 0.69 | 0.54 | 0.44 | 0.66 |
| Llama-8B | RB2 Math | 0.75 | 0.65 | 0.56 | 0.60 |

**Plain reading:** "judge" and "self-check" share a direction — they are the same *task* (give a verdict), even though
self-check is about the model's own answer. The state after *writing* an answer encodes correctness along an unrelated
direction, and a reader trained on one does not work on the other. So the model has no single "this is right" signal
that solving and judging share.

Two smaller results: before writing anything, the model's state predicts whether it will solve the question
(AUROC 0.72 Qwen, 0.74 Llama on BBEH); and on its *own* five answers to a question, Qwen-9B's state after writing ranks
its right answers above its wrong ones at 0.68 (its spoken self-check: 0.61; the judge-role probe applied there: 0.54).

### 3c. Steering the judge

On the judge prompt, at the verdict position, the hidden state is edited along a direction learned on the *other*
half of the questions, and the verdict is read again. Two edits: **shift** = add the same push to every answer (±4,
±8 standard deviations of the projection); **stretch** = multiply each answer's distance from the average along the
direction (×2, ×4, ×11), which can only help if the direction separates answers. Layers: where the question-centred
judge direction carries the most within-question signal on unsolved BBEH questions (Qwen 26, Llama 14).

Within-question AUROC of the verdict on BBEH questions the model did **not** solve (accept rates of right / wrong
answers in brackets):

| Model | no edit | generate direction, best edit | judge direction, shift +8 | judge direction, stretch ×11 | random direction, stretch ×11 |
|---|---|---|---|---|---|
| Qwen-9B | 0.50 (0.26 / 0.32) | 0.51 | 0.49 (0.64 / 0.59) | 0.51 (0.37 / 0.42) | 0.50 |
| Llama-8B | 0.53 (0.53 / 0.62) | 0.55 | 0.56 (0.69 / 0.73) | **0.60** (0.56 / 0.56) | 0.52 |

- **Generate direction**: no effect on the judge in either model, at any strength, on BBEH or RB2 Math.
- **Shift along the judge direction**: a leniency dial; right and wrong answers move together (as in the anchoring
  study).
- **Stretch along the judge direction**: Llama +7 points [+1, +14] on unsolved questions, no change on solved ones
  (+1 [−1, +5]); Qwen +1 [−7, +9]. On RB2 Math it gives nothing in either model.

**Plain reading:** a weak judge cannot borrow what it knows from *solving*, because that knowledge sits on a
different axis than the one it reads when judging. Its judge-role state does hold a little unused signal, and stretching
it can recover part of that in Llama (whose spoken verdict throws away the most). The ceiling is low: at best the
probe's 0.63–0.69, far from the 0.95 a reference answer gives.

---

## Step 4 — "Your own answer" framing, and letting the judge think

**Why.** In Step 3 the self-check role (the answer shown as the model's own, then "is your answer correct?") held a
little more signal than the judge role on unsolved BBEH questions (0.67 vs 0.63). Can a prompt that presents the
candidate as the judge's own answer put that to use? The candidate is still someone else's answer; only the framing
changes.

| Condition | What the judge sees |
|---|---|
| No framing (baseline) | "You are grading an AI assistant's answer…" |
| Shown as its own reply | the question, the candidate as *its own* reply, then "Is your final answer above correct?" |
| "Here is the answer you gave earlier" | one prompt saying the candidate is the answer it gave earlier |

Cells: balanced accuracy (share of right answers accepted / share of wrong answers accepted). Δ vs the no-framing
baseline with thinking off, same answers, 95% interval.

**BBEH, thinking off, 4 judges pooled**

| Framing | solved | not solved | Δ not solved |
|---|---|---|---|
| No framing | 0.71 (0.88 / 0.46) | 0.55 (0.68 / 0.58) | — |
| Shown as its own reply | 0.61 (0.87 / **0.65**) | 0.52 (0.74 / **0.70**) | −3 [−5, −1] |
| "The answer you gave earlier" | 0.69 (0.88 / 0.50) | 0.53 (0.68 / 0.61) | −2 [−4, 0] |

**BBEH, Qwen3.5-9B with thinking on** (one sample each)

| Condition | solved | not solved | Δ not solved vs thinking off |
|---|---|---|---|
| Thinking off, no framing | 0.69 (0.90 / 0.52) | 0.51 (0.69 / 0.66) | — |
| Thinking on, no framing | 0.74 (0.95 / 0.47) | 0.56 (0.75 / 0.63) | **+5** [0, +10] |
| Thinking on, shown as its own reply | 0.72 (0.95 / 0.51) | 0.55 (0.78 / 0.68) | +4 [0, +9] |
| Thinking on, "the answer you gave earlier" | 0.76 (0.95 / 0.42) | 0.55 (0.76 / 0.66) | +4 [0, +8] |

**BFF-Bench**

| Judges | Condition | solved | not solved | Δ not solved |
|---|---|---|---|---|
| 4 judges, thinking off | No framing | 0.77 (0.85 / 0.30) | 0.69 (0.67 / 0.29) | — |
| 4 judges, thinking off | Shown as its own reply | 0.78 (0.77 / 0.20) | 0.63 (**0.48** / 0.23) | −6 [−11, −1] |
| 4 judges, thinking off | "The answer you gave earlier" | 0.78 (0.85 / 0.29) | 0.69 (0.68 / 0.30) | 0 [−4, +4] |
| Qwen3.5-9B, thinking on | No framing | 0.86 (0.84 / 0.12) | 0.77 (0.68 / 0.15) | +4 [−4, +12] (vs thinking off) |

**Plain reading:**
- The framing never helps. The extra signal the self-check role carries inside the model does not reach the verdict
  through a prompt.
- What the framing does change is **leniency**. On BBEH, calling someone else's answer "yours" makes the judge accept
  far more wrong answers (58% → 70% on unsolved, 46% → 65% on solved questions). Self-preference does not need the
  judge to recognise its own text: being *told* it wrote the answer is enough.
- On BFF-Bench, the conversational version (its "own" reply followed by the user asking "Is your final response above
  correct?") makes **Qwen-4B and Qwen-9B much stricter**: they accept 58% and 66% of right answers instead of 82–83%.
  Qwen-35B is unchanged, Nemotron becomes *more* lenient (40% → 50% of wrong answers accepted), and the single-prompt
  "the answer you gave earlier" version causes no strictness for anyone. Reading Qwen-4B's 68 newly rejected right
  answers, it invents errors to correct ("double entries apply to entities, not individuals"; a made-up "step-up in
  basis"; "Wait, let's re-verify the numbers"). This looks like the known "are you sure?" effect (models back down
  when a user questions their answer; Sharma et al. 2023, Laban et al. 2023), not ownership itself. Separating the two
  would need a framing that questions the answer without claiming it is the judge's own.
- Letting Qwen-9B think helps a little on questions it cannot solve (+5 on BBEH, +4 on BFF-Bench, the latter not
  significant), and the framing adds nothing on top.

---

## What this means

- A judge cannot be prompted into judging what it cannot solve. Verification prompts, juries of similar models and
  difficulty-aware thresholds each move unsolved-question accuracy by at most a few points.
- What works is getting the answer from somewhere else: an expert or official reference (best), a stronger model's
  answer, or the stronger model as judge. On BBEH the gain is bounded by the stronger model's own accuracy.
- Never give the judge its own answer as a reference on hard questions: it turns a coin flip into a systematic
  mistake (−17 points).
- A practical recipe: a cheap judge plus a label-free trigger (its own attempts disagree, its verdict votes split, or its
  answer differs from the most common candidate answer) that escalates about half the items to a stronger judge.
- Steering is not the fix: solving knowledge lives on a different axis from judging, and the judge's own unused signal
  is small.
- Don't tell a judge an answer is its own: it makes the judge more lenient without making it more accurate, and a
  follow-up "is your answer correct?" turn can make small models back down from right answers.

## Caveats

- **Nemotron-Super**: its thinking-off BBEH answers have no reasoning, so its "solved" label is weak (by that label its
  gap is only +4; by its thinking-on answer, +21). Pooled tables include it.
- **Candidates**: BBEH answers that never reach a final answer (cut off at the earlier pool's 16K cap) are trivially
  wrong and were dropped.
- **Cut-offs left**: 11 (4B) and 4 (9B) of 2,300 BBEH solve samples, and 7 of ~50,000 judgments, still hit the 64K
  limit after 3 fresh reruns; they count as no answer / reject.
- **BFF solve labels** are GLM-5.3-Flash grades against the expert reference (proxy labels), and BFF unsolved sets are
  small (72–217 items per judge).
- **RB2 Math / JudgeBench** results reuse the anchoring study's single-sample solves and existing judgments; no
  interventions were run there.
- **Probe**: the best layer was chosen by the anchoring study on all items (slight selection bias); BBEH probe items are
  the older 2-per-question candidate set, so within-question pairs are few.
- **Stronger model**: one Kimi answer per question; "strong reference" shows the judge only Kimi's final answer line.
- **Step 3**: steering edits one position (the verdict token) and reads the verdict immediately, without letting the
  judge reason; directions are linear and one per layer. A first steering run used directions from uncentred states,
  which on BBEH mostly encoded question difficulty (no within-question signal); the reported BBEH results use
  question-centred directions. Llama's "solved" labels on BBEH come from one answer per question (it solves 10%).

## Files

All in `experiments/beyond_capability/`:

| File | What it does |
|---|---|
| `bc_common.py` | models, prompts (judge, reference, verify), answer normalisation |
| `bc_jobs.py`, `modal_app.py` | Tinker jobs on Modal: `solve`, `judge`, `bff_solve`, `bff_grade`, `bff_judge`, `fill` |
| `build_inputs.py`, `build_bff_inputs.py` | BBEH candidates / BFF items and questions (`inputs/`) |
| `characterise_existing.py` | RB2 Math + JudgeBench solved-split rows from the anchoring study's outputs |
| `analyze_bbeh.py`, `analyze_bff.py`, `cross_bench.py`, `probe_split.py` | all tables: `out/bbeh_tables.md`, `out/bff_tables.md`, `out/cross_bench.md`, `out/probe_split.md` |
| `status.sh` | pull outputs from the Modal volume (`dynamic-llm-juries-results:/beyond_capability`) into `out/` |
| `dir_build.py` | Step 3 inputs: the same answers in judge / generate / self-check roles (`inputs/dir_items*.jsonl.gz`) |
| `dir_capture.py`, `dir_modal.py` | Step 3 on an H100: hidden-state capture and steering (volume `beyond_capability_dirs/`) |
| `dir_analyze.py`, `dir_steer_prep.py`, `dir_steer_analyze.py` | Step 3 tables: `out_dirs/dirs_tables_<model>.md`, `out_dirs/steer_tables_<model>.md` |
| `analyze_framing.py` | Step 4 tables: `out/framing_tables.md` |
| `azure/` | steering during thinking-on reasoning on a plain GPU machine: `prep_think.py` (directions, items), `cannon_setup.sh` and `cannon_steer.sh` (Harvard Cannon Slurm jobs), `run_steergen.sh` (any GPU machine) |
