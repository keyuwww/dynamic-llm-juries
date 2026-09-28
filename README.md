# Dynamic LLM Juries

AC297r capstone (Harvard IACS, Fall 2026). Team 10, partnered with Kensho R&D (Seth Ebner, Chris Tanner).

**Goal:** make LLM juries more reliable by choosing, for each question, which judges get to grade it. The working idea is a "Jev for juries": a fast, cheap model that predicts, before any judge is called, how likely each judge is to answer the question correctly. Only confident judges vote, their votes are weighted by that probability, and the question is escalated when no judge qualifies.

Background:

- [No Free Labels](https://arxiv.org/abs/2503.05061) (Kensho): judges agree with humans mainly on questions they can solve themselves.
- [Trust or Escalate](https://arxiv.org/abs/2407.18370): selective judging with guarantees on how often the judge agrees with humans.

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
docs/                 method plan and literature notes
experiments/
  jev_bff/            Exp 1: Jev as a correctness judge on BFF-Bench (baseline B7)
requirements.txt
```

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

API keys go in environment variables (`TYPESAFE_API_KEY`, etc.). Never commit them; `.env` is git-ignored.

## Data

All public on Hugging Face (Apache 2.0):

- [`kensho/BFFBench`](https://huggingface.co/datasets/kensho/BFFBench): 80 two-turn finance questions with expert references.
- [`kensho/VERDICTS`](https://huggingface.co/datasets/kensho/VERDICTS): human correct/incorrect labels on model responses from six models.

## Team

Methods: Andrew, Keyu · Closed-ended benchmarks: Ingrid · Open-ended benchmarks: Janys · Implementation: Isaac, Minh
