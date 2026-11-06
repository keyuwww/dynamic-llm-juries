#!/usr/bin/env python
"""For each judge: how well do two signals rank 'this judge is right' above 'this judge is wrong' (AUROC)?
  probe             held-out scores from probe_analysis.py --save-scores
  others disagree   share of the other 7 judges whose verdict differs from this judge's (needs all other judges to be run)"""
import argparse, os, sys
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "role_conditioned_panels"))
from data import load_judgments
from audit import match_matrix

ap = argparse.ArgumentParser(); ap.add_argument("--judgments", required=True); ap.add_argument("--bench", required=True); ap.add_argument("--scores", required=True)
a = ap.parse_args(); d = load_judgments(a.judgments, a.bench, condition="none"); J = list(d.judge_names); C = match_matrix(d.Z, d.Y)
S = pd.read_csv(a.scores).set_index("item_id").loc[d.item_ids]; rows = []
for j in range(len(J)):
    oth = [k for k in range(len(J)) if k != j]; dis = (d.Z[:, oth] != d.Z[:, [j]]).mean(1)
    rows.append((J[j], roc_auc_score(C[:, j], S[f"p_{J[j]}"]), roc_auc_score(C[:, j], -dis)))
R = pd.DataFrame(rows, columns=["judge", "probe", "others_disagree"]); print(R.round(3).to_string(index=False)); print(R[["probe", "others_disagree"]].mean().round(3).to_dict())
