# Cross-benchmark qualitative analysis

Repeats the BFF-Bench qualitative and judge-level analyses on every benchmark in
`docs/qualitative_analysis_plan_other_benchmarks.md`, tests a threshold jury against top-k, and asks what makes
items hard to judge. Open **`results/report.html`**: an overview tab, a question-analysis tab and one tab per
benchmark. The written findings are in `docs/qualitative_question_analysis.md`.

## Benchmarks

| Benchmark | Format | Items judged | Source of judge verdicts |
|---|---|---|---|
| BFF-Bench (2-of-3 labels) | single | 808 | `tinker_pool/run_judges.py --bench bff --consensus majority` |
| (C)MT-Bench | single | 228 | `run_judges.py --bench mtb --consensus majority` |
| BFF pairwise | pair | 884 | `run_judges.py --bench bffpair` |
| RewardBench 2 Safety | single | 1,800 | `run_judges.py --bench safety` |
| BBEH Mini | single | 920 | `run_answers.py --bench bbeh`, then `run_judges.py --bench bbeh --per-item 2 --max-tokens 8192` |
| JudgeBench (GPT-4o split) | pair | 700 | `run_xb_judges.py --bench judgebench --max-tokens 8192` |
| RewardBench 2 other (60 prompts per subset) | single | 960 | `run_xb_judges.py --bench rb2` |
| AlpacaFarm human cross-annotations | pair | 1,002 | `run_xb_judges.py --bench alpacafarm` |
| MT-Bench human (400 groups) | pair | 642 | `run_xb_judges.py --bench mtbhuman` |
| llm-judge-dpo-5k (15 distinct items) | pair | 30 | `run_xb_judges.py --bench dpo5k` |

TriviaQA (“Judging the Judges”) was not run: its human labels were never released.

## Pipeline

Run from the repo root with `uv run python experiments/cross_benchmark/<script> ...`. Every step caches its
API calls, so reruns only pay for what is missing. `--work` is the folder holding `tinker_pool/` and
`cross_benchmark/` (the repo's `experiments/` folder by default).

1. `xb_items.py`: one item table per benchmark, in a shared shape (`data/<bench>_items.pkl`).
2. `annotate.py --bench B`: six 0–3 demand codes per question (gpt-oss-120b), with a 20% second coder (Qwen3.6-35B).
3. `analyze_xb.py --bench B --work W`: judges, label agreement, error structure, aspects, answer models,
   length / position, and top-k vs threshold juries → `results/<bench>/analysis.json`.
4. `code_errors.py`: LLM-coded error types for the best judge's errors (DeepSeek-V3.1).
5. `probe_xb.py`: question-completion contamination probe (gpt-oss-120b vs qwen3.5-4b).
6. `xb_factors.py --work W`: what makes items hard and which judges are good at what → `results/factors.json`.
7. `code_content.py --bench B`: content coding of judge-hard vs judge-easy items (blind to which is which).
8. `build_report.py --work W --out results/report.html` (reads `results/takeaways.json` for the written summary).

Raw judgments (`*judgments.jsonl`) are git-ignored, like the other experiment caches.

## Order-flip and confidence study

Can the best judge's own confidence, or other judges changing their pick when the answer order is swapped, flag
the best judge's confident errors? Write-up: `docs/results_order_flip_study.md`; HTML report:
`reports/order-flip-study.html`. Tables go to `results/flips/`. Run from this folder, after steps 1 and 3 above
(the scripts read `data/<bench>_decisions.pkl`).

Stored verdicts only (no new calls):
1. `order_consistency.py`: per-judge flips and the first look at others' flips vs the best judge's errors.
2. `judge_pairs.py`: which judge catches which judge's confident errors, reciprocity, similarity.
3. `flip_analysis.py`: Stage A. Controls, matched strata, flips vs disagreement, siblings, solvability,
   label-free difficulty, checker sets, unflaggable floor. Also writes the pair feature tables.
4. `flip_followups.py`: unflaggable errors for inspection; AlpacaFarm split by human vote margin.
5. `flip_embeddings.py`: semantic controls and text-only flip prediction (local all-MiniLM-L6-v2).
6. `flip_threshold.py`: error rate by number of other judges flipping, for both pair conditions.

New calls (Tinker), then analysis:
7. `run_confidence.py`: verdict + stated confidence + verdict-token probability (+ full reasoning text).
   `build_ctrl_pairs.py` first builds the controlled BFF pairs for `--bench bffctrl`.
8. `conf_analysis.py <run> [bench ...]`: Stage B, confidence vs flips (`confidence_pilot` and `confidence`).
9. `stage_c.py`: controlled pairs and single-answer grading (RewardBench 2).
10. `roc_curves.py`: ROC curves for the report.
