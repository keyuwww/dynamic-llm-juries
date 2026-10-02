## Calibration: items.csv

Reliability: within each confidence bin, how often the event is actually true. Perfect calibration ⇒ frac_true ≈ mean_pred. ECE = weighted average |gap| (lower is better). Brier = mean squared error of the probability (lower is better; 0.25 = coin flip).

**noref** — n=459, ECE=0.486, Brier=0.486 (constant-guess Brier=0.247)

| Bin | n | Mean predicted | Fraction true | Gap |
|---|---|---|---|---|
| 0.0–0.1 | 360 | 0.06 | 0.59 | +0.53 |
| 0.1–0.2 | 95 | 0.13 | 0.44 | +0.31 |
| 0.2–0.3 | 3 | 0.23 | 0.00 | -0.23 |
| 0.3–0.4 | 1 | 0.34 | 0.00 | -0.34 |

**ref** — n=456, ECE=0.286, Brier=0.346 (constant-guess Brier=0.246)

| Bin | n | Mean predicted | Fraction true | Gap |
|---|---|---|---|---|
| 0.0–0.1 | 14 | 0.07 | 0.93 | +0.86 |
| 0.1–0.2 | 96 | 0.16 | 0.60 | +0.44 |
| 0.2–0.3 | 181 | 0.25 | 0.52 | +0.28 |
| 0.3–0.4 | 89 | 0.34 | 0.53 | +0.18 |
| 0.4–0.5 | 59 | 0.44 | 0.58 | +0.14 |
| 0.5–0.6 | 14 | 0.54 | 0.50 | -0.04 |
| 0.6–0.7 | 3 | 0.63 | 0.33 | -0.30 |

(Install matplotlib for a reliability-diagram PNG.)
