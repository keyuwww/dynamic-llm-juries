# Own belief vs other judges' belief (Nov 21 review B2; post hoc)

Own belief vs other judges' belief (Nov 21 strict review, item B2). CPU only; no model calls; POST HOC.

Question: does a judge's OWN belief in a wrong candidate predict its approval beyond how much OTHER models agree
with that candidate? If not, the finding is about shared answer agreement (the candidate is a popular wrong answer)
rather than anything specific to the judge.

For every (judge, wrong candidate) judgment:
  own        the judge's belief (share of its 7 own answers reaching the candidate)
  cons_j     leave-that-judge-out consensus: mean belief of the OTHER judges in the same candidate
  cons_f     leave-that-family-out consensus: mean belief of judges from OTHER families (stricter: a Qwen judge's
             consensus uses no Qwen)
  own_c, cons_c   the same for the competing (right) response, pairwise data only
Analyses, per dataset:
  1. Linear probability model, benchmark-by-judge fixed effects: y ~ cons, and y ~ cons + own (coefficients 0->1 in
     points, 95% question-cluster bootstrap, 2,000 draws).
  2. Prediction on held-out questions: logistic regression with benchmark-by-judge intercepts; 10-fold split by
     question; out-of-fold log loss, Brier and AUROC for intercepts only / cons / cons + own / own. The paired
     difference (cons + own) - cons resamples questions (2,000 draws). Repeated over 5 fold partitions.
  3. Collinearity and identifying sample: corr(own, cons); judgments with |own - cons| >= 2/7.


cons_f = other families only; cons_j = all other judges. LPM: points per 0->1, benchmark-by-judge FE.
Held-out: 10-fold by question, logistic, 5 partitions averaged; delta = (cons+own) - cons, negative = own helps.

| data | consensus | n (q) | corr | |own-cons|>=2/7 | LPM cons alone | LPM cons (+own) | LPM own (+cons) | logloss cons | logloss cons+own | delta logloss [95%] | AUROC cons -> cons+own |
|---|---|---|---|---|---|---|---|---|---|---|---|
| original (7 judges, audited) | cons_f | 4621 (434) | 0.69 | 368 | +42 [+28, +56] | +23 [+9, +37] | +25 [+16, +35] | 0.4626 | 0.4595 | -0.0031 [-0.0058, -0.0006] | 0.722 -> 0.728 |
| original (7 judges, audited) | cons_j | 4621 (434) | 0.72 | 360 | +44 [+29, +58] | +23 [+9, +37] | +25 [+16, +34] | 0.4624 | 0.4597 | -0.0027 [-0.0050, -0.0005] | 0.722 -> 0.728 |
| MMLU-Pro (key) | cons_f | 5305 (1335) | 0.60 | 1151 | +51 [+44, +58] | +27 [+20, +34] | +34 [+29, +39] | 0.5492 | 0.5343 | -0.0149 [-0.0194, -0.0102] | 0.680 -> 0.714 |
| MMLU-Pro (key) | cons_j | 5305 (1335) | 0.64 | 1077 | +56 [+49, +62] | +32 [+24, +39] | +31 [+26, +36] | 0.5442 | 0.5327 | -0.0115 [-0.0151, -0.0076] | 0.692 -> 0.718 |
| MMLU-Pro (audited) | cons_f | 4164 (1048) | 0.52 | 743 | +47 [+38, +57] | +25 [+16, +35] | +34 [+27, +41] | 0.5067 | 0.4944 | -0.0123 [-0.0174, -0.0073] | 0.652 -> 0.691 |
| MMLU-Pro (audited) | cons_j | 4164 (1048) | 0.57 | 691 | +53 [+44, +63] | +31 [+22, +41] | +30 [+24, +37] | 0.5013 | 0.4924 | -0.0090 [-0.0131, -0.0049] | 0.668 -> 0.696 |
| math (key) | cons_f | 3227 (818) | 0.73 | 72 | +88 [+71, +109] | +65 [+44, +90] | +28 [+14, +45] | 0.1712 | 0.1703 | -0.0008 [-0.0028, +0.0010] | 0.683 -> 0.709 |
| math (key) | cons_j | 3227 (818) | 0.76 | 68 | +91 [+73, +112] | +71 [+49, +97] | +23 [+10, +39] | 0.1700 | 0.1697 | -0.0003 [-0.0017, +0.0010] | 0.700 -> 0.716 |
| math (audited) | cons_f | 3086 (781) | 0.29 | 58 | +74 [+33, +121] | +63 [+25, +105] | +27 [+7, +53] | 0.1415 | 0.1404 | -0.0011 [-0.0038, +0.0013] | 0.619 -> 0.649 |
| math (audited) | cons_j | 3086 (781) | 0.36 | 53 | +82 [+40, +129] | +71 [+32, +114] | +22 [+4, +45] | 0.1399 | 0.1389 | -0.0010 [-0.0030, +0.0008] | 0.644 -> 0.656 |

Pairwise (competing right response included), cons_f:
- original (7 judges, audited): n=563; own +18 [+3, +33], cons +21 [+2, +39], own (right) -20 [-33, -8], cons (right) +2 [-15, +19]
- MMLU-Pro (key): n=5305; own +15 [+8, +22], cons +18 [+8, +29], own (right) -22 [-27, -16], cons (right) -8 [-16, -0]
- MMLU-Pro (audited): n=4164; own +15 [+6, +24], cons +12 [-1, +26], own (right) -20 [-27, -14], cons (right) -11 [-21, -2]
- math (key): n=3227; own +14 [-4, +35], cons +59 [+32, +85], own (right) -14 [-23, -5], cons (right) -5 [-18, +6]
- math (audited): n=3086; own +14 [-10, +41], cons +53 [+11, +98], own (right) -11 [-20, -3], cons (right) -5 [-18, +6]
