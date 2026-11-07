# Smoke test: Qwen3.5-0.8B, forced verdict, thinking off

## bff  (n=100, 50 positive, mean 1114 tokens, 0 truncated)

- Verdict: says positive 44%, accuracy 66%, AUROC 0.66; P(pos)+P(neg) mass 0.97
- Hidden-state probe (5-fold grouped CV, best layer 2, optimistic): AUROC 0.81
- Logit lens best layer 17: AUROC 0.74 (final layer 0.66)

| layer | 0 | 4 | 8 | 12 | 16 | 20 | 24 | last |
|---|---|---|---|---|---|---|---|---|
| probe | 0.42 | 0.75 | 0.76 | 0.76 | 0.79 | 0.79 | 0.80 | 0.80 |
| lens | 0.50 | 0.33 | 0.63 | 0.51 | 0.74 | 0.62 | 0.66 | 0.66 |

## judgebench  (n=100, 50 positive, mean 1625 tokens, 0 truncated)

- Verdict: says positive 78%, accuracy 56%, AUROC 0.55; P(pos)+P(neg) mass 0.99
- Hidden-state probe (5-fold grouped CV, best layer 14, optimistic): AUROC 0.64
- Logit lens best layer 23: AUROC 0.56 (final layer 0.55)
- Position bias: same position picked in both orders for 76% of 50 pairs

| layer | 0 | 4 | 8 | 12 | 16 | 20 | 24 | last |
|---|---|---|---|---|---|---|---|---|
| probe | 0.50 | 0.51 | 0.54 | 0.54 | 0.53 | 0.51 | 0.52 | 0.52 |
| lens | 0.50 | 0.52 | 0.49 | 0.46 | 0.55 | 0.54 | 0.55 | 0.55 |

## rb2safety  (n=100, 50 positive, mean 375 tokens, 0 truncated)

- Verdict: says positive 4%, accuracy 48%, AUROC 0.58; P(pos)+P(neg) mass 0.99
- Hidden-state probe (5-fold grouped CV, best layer 22, optimistic): AUROC 0.92
- Logit lens best layer 19: AUROC 0.68 (final layer 0.58)

| layer | 0 | 4 | 8 | 12 | 16 | 20 | 24 | last |
|---|---|---|---|---|---|---|---|---|
| probe | 0.50 | 0.81 | 0.84 | 0.87 | 0.90 | 0.91 | 0.91 | 0.91 |
| lens | 0.50 | 0.23 | 0.40 | 0.50 | 0.50 | 0.60 | 0.58 | 0.58 |
## Surface-feature baselines (same items, same grouped 5-fold CV)

| Benchmark | Verdict AUROC | Probe AUROC (best layer) | Surface-only AUROC |
|---|---|---|---|
| bff | 0.66 | 0.81 | 0.72 (length) / 0.78 (answer model + length) |
| rb2safety | 0.58 | 0.92 | 0.60 (length) / 0.72 (refusal phrases + length) |
| judgebench | 0.55 | 0.64 (layer 14; ~0.52 elsewhere) | n/a |

- BFF real answers: the probe barely beats which model wrote the answer plus its length, so at this size the
  "gap" is mostly that confound (as in judge_confidence findings §8). The clean test needs planted-error pairs.
- RB2-Safety: the probe clears the surface baseline by ~0.20 while the verdict says INCORRECT 96% of the time:
  the clearest "knows but doesn't say" case for the 0.8B judge.
- JudgeBench: no signal in any layer and a strong position bias (same slot picked in both orders for 76% of
  pairs, "A" 78% of the time): an ability gap plus a bias, the Gemma-like case.
