# Diversity / error-overlap analysis: mixed-architecture vs. same-family agreement

Phi coefficient (binary correlation) of per-item correctness between judge pairs. Lower correlation = more independent errors = more ensemble value from combining them.

## BFF noref (n=459)

- Mean intra-Tinker-pool correctness correlation: 0.357
- Mean intra-HTTP-backend (Jev/Laya/jeff) correctness correlation: -0.083
- Mean cross-family (HTTP vs. Tinker) correctness correlation: 0.187

Unique catches (judge right, Tinker-8 majority wrong):
  - jev: 28 items
  - laya: 54 items
  - jeff: 63 items
Tinker-8 majority right, HTTP-judge majority wrong: 43 items

## BFF ref (n=456)

- Mean intra-Tinker-pool correctness correlation: 0.432
- Mean intra-HTTP-backend (Jev/Laya/jeff) correctness correlation: -0.120
- Mean cross-family (HTTP vs. Tinker) correctness correlation: 0.211

Unique catches (judge right, Tinker-8 majority wrong):
  - jev: 11 items
  - laya: 32 items
  - jeff: 5 items
Tinker-8 majority right, HTTP-judge majority wrong: 14 items

## Safety (n=1800)

- Mean intra-Tinker-pool correctness correlation: 0.456
- Mean intra-HTTP-backend (Jev/Laya/jeff) correctness correlation: 0.106
- Mean cross-family (HTTP vs. Tinker) correctness correlation: 0.256

Unique catches (judge right, Tinker-8 majority wrong):
  - jev: 136 items
  - laya: 177 items
  - jeff: 166 items
Tinker-8 majority right, HTTP-judge majority wrong: 256 items
