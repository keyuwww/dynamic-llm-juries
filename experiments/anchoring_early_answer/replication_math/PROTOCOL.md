# Second fresh-question replication: open-ended math (fixed Nov 20, before any data were collected)

## Why this design
Reviewer concern (Nov 20 self-review): the first pre-registered replication (`../replication`, MMLU-Pro) is
multiple choice, and the main study's open-ended benchmarks (RewardBench 2 Math, BFF-Bench) need a model to decide
whether two final answers match. We repeat the replication on problems whose answer is written out, not chosen from
options, and whose final answer is an integer, so matching is exact (no model matcher). Everything except the
questions and the answer parser is copied from the MMLU-Pro protocol.

## Data
- Questions: DAPO-Math-17k (open-r1/DAPO-Math-17k-Processed, "en"; competition problems with integer answers),
  deduplicated by text, integer gold only, excluding any problem overlapping a RewardBench 2 Math prompt (none
  found). Order fixed by `random.Random(20261120).shuffle`: 13,985 questions. Pilot = the first 80 (reported
  separately, used only to set the size and check the parser); confirmatory set = the next questions in order.
- Question text: DAPO's own instruction ("Solve the following math problem step by step. The last line of your
  response should be of the form Answer: $Answer ...") around the problem.
- Final answer parser (fixed now): the integer after the last "Answer:"; without one, the integer in the last
  `\boxed{}`. `$`, `*`, `\boxed`, `\text`, spaces and thousands commas are ignored; "12.0" counts as 12; anything
  else (fractions, expressions, "x = 5") is unparsed. Exact integer equality.
- Answer writer: Nemotron-3.5-Super-VL-120B, thinking off, T = 1.0, 6 samples, 8192 tokens. Eligible if at least one
  sample equals the gold and one parsed sample differs from it; pair = lowest-index correct and lowest-index wrong
  sample; position from `random.Random(zlib.crc32(question id))`. Eligibility never depends on a judge.
- Judges: Qwen3.6-35B-A3B, Qwen3.5-9B, DeepSeek-V4.1-Flash, Kimi-K2.6 (none NVIDIA). JudgeBench judge prompt,
  thinking off, T = 0.7, 8192 tokens, one verdict.
- Own answers: 8 per judge per question, the question as the only message, thinking off, T = 0.7, 16,384 tokens
  (bounded for cost; the MMLU-Pro run used the whole context). Sample 0 = one-sample label; samples 1-7 = belief;
  belief needs at least 5 parsed of samples 1-7.

## Outcomes and analyses (fixed now; identical to the MMLU-Pro protocol)
Approval = the judge prefers the wrong response. Belief = share of parsed samples 1-7 equal to the wrong response's
answer; competitor belief = share equal to the gold. Bins by round(7 x belief): 0, 1-3, 4-6, 7.
1. Primary: pooled linear slope of approval on belief, judge fixed effects, 2,000 question-bootstrap draws; per judge;
   bin staircase.
2. Same candidate across judges (candidate + judge fixed effects).
3. Target and competitor belief together.
4. One-sample label vs belief.
5. Label sensitivity: Kimi-K3.1-Pro (high reasoning, the same audit prompt) audits **every** wrong response (not only
   believed ones, after the MMLU-Pro lesson); analyses 1-4 repeated keeping only responses it calls clearly wrong,
   applied per candidate across judges. Also: audit verdicts by the highest belief any judge has in the response.
No other analysis is confirmatory.

## Size and budget
Set from the pilot's yield and cost only (no approval result looked at) and recorded in `SIZE.md` before the
confirmatory run. Hard cap for this replication: $300 on Tinker (belief-paper total so far $491 of $1,000).
