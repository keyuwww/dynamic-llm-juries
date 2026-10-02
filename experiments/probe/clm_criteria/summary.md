# CLM criteria-inversion probe

n=60
AUROC, normal criteria (p directly):        0.409
AUROC, swapped criteria (p directly):        0.464
AUROC, swapped criteria (1-p, un-swapped):   0.536
Mean p, normal:  0.069   Mean p, swapped: 0.794
Human base rate (share correct): 0.483

If 'swapped (1-p)' AUROC >> 'normal' AUROC, the criteria mapping is inverted (fixable).
If both hover near 0.5, it's a genuine no-signal failure, not a phrasing bug.