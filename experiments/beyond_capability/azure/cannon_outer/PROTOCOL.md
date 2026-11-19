# Outer held-out evaluation of the full recipe (frozen 2026-11-18, before any outcome is seen)

Purpose: in the paper, the layer, the gap eligibility (gap > 5) and the direct-readout layer are chosen with labels of the
questions that are later evaluated. Here every choice is made on training questions only and the whole recipe is scored
on held-out questions.

## Scope (fixed now)

Judges: Llama-3.1-8B-Instruct and Qwen2.5-7B-Instruct (primary, as the reviewer asked), plus Phi-4-mini-instruct and
Granite-3.3-8B-instruct (added because Cannon GPUs are free). Benchmarks: MMLU-Redux, MATH, BBEH main answer pools (the
same item files as the paper). 12 pairs. Every pair is reported, including pairs where the rule abstains.
Not included: Llama-3.2-1B/3B, Mistral-7B, Qwen3.5-4B (no KV-cache shortcut; much slower), Llama-3.1-70B.

## Folds

Outer folds = the paper's two question halves (seed 0). For each fold, train = one half, test = the other.

## Choices made on the training half only (per fold)

1. Directions: per candidate layer (every 2nd layer except 0 and the last), question-centred mean(right) - mean(wrong)
   on all training answers; centring constant mu and scale sd = mean and sd of training projections.
2. Inner ranking: split training questions in two (seed 1); learn on one quarter, score the other, both ways ->
   inner KNOWS(L) = within-question AUROC; inner SAYS = verdict AUROC on training answers.
3. Eligibility: max_L inner KNOWS - SAYS > 5 AUROC points (the paper's threshold).
4. Direct-readout layer L_d = argmax inner KNOWS.
5. Push test: 400 random training answers, add -8 / +8 sd of the training direction at each candidate layer;
   sensitivity = mean verdict-score change / 16 / within-question verdict sd on training answers. No labels.
6. Stretch layer L_s = argmax inner KNOWS among layers with sensitivity >= 0.05, else L_d.
7. Strength fixed at x11 (beta = 10). No strength selection.

## Scored on test answers (pooled over the two folds, then within-question AUROC on all questions)

- verdict (unedited)
- direct: projection on the training direction at L_d
- verdict + direct: each divided by its within-question sd on the test question, summed (no fitted weight)
- rule: stretch x11 at L_s if the fold is eligible, else the unedited verdict  (PRIMARY)
- stretch x11 at L_s regardless of eligibility
- random-direction x11 at L_s (control)
- for diagnosis only: x11 at every candidate layer (gives the post-hoc best layer = selection optimism)

Primary: gain of the rule and of direct over the verdict, per pair, with 2,000 question resamples; pooled as the
equal-weight mean over pairs with questions resampled within benchmark, synchronised across judges.
Compared with the paper's in-sample-selected numbers for the same pairs.

Reasoning (repaired) is a separate run: see cot_exact.py.
