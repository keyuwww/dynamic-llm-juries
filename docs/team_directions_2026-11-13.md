# Judges Approve What They Already Believe: Six Projects for the Team

## The finding in plain words

When an LLM judge grades an answer to a question it **can't solve itself**, it doesn't really check the answer. It
asks "is this what I would have said?" If yes, it says "correct", even when the answer is wrong. If no, it says
"incorrect", even when the answer is right.

We measure this with **belief strength**. We let the judge solve the question 7 times on its own, then count how many
of those 7 attempts land on the candidate's answer.

| How often the judge itself reaches this wrong answer | Share of these wrong answers it calls "correct" |
|---|---|
| never (0 of 7) | 18% |
| 1–3 of 7 | 35% |
| 4–6 of 7 | 54% |
| every time (7 of 7) | 74% |

The data: three Qwen judges, thinking off, on RB2 Math, JudgeBench and BFF-Bench. The table leaves out answers
that turned out to be mislabelled (see Project 0). Right answers the judge never reaches itself get called "correct" only
30% of the time.

**Why the team should care.** Our project picks which judges grade which question. This finding tells us *when* a
judge's verdict can't be trusted: when it is grading something it couldn't solve, and the answer happens to match its
own guess (or doesn't). Several other things we know point the same way:

- On questions they can't solve, strong and weak judges are equally unreliable. A stronger judge only does better on
  the questions it can solve.
- Judges share their wrong guesses. When one judge is confidently wrong, on average 4 of the other 7 judges are wrong
  on the same item, against about 1 if mistakes were independent. That's from Janys's confident-errors study.
- So a majority vote of our weak judges barely helps: +4 points.
- Outside information helps a lot: the official answer raises balanced accuracy from 0.55 to 0.95. More effort from
  the judge doesn't help: a "verify the steps" prompt changes it by −2.

Each project below is for one person. Most use data we already have.

---

## Project 0 (do first, small): check which "wrong" answers are really wrong

**The problem.** Pulling examples for this document turned up a labelling problem in RewardBench 2 Math (RB2 Math).
Many answers it marks wrong have the same value as the answer it marks right, just written differently. Real
examples:

| Question | Marked right | Marked wrong |
|---|---|---|
| Rest energy of 932 electrons, in eV | 476,252,000 | 476,000,000 |
| New volume of a 4.51 L gas warmed from 273 K to 546 K | 9.02 L | 9 L |
| Protons needed to release 63.1 J, in units of ×10⁹ | 420 | 4.20 × 10¹¹ |
| Solve 2e^(x−5)+3=7 (multiple choice) | e. x = ln(2)+5 | "x = ln(2)+5: e" |

A judge that calls "476,000,000 eV" correct is not anchoring. It is arguably right.

**How big it is.** GLM-5.3-Flash compared every RB2 Math wrong answer with the right one (`clean_labels.py`, $0.52):

- 61 of the 549 wrong answers reach the right value. 39 more couldn't be decided, because one of the two gave no
  final answer.
- They sit almost entirely among the answers the judges believe: 180 judge × answer rows, more than half of the
  "7 of 7" bin.

Removing them **does not change the finding**: the "7 of 7" rate goes from 71% to 74%. But that bin shrinks from 211
rows to 101, and RB2 Math now contributes only 10 of them. The anchoring reports now use the clean labels.

It did break one result. The probe test "can the judge tell its confident wrong beliefs from its right ones?" had 42
"wrong" RB2 Math answers per judge, and 35 of them were mislabelled. With clean labels only 7–8 remain, too few to
test.

**What to do.**

1. **RB2 Math.** Done automatically. GLM's verdicts are in
   `experiments/anchoring_early_answer/out/label_audit_glm5.3-flash.jsonl`. Still to do:
   - hand-check 50 of the verdicts;
   - settle the 39 undecided pairs.
2. **BFF-Bench and JudgeBench.** The trick above doesn't work here, because there is often no labelled-right
   candidate to compare against. Hand-check about 50 of the "7 of 7" wrong answers on each, and classify each one:
   - really wrong;
   - right answer with wrong working;
   - a label we disagree with.
3. Produce a clean label file that every other project uses.

**Also affected.** Earlier results that use RB2 Math:

- the judging-beyond-capability study ("checking beats solving on RB2 Math");
- Robin's and Janys's results on RB2 Math.

**Needs.** No new spending for RB2 Math. Hand checks on BFF and JudgeBench take about 2–3 days. Anyone can do this
one.

---

## Project 1: use "the judge only approves what it believes" to decide what to escalate

**The idea.** A cheap judge grades everything, and we send only its untrustworthy verdicts to a stronger judge. The
question is how to spot the untrustworthy ones. Our finding suggests a specific signal. Be suspicious when:

- the judge can't reliably solve the question (its 7 own attempts disagree with each other), **and**
- its verdict simply follows its own guess. It said "correct" to an answer it believes, or "incorrect" to one it
  doesn't.

**Why we think it might work.** The signals we use now don't look at this. Robin found:

- the judge's activations only help on one benchmark (RB2 Safety);
- on BFF, rerunning the judge 10 times or checking whether other judges disagree works better.

Neither of those asks "did the judge just agree with itself?".

**What you would do.**

1. For each graded answer, compute three numbers from the 7 solve attempts we already have:
   - **how consistent the judge is with itself:** the share of its 7 attempts that agree with its most common
     answer. This is a stand-in for "can it solve this?";
   - **how strongly it believes this candidate:** 0 to 7 of 7;
   - **whether its verdict matches that belief.**
2. Combine them into a trust score. Start with a simple rule. Then fit a small logistic regression on half the
   questions and test it on the other half.
3. Put it into Robin's escalation code (`experiments/calibrating_judges/cascade_eval.py`). Escalate the least
   trusted 10%, 20% or 30%, and compare the final accuracy against:
   - 10 reruns;
   - other judges' disagreement;
   - the judge's stated confidence;
   - Robin's probe;
   - random escalation.

**What the results would mean.**

- **It beats 10 reruns at the same cost:** a new, cheap escalation signal for the jury.
- **It only wins when it uses more calls than the alternatives:** we need Project 2's cheap version.
- **It doesn't win:** belief explains *why* judges fail, but other judges' disagreement already captures it.

**Needs.** All the data exists:

- 7 attempts per question: `experiments/anchoring_early_answer/out/solves_k.jsonl`;
- GLM matches: `out/matches_glm5.3-flash_k.jsonl`;
- verdicts: in the same folder.

No new runs. About one week. Natural fit: Robin, who wrote the escalation code.

---

## Project 2: a one-step belief score instead of 7 attempts

**The idea.** Seven attempts per question is expensive. A cheaper way to ask "how much does the judge believe this
answer?" is to show the model the question followed by "The answer is" and read off the probability it gives the
candidate's answer. That takes one pass through the model and no writing.

**Why it matters, two reasons.**

1. **Cost.** If the one-step score matches the 7-attempt score, Project 1's signal becomes almost free.
2. **Whether our finding is new.** A 2024 paper (Wataoka et al.) found that judges favour text the model finds likely,
   measured by *perplexity*: how surprised the model is by the text. If perplexity explains our result just as well,
   our belief-strength finding is mostly theirs in a new form. If the 7-attempt score explains much more, ours adds
   something real.

**What you would do.**

1. Load Qwen3.5-4B, Qwen3.5-9B and Llama-3.1-8B on Cannon, which is free.
2. For each question and candidate answer, compute two scores:
   - **(a) answer probability:** the probability of the candidate's final answer after "The answer is";
   - **(b) Wataoka's measure:** the perplexity of the whole candidate response.
3. Check how closely each tracks the 7-attempt belief score.
4. Check how well each predicts which wrong answers the judge accepts. Compare only answers to the *same* question,
   so "this question is easy" can't help.
5. Look at the cases where (a) and the 7-attempt score disagree. We expect these to be questions that need several
   steps of working.

**What the results would mean.**

- **(a) is nearly as good as 7 attempts:** a cheap signal for Projects 1 and 3.
- **Both (a) and (b) fall clearly short:** sampled belief captures something likelihood doesn't, and our finding
  stands apart from Wataoka's.

Both are worth reporting.

**Needs.** Free (Cannon GPUs). The candidates and belief scores exist. About one week. Use RB2 Math and BFF; JudgeBench
answers are just "A" or "B", which is too short for (a). Natural fit: Ingrid, who already runs Qwen locally.

---

## Project 3: choose jurors whose guesses differ, not just whose model families differ

**The idea.** A jury fails when its members share the same wrong guess. The README suggests "recusal by model
family": a judge doesn't grade answers from its own family. But Janys found that:

- judges from *different* families share wrong answers almost as often as judges from the same family (2.4× vs
  2.6–2.8× more often than chance);
- what's actually shared is the *guess on that specific question*.

So choose jurors by their guesses, not their families.

**Two rules to test.**

- **Rule A, belief recusal:** on a question a juror probably can't solve, it doesn't vote on an answer that matches
  its own guess. Its vote there is just its guess repeated.
- **Rule B, disagreement escalation:** before anyone grades, look at the jurors' own answers to the question. If they
  disagree with each other, send the question to a stronger judge instead of voting.

**What you would do.**

1. Use the judges' existing solve attempts and verdicts on BBEH and BFF:
   - `experiments/beyond_capability/out/`, which has four judges and Kimi;
   - the 8-judge pool from the cross-benchmark study.
2. Build juries of the same size and cost five ways:
   - plain majority vote (baseline B2);
   - weighted vote (B3);
   - family-diverse;
   - Rule A;
   - Rule B.
3. Report results separately for questions the jurors can and can't solve.

**What the results would mean.**

- **A rule beats majority vote by more than the current +4 on unsolved questions:** a concrete jury-selection method
  for the project.
- **Neither helps:** shared guesses are too common to vote around, and escalation (Project 1) is the only way out.

**Needs.** Mostly existing data. If some pool judges are missing solve attempts, price those calls before running.
About 1–1.5 weeks. Natural fit: Janys, who measured how often judges share errors.

**Watch out.** Rule A must not silence judges that *did* solve the question, since their guess matches the right
answer. That is why it only applies on questions the juror probably can't solve. Decide that with the consistency
score from Project 1.

---

## Project 4: hide the final answer from the judge

**The idea.** The judge anchors on the candidate's *final answer*: "that's what I got too". So hide it. Grade each
candidate three ways:

1. **full:** the normal version, which we already have;
2. **working only:** every mention of the final answer removed;
3. **final answer only:** no working shown.

**Why we think it might work.** The "verify the steps" prompt failed, but that judge could still see the answer and
agree with it. Without the answer, the judge has to follow the working.

**What you would do.**

1. Have GLM-5.3-Flash remove every statement of the final answer from each candidate. Hand-check 50 of them.
2. Grade the "working only" and "final answer only" versions with the three Qwen judges, thinking off, on RB2 Math,
   BFF and BBEH. Use the clean labels from Project 0.
3. Compare, for each version:
   - how often believed wrong answers are accepted;
   - the same for wrong answers the judge doesn't believe;
   - the same for right answers.

**What the results would mean.**

- **"Working only" cuts acceptance of believed wrong answers and keeps right answers:** a prompt-level fix every judge
  in the jury could use.
- **Nothing changes:** the judge rebuilds the answer from the working, so the anchor is in the reasoning itself. That
  is useful to know too: it means only outside information helps.
- **"Final answer only" looks the same as "full":** the judges were never reading the working at all.

**Needs.** About 12,000 new grading calls plus about 2,000 GLM edits. That is roughly $50–80 on Tinker, based on the
Nov 9 bill; get an exact price from token counts before launching. About one week.

**Watch out.** In BBEH puzzles the working often gives the answer away. Measure that by asking GLM to guess the hidden
answer from the edited text.

---

## Project 5: read what the judge writes when it approves a wrong answer

**The idea.** When a judge (with thinking on) approves a wrong answer it believes, what does its reasoning show? Two
possibilities:

- **(a) It solves the question itself, gets the same wrong answer, and approves because they match.** It never
  checks the candidate's steps.
- **(b) It walks through the candidate's steps and misses the mistake.**

**Why it matters.** The two need different fixes:

- if (a), no reasoning prompt will help, and the fix is Project 4 or outside information;
- if (b), a better checking prompt might work.

We already know the judge leans toward its belief *before* it starts reasoning, and that reasoning makes the lean
stronger. We don't know *how*.

**What you would do.**

1. Pick about 300 reasoning transcripts from four groups:
   - believed wrong answers that were accepted;
   - believed wrong answers that were rejected;
   - wrong answers the judge doesn't believe;
   - right answers.
2. Have GLM-5.3-Flash label each transcript:
   - Did the judge solve the question itself?
   - Did it walk through the candidate's steps?
   - Did it point to a specific error?
   - Did it say something like "this matches my result"?
   - Where did it first state an answer?
3. Label 50 transcripts by hand, without knowing which group they're from, to check GLM.
4. Compare the groups.

**What the results would mean.** A plain statement such as "in 80% of believed wrong approvals, the judge re-solved
the question and approved because the answers matched." That would point directly to the fix.

**Needs.** The transcripts exist: `*-think__judgments.jsonl.gz` in `drive_upload_anchoring_traces/`, which is going to
the team Drive. GLM labelling costs about $10–20. About one week, mostly reading. Natural fit: Janys, who has done
blind hand-labelling before.

**Watch out.** What a model writes isn't always why it decided. We have a reading of its verdict from *before* it
started writing. If the verdict was already set then, the transcript may just be justifying it after the fact.

---

## Project 6: be stricter on questions that look hard

**The idea.** When there's no stronger judge to escalate to, the only lever left is to make the judge say "correct"
less easily on hard questions. We have signals that a question is hard *before* the judge grades it:

- Robin's question-only probe (`experiments/no_answer_needed`);
- the judge's internal state before it answers, which predicts whether it will solve the question (AUROC 0.72–0.74);
- low consistency across its 7 attempts.

**Why it might help.** On BBEH questions the judges can't solve, they accept 58% of wrong answers. The model's
internal state "knows" the question is hard, but the verdict ignores it.

**What you would do.**

1. Read how sure the judge is that an answer is correct, from its verdict (we already have these readings:
   `experiments/anchoring_early_answer/out/readouts.jsonl`).
2. Set a bar the score must clear to count as "correct", and raise that bar when the question looks hard. Fit how
   much to raise it on half the questions and test on the other half.
3. Compare a fixed bar, the difficulty-adjusted bar, and escalating those same questions instead.

**What the results would mean.**

- **Overall accuracy improves:** a free fallback for when no stronger judge is available.
- **It doesn't:** the judge's verdict on hard questions is too close to a coin flip for any bar to help.

**Needs.** Free; the data and probe code exist. About 3–5 days. Natural fit: Robin, who has the question-only probe.

**Watch out.** Expect a small gain. On hard questions alone the judge is near a coin flip, so a bar can't rescue it
there. The gain comes from treating hard and easy questions differently. Adjusting the bar by the judge's *own* stated
confidence gave only +1 to +5 before. This version is different because the difficulty signal comes from the
question, not from the judge's verdict.

---

## How they connect

- **Project 0** comes first: every other project needs clean right/wrong labels.
- **Projects 1 and 2** build an "is this judge just agreeing with itself?" alarm, and make it cheap.
- **Project 3** uses the same idea to choose who sits on the jury.
- **Projects 4 and 5** ask whether the judge can be stopped from anchoring at all, and why or why not.
- **Project 6** is the fallback when there's nobody to escalate to.

All six use the judges we already run, with prompts, sampling, or reading the model's internal state. None needs
training a model or a large new study across many models.

## Terms

- **Solved / unsolved question:** whether the judge, answering by itself, gets the question right (majority of its
  attempts).
- **Belief strength:** out of 7 attempts at the question by itself, how many reach the candidate's answer.
  GLM-5.3-Flash decides whether two answers are the same.
- **Anchoring:** accepting an answer because it matches the judge's own guess, not because it is right.
- **Balanced accuracy:** the average of (share of right answers accepted) and (share of wrong answers rejected). 0.5
  is a coin flip, 1.0 is perfect.
- **AUROC:** how well a score ranks one group above another. 0.5 is chance, 1.0 is perfect.
- **Escalation:** sending a verdict to a stronger judge. We compare methods at a fixed share escalated (10%, 20%,
  30%).
- **Benchmarks:**
  - **BBEH:** hard reasoning puzzles with short exact answers.
  - **RB2 Math:** RewardBench 2 math, where one solution is graded right or wrong.
  - **JudgeBench:** pairs of answers, and the judge picks the better one.
  - **BFF-Bench:** finance questions with expert labels.
