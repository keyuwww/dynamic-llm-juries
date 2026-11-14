# Recovering What an LLM Judge Knows but Doesn't Say

*November 9, 2026*

::: summary
## Summary

- **Question.** Inside an LLM judge, is there a direction that tracks whether a candidate answer is actually right? Does stretching along it help the judge, especially on questions the judge cannot solve itself? Judges: Llama-3.1-8B and Qwen3.5-9B on MMLU-Redux.
- **Llama knows more than it says, on questions it can solve.** Its internal judge direction ranks right above wrong answers at 0.70, but its verdict only at 0.55.
- **Stretching recovers part of that gap.** Llama's ranking rises by +8 points [+4, +13]. The gain holds (+6 [+2, +10]) when we compare only answers written by the same model, so it is not explained by the judge recognising which model wrote the answer. A random direction does nothing.
- **No real gain on questions the judge can't solve.** An apparent +6 there disappears (+0.3 [−4, +5]) once we compare only answers from the same model. It came from the judge sensing which model wrote the answer, not whether the answer was right.
- **No gain for Qwen.** Its verdict already follows the direction (correlation 0.9), so stretching only makes it stricter. The gap between what the judge knows and what it says predicts the gain.
- **A preregistered test on a third judge agrees.** Before stretching Qwen3.5-4B, we wrote down that its small gap (1–3 points) means no gain. The measured gains were −0.4 to −3 points, all within range, in 6 of 6 groups.
:::

## 1. Motivation and setup

*Inside the Unfair Judge* ([Xu et al., 2026](https://arxiv.org/abs/2607.11871)) shows that an LLM judge's biases, such as favouring longer answers, live in a few directions of its hidden states, and that steering along them adds or removes the bias. Inspired by an insight from Phaedrus on that paper, we ask whether there is also a direction for whether an answer is *actually right*, and whether stretching it makes the judge better.

- **Benchmark:** MMLU-Redux, multiple choice with an expert-checked answer key.
- **Candidate answers:** for each question, three other models (Qwen3.5-4B, Qwen3.6-35B, Nemotron-3-Super) wrote answers. An answer is right if its final letter matches the key. We keep questions with at least one right and one wrong answer.
- **Judges:** Llama-3.1-8B and Qwen3.5-9B, thinking off. The judge sees the question and one answer and replies starting with `VERDICT:`.
- **Solved vs not solved:** whether the judge answers the question correctly itself.

| Judge | Questions not solved (answers) | Questions solved (answers) |
|---|---|---|
| Llama-8B | 512 (1,940) | 410 (1,556) |
| Qwen-9B | 287 (1,072) | 635 (2,424) |

## 2. The judge direction and the stretch

1. Record the judge's hidden state at `VERDICT:` for every answer.
2. Subtract each question's average state, so only differences between answers to the same question remain.
3. **Judge direction** = average state of right answers − average state of wrong answers. No classifier is trained.
4. Learn it on half the questions and test on the other half. Keep the layer that best separates right from wrong on held-out questions: layer 16 of 32 for Llama, layer 20 for Qwen.
5. **Stretch:** multiply how far each answer's state sits from the average along the direction (×11 in the main results), leaving everything else unchanged. Each answer is pushed further the way it already leans. Control: a random direction of the same size.

## 3. How we measure

- **Verdict score** = log P(CORRECT) − log P(INCORRECT) at the first word after `VERDICT:`. Above 0 means the judge says CORRECT.
- **Ranking:** each answer is judged in its own prompt. Afterwards, for every pair of one right and one wrong answer to the same question, we score 1 if the right one has the higher verdict score, ½ for a tie, 0 otherwise, and average. 0.50 is chance.
- **Why ranking and not balanced accuracy:** balanced accuracy can rise just because the judge becomes stricter. Stretching Qwen raises its balanced accuracy by +6 on solved questions while its ranking stays at 0.76. Ranking is unaffected by strictness, so we use it, and check strictness separately in section 5.
- **Same-model control:** the stronger answering models are right more often, so simple surface clues, chiefly *which model wrote the answer*, already rank right above wrong at 0.65–0.72 without looking inside the judge. To rule this out, we repeat the ranking using only pairs of answers to the same question written by the same model (mostly Qwen3.5-4B, the only model with several answers per question).
- **95% intervals** come from resampling questions.

## 4. Results: the gap between knowing and saying predicts the gain

*Knows* = ranking from the position along the judge direction alone. *Says* = ranking from the verdict score.

| Judge | Questions | Knows | Says | Says after ×11 | Gain [95% CI] | Gain, same-model pairs | Verdict–direction correlation |
|---|---|---|---|---|---|---|---|
| Qwen | solved | 0.75 | 0.76 | 0.76 | 0 [−3, +2] | −1 [−4, +2] | 0.90 |
| Qwen | not solved | 0.53 | 0.48 | 0.50 | +2 [−1, +6] | +3 [−1, +8] | 0.87 |
| Llama | solved | 0.70 | 0.55 | 0.64 | **+8 [+4, +13]** | **+6 [+2, +10]** | 0.40 |
| Llama | not solved | 0.58 | 0.48 | 0.54 | +6 [+2, +10] | +0.3 [−4, +5] | 0.28 |

- **Qwen:** its verdict already reflects what the direction knows, so there is nothing to recover.
- **Llama, solved questions:** the information is present in the middle of the model but mostly lost before the verdict. Stretching pushes more of it through, and the gain survives the same-model control.
- **Llama, questions it can't solve:** with the same-model control, the direction barely knows more than the verdict (0.56 vs 0.53) and stretching adds nothing. The earlier gain came from the answering model's identity.
- **Strength:** gains peak at ×11–×21 and never exceed what the direction knows. Much stronger stretches (×101) start to hurt. The random direction stays flat.

![Ranking vs stretch strength, all answer pairs (shaded: ×11)](out_mmlu/stretch_curve_mmlu.png){width=92%}

**Where right and wrong answers sit.** For Llama on solved questions, right (green) and wrong (pink) answers are clearly apart along the direction but almost overlap along the verdict. For Qwen, both look alike:

![Right vs wrong answers along the direction (knows) and the verdict (says)](out_mmlu/direction_hist_mmlu.png){width=100%}

## 5. Better, or just stricter?

Stretching makes both judges reject more answers, right and wrong. To separate "better" from "stricter", we raise the unedited judge's cutoff until it accepts exactly as many wrong answers (same false positive rate, FPR) as the stretched judge, then compare how many right answers each accepts (true positive rate, TPR). Unlike ranking, this compares answers across questions, so we also repeat it on answers from a single model (Qwen3.5-4B).

| Judge | Questions | Stretched ×11 | Unedited, same FPR | Difference | Difference, one answering model [95% CI] |
|---|---|---|---|---|---|
| Llama | solved | TPR 89% at FPR 76% | TPR 82% | +7 | +2 [−2, +7] |
| Llama | not solved | TPR 84% at FPR 79% | TPR 76% | +8 | +7 [+1, +14] |
| Qwen | solved | TPR 72% at FPR 37% | TPR 73% | −1 | −1 [−5, +2] |
| Qwen | not solved | TPR 53% at FPR 52% | TPR 50% | +3 | +7 [−1, +17] |

- **Qwen:** stretching is equivalent to raising the cutoff.
- **Llama:** on all answers, stretched Llama accepts 7–8 points more right answers than an equally strict unedited judge. With one answering model, the solved-question advantage shrinks to +2 and is no longer clear.
- **Llama, questions it can't solve:** the advantage stays (+7) with one answering model, but the same-model ranking test above finds no gain within questions. The advantage therefore comes from treating whole questions differently, not from telling a right answer from a wrong one to the same question. We do not count it as better judging.

## 6. A preregistered test on a third judge

The gap rule was found by looking at the results above, so we tested it on a judge it had not seen: Qwen3.5-4B (thinking off) on the same MMLU-Redux answers. We wrote the predictions down before any stretch was run.

- **The rule:** if the verdict responds to pushes along the direction, the gain from stretching ×11 ≈ half the gap between *knows* and *says*. Qwen3.5-4B's verdict responds, but its gap is small (−3 to +1 points), so the rule predicts no gain.
- **What counts as passing:** in each group the gain lands within ±4 points of the prediction, and its 95% interval includes 0.
- **Own answers:** Qwen3.5-4B wrote some of the candidate answers, so we score each group with and without them.

| Questions | Answers judged | Knows | Says | Predicted gain | Measured gain [95% CI] |
|---|---|---|---|---|---|
| all | including its own | 0.62 | 0.61 | +0.6 | −0.4 [−1.5, +0.8] |
| solved | including its own | 0.72 | 0.70 | +0.6 | −0.4 [−1.9, +1.2] |
| not solved | including its own | 0.53 | 0.52 | +0.6 | −0.4 [−2.1, +1.2] |
| all | other models' only | 0.55 | 0.58 | −1.3 | −2.5 [−5.6, +0.5] |
| solved | other models' only | 0.67 | 0.70 | −1.7 | −3.1 [−7.5, +1.2] |
| not solved | other models' only | 0.43 | 0.44 | −0.6 | −1.7 [−6.2, +2.8] |

- **The rule passes in all 6 groups.** Stretching only makes Qwen3.5-4B stricter: at ×11 it accepts 71% of right and 57% of wrong answers, down from 84% and 74%, while its ranking stays at 0.61.
- **Same-model control:** using only pairs from the same answering model also gives no gain (−1.3 [−3.1, +0.5]).
- **Caveat:** predicting "no gain" is an easier test than predicting a specific gain. We also preregistered a formula for the best stretch strength (1 + 1/sensitivity, which picked ×9). It passed, but since no strength moved the ranking by more than 0.4 points, any choice would have passed.

## Limitations

- The gain does not carry over to other benchmarks. On MATH, neither judge gains clearly from stretching (Llama +1 [−5, +7] on solved questions and +2 [−2, +5] on unsolved; Qwen +2 [−2, +5] and +7 [−1, +15]), because Llama's verdict barely responds to pushes at that layer. On RewardBench 2 Safety, a preregistered test, Qwen gains nothing as predicted, and ×11 makes Llama worse (−6 [−9.5, −3.5]) because its verdict responds so strongly that the stretch overshoots.
- The gap rule has passed one fresh test, and only for a judge where it predicts no gain. It has not yet been tested on a new judge where it predicts a gain.
