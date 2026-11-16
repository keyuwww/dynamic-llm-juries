# Push while solving (Qwen3.5-9B, RB2 Math)

The belief direction (held-out half, layers 14–26) is pushed while the judge solves the question with no candidate shown; 7 answers per question at T = 0.7. Belief in a candidate = share of those answers that reach the candidate's answer (GLM-5.3-Flash). A new answer with the same boxed answer as one of the judge's original solves reuses that solve's GLM verdict; the rest are matched by GLM directly. Answers still unmatched or cut off are left out. Changes are against the no-push run; 95% intervals resample questions.

| condition | answers | still cut off | reused match | new GLM match | unmatched | mean length (tokens) |
|---|---|---|---|---|---|---|
| no push | 1281 | 6 | 1164 | 111 | 0 | 1339 |
| belief −6 sd | 1281 | 11 | 1033 | 237 | 0 | 2360 |
| belief +6 sd | 1281 | 17 | 960 | 304 | 0 | 1691 |
| random −6 sd | 1281 | 21 | 830 | 430 | 0 | 2026 |

Mean belief (share of the 7 answers reaching the candidate), and change vs no push:

| condition | wrong, originally believed (≥ 1/7) | wrong, never reached | correct |
|---|---|---|---|
| no push | 70% (n=83) | 1% (n=424) | 84% (n=182) |
| belief −6 sd | 69% (-1 [-5, +3]) | 1% (-0 [-1, +1]) | 82% (-2 [-6, +1]) |
| belief +6 sd | 65% (-5 [-9, -2]) | 1% (+1 [-0, +2]) | 78% (-7 [-10, -4]) |
| random −6 sd | 61% (-10 [-17, -2]) | 2% (+1 [+0, +2]) | 73% (-11 [-16, -7]) |

Sanity check: no-push belief vs the original 7 solves, correlation 0.98 over 689 candidates.
