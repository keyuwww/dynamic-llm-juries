# Tinker model pool: answer, judge, route

Runs the judge/answer-writer pool on Tinker and saves every output so later experiments reuse it.

Two phases, as discussed for the plan:

| Phase | What happens | Script |
|---|---|---|
| 1. Answer | Every pool model answers every question itself. Gives the "did it solve it?" label (the No Free Labels certificate) and, on BBEH, the candidate answers. | `run_answers.py` (+ `grade_bff_answers.py` for BFF) |
| 2. Judge | Every pool model grades candidate responses; verdicts are scored against gold labels. | `run_judges.py` |
| Router | Jev picks a model per question from the question alone, with the cost-aware prompts. | `run_router.py` |

Benchmarks wired up now: **BFF-Bench** (with VERDICTS as the human-labelled judging set) and **BBEH Mini**.
JudgeBench, RewardBench 2 and AlpacaEval only need Phase 2 loaders (responses are provided); next step.

## Setup (once)

```bash
uv sync                                  # installs tinker + tinker-cookbook (pulls torch, ~1-2 GB)
echo 'TINKER_API_KEY=...' >> .env        # .env is git-ignored; never commit or paste keys
```

`TYPESAFE_API_KEY` (Jev) must also be in `.env` or exported for the grading and router steps.
One Tinker key is enough: speed comes from concurrent requests (`--concurrency`), not from more keys.

## Tonight's run, in order

Do a dry run, then a small pilot, check the cost table, then the full runs. Every script resumes from
its cache, so rerunning a command only pays for what is missing.

```bash
# 0. offline dry runs (no keys, no cost): check the pipeline end to end
uv run python experiments/tinker_pool/run_answers.py --bench bff --mock --limit 3

# 1. Phase 1 on BFF-Bench: pilot, then all 80 conversations x 2 turns x 8 models
uv run python experiments/tinker_pool/run_answers.py --bench bff --limit 5
uv run python experiments/tinker_pool/run_answers.py --bench bff
uv run python experiments/tinker_pool/grade_bff_answers.py          # Jev + expert reference -> solve labels
#    optional robustness check of the proxy labels:
uv run python experiments/tinker_pool/grade_bff_answers.py --second-grader gpt-oss-120b

# 2. Phase 2 on BFF-Bench: judge the 459 consensus VERDICTS responses (none / self / human reference)
uv run python experiments/tinker_pool/run_judges.py --bench bff --limit 40     # pilot
uv run python experiments/tinker_pool/run_judges.py --bench bff

# 3. Jev as cost-aware router (question only)
uv run python experiments/tinker_pool/run_router.py --bench bff

# 4. BBEH Mini (auto-graded): answers, then cross-judging, then routing
uv run python experiments/tinker_pool/run_answers.py --bench bbeh --limit 40
uv run python experiments/tinker_pool/run_answers.py --bench bbeh
uv run python experiments/tinker_pool/run_judges.py --bench bbeh --per-item 2
uv run python experiments/tinker_pool/run_router.py --bench bbeh
```

Useful flags: `--models routing|strong|all|<keys>`, `--samples 5` (No Free Labels' 5-vote self-consistency;
one request, prefill paid once), `--thinking on` (reasoning renderers; much longer outputs), `--concurrency`.

## What to look at

- `bff_results/grades_summary.md` and `bbeh_results/answers_summary.md`: per-model accuracy and the
  **oracle − best single** gap. This decides the routing pool: keep models only if no single model
  dominates and the gap is ≥ ~0.08 (the original six BFF models gave ~0.04).
- `*_results/judges_summary.md`: judge κ per condition, the No Free Labels table (κ when the judge solved
  vs. failed the question), self-preference (BBEH), judge-routing headroom, cost.
- `*_results/router_summary.md`: your three Jev prompts vs. the explicit "cheapest model with P ≥ τ" rule,
  scored on accuracy, $ per call, overshoot and miss rates, against random / best-single / cheapest / oracle.
- Every `*_summary.md` has a measured cost table: use it to budget the full sweep.

## Rough cost (8 models, 1 sample)

| Step | Calls | Est. cost |
|---|---|---|
| Phase 1 BFF answers | 80 × 2 × 8 = 1,280 | ~$3 |
| Jev grading of those | 1,280 | ~$0.10 |
| Phase 2 BFF judging | 459 × 3 × 8 ≈ 11k | ~$100–150 (DeepSeek is ~⅓ of it; drop it with `--models routing`) |
| Jev router (BFF) | 80 | <$0.05 |
| Phase 1 BBEH answers | 460 × 8 = 3,680 | ~$15–30 |
| Phase 2 BBEH judging | 920 × 2 × 8 ≈ 15k | ~$40–80 |

These are estimates from assumed token counts; the summaries report the real numbers after the pilots.

## Notes and caveats

- Pool, model ids and prices live in `common.py` (`POOL`). Strong tier = `gpt-oss-120b`, `deepseek-v3.1`.
- Thinking is **off** by default (no-thinking renderers for Qwen, Nemotron, DeepSeek). GPT-OSS always reasons.
  Mixing reasoning and non-reasoning models is fine for routing, but report it.
- BFF solve labels for new models come from Jev + expert reference (κ = 0.856 vs. humans in Exp 1):
  proxy labels, say so in the paper; the `--second-grader` agreement table shows how noisy they are.
- BBEH Mini has no task field; tasks are inferred as blocks of 20 (`block00`…`block22`). Spot-check.
- Mock files (`*_mock.jsonl`) are separate from real caches, so dry runs never mix with real results.
