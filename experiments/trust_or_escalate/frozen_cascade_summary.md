# Frozen-threshold cascade (arXiv:2609.26550 methodology)

Confidence threshold tuned on a held-out 50% TUNE split, frozen, then applied to the other 50% TEST split (no test-set leakage, unlike run_toe.py's sweep-and-report-best). Escalation target fixed in advance: gpt-oss-120b (a Tinker-pool reasoning judge), not re-picked per benchmark. Uses only already-collected judge data.

| Benchmark | Fast judge | Frozen tau | Coverage (test) | Cascade kappa | Comparator kappa | Fast-alone kappa | % of comparator accuracy retained |
|---|---|---|---|---|---|---|---|
| BFF noref | jev | 0.75 | 0.430 | 0.764 | 0.782 | 0.531 | 99.0% |
| BFF noref | laya | 0.60 | 0.039 | 0.755 | 0.782 | 0.140 | 98.5% |
| BFF noref | jeff | 0.75 | 0.039 | 0.765 | 0.782 | 0.392 | 99.0% |
| BFF ref | jev | 0.10 | 0.974 | 0.877 | 0.868 | 0.877 | 100.5% |
| BFF ref | laya | 0.65 | 0.018 | 0.868 | 0.868 | 0.130 | 100.0% |
| BFF ref | jeff | 0.80 | 0.219 | 0.851 | 0.868 | 0.394 | 99.1% |
| Safety | jev | 0.05 | 0.960 | 0.565 | 0.524 | 0.572 | 102.7% |
| Safety | laya | 0.95 | 0.007 | 0.522 | 0.524 | 0.065 | 99.9% |
| Safety | jeff | 0.95 | 0.003 | 0.524 | 0.524 | 0.178 | 100.0% |