#!/usr/bin/env python3
"""
Step 1.3: which item features predict LOW CONFIDENCE, and which predict ERRORS?

A feature that raises the error rate without lowering confidence marks a source of confident errors.

Data: results/raw/judgments_real.jsonl (3 judges x 960 real BFF answers, 5 samples each), restricted to answers with a
unanimous expert label. Features: the six coded question aspects from experiments/cross_benchmark
(knowledge, reasoning, constraints, open_endedness, context_load, risk; 0-2 each), log answer length, turn, and the
answer model. Targets per (judge, answer, condition):
  error       majority verdict disagrees with the expert label
  unsure      the 5 samples are not unanimous
  conf_error  all 5 samples agree and are wrong

Output: results/features_summary.md and results/features.json (grouped-by-question cross-validated AUROC of a
logistic model per target, its standardized coefficients, and per-level rates).

  python experiments/judge_confidence/features.py
"""
import json, math

import numpy as np
import pandas as pd

from jc_common import HERE, RAW, REPO

ASPECTS = ["knowledge", "reasoning", "constraints", "open_endedness", "context_load", "risk"]


def table():
    rows = [json.loads(l) for l in open(RAW / "judgments_real.jsonl")]
    d = pd.DataFrame([dict(judge=r["judge"], item_id=r["item_id"], qid=r["qid"], turn=r["turn"], examinee=r["examinee"],
                           condition=r["condition"], gold=r["gold_unanimous"], vote=r["vote_share"],
                           prompt_len=len(r["prompt"])) for r in rows])
    d = d[d.gold.notna() & d.vote.notna()].copy()
    items = pd.read_pickle(REPO / "experiments" / "cross_benchmark" / "data" / "bff_items.pkl")
    items["item_id"] = items.key.str.split("|").str[0]
    d = d.merge(items[["item_id", "question_key", "resp_len"]], on="item_id", how="left")
    asp = pd.read_pickle(REPO / "experiments" / "cross_benchmark" / "data" / "bff_aspects.pkl")
    d = d.merge(asp, on="question_key", how="left")
    d["log_len"] = np.log(d.resp_len.fillna(d.prompt_len))
    d["error"] = ((d.vote >= 0.5).astype(int) != d.gold.astype(int)).astype(int)
    d["unsure"] = (~d.vote.isin([0.0, 1.0])).astype(int)
    d["conf_error"] = ((d.unsure == 0) & (d.error == 1)).astype(int)
    d["group"] = d.question_key.fillna(d.qid)
    return d


def fit(d, target, feats):
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import GroupKFold
    X = d[feats].astype(float).fillna(d[feats].astype(float).median())
    X = (X - X.mean()) / X.std().replace(0, 1)
    y = d[target].values
    if y.sum() < 10:
        return None
    pred = np.zeros(len(y))
    for tr, te in GroupKFold(n_splits=5).split(X, y, d.group):
        pred[te] = LogisticRegression(C=0.5, max_iter=2000).fit(X.iloc[tr], y[tr]).predict_proba(X.iloc[te])[:, 1]
    coef = LogisticRegression(C=0.5, max_iter=2000).fit(X, y).coef_[0]
    return dict(auroc=float(roc_auc_score(y, pred)), n=int(len(y)), positives=int(y.sum()),
                coef={f: float(c) for f, c in zip(feats, coef)})


def main():
    d = table()
    cover = d.knowledge.notna().mean()
    exam = pd.get_dummies(d.examinee, prefix="model", dtype=float)
    d = pd.concat([d, exam], axis=1)
    feats = ASPECTS + ["log_len", "turn"] + list(exam.columns)
    res = {}
    L = ["# Which item features predict low confidence vs errors (real BFF answers)", "",
         f"{d.item_id.nunique()} answers with a unanimous expert label × 3 judges × condition; aspect codes cover "
         f"{cover:.0%} of rows (missing filled with the median). AUROC = logistic model on all features, 5-fold CV "
         "grouped by question. Coefficients are standardized (positive = more likely).", ""]
    for cond in ("none", "human"):
        dc = d[d.condition == cond]
        if dc.empty:
            continue
        res[cond] = {t: fit(dc, t, feats) for t in ("error", "unsure", "conf_error")}
        L += [f"## {'No reference' if cond == 'none' else 'With reference'} (n = {len(dc)} judge × answer rows)", "",
              "| Target | Positives | CV AUROC |", "|---|---|---|"]
        for t, r in res[cond].items():
            if r:
                L.append(f"| {t} | {r['positives']} | {r['auroc']:.2f} |")
        L += ["", "| Feature | → error | → unsure (low confidence) | → confident error |", "|---|---|---|---|"]
        for f in feats:
            cells = [f"{res[cond][t]['coef'][f]:+.2f}" if res[cond][t] else "" for t in ("error", "unsure", "conf_error")]
            L.append(f"| {f} | " + " | ".join(cells) + " |")
        L += ["", "Rates by answer model (all judges pooled):", "",
              "| Answer model | Error | Unsure | Confident error |", "|---|---|---|---|"]
        for m, g in dc.groupby("examinee"):
            L.append(f"| {m} | {g.error.mean():.2f} | {g.unsure.mean():.2f} | {g.conf_error.mean():.2f} |")
        L.append("")
    (HERE / "results" / "features_summary.md").write_text("\n".join(L) + "\n")
    (HERE / "results" / "features.json").write_text(json.dumps(res, indent=1))
    print("\n".join(L))


if __name__ == "__main__":
    main()
