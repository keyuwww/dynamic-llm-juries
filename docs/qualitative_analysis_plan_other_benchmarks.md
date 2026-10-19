# Repeating the BFF-Bench qualitative analysis on other benchmarks

Plan for running the same qualitative and judge-level analyses we did on BFF-Bench on every other benchmark
the team has used or been pointed to. Sources:

- this repo (`experiments/`)
- the Meeting Notes doc: 9/28 benchmark notes, 10/5 meeting, Ingrid's 10/9 JudgeBench update
- the papers in our literature table

The team's benchmark Google Sheet wasn't readable from here, so check it for anything missing below.

## 1. What "the BFF analysis" consists of

These are the steps to repeat. Each benchmark gets the ones its data supports (see the matrix in §3).

| ID | Step | BFF version |
|---|---|---|
| A | **Coverage and taxonomy**: domain, subtopic and task tags per question | `bff_annotation`, `questions_annotated` |
| B | **Demand scores**: 0–3 ordinal aspects plus a difficulty band, coded from the question alone | `methods/RUBRIC.md` (K, Q, R, I, C) |
| C | **Question audit**: review flags, stated assumptions, source-integrity checks (like the Q18 mismatch), sensitivity of the difficulty band to a one-point change | `annotation_audit_log`, `composite_score_sensitivity` |
| D | **Label audit**: vote patterns, unanimous vs 2-of-3 gold rule, κ on split-vote items | `docs/advisor_questions_bff.md` Q4, `compare_label_rules.py` |
| E | **Candidate outcomes by aspect**: answering accuracy per model × domain/aspect, with fixed denominators | `model_capability_summaries` |
| F | **Answering complementarity**: oracle vs best single, rescue rates, pairwise error phi between candidate models | `answering_rescue_pairs` |
| G | **Aspect strengths**: model × aspect interaction (relative score, permutation test, BH correction), for candidates and judges | `experiments/aspect_strengths` |
| H | **Judge error structure**: pairwise error phi between judges, "everyone wrong" vs independence, error patterns of the best judge, coding of its reasoning traces | `advisor_questions_bff.md` Q1/Q3 |
| I | **Contamination probe**: reference completion and masked-number recall against a control model | `tinker_pool/probe_contamination.py` |
| J | **Response descriptors**: length and formatting indicators, and their association with judge verdicts (length bias) | `responses_with_human_outcomes` |

## 2. Benchmarks

**Status:** ✅ judged in repo · 🟡 loader only or partial · 🔵 used by a teammate outside this repo ·
⚪ suggested, not loaded.

Figures marked (check) are from memory and should be confirmed before planning around them.

| # | Benchmark | Where it came from | Format | Gold label | Size | Candidate models | Status |
|---|---|---|---|---|---|---|---|
| 1 | **(C)MT-Bench half of VERDICTS** (`kensho/VERDICTS`, `kensho/CMTBench`) | No Free Labels; Tinker pool `--bench mtb` | Single grading, 2 turns, open-ended | 3 expert votes (same scheme as BFF) | 40 turns × 6 models = 240 responses; 177 unanimous | Same 6 as BFF | ✅ 8 judges, none + human |
| 2 | **BFF-Bench pairwise** (`kensho/VERDICTSPairwise`) | No Free Labels; `--bench bffpair` | Pairwise, one correct vs one incorrect answer | Human pick | 442 pairs × 2 orders = 884 | Same 6 as BFF | ✅ 8 judges |
| 3 | **RewardBench 2 Safety** (`allenai/reward-bench-2`) | 10/5 meeting; `safety_judge.py`, `--bench safety` | Single grading of chosen/rejected | Human chosen/rejected, 1 label per response | 450 prompts → 1,800 responses | Mixed generators (check) | ✅ 8 Tinker judges + Jev, Jeff, Laya, CLM |
| 4 | **BBEH Mini** | 10/5 meeting; `--bench bbeh` | Pool answers, then judges grade them | Auto-grader against the answer key | 460 questions, 23 tasks (inferred blocks of 20) | Our 8 pool models (Phase 1) | 🟡 loader and scripts exist; no results in repo |
| 5 | **JudgeBench** | 9/28 advisor recommendation; Ingrid (SHAP, 10/9) | Pairwise, objectively correct vs incorrect | Verifiable ground truth | ~350 GPT-4o pairs (check) | One source model (GPT-4o) | 🔵 Ingrid's runs; not in this repo |
| 6 | **RewardBench 2, other subsets** (Factuality, Precise IF, Math, Focus, Ties) | 10/5: allowed if marked LLM-labeled | Best-of-4 | Mostly LLM or algorithmic labels | ~1.4k prompts (check) | Mixed | ⚪ |
| 7 | **AlpacaEval / AlpacaFarm human preferences** | Tinker README "next step" list | Pairwise, open-ended instructions | Crowd human preferences, several per pair (check) | ~2.5k cross-annotations (check) | Several | ⚪ |
| 8 | **MT-Bench human judgments** (`lmsys/mt_bench_human_judgments`) | MT-Bench / Wang et al. in our literature table | Pairwise, 2 turns | Expert human votes | ~3.3k votes, 80 questions × 6 models (check) | 6 models | ⚪ |
| 9 | **TriviaQA judge set** ("Judging the Judges") | Literature table | Single grading against a short reference | 3 human labels, majority vote | 400 questions × 9 exam-takers (check) | 9 models | ⚪ |

Also mentioned but out of scope:

- **Humanity's Last Exam:** too hard for our budget (9/28).
- **Math/code with verifiers:** these need no LLM judge (9/28).
- **SuiteTogether:** dynamic multi-turn, not a fixed dataset.
- **`stindardlogic/llm-judge-dpo-5k`:** checked 2026-10-16 and excluded as a benchmark.
  - **Only 15 distinct items.** Its 5,000 rows are 15 unique (prompt, chosen, rejected) triples, one per
    category, each copied 290–375 times.
  - **The labels aren't independent gold.** "Chosen" is a calibrated critique and "rejected" a deliberately
    miscalibrated one, written by an undocumented process. The card names no humans, no source datasets and
    no generating models, and the data is tagged synthetic.
  - **It has no test split** and no gold answers to the underlying questions.
  - **At most, use it as a 15-item bias checklist** for judges: verbosity, leniency, missed errors, format
    excuses. Treat it as a sanity check, not a measurement.
- **Trust-or-Escalate data** (Chatbot Arena, TL;DR) and **Jury-on-Demand data** (summarization, RAG): only
  if we reproduce those baselines on their own data.

## 3. Which steps apply to which benchmark

✔ = applies as on BFF · ◐ = applies with a changed rubric or a weaker version · ✘ = not possible with this data.

| Step | 1 MT-Bench | 2 BFF pair | 3 RB2 Safety | 4 BBEH | 5 JudgeBench | 6 RB2 other | 7 AlpacaEval | 8 MT-Bench human | 9 TriviaQA |
|---|---|---|---|---|---|---|---|---|---|
| A Taxonomy | ✔ (8 categories) | reuse BFF | ◐ harm categories | ✔ 23 tasks | ✔ source dataset | ✔ subset | ◐ | ✔ | ◐ |
| B Demand scores | ◐ new rubric | reuse BFF | ◐ new rubric | ◐ new rubric | ◐ new rubric | ◐ | ◐ | ◐ reuse #1 | ◐ |
| C Question audit | ✔ | reuse BFF | ✔ | ✔ | ✔ | ✔ | ◐ | ✔ | ✔ |
| D Label audit | ✔ 3 votes | ◐ | ✘ 1 label | ✘ auto | ✘ auto | ✘ | ✔ several votes | ✔ | ✔ 3 votes |
| E Outcomes by aspect | ✔ | ✘ | ◐ by generator, if known | ✔ | ✘ one model | ◐ | ◐ | ✔ | ✔ |
| F Answering complementarity | ✔ | ✘ | ✘ | ✔ | ✘ | ✘ | ✘ | ✔ | ✔ |
| G Aspect strengths | ✔ | ◐ | ◐ | ✔ | ◐ judges only | ◐ | ◐ | ✔ | ✔ |
| H Judge error structure | ✔ have verdicts | ✔ have verdicts | ✔ have verdicts | ✔ after Phase 2 | ✔ (Ingrid's verdicts) | ✔ | ✔ | ✔ | ✔ |
| I Contamination | ✔ | reuse BFF | ✔ | ✔ high risk, popular benchmark | ✔ | ✔ | ✔ | ✔ high risk, old | ✔ high risk, old |
| J Response descriptors | ✔ | ✔ + position bias | ✔ | ✔ | ✔ + position bias | ✔ | ✔ | ✔ | ✔ |

## 4. Priority order

1. **(C)MT-Bench (#1).** Same annotators, label scheme and candidate models as BFF, and judge verdicts
   already exist. It tests whether BFF findings hold on open-ended questions with no other change, which is
   the advisor's "do your findings hold on other datasets" question.
2. **RB2 Safety (#3).** Verdicts exist for 12 judges, including Jev and Jeff. It is the one domain where a
   different judge (gpt-oss-20b) is best, so it is the best test of the shared-error (Q1) finding.
3. **JudgeBench (#5).** Ingrid already has verdicts and SHAP features. The work is converting them to the
   shared decisions table and adding steps C, H and I.
4. **BFF pairwise (#2).** Steps H and J only: position and length bias on the same questions as BFF.
5. **BBEH Mini (#4).** Needs Phase 1 answers and Phase 2 judging first (about $55–110 by the Tinker README
   estimate). Run a 40-question pilot before the full set.
6. **#6–#9.** Add loaders only if 1–5 leave open questions. #8 and #9 are the best extra tests of label
   ambiguity (step D), since they have several human votes per item.

## 5. Shared setup (do once, before per-benchmark work)

1. **One decisions table for every benchmark.** Extend `judge_decisions/build_judge_decisions.py` to emit
   the `decisions.csv` schema for any `--bench`, with these columns:
   `item_id, question_key, benchmark, category, aspect columns…, examinee, human, n_votes, vote_pattern,
   judge, condition, verdict, agree, score, raw`.
   Then `aspect_strengths`, `jury_size.py`, the Q1/Q3 analysis and `compare_label_rules.py` run unchanged.
2. **Shared rubric core plus per-benchmark extensions.** Keep the BFF codebook's format: ordinal 0–3 anchors,
   coded from the question only, never from candidate correctness. Each benchmark gets a short extension
   file in `experiments/<bench>_annotation/methods/RUBRIC.md` (proposed aspects in §6).
3. **Annotation reliability.** Have two coders, or two independent LLM passes, score the same 20% of
   questions blind, and report weighted κ per aspect before using the scores. BFF never had this step
   (its report flags reliability as unvalidated), so add it here and backfill BFF.
4. **Splits.** Use the same conversation- or prompt-level 60/20/20 split method as BFF, stratified by
   category, frozen before any judge analysis.
5. **Make Q1/Q3 a script.** The Q1/Q3 analysis currently lives in a scratch file. Move it to
   `judge_decisions/judge_error_patterns.py`, with grouping columns as an argument.

## 6. Proposed aspect rubrics per benchmark (step B)

| Benchmark | Aspects to code (0–3 unless noted) |
|---|---|
| (C)MT-Bench | **Kept from BFF:** knowledge, numerical execution, information integration, conversation dependence. **New:** open-endedness (one right answer → many acceptable), instruction constraints (count of explicit format or length rules) |
| RB2 Safety | **Harm severity** if complied with. **Request legitimacy:** should comply / borderline / should refuse. **Intent ambiguity.** **Over-refusal bait:** benign but sounds harmful |
| BBEH | Task family (nominal), reasoning steps, input length / information integration, answer type (nominal: MCQ / number / free text), adversarial distractors |
| JudgeBench | Source (nominal: MMLU-Pro, LiveBench, LiveCodeBench), knowledge, reasoning steps, how close the two answers are (wording overlap of the pair), verifiability of the final answer |
| Pairwise sets (#2, #7, #8) | Per pair: length difference, formatting difference, quality gap (1 if one answer is clearly wrong, 3 if subtle) |

## 7. Test plan per step

For every benchmark, each step has a definition of done. A step counts as done only when its checks pass.

| Step | Procedure | Checks before reporting |
|---|---|---|
| A | Assign one primary category per item from the benchmark's own field, or code it if absent. Add tags | Counts per category reported. Any category with fewer than 20 items is starred and kept out of headline claims |
| B | Code aspects from question text only, with candidate answers hidden. Store rationale and assumptions per item | Blind double-coding agreement: weighted κ ≥ 0.6 per aspect, or the aspect is dropped. Band sensitivity to a one-point change reported |
| C | Flag ambiguous or convention-dependent items. Check the source integrity of question–reference–response joins | Joins validated with hashes. Every exclusion logged with a reason. Flagged items analysed both with and without them |
| D | Tabulate vote patterns. Score each judge under unanimous and 2-of-3 rules | The published paper's counts are reproduced when it reports them (e.g. 808 for BFF). Headline κ uses the published rule. κ on split-vote items reported separately |
| E | Accuracy per candidate × category/aspect, with fixed denominators | The original benchmark's per-model accuracy is reproduced before any new cut. Known-label vs all-items denominators are stated |
| F | Oracle − best single, rescue rate per model pair, error phi | Same item set for every model. A conversation-bootstrap CI on oracle − best |
| G | Run `aspect_strengths` with permutation by conversation or prompt | Benjamini–Hochberg q < 0.1 to call an interaction. Report effect sizes, not just q |
| H | Judge error phi matrix. Observed vs independent "all right" / "≥6 wrong". Best judge's FP/FN rates by category. Hand-code 30 of its errors (or all, if fewer) into a fixed error taxonomy | The taxonomy is fixed on the first 10 errors, then applied to the rest. A second coder codes 10 of them |
| I | `probe_contamination.py` (extend to each benchmark's text fields), with the same control model | Every "specific" hit checked by hand for derivability. Results compared against the control, not read as absolute rates |
| J | Length and formatting features. Their association with judge verdicts conditional on the human label; position swap for pairwise | Pairwise: both presentation orders judged, and a tie counted when they disagree (as in No Free Labels) |

**Repeat-sampling requirement for H and D.** The current Tinker runs use 1 sample per verdict, so judge
confidence is always 0 or 1. Rerun the best two judges per benchmark with `--samples 5` to get vote shares
for calibration and selective-judging curves.

## 8. Cross-benchmark synthesis

The deliverable is one table answering "do the BFF findings hold?":

| Finding on BFF | Test on each benchmark |
|---|---|
| The best single judge beats every jury | Best single vs majority vote of 3/5/8, cross-validated (`jury_size.py`) |
| Judges' errors are strongly correlated (mean phi 0.39) | Mean and min pairwise phi. Observed vs independent "all wrong" |
| Judges fail on the questions candidates fail (No Free Labels) | κ when the judge solved vs failed the item (needs step F answers) |
| The unanimous-only gold rule inflates κ (0.70 → 0.60) | Step D on #1, #7, #8, #9 |
| The best judge's errors cluster by category, not by examinee | Step H by category and by examinee |
| With a reference, the judge rejects correct answers for small deviations | Step H on the `human` condition |
| No memorization signal | Step I against the control model |

## 9. Budget (rough)

Known costs come from earlier runs; new ones assume 8 judges and 1 sample.

- **#1, #2, #3:** $0. Verdicts already exist; the work is annotation and analysis.
- **Contamination probe:** about $0.50 per benchmark for 3 models.
- **5-sample reruns of 2 judges:** about $5–15 per benchmark.
- **BBEH Phase 1 + 2:** about $55–110 (Tinker README estimate).
- **New loaders (#6–#9):** about $5–40 each for judging, depending on size.
