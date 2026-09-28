# Methods plan: baselines & method paths

Methods track (Andrew & Keyu), Sept 2026. The full paper-by-paper review (64 papers) is in the team Drive folder.

## The idea

Build a **"Jev for juries"**: a small, fast model that reads a question and outputs, for every judge in the pool, P(judge answers this question correctly). Only judges with a high probability grade the question, and their votes are weighted by that probability. When no judge qualifies, the question is escalated.

- **Why it should work:** judges agree with humans on questions they can solve themselves. This comes from No Free Labels, from JudgeBench, and from Zhang et al. 2026, who report r > 0.90 between task accuracy and judging accuracy.
- **Why it is Jev-like:** it runs before any judge is called, costs about one embedding, and returns a calibrated probability.
- **Why it is cheap to train:** on closed-ended sets we only need each judge's answers checked against gold, not new human labels.

## Baselines

| ID | Baseline | What it is | Source |
|---|---|---|---|
| B0 | Human reference | Judge sees the expert reference answer (upper bound) | [No Free Labels](https://arxiv.org/abs/2503.05061) |
| B1 | Best single judge | Highest-κ judge on a dev split, used for every question | the bar to beat |
| B2 | Static jury | All judges vote; majority wins | [PoLL](https://arxiv.org/abs/2404.18796) |
| B3 | Weighted static jury | Votes weighted by each judge's estimated error rates | [Zhang et al. 2026](https://arxiv.org/abs/2609.12002) |
| B4 | Oracle certification | Only judges that answered this question correctly vote; falls back to the full jury | Kensho proposal |
| B5 | Jury-on-Demand | XGBoost reliability predictor per judge; top-K weighted | [Li et al. 2025](https://arxiv.org/abs/2512.01786) |
| B6 | Trust or Escalate | Cheap judge → stronger judge cascade with calibrated abstention | [Jung et al. 2025](https://arxiv.org/abs/2407.18370) |
| B7 | Jev | Jev answers "is this correct?"; accept if confident, else escalate | [JEV-as-a-Judge](https://arxiv.org/abs/2609.26550) |

Start with B1, B2 and B4. All three come from one run of every judge on every question.

## Path A: Certifier router (core, Jev-like)

1. **kNN:** P(correct) = the judge's accuracy on the k most similar training questions ([kNN routers](https://arxiv.org/abs/2505.12601)).
2. **Matrix factorization:** a question × judge model in the style of [EmbedLLM](https://arxiv.org/abs/2410.02223) / [IRT-Router](https://aclanthology.org/2025.acl-long.761/).
3. **Optional activation probe:** a probe on one open model's hidden states predicts a certification vector for every judge at once ([NVIDIA prefill router](https://arxiv.org/abs/2603.20895)).
4. **Jev as certifier:** ask Jev "will judge j answer this correctly?" and compare with the kNN certifier.

**Key number:** how much of the oracle gain (B4 − B1) survives when certification is predicted rather than known.

## Path B: Jury protocol

- **Solve-then-judge:** each judge answers the question first, then grades against its own answer ([Do Before You Judge](https://aclanthology.org/2025.findings-emnlp.1342/)).
- **Pick diverse judges, not just the top K:** judges make correlated mistakes; nine judges carry only about two independent votes ([Kohli 2026](https://arxiv.org/abs/2605.29800)). Drop redundant judges ([Stopping & Routing Judge Panels](https://arxiv.org/abs/2608.19802)).
- **Recusal:** a judge does not grade answers from its own model family.
- **Weighting:** votes are weighted by the certifier's log-odds.

## Path C: Guaranteed cascade

1. **Tier 0:** Jev, or two small judges that agree, accepts easy questions when confident.
2. **Tier 1:** the certified jury from Paths A and B.
3. **Tier 2:** if no judge is certified, a stronger model writes a reference and the jury re-judges against it ([Judge, Retrieve, or Abstain](https://arxiv.org/abs/2608.17994)), or the question goes to a human.

Thresholds are calibrated so that agreement on accepted questions is at least the target, with high probability (Trust or Escalate). **Output:** a curve of agreement vs cost vs coverage.

## Next steps

1. Build the judge × question matrix on BFF-Bench (plus one open-ended set).
2. Reproduce B1, B2 and B4 with solve-then-judge. If B4 does not beat B1, make cost the main claim, using the Path C cascade.
3. Path A v1: kNN certifier vs Jev as certifier.
4. Add Path B, then Path C. Compare against B3 and B5–B7.

## Questions for Kensho

- Is the headline claim "beat the best single judge on κ", or "match it at lower cost"?
- Can we use the BFF-Bench gold answers to train the certifier?
- Is there Jev access or credit available?
