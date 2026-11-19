# Fresh-question replication (frozen Nov 18, before any data were collected)

## Why this design
The main study used every usable question in its three benchmarks (183 RewardBench 2 Math, 459 non-coding JudgeBench,
298 BFF-Bench), so no held-out split of those benchmarks exists. JudgeBench's knowledge items are MMLU-Pro questions
answered by GPT-4o / Claude, with labels from the MMLU-Pro answer key. We rebuild that protocol on MMLU-Pro questions
that JudgeBench does not contain. Answers are letters, so matching is exact (no model matcher).

## Data
- Questions: MMLU-Pro test split (TIGER-Lab/MMLU-Pro), excluding every question whose text appears in JudgeBench.
  Order fixed by `random.Random(20261118).shuffle`. The pilot uses the first 80; the confirmatory set uses the next
  questions in the same order (pilot questions are not reused).
- Question text: the MMLU-Pro question, options "(A) ...", and JudgeBench's MMLU-Pro instruction suffix verbatim.
- Answer writer: Nemotron-3.5-Super-VL-120B (NVIDIA), thinking off (`nemotron3_ultra_disable_thinking`), T = 1.0,
  6 samples, 8192 tokens. A question is eligible if at least one sample's letter equals the gold and at least one sample's letter
  differs from it. The pair is the lowest-index correct and lowest-index wrong sample. Position (A/B) is drawn from
  `random.Random(zlib.crc32(question id))`. Eligibility depends only on the writer's samples, never on any judge.
- Judges (3 families, none NVIDIA): Qwen3.6-35B-A3B, Qwen3.5-9B, DeepSeek-V4.1-Flash, Kimi-K2.6.
  Judging: JudgeBench judge prompt, thinking off, T = 0.7, 8192 tokens, one verdict (as the main study's pool
  judgments for the added families).
- Own answers: 8 per judge per question, the question as the only message, thinking off, T = 0.7, whole remaining
  context as budget (as the main study). Sample 0 is the one-sample "matches" label; samples 1-7 give belief.
  An answer without a parseable 5x letter is unavailable; belief needs at least 5 available of samples 1-7.

## Outcomes and analyses (fixed now)
Target = the wrong response. Approval = the judge prefers it (parsed "VERDICT: A/B"). Belief = share of available
samples 1-7 whose letter equals the wrong response's letter; competitor belief = share equal to the right response's.
Bins by round(7 x belief): 0, 1-3, 4-6, 7.
1. Primary: pooled linear slope of approval on belief with judge fixed effects; 95% interval from 2,000 bootstrap
   draws of whole questions (all judges kept together). Also per judge, and the bin staircase.
2. Same candidate across judges: candidate + judge fixed effects.
3. Pairwise protocol: target and competitor belief together, judge fixed effects.
4. One-sample label vs belief: both in one model, judge fixed effects.
5. Label sensitivity: wrong responses that any judge believes at >= 4/7 are audited by Kimi-K3.1-Pro
   (high reasoning, the main study's audit prompt); analyses 1-4 repeated keeping only answers it calls clearly wrong.
No other analysis is confirmatory; anything else is labelled exploratory.

## Size
Set from the pilot's cost per question and eligibility yield only (not from any approval result), and recorded in
`SIZE.md` before the confirmatory run. Budget for this replication: at most $450 on Tinker (of the $1,000 cap).

## Change log
- Nov 18, before any judge call: the writer was first GLM-5.3-Flash (low reasoning). A 5-question smoke test showed
  its visible answers are mostly the bare letter (its reasoning is hidden), unlike JudgeBench's step-by-step
  responses. No non-judge family on Tinker writes visible reasoning, so the writer became Nemotron-3.5-Super with
  thinking off, and the NVIDIA judge (Nemotron-3-Super) was replaced by Qwen3.5-9B so no judge shares the writer's
  family. The smoke-test generations are discarded (data/gen_glm_smoke.jsonl).

## Re-measuring belief on the original JudgeBench questions (fixed Nov 18, before collection)
Each original judge still served on Tinker (the three Qwens, Nemotron-3-Super, DeepSeek-V4.1-Flash, Kimi-K2.6;
Nemotron-3-Nano is retired) answers each of the 459 JudgeBench questions 7 more times with the original own-answer
prompt and settings. On the paper's audited wrong-answer JudgeBench judgments (original approvals, unchanged), we
report: correlation and bin agreement between original and new belief; the judge-fixed-effect slope of approval on
original belief, on new belief, and on their average (14 samples); and the staircase by new belief. This is a
reliability check of the measurement (conditional resampling), not a new population estimate. Cap: $100.
- Nov 18, cap change: the first collection pass hit the $100 cap through worst-case reservations (actual spend
  $47.66) with DeepSeek-V4.1-Flash 71/459 and Kimi-K2.6 0/459 done. The cap was raised to $150 and the remaining
  calls run at lower concurrency so that all six judges are measured as planned. A partial analysis (four judges)
  had been run; the decision to finish all six is the protocol's, not a response to it.

## Data files

`data/{gen,judge,pairs,questions,resolve,solve}.jsonl` are committed gzipped (GitHub's file-size limit). Before rerunning
`analyze.py` or `reliability.py analyze`, run `cd data && gunzip -k *.jsonl.gz`. `audit.jsonl`, `timeouts.jsonl` and
`gen_glm_smoke.jsonl` are committed as is.
