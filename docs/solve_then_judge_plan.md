# Design plan: solve-then-judge on BFF-Bench

**Question.** Does a judge grade more accurately if it first answers the question itself and then grades the
candidate against its own answer? When does it help, and when does it hurt?

**Why now.**
- The gpt-oss judges, which reason before answering, are the best judges on 8 of 9 benchmarks.
- On JudgeBench, the most common reason the best judge failed was solving the problem itself and getting it wrong.
- No Free Labels reports a small gain from grading against the judge's own answer (GPT-4o κ 0.47 → 0.52, pooled
  over BFF and (C)MT-Bench).

So the effect could go either way, and it should depend on whether the judge can solve the question.

## 1. Conditions

All 8 Tinker judges, the 808 BFF responses with a 2-of-3 human label, 1 sample per verdict, T = 0.7.

| Arm | What the judge sees | Calls per verdict | Status |
|---|---|---|---|
| **none** | conversation + candidate answer | 1 | Rerun for the 349 split-vote items (the 459 unanimous ones exist) |
| **self (two-step)** | + its own answer, written in a separate earlier call | 1 (+ 1 answer per question) | New; main arm |
| **solve-in-prompt** | one call: “first solve the question yourself, then grade the answer” | 1 | New; cheaper variant of self |
| **peer** | + gpt-oss-120b's answer, for every judge | 1 | New; separates “own answer” from “a good answer” |
| **human** | + the expert reference | 1 | Upper bound; exists for the 459 unanimous items, run the other 349 |

The judge's own answer comes from the same model and setup it judges with: thinking off where it can be switched
off; the gpt-oss judges always reason.

## 2. Steps

| # | Step | Command / change | Calls | Est. cost | Time |
|---|---|---|---|---|---|
| 1 | Write raw caches to the repo folder, not a temp folder | run everything from the repo; copy caches to a second place after each step | – | – | 5 min |
| 2 | Each judge answers all 160 BFF turns | `run_answers.py --bench bff --max-tokens 4096` | 1,280 | ~$3 | 20 min |
| 3 | Label which answers are right (“solved” label) | `grade_bff_answers.py`, with gpt-oss-120b + expert reference as the grader (no Jev key in `.env`); DeepSeek-V3.1 + reference as a second grader on a 20% sample | ~1,550 | ~$3 | 20 min |
| 4 | Judge arms: none (missing items), self, peer, human (missing items) | `run_judges.py --bench bff --consensus majority --conditions none,self,human --max-tokens 8192`, plus a small `peer` condition added to `build_prompt` | ~19,000 | ~$25–30 | 1.5 h |
| 5 | solve-in-prompt arm | new prompt variant in `run_judges.py` (`--conditions solve`) | 6,464 | ~$10–12 | 45 min |
| 6 | Analysis + report tab | new `experiments/solve_then_judge/analyze.py`; add a tab to the cross-benchmark report | – | – | 1.5 h |

**Total: about $40–50 and 4–5 hours,** most of it waiting on runs. To cut it to about $20, drop step 5 and the
peer arm. You'd still get the main answer (self vs none), just not the "own answer vs good answer" split.

## 3. Analyses

1. **Headline.** Agreement and κ for each judge, self vs none vs human, on the 808 responses (2-of-3 labels).
   Paired difference with a 95% interval resampling whole conversations.
2. **Does it help only when the judge solved the question?** Split each judge's items by its own solved label
   (No Free Labels Table 4 analogue): Δκ(self − none) when it solved vs when it failed.
   - Expected: a gain when solved, a loss when failed.
3. **Anchoring.** Count flips between none and self: right → wrong vs wrong → right. Break them down by whether
   the judge's own answer was right. This shows whether a wrong own answer drags the verdict wrong.
4. **What kind of question.** Use the existing demand codes and content codes to compare the effect on
   calculation items (judge can recompute) against rule / convention items (tax, IFRS vs GAAP).
   - Expected: self helps calculations and hurts convention-heavy items.
5. **A new escalation trigger.** Escalate when the judge's own final answer disagrees with the candidate's.
   Compare errors caught and escalation rate with the disagreement triggers in `escalation_sim.csv` (BFF row).
   - The candidate and the judge's answer are free text, so the match is decided by a cheap judge call or by
     comparing extracted final numbers.
6. **Own vs peer answer.** Does grading against gpt-oss-120b's answer beat grading against your own? If yes, the
   value is in having a good reference, not in self-solving, and the cheaper design is one strong solver plus
   cheap judges.
7. **Cost.** Tokens and $ per verdict for each arm. Two-step self pays for an extra answer per question
   (shared across all responses to that question); solve-in-prompt pays once, inside a longer call.

## 4. Decision rule

- **Adopt self (or solve-in-prompt) as the default** if mean κ over the 8 judges rises by at least 0.03 with an
  interval above 0, and the best judge does not get worse.
- **Adopt it only as a routing rule** if it helps on solved items but hurts on failed ones: use self-reference
  only when a cheap check says the judge can solve the question.
- **Adopt the peer design** if peer ≥ self: one strong solver writes the reference, and the cheap judges grade
  against it.
- **Adopt the answer-mismatch trigger** if, at the same escalation rate, it catches more errors than the
  two-complementary-judge trigger (BFF: 57% of errors caught at 40% escalated).

## 5. Risks and how the plan handles them

| Risk | Handling |
|---|---|
| Turn-2 answers depend on the conversation: the judge's own turn 1 differs from the candidate's | Report turn 1 and turn 2 separately; flag the 37 turns coded “needs earlier results” (conversation dependence ≥ 2) |
| The grader of “solved” (gpt-oss-120b) is also a judge | Second grader (DeepSeek + reference) on 20%; report agreement; repeat the split analysis with DeepSeek labels |
| Long answers + reasoning run out of tokens | `--max-tokens 8192` for judging; report parse rates per arm |
| Thinking-off judges answer worse than they would with thinking on | Report as a limitation; a thinking-on arm is a follow-up |
| One sample per answer gives a noisy solved label | Optional: `--samples 5` on step 2 (prefill paid once, about +$5) for a per-question solve confidence |
| Raw results lost again | Step 1: caches in the repo folder (git-ignored) and copied to a second place after each step |

## 6. What it will not tell us

- **Other benchmarks.** It is one benchmark (finance, 80 conversations), so effects that differ by question type
  need the other benchmarks.
- **Five-sample voting.** It uses one sample per verdict, unlike No Free Labels' 5-vote setup, so absolute κ is
  not directly comparable to their numbers.
