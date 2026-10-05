# Cross-benchmark transfer: does judge reliability generalize across tasks?

Reliability model (logistic regression, same features as the certifier) fit on one benchmark's full data, applied as-is to another's. Top-3 weighted vote, kappa vs. gold.

| Trained on | Evaluated on | Kappa (transferred) | Kappa (in-domain, from run_certifier.py) |
|---|---|---|---|
| BFF noref | BFF ref | 0.868 | 0.881 |
| BFF noref | Safety | 0.583 | 0.639 |
| BFF ref | BFF noref | 0.629 | 0.745 |
| BFF ref | Safety | 0.516 | 0.639 |
| Safety | BFF noref | 0.605 | 0.745 |
| Safety | BFF ref | 0.816 | 0.881 |