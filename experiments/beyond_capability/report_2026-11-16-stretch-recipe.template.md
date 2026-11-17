# Making Small LLM Judges Rank Better: Find the Correctness Direction, Pick the Layer the Verdict Reads, Stretch

*November 16, 2026*

::: summary
## Summary

- **Question.** Small open LLM judges often know more about whether an answer is right than their verdict shows. Can we turn that hidden knowledge into a better judge, reliably, across judges and benchmarks? And does it help on questions the judge cannot solve itself?
- **A recipe that works across judges and benchmarks.** (1) Check for a gap between what the judge's hidden state knows and what its verdict says. (2) Shortlist layers by how well the direction ranks answers. (3) Keep only layers where pushing along the direction actually moves the verdict. (4) Stretch there. With the layer rule fixed in advance, 14 of 21 judge–benchmark pairs have a gap; in **11 of the 12 where a layer responds, ranking improves by +2 to +8 points** (6 judges from 3 B to 8 B; MMLU-Redux, MATH, BBEH). A random direction does nothing.
- **Solved vs not solved.** Gains are largest where the judge can solve the question (Llama-3.1-8B on MMLU: +7.9, and +5.9 even within one answering model's answers). On questions it cannot solve the raw gains are also large (up to +9), but mostly come from recognising *which model wrote the answer*. Comparing only right vs wrong answers written by the **same** model, a smaller real gain remains on **reasoning benchmarks**: Llama-3.1-8B gains **+5.0 [+1.8, +8.5]** on 256 MATH questions it failed in all 9 of its own tries, Granite +3 on BBEH questions it can't solve, and small judges +2 to +3 with a gentle stretch; pooled over judges, +1 to +1.5 on MATH and BBEH. On **MMLU** (recalling facts) there is little or none. Checking a worked answer is easier than solving the problem; checking a recalled fact is not.
- **Why it fails when it fails, three causes:** (a) the layer is too early (the verdict rebuilds its decision from later layers and ignores an edit there); (b) the verdict reads the direction backwards (Llama-3.2-3B and, in the fresh test, Qwen2.5-7B distrust the most accurate answering model on MMLU); (c) the verdict is saturated (Mistral says CORRECT to 99% of answers, so pushes move its score but never its decision). The push test fixes (a); measuring the response on the verdict score instead of the accept rate fixes (c); (b) has no fix at those layers.
- **Most of the hidden gap is "which model wrote this answer"** (75–88% of the direction's spread within a question), which is why gains shrink on same-model pairs.
- **Strength:** ×11 is a safe default; judges whose verdict score responds strongly need a gentler stretch (×4), weakly responding ones a stronger one (×21).
- **Baseline: read the direction directly.** It ranks better than the stretch on the full pool (+5) and on same-model pairs the judge cannot solve (+1 to +2); adding it to the verdict score does about as well. Exception: Llama-3.1-8B on MATH, where the stretch is best. The stretch is one way, not the best way, to use the signal.
- **Fresh preregistered test on two new judges: half held.** Llama-3.2-1B gains +5.4 (MMLU) and +7.9 (MATH), and on MATH questions it cannot solve (it solves 16 of 602) its same-model gain is +2 to +4 at every strength. Both misses are on BBEH (in both, the rule picked between layers whose *knows* differ by less than split noise, and a neighbouring layer the verdict reads more strongly gains +4.6 and +6.4).
:::

## 1. Setup

*Inside the Unfair Judge* ([Xu et al., 2026](https://arxiv.org/abs/2607.11871)) shows that an LLM judge's biases live in a few directions of its hidden states and can be steered. Building on an insight from Phaedrus on that paper, we look for a direction that tracks whether an answer is *actually right* and stretch it.

- **Judges** (thinking off): Llama-3.1-8B, Llama-3.2-3B, Qwen3.5-9B, Qwen3.5-4B, Phi-4-mini, Mistral-7B, Granite-3.3-8B.
- **Benchmarks:** MMLU-Redux (multiple choice, expert-checked key; 3,496 answers to 922 questions), MATH (competition math, graded by GLM-5.3-Flash; 2,384 answers to 602 questions), BBEH (hard reasoning; 2,244 answers to 447 questions). Answers come from other, mostly stronger models; the judge sees one question and one answer and replies starting with `VERDICT:`.
- **Solved / not solved:** whether the judge answers the question correctly itself (its own answer, thinking off).
- **Verdict score:** log P(CORRECT) − log P(INCORRECT) at the word after `VERDICT:`.
- **Ranking:** for every pair of one right and one wrong answer to the same question, 1 if the right one gets the higher verdict score, ½ for a tie, 0 otherwise; averaged. 0.50 is chance. Unlike accuracy, ranking cannot improve by the judge just becoming stricter.
- **Gain:** ranking after the stretch minus before, ×100, with 95% intervals from resampling questions.
- **Same-model pairs:** only pairs where the right and the wrong answer were written by the same model. This removes the clue "this answer came from the stronger model".

## 2. The recipe

1. **Capture.** One forward pass per answer; save the hidden state at `VERDICT:` at every other layer.
2. **Direction and gap.** At each layer, subtract each question's average state, then take (average state of right answers) − (average state of wrong answers), learned on half the questions and scored on the other half. *Knows* = ranking from the position along this direction. *Says* = ranking from the verdict score. **Gap** = best layer's *knows* − *says*. Stop if the gap is 5 points or less: there is nothing to recover.
3. **Push test (no labels).** On 400 answers, push each answer −8 and +8 standard deviations along the direction at each layer and record how often the judge then says CORRECT. A layer *responds* if the accept rate rises by at least 10 points.
4. **Pick the layer:** among responding layers, the one whose direction ranks best.
5. **Stretch:** at that layer, multiply each answer's distance from the average along the direction (×11 default), leaving everything else unchanged.

Steps 3–4 were fixed in a written rule before any of the 15 new pairs was run (`out_allpairs/RULE.md`). Only the chosen layer is stretched, so the layer cannot be picked by its gain. Cost: one capture pass plus a few edited re-reads of the last token per answer, under an H100-hour per pair.

## 3. Results across judges and benchmarks

![Ranking gain from stretching ×11 at the rule's layer, every judge × benchmark pair with a gap](out_allpairs/recipe_gains.png)

TABLE_MAIN

- **Every judge with a gap gains somewhere.** The ×11 gain is significant in 11 of the 12 pairs where a layer responds (not Mistral on MATH, +2.1), and in one where none does (Llama-3.2-3B on MMLU, at the fallback layer). The random direction stays within ±1.
- **Small judges benefit too:** Llama-3.2-3B (+4 to +6), Phi-4-mini (+4 to +7), Qwen3.5-4B on BBEH (+5).
- **No gap, no gain:** Qwen3.5-9B has no gap on any benchmark; its verdict already uses what the direction knows.
- **The layer check matters.** Earlier we steered Llama-3.1-8B on MATH at layer 14 (chosen by *knows* alone) and Phi-4-mini on MMLU at layer 14: gains of +1.5 and +1.2. The rule moves both to layer 16, where the verdict listens: +8.2 and +3.8.

## 4. Beyond the judge's ability: the same-model test

The not-solved gains in section 3 mostly vanish on same-model pairs of the original answer pool, because most of what the direction knows is which model wrote the answer, and that pool has few same-model pairs. To test this with enough power we built answer sets with many right *and* wrong answers from the same model per question: on MMLU and MATH, Qwen3.5-4B answered each question Llama-3.1-8B cannot solve 12 more times; on BBEH, four answering models each contributed up to 2 right and 2 wrong of their existing 5 samples. That is 2,400–3,000 same-model pairs per benchmark. Each judge is stretched at the rule's layer, with the direction learned on the original answers to the other half of the questions. "Own unsolved" = questions the judge itself got wrong.

TABLE_SM

- **MATH: real checking beyond ability, strongest for Llama-3.1-8B.** It gains at every strength, including +5.0 [+1.8, +8.5] on the 256 questions it failed in all 9 of its own attempts. The smaller judges gain only with a gentle stretch (×4: Llama-3.2-3B +2.8, Phi-4-mini +1.7); ×11–×21 overshoots and hurts them.
- **BBEH: a smaller real gain, clearest for Granite** (+3.1 to +3.3 on its own unsolved questions) and Llama-3.2-3B (+2.2 at ×4); pooled over five judges +1.0 to +1.3.
- **MMLU: little or none.** Llama-3.1-8B and Granite gain nothing; Phi-4-mini +1.6 at ×4. Recognising a right multiple-choice answer needs the fact; a worked math or reasoning answer can be checked step by step.
- The random direction stays within ±0.4 everywhere.

## 5. Why it fails when it fails

DIAG

## 6. Choosing the strength

SENS

## 7. A fresh test of the score-based rule

The score-based rule (section 5) was written down before running two judges new to this study, a deliberately weak one (Llama-3.2-1B) and a stronger one (Qwen2.5-7B), on all three benchmarks (`out_allpairs/RULE_v2.md`). Prediction: wherever there is a gap and a responding layer, the ×11 gain is above 0 and the random direction stays within ±1.

FRESH_TABLE

- **Held:** Llama-3.2-1B gains +5.4 on MMLU and +7.9 on MATH; the random direction stays within ±1.
- **Checking beyond ability replicates on MATH.** On same-model pairs from MATH questions the 1B cannot solve (it solves 16 of 602), the gain is +2.2 / +3.7 / +3.5 at ×4 / ×11 / ×21, all with intervals above 0. MMLU stays at about 0, as predicted.
- **Qwen2.5-7B on MMLU: no layer responds** (best sensitivity 0.047), with the same signature as Llama-3.2-3B: it accepts 63% of Nemotron's answers against 90–95% of the Qwens', and its verdict runs against the direction at layers 2–18 (correlation −0.4 to −0.5). Stretching at the fallback layer still gains +2.5. Its MATH gap is +5.0, so MATH was not stretched.
- **Both misses are on BBEH.** The 1B's gap is +7.9 on the rule's split but +5.9 averaged over 20 splits (*knows* 0.55): little to recover. Qwen2.5-7B has a real gap (+8.5 over 20 splits). In both, *knows* is flat across the responding layers to within split noise, and the rule took the layer where the verdict only starts to respond. A full sweep shows a neighbouring layer the verdict reads more strongly does gain: +6.4 [+3.3, +10.3] for the 1B (layer 14) and +4.6 [+1.2, +8.2] for Qwen2.5-7B (layer 22). *Lesson (not yet tested):* average *knows* over several splits and, among near-ties, prefer the layer with the stronger response.

## 8. Baseline: read the direction directly

With labels and hidden states in hand, one can skip the stretch and rank answers by their position along the direction, or add that position to the verdict score (each scaled by its spread within a question; nothing tuned).

TABLE_DIRECT

- **Full answer pool: the direction alone beats the stretch by about 5 points;** the stretch passes on about 40% of the gap. Most of that lead is who wrote the answer: on same-model pairs it shrinks to +1 to +2.
- **Same-model pairs the judge cannot solve: the direction beats the verdict on MATH and BBEH, by more than the stretch does.** The checking signal is real; the stretch carries part of it. On MMLU every method stays at or below chance (rankings 44–51).
- **Exception, the strongest case:** Llama-3.1-8B on MATH questions it failed 9 of 9 times, where the stretch (+5.0) and the sum (+4.7) beat the direction (+3.1); its verdict holds checking information the direction lacks. For ranking alone, the direction or the sum is simpler; the stretch is the option that changes the judge's own verdict.

## Limitations

- The layer rule's accept-rate check failed on one judge (Mistral); the score-based fix was found after that failure, and on two fresh judges it held in 2 of the 4 pairs with a responding layer (section 7).
- The beyond-ability gains are clear on MATH (Llama-3.1-8B, and the fresh Llama-3.2-1B) and small elsewhere; MMLU and MATH same-model answers come from one answering model (Qwen3.5-4B). The pooled rows treat judges as independent, which they are not (same questions and answers).
- The gap is measured on one split of the questions; on BBEH it varies by ±1–4 points across splits, enough to push a borderline pair over the bar (section 7).
- "Not solved" uses one sample of the judge's own answer, except the strict MATH test (9 samples); one sample overstates how often a judge truly cannot solve a question.
- Ranking ignores the accept threshold a deployed judge needs, which stretching shifts.
