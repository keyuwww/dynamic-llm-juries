## Calibration: items.csv

Reliability: within each confidence bin, how often the event is actually true. Perfect calibration ⇒ frac_true ≈ mean_pred. ECE = weighted average |gap| (lower is better). Brier = mean squared error of the probability (lower is better; 0.25 = coin flip).

**noref** — n=459, ECE=0.071, Brier=0.165 (constant-guess Brier=0.247)

| Bin | n | Mean predicted | Fraction true | Gap |
|---|---|---|---|---|
| 0.0–0.1 | 52 | 0.05 | 0.15 | +0.10 |
| 0.1–0.2 | 38 | 0.15 | 0.18 | +0.04 |
| 0.2–0.3 | 27 | 0.25 | 0.22 | -0.02 |
| 0.3–0.4 | 17 | 0.34 | 0.18 | -0.17 |
| 0.4–0.5 | 31 | 0.44 | 0.39 | -0.06 |
| 0.5–0.6 | 27 | 0.55 | 0.44 | -0.10 |
| 0.6–0.7 | 37 | 0.65 | 0.51 | -0.14 |
| 0.7–0.8 | 49 | 0.75 | 0.57 | -0.18 |
| 0.8–0.9 | 70 | 0.85 | 0.80 | -0.05 |
| 0.9–1.0 | 111 | 0.94 | 0.95 | +0.00 |

**ref** — n=456, ECE=0.090, Brier=0.060 (constant-guess Brier=0.246)

| Bin | n | Mean predicted | Fraction true | Gap |
|---|---|---|---|---|
| 0.0–0.1 | 200 | 0.03 | 0.05 | +0.02 |
| 0.1–0.2 | 8 | 0.15 | 0.50 | +0.35 |
| 0.2–0.3 | 9 | 0.27 | 0.67 | +0.40 |
| 0.3–0.4 | 4 | 0.35 | 1.00 | +0.65 |
| 0.4–0.5 | 11 | 0.46 | 0.73 | +0.27 |
| 0.5–0.6 | 12 | 0.54 | 1.00 | +0.46 |
| 0.6–0.7 | 13 | 0.65 | 1.00 | +0.35 |
| 0.7–0.8 | 11 | 0.74 | 1.00 | +0.26 |
| 0.8–0.9 | 41 | 0.84 | 1.00 | +0.16 |
| 0.9–1.0 | 147 | 0.95 | 0.99 | +0.04 |

(Install matplotlib for a reliability-diagram PNG.)
