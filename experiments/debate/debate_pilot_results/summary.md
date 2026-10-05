# Multi-judge debate pilot: Jev vs gpt-oss-120b, BFF-noref disagreement items

n=93 items where round-1 (independent) verdicts disagreed. Reconsidering arXiv:2608.30373's order-asymmetry finding -- every item debated in both orders.

## Round-1 accuracy on this (hard, disagreement-only) subset

- Jev alone: 0.269
- gpt-oss-120b alone: 0.731

## Round-2 (post-debate) final-verdict accuracy, by order

- Order A (Jev revises first, gpt-oss has last word): 0.828
- Order B (gpt-oss revises first, Jev has last word): 0.860

## Order-asymmetry / groupthink check

- Of 25 items where Jev was right and gpt-oss was wrong (round 1): debate ends up wrong 44% of the time under Order A, 24% under Order B.
- Of 68 items where gpt-oss was right and Jev was wrong (round 1): debate ends up wrong 7% of the time under Order A, 10% under Order B.
