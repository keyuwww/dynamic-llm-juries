# Speaker script: Judges approve what they believe (10 min)

Deck: https://claude.ai/artifact/VEyRFQ3gWgrUJ3heXp9mep
Backup (full deck, for questions): https://claude.ai/artifact/HYTsJ53h9u9UxaaHydhMAv

---

## 0 · Team teaser (before the talk, ~0:20)

- Presenting order:
  1. **Janys:** judge prompt evolution through learning from its errors
  2. **Keyu (me):** do LLM judges approve wrong answers they would give themselves?
  3. **Minh:** belief-based judge escalation through self-contradiction checks
  4. **Ingrid:** quick gut, cheap read, careful thought: one judge policy
  5. **Andrew:** judges debate before voting: does arguing beat a simple majority?

---

## 1 · Cover (0:30) · total 0:30

- Hook: LLM judge waves through wrong answers **it would give itself**
- Picture: 3x + 7 = 31, candidate says 9
  - judge would also say 9 → **approves**
  - judge gets 8 → **rejects**
- Not self-preference: judge **never wrote** any candidate
- Two questions:
  1. Does approval rise with how strongly the judge believes the answer?
  2. What happens inside the model?

→ next: "What others found first"

---

## 2 · Prior work (0:45) · total 1:15

- Behaviour:
  - **Panickssery 2024:** judges rate their **own** outputs higher → ours never wrote any candidate
  - **Roytburg 2026:** much of that is the judge simply being wrong → we measure that belief **per answer**
  - **Krumdick 2025, No Free Labels:** judges agree with experts mainly where they can answer themselves; expert references fix it → we grade that per answer (belief 0–7); also where BFF-Bench comes from
  - **Goel 2025:** judges favour models with the **same mistakes** → theirs per model, ours per answer
  - **Lin 2025:** solving and judging only weakly linked; its own answer as reference strengthens the link → we test "commit first" by belief level
- Inside the model:
  - **Marks & Tegmark 2023:** "true vs false" direction inside → method behind our arrows
  - **Gulati & Wunder 2026:** on judges, correctness labels can't separate truth from the judge's belief → we build a **separate belief arrow**
- What we add: belief per answer (re-solving) · no authorship · transcripts + insides · fixes by belief level

→ next: "Here is the whole story on one slide"

---

## 3 · The story (1:00) · total 2:15

- Four steps, each is one later slide
  1. **Measured belief** → wrong answers approved **18% → 74%**
  2. **Read transcripts** → **92–100%** of approved wrong answers come with a re-solve (thinking on)
  3. **Looked inside** → belief and correctness closer **when judging**, all 4 cases
  4. **Tried fixes** → commit-first **+5**, second family **−3** (balanced accuracy)
- So: judge asks **"does this match what I get?"**
  - errors on answers it doesn't believe → fixable
  - errors it believes → need a stronger reference

→ next: "First, what I mean by belief"

---

## 4 · Measuring belief (1:00) · total 3:15

- 4 steps: question only → solve **7 times** alone (T = 0.7) → match → **belief = k / 7**
- Judge **never sees the candidate** while solving
- Matching: **GLM-5.3-Flash** compares final answers; JudgeBench letters exact
- Illustration: tries 8 8 9 8 8 8 8 → belief in 9 = **1/7**
- Real item (JudgeBench philosophy): right answer F, Qwen-9B says H **7/7** → believes a wrong answer fully
- Candidates always written by **other models**

→ next: "Now, does approval follow belief?"

---

## 5 · Main result (1:30) · total 4:45

- Chart: wrong answers approved, by belief, one line per judge
- **Three Qwens: 18% → 74%** (+54 points, 0/7 → 7/7)
- **Nemotron (NVIDIA): 26% → 85%** → not a Qwen quirk
- **Not authorship:** same wrong answer, the Qwen that believes it more approves it more (+23)
- Bigger Qwens: stricter at 0/7 (27% → 8%), **just as trusting** at 7/7
- Belief beats a one-sample "matches my answer" label (it adds nothing once belief is in)
- Llama-3.1-8B left out: too weak a judge (~54% at every level)
- Setting: thinking **off**

→ next: "How does the judge get there? Read what it writes"

---

## 6 · Transcripts (1:00) · total 5:45

- **Method:** GLM-5.3-Flash read **7,443** judge transcripts, labelled:
  - did the judge work out its own answer?
  - did that answer match the candidate's?
  - 8 labels hand-checked
- Approved wrong answers, range over belief levels, 3 Qwens:
  - re-solves: thinking off **26–44%** · thinking on **92–100%**
  - re-solves **and** lands on the same wrong answer: off **23–43%** · on **86–96%**
  - both rows are out of **all approved wrong answers** (row 2 is a subset of row 1)
- Thinking off **hides it**: most approvals (67–86%) only check the given steps in writing
- Thinking on **shows it**: works the problem → same wrong answer → approves
- Rejections also re-solve, but land on a **different** answer

→ bridge to 6: "But the main result is thinking off, where the re-solve is mostly **not written**. And the belief effect is already **+35** before the judge writes anything. So we looked inside."

---

## 7 · Inside the model (1:15) · total 7:00

- Four arrows in the hidden state (2 Qwens: 9B, 35B; nothing generated)
  - rows: **correctness** (truly right − truly wrong) · **belief** (believed − never-reached wrong answers)
  - columns: **solving** (answer in its own voice) · **judging** (grading it)
- Cosine: 1 = same direction, 0 = unrelated
- **A vs B: 0.0–0.3, unrelated** (settled)
  - the judge does **not** reuse the solver's sense of "correct"
- **B vs D: 0.5–0.8, overlap** (likely)
  - while grading, "I'd say this" **looks like** "this is right"
- **A vs C: 0.3–0.5**, less overlap when solving
- So: they connect through the **answer**, not a shared sense of right
- Careful wording: consistent with a silent match, **not proof** of a hidden re-solve
- Caveat: partly the lean toward saying CORRECT; Qwen only

→ next: "Can we fix it?"

---

## 8 · A fix that works (1:15) · total 8:15

- **Commit first:** the model's own earlier answer goes in the chat, then it grades
- Wrong answers approved, usual → commit first:
  - 0/7: **18% → 1%** (−17 [−20, −14]) → floor gone
  - 1–3: 38% → 22%
  - 4–6: 58% → 51%
  - 7/7: **74% → 69%** → not clearly changed, belief still wins
- Net: balanced accuracy **80% → 85% (+5)**
- Cost: right answers it can't reach get approved less (1–3 of 7: 73% → 36%)
- Same pattern with "don't re-solve, verify the steps" (Qwen and Nemotron)
- Shown the answer but asked to **solve**: almost no pull (2%) → the 18% floor is the **grading frame**

→ next: "What about the confidently wrong ones?"

---

## 9 · A fix that fails (0:45) · total 9:00

- Idea: when a Qwen believes an answer (≥ 4/7), hand it to **Nemotron**
- Balanced accuracy goes **down**:
  - 4B 76% → 74%
  - 9B 80% → 77%
  - 35B 86% → 82%
- Why: Nemotron believes **77–81%** of the same wrong answers
- Even routing only when beliefs differ: 86% → 84% (35B)
- So: confident errors are **shared across families** → need a much stronger reference, not a peer

→ next: "Putting it together"

---

## 10 · Takeaways (1:00) · total 10:00

- Flow: wrong answer arrives → judge **re-solves and checks for a match**
  - **low belief (0/7):** still approves 18%, the grading frame → **fixed** by commit first (18 → 1%, +5)
  - **high belief (7/7):** approves 70–75%, even when told not to re-solve → **open**, shared across families
- One sentence: **a judge's belief predicts its verdict**
- Next:
  - frontier model or expert answer as the reference for believed items
  - the fixes with thinking on
  - hand-check BFF and JudgeBench labels
- Limits to say out loud: 7/7 groups small (28–41 per judge) · inside-the-model is Qwen only · fixes ran thinking off

No buffer at 10:00: if short on time, cut slide 9 (second judge) to one sentence

---

## 11 · Takeaways (0:30) · closing

1. **Judges approve what they believe:** wrong answers approved 18% → 74% as belief rises (4 judges, 2 families)
2. **They check for a match, not for truth:** re-solve, agree when they land on the same answer
3. **Low-belief errors are fixable:** commit first, 18% → 1%, +5 balanced accuracy
4. **High-belief errors are not, by peers:** shared across families (~80%), second judge doesn't help
- **Next:** a stronger reference (frontier model, expert answer, tool) for exactly the items the judge believes
- If asked "is it solved?": low-belief yes, high-belief not yet

---

## Likely questions → where to look in the backup

- **"Isn't this just self-preference?"** → no, candidates written by other models; same-answer test (+23) · backup 2.10
- **"Are the labels right?"** → RB2 Math audited (61 mislabelled answers removed, effect got stronger); BFF and JudgeBench not yet · backup 2.3
- **"Why 7 tries?"** → one try is a noisy yes/no; 7 gives a graded score · backup 2.4
- **"How do you know GLM's labels are right?"** → different family from every judge; 8 hand-checked, all agree · backup 4.1
- **"Is the inside result just 'about to say CORRECT'?"** → partly; removing that lean leaves 3 of 4 cases, cuts Qwen-35B BFF 0.72 → 0.23 · backup 3.4
- **"Why not Llama?"** → too weak a judge, ~54% at every belief level, only 5 answers at 7/7 · backup 2.9
- **"Prior work?"** → Panickssery, Roytburg, No Free Labels, Goel, Lin (behaviour); Marks & Tegmark, Yang & Jia, Gulati & Wunder (inside) · backup 1.2, 1.3
- **"Compute?"** → Tinker (judging, GLM), Modal GPUs (hidden states), Harvard Cannon (Llama) · backup A.1
