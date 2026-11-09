"""Per-layer probe AUROC (same-source, 5-fold grouped CV) for the line chart in pilot_summary.html.

For every layer 0..24 a linear probe is fit with 5-fold grouped CV and scored within strata
(the same fair comparison as gap_check's cv_all). Writes results/layer_curve.json.
"""
import json

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from gap_check import RAW, RES, items_rb2safety, strat_auc

out = {}
summary = json.loads((RES / "gap_summary.json").read_text())
for bench in ("rb2safety", "bff", "judgebench"):
    recs = [json.loads(l) for l in open(RAW / bench / "index.jsonl")]
    if bench == "rb2safety" and "resp_model" not in recs[0]:
        rm = {it["id"]: it["resp_model"] for it in items_rb2safety()}
        for r in recs:
            r["resp_model"] = rm[r["id"]]
    y = np.array([r["gold"] for r in recs])
    groups = np.array([r["group"] for r in recs])
    p = np.array([r["p_pos"] for r in recs])
    X = np.stack([np.load(RAW / bench / r["file"]).astype(np.float32) for r in recs])
    key = {"rb2safety": lambda r: f"{r['resp_model']}|{r['refusal']}",
           "bff": lambda r: r["examinee"], "judgebench": lambda r: r["category"]}[bench]
    strata = np.array([key(r) for r in recs])
    allm = np.ones(len(y), bool)
    C = summary[bench]["probe_C"]
    curve = []
    for l in range(X.shape[1]):
        oof = np.zeros(len(y))
        for tr, tt in GroupKFold(5).split(X, y, groups):
            oof[tt] = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=3000)).fit(
                X[tr, l], y[tr]).predict_proba(X[tt, l])[:, 1]
        curve.append(round(strat_auc(y, oof, strata, allm)[0], 3))
        print(bench, l, curve[-1], flush=True)
    out[bench] = dict(probe_by_layer=curve, verdict=round(strat_auc(y, p, strata, allm)[0], 3),
                      surface=round(summary[bench]["cv_all"]["surface_strat"], 3))
(RES / "layer_curve.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out))
