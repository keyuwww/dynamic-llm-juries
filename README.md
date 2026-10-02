# Dynamic LLM Juries

AC297r capstone (Harvard IACS, Fall 2026). Team 10, partnered with Kensho R&D (Seth Ebner, Chris Tanner).

**Goal:** make LLM juries more reliable by choosing, for each question, which judges get to grade it. The working idea is a "Jev for juries": a fast, cheap model that predicts, before any judge is called, how likely each judge is to answer the question correctly. Only confident judges vote, their votes are weighted by that probability, and the question is escalated when no judge qualifies.

Background:

- [No Free Labels](https://arxiv.org/abs/2503.05061) (Kensho): judges agree with humans mainly on questions they can solve themselves.
- [Trust or Escalate](https://arxiv.org/abs/2407.18370): selective judging with guarantees on how often the judge agrees with humans.
- [Jury-on-Demand](https://arxiv.org/abs/2512.01786): per-judge reliability predictors pick a dynamic top-K jury per question.
- [CLM (Contrastive Language Models)](https://github.com/Contrastive-LM/CLM): open-weight alternative to Jev, served ourselves on Modal.

## Results so far

Jev vs CLM-8B on BFF-Bench, as a correctness judge, a router among 6 candidate models, and B5/B6
lite reproductions — **[dashboard (charts)](https://claude.ai/artifact/5TJcc7Lh1MD2g1Kyd3asHx)** ·
**[full write-up](docs/findings_zeroshot_juries.md)**.

Headline: Jev is a solid judge (beats No Free Labels' own GPT-4o numbers) but, like every jury/ensemble
variant we've tried so far (dynamic jury, Jury-on-Demand-style reliability weighting), it doesn't beat
simply routing everything to the single best available judge. The one exception is Trust-or-Escalate:
a confidence-gated cheap→strong cascade genuinely beats always using either tier alone. CLM-8B is
currently near-chance on this domain zero-shot — root-caused (not just observed) in the write-up.

## Baselines

| ID | Baseline | Role |
|---|---|---|
| B0 | Judge given the human reference answer | Upper bound |
| B1 | Best single judge | The bar to beat |
| B2 | Static jury, majority vote ([PoLL](https://arxiv.org/abs/2404.18796)) | Standard jury |
| B3 | Weighted static jury (Dawid–Skene / [label-free weighted majority](https://arxiv.org/abs/2609.12002)) | Strongest jury that doesn't choose judges per question |
| B4 | Oracle certification: only judges that answered correctly vote | Upper bound for our method |
| B5 | [Jury-on-Demand](https://arxiv.org/abs/2512.01786) | Closest prior work |
| B6 | [Trust or Escalate](https://arxiv.org/abs/2407.18370) cascade | Cost/coverage baseline |
| B7 | Jev as judge or first filter ([JEV-as-a-Judge](https://arxiv.org/abs/2609.26550)) | Existing fast router |

Metrics:

- Agreement with humans: Cohen's κ and Krippendorff's α (α handles a jury whose members change per question).
- Cost per 1k judgments.
- Latency.
- Coverage: the share of questions not escalated.

## Method paths

- **A. Certifier router:** predict P(judge j answers question q correctly) from the question alone. Models to try, in order: kNN over embeddings, then an EmbedLLM-style matrix factorization, then an activation probe. Also test Jev as the certifier.
- **B. Jury protocol:**
  - solve-then-judge: each judge answers the question itself first, then grades against its own answer;
  - pick certified judges whose mistakes don't overlap;
  - recusal: a judge doesn't grade answers from its own model family;
  - weight votes by the certifier's log-odds.
- **C. Guaranteed cascade:**
  1. Jev as tier 0 handles easy questions.
  2. Certified jury.
  3. If no judge is certified: a stronger model writes a reference answer, or the question goes to a human.

  Thresholds are calibrated Trust-or-Escalate style.

Details: [`docs/methods_plan.md`](docs/methods_plan.md)

## Repo layout

```
docs/                        method plan, literature notes, and findings write-ups
experiments/
  jev_bff/                  Exp 1: judge (Jev or CLM) as a correctness grader on BFF-Bench (B0/B7)
  jev_router/               Exp 2: judge as a router/certifier among 6 candidate models (path A) + dynamic jury
  trust_or_escalate/        B6 reproduction: cheap->strong cascade, reused from Exp 1's noref/ref pairs
  jury_on_demand/           B5 lite reproduction: reliability-weighted top-K jury voting
  common/backends.py        shared Jev/CLM client wrapper so experiments run with --backend jev|clm
  clm_modal.py              deploy CLM-8B (vLLM + clm-serve) on a Modal GPU and run the experiments against it
  compare_backends.py       merges {jev,clm}_*_results/metrics.json into one comparison table
  dashboard.html            source for the published dashboard artifact (see Results above)
pyproject.toml
```

## Setup

Uses [uv](https://docs.astral.sh/uv/) for dependency management:

```bash
uv sync
```

This creates `.venv` and installs everything from `pyproject.toml`/`uv.lock`. Run scripts with `uv run`, e.g. `uv run python experiments/jev_bff/run_jev_bff.py ...`.

API keys go in environment variables (`TYPESAFE_API_KEY`, etc.). Never commit them; `.env` is git-ignored.

To also run experiments against CLM-8B, you need a Modal account (`uv run modal setup`) and a GPU budget
— `uv run modal run experiments/clm_modal.py --judge` deploys CLM on a GPU, runs the router + judge
experiments against it, and pulls the results back into `experiments/*/clm_*_results/`. See the header of
`clm_modal.py` for options (`--limit`, `--judge-limit`, `--probe`, `--clm-model clm-raw`).

## Data

All public on Hugging Face (Apache 2.0):

- [`kensho/BFFBench`](https://huggingface.co/datasets/kensho/BFFBench): 80 two-turn finance questions with expert references.
- [`kensho/VERDICTS`](https://huggingface.co/datasets/kensho/VERDICTS): human correct/incorrect labels on model responses from six models.

## Team

Methods: Andrew, Keyu · Closed-ended benchmarks: Ingrid · Open-ended benchmarks: Janys · Implementation: Isaac, Minh
