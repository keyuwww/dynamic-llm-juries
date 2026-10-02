# Zero-shot LLM juries on BFF-Bench: findings so far

Scope: Jev (TypeSafe) and CLM-8B (`clm-latest`, zero-shot, no fine-tuning) as judges and
routers on Kensho's BFF-Bench + VERDICTS. Covers Exp 1 (judge), Exp 2 (router/certifier),
the dynamic jury (P>60%, capped at 3), and lite reproductions of B5 (Jury-on-Demand) and B6
(Trust-or-Escalate). All experiment code lives under `experiments/`; this file is the
running summary of what we've learned, not a replacement for the per-experiment
`summary.md`/`metrics.json` files.

## 1. Jev is a strong judge; CLM-8B is not, zero-shot, on this domain

| | Jev | CLM-8B |
|---|---|---|
| Judge κ, noref | 0.505 | ~0.00 |
| Judge κ, ref | 0.856 | ~-0.01 |

CLM degenerates to almost always predicting "incorrect" regardless of the truth (`pred_correct_rate`
≈ 0-4%). This is not a bug we introduced (checked: not the `--max-tokens` truncation issue, fixed and
reran, numbers barely moved) — it looks like a genuine zero-shot domain gap. CLM's released head and
published benchmarks cover computer-use, gaming, tool-calling and agentic coding; finance/accounting
correctness judging is a domain it was never shown, and the CLM authors themselves note fine-tuning is
needed to be strong outside their evaluated domains. Treat CLM's numbers here as a zero-shot floor, not
its ceiling — a natural follow-up is fine-tuning a head on some BFF-Bench-adjacent data (the CLM repo
ships `train/finetune.py` for exactly this).

## 1b. CLM's noref miscalibration is not just weak, it's *inverted* in its main bin

Reliability check (`analysis/calibration.py`, 10 equal-width bins): CLM noref has ECE=0.486 (vs
Jev's 0.071) — roughly as far from calibrated as a probability score can get. The sharpest signal:
**360 of 459 items (78%) land in CLM's p=0.0-0.1 bin** (very confident "incorrect"), and within that
bin the *actual* fraction correct is **0.59** — i.e. on the single largest mass of its predictions,
CLM is more often right than wrong about the thing it says is almost certainly wrong. **Tested and ruled out**: this could look like an inverted true/false criteria mapping, so we probed
it directly (`experiments/jev_bff/probe_clm_criteria.py`, n=60, live against CLM) by asking the same
items with the criteria's true/false text swapped. Result: normal-criteria AUROC 0.409, swapped-criteria
(un-swapped by taking 1-p) AUROC 0.536 — both within noise of chance (0.5), not "one direction is clearly
informative." So it is **not** a simple criteria-phrasing bug we can fix by rewording; CLM confidently
picks a side either way (mean p=0.069 normal vs 0.794 swapped — flipping the framing flips its
confidence, as expected) but that confidence carries ~no real signal about correctness in this domain,
in either direction. This is genuine no-signal zero-shot behavior, not a fixable prompt-inversion bug.

**Sharper still**: broken out by examinee model, CLM noref outputs a near-constant mean p (0.070-0.086
across all six models) regardless of the model's true base correctness rate, which itself ranges
0.34-0.84 across examinees. Per-examinee AUROC is 0.29-0.49 (i.e. at-or-below chance for every single
one). CLM's `is_correct` score for this domain isn't just weakly informative — it's close to
**input-invariant**: it barely moves whether the actual response is from a 2B or a frontier model, or
whether that model is usually right 34% or 84% of the time. That rules out "it's picking up some signal,
just not enough"; the state content doesn't appear to be reaching the decision in a way this task can use.

## 2. Neither backend beats "always ask GPT-4o" as a router

Given only the question (no candidate's response), asking a backend "which of 6 models would answer
this correctly" ties (Jev) or loses to (CLM) the trivial fixed policy of always picking the single
best-overall model:

| Strategy | Jev | CLM |
|---|---|---|
| Random pick | 0.760 | 0.760 |
| Always pick GPT-4o | 0.872 | 0.872 |
| Router (yes/no argmax) | 0.872 | 0.809 |
| Router (choice call) | 0.872 | 0.745 |
| Oracle | 0.915 | 0.915 |

Jev's per-(question,model) AUROC (0.837) is well above chance, but it isn't finding *question-level*
signal about which weaker model can handle an *easy* question — it's mostly recovering "GPT-4o is
usually the safe bet," which a zero-signal fixed policy already captures for free.

## 3. Dynamic jury (P>60%, capped at 3): majority vote underperforms the single best judge

| | Jev | CLM |
|---|---|---|
| Jury majority-vote accuracy | 0.766 | 0.783 |
| Always-pick-best-single (baseline) | 0.872 | 0.870 |
| Oracle (baseline) | 0.915 | 0.913 |

A ~2.6-member jury, majority-voted, loses to just trusting the single best model outright — weaker
jury members outvote the strong one on questions it would have gotten right alone. (CLM's jury number
being *slightly higher* than Jev's here is noise from n=47 and shouldn't be read as CLM's jury logic
being better; see [[dashboard]] for the full breakdown.)

## 4. B6 (Trust-or-Escalate) reproduction: works well for Jev, inert for CLM

Built directly from Exp 1's noref/ref pairs (no new API calls): treat noref as the cheap tier, ref as
the escalation tier, gate on noref confidence `|p-0.5|x2`.

- **Jev**: κ climbs smoothly from 0.505 (never escalate) to a peak of **0.803 at only 28.5%
  escalation** (τ=0.85) — genuinely useful, matches the project's own cost/coverage framing well.
- **CLM**: flat curve near κ≈0 throughout. CLM's own noref confidence stays high even when it's wrong,
  so it barely escalates even at high thresholds — a second, independent piece of evidence (beyond
  #1) that CLM is badly *miscalibrated* here, not just less accurate.

Full curves: `experiments/trust_or_escalate/summary.md`.

**By turn (Jev only)**: turn-2 items benefit *more* from escalation than turn-1 items — pure-ref
κ is 0.886 (turn 2) vs 0.810 (turn 1), and the τ=0.85 cascade point reaches 0.868 (turn 2) vs 0.817
(turn 1). Plausible reason: turn-2 correctness depends on multi-turn context that's harder for Jev to
track without a reference, but resolves cleanly once the reference is available. (Turn-1 pure-noref
κ=0.524 vs turn-2's 0.468 — turn 2 is the *harder* case noref, and the *more helped* case with ref.)

## 5. B5 (Jury-on-Demand) lite reproduction: reliability-weighting helps, but not enough to beat the single best judge

Substitution note: no XGBoost/embeddings available offline here, so reliability was predicted by a
from-scratch (numpy) logistic regression over *structural* features only (input-token count, turn,
annotator count, examinee model, the judge's own p/confidence) — a lite reproduction, treat as a lower
bound on the real method. Jury pool: 4 pseudo-judges (jev_noref, jev_ref, clm_noref, clm_ref), since
that's what we have on hand — note two of the four share a backend, which likely correlates their
errors more than genuinely independent judge models would.

| Strategy | κ |
|---|---|
| Single judge: jev_ref | **0.856** |
| Top-1 reliability-weighted | 0.834 |
| Top-2 reliability-weighted | 0.808 |
| Unweighted majority (all 4) | 0.553 |

Reliability-weighting clearly beats naive unweighted majority voting (0.834 vs 0.553) — confirming
the paper's core idea has real value over a static jury. But **no jury configuration, weighted or not,
beat simply always trusting the single best judge (jev_ref)**. Exhaustively checked all 15 non-empty
subsets of the 4 pseudo-judges (simple averaging, not even reliability-weighted): the ranking is
monotonic in "how much CLM is in the mix" — `jev_ref` alone is #1, adding any CLM judge only ever hurts,
and even `jev_noref + jev_ref` (both Jev, unweighted) already underperforms `jev_ref` alone (0.833 vs
0.856). See `experiments/jury_on_demand/summary.md`.

**Methodological gotcha worth flagging**: `clm_noref`'s reliability-predictor AUROC (0.820) is
*higher* than `jev_noref`'s (0.723), despite `clm_noref` being the far worse judge in absolute terms.
This is because `clm_noref` is nearly a constant predictor ("always incorrect"), so "will this judge
be right" collapses to "is the true label Incorrect" — trivially learnable from examinee-model identity
alone, and NOT a genuine measure of meta-judgment quality. A real deployment of this style of reliability
predictor needs a check against degenerate/near-constant judges, or it will over-trust judges that are
merely predictable rather than actually good.

## 1c. Root-cause hypothesis for CLM's failure, after ruling out three simpler explanations

Diagnostic chain, cheapest-to-rule-out first:
1. **Truncation** (`clm-serve` defaults to 2048-token states): fixed `--max-tokens 8192` to match the
   encoder, reran — numbers barely moved. Not the cause.
2. **Inverted true/false criteria mapping**: probed directly (`probe_clm_criteria.py`, n=60) by swapping
   the criteria text. Un-swapping the result (1-p) gave AUROC 0.536 vs normal's 0.409 — both within noise
   of chance, not "the other direction is clearly informative." Not the cause.
3. **The trained 20M-param head is what's broken** (the encoder/state pipeline would be fine on
   `clm-raw`, CLM's own ablation model that scores by cosine similarity in the raw encoder space,
   bypassing the head): tested directly, n=80 — equally degenerate (noref κ≈0, `pred_correct_rate`=0),
   and *worse* on ref (AUROC 0.148, i.e. below chance). Not the cause either.

**Working hypothesis, given all three are ruled out**: CLM's whole mechanism is retrieval by embedding
similarity between the *state* and short, generic *criteria descriptions* ("the final response is
substantively correct" vs "...contains a substantive error"). That works well for CLM's own benchmarks
(picking the right short action out of a few candidates — T-Rex moves, tool names, wiki links) where
the candidates are lexically/semantically distinct from each other. It's plausibly the wrong mechanism
for "is this specific multi-step financial calculation correct," where the two criteria descriptions are
topically generic and don't hinge on the actual numbers/facts in the response — an embedding-similarity
judge has little reason to place a response embedding closer to one generic description than the other
based on whether its arithmetic happens to be right. This is architecture-vs-task mismatch, not a
fixable bug in our integration, and not something fine-tuning trivially resolves either (fine-tuning
would need the SAME contrastive mechanism to learn to encode "is this arithmetic correct" into the
embedding geometry, which is a much harder ask than the short-action-selection tasks CLM was built for).

## Overall takeaway so far

Across every framing tried (raw judge accuracy, routing, dynamic jury, Trust-or-Escalate, Jury-on-Demand),
the same pattern holds: **on this data, identifying and trusting the single best available judge/model
beats every jury/ensemble variant we tried.** The dynamic-jury idea this project is centered on has a
real, calibratable win in the Trust-or-Escalate framing (cheap-then-strong cascade, not a same-tier
majority vote) — that's the strongest positive result so far. The weakest link across the board is
CLM-8B's zero-shot performance on this specific domain; a fine-tuned CLM head is the most promising
next experiment to actually stress-test the jury ideas with two *comparably competent* judges instead
of one strong (Jev) and one degenerate (CLM) one.

## Suggested next experiments (not yet run)

1. Given §1c's hypothesis, fine-tuning CLM on BFF-Bench-adjacent data (`train/finetune.py` ships in
   the repo) is a *real test of the hypothesis itself*, not just a fairness fix: if fine-tuning can't
   lift CLM off ~chance here, that's strong confirmation the contrastive-embedding mechanism is
   fundamentally mismatched to open-ended correctness verification, regardless of training data.
   If it *can*, the architecture-mismatch hypothesis is wrong or at least incomplete.
2. A faithful B5: real XGBoost + token-distribution/embedding features (needs the `contrastive-lm`
   embeddings or another embedding source, and an XGBoost install — both blocked by this network's
   PyPI restriction tonight; same wheel-transfer workaround as before would unblock it).
3. Recruit a 3rd genuinely independent judge (a third vendor/model) so B5's jury pool isn't half
   "the same backend under two conditions" — correlated errors between jev_noref/jev_ref likely
   understate how much a real, more diverse jury could help.
4. Turn-2 items (excluded from the router/jury experiments here because the pre-response context
   already differs per model) could still be analyzed for the *judge* task (Exp 1 already includes
   them) — done for Trust-or-Escalate (§4), worth extending to the router/jury framing too if turn-2
   candidate responses can be made comparable across models some other way.
5. Test CLM on a task closer to what it's actually built for (e.g. `examples/t_rex`, or a short
   best-of-N candidate selection over BFF-Bench-style multiple-choice-ified questions) as a sanity
   check that the specific deployment here isn't itself broken in some way the three ruled-out
   explanations didn't catch.
