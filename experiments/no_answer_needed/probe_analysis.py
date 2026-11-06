#!/usr/bin/env python
"""The probe from "No Answer Needed" (arXiv 2509.10625) applied to our judges. CPU only.

Probe (paper, Section 3): w = mu_true - mu_false (class means of the activations), mu = (mu_true + mu_false)/2,
score(h) = (h - mu) . w / ||w||. No sigmoid, no threshold; quality = AUROC.
Layer choice (paper, 4.3): k-fold CV AUROC per layer on training data. Ours: question-grouped 3-fold CV inside the training
questions (several items share a question), then the probe is retrained on all training questions and scored on held-out
questions. Repeated over random question splits. Optional baseline (paper's 'assessor'): logistic regression on
question-text embeddings (--emb, --emb-ids) with the same splits."""
import argparse, json, os
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score


def probe_scores(Xtr, ytr, Xte):
    mt, mf = Xtr[ytr == 1].mean(0), Xtr[ytr == 0].mean(0)
    w = mt - mf; mu = 0.5 * (mt + mf)
    return (Xte - mu) @ w / (np.linalg.norm(w) + 1e-12)


def auc(y, s):
    return roc_auc_score(y, s) if len(set(y)) == 2 else np.nan


def group_folds(groups, k, rng):
    ug = rng.permutation(np.unique(groups)); fold_of = {g: i % k for i, g in enumerate(ug)}
    f = np.array([fold_of[g] for g in groups]); return [(np.where(f != i)[0], np.where(f == i)[0]) for i in range(k)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--acts", required=True); ap.add_argument("--layers", required=True); ap.add_argument("--items", required=True)
    ap.add_argument("--targets", nargs="*", default=None, help="judge names to predict; default = all judges in the items file")
    ap.add_argument("--repeats", type=int, default=20); ap.add_argument("--test-frac", type=float, default=0.2)
    ap.add_argument("--emb"); ap.add_argument("--emb-ids"); ap.add_argument("--save-scores", help="write held-out P(judge correct) per item and judge to this csv (5-fold question-grouped; for routing), then exit"); ap.add_argument("--assessor-only", action="store_true", help="skip the probe; only the text-embedding assessor, on the same splits"); ap.add_argument("--seed", type=int, default=0); ap.add_argument("--out", default="probe_results.csv")
    a = ap.parse_args(); pd.set_option("display.width", 200)

    X = np.load(a.acts).astype(np.float32); layers = json.load(open(a.layers)); items = pd.read_csv(a.items)
    groups = items["group"].astype(str).values; judges = [c[3:] for c in items.columns if c.startswith("ok_")]
    targets = a.targets or judges
    XL = [np.ascontiguousarray(X[:, li, :]) for li in range(len(layers))]     # per-layer matrices, made once
    E = None
    if a.emb:
        ids = pd.read_parquet(a.emb_ids)["item_id"].tolist(); pos = {i: k for k, i in enumerate(ids)}
        E = np.load(a.emb)[[pos[i] for i in items["item_id"]]]
    print(f"{len(items)} items, {len(np.unique(groups))} questions, activations {X.shape}, layers {layers}")
    if a.save_scores:                       # held-out, calibrated P(correct) per item and judge, for routing experiments
        rng = np.random.default_rng(a.seed); out = items[["item_id", "group"]].copy()
        for t in targets:
            y = items[f"ok_{t}"].values; p = np.full(len(y), np.nan); lay = []
            for tr_i, te_i in group_folds(groups, 5, rng):               # outer: each item scored by a probe that never saw its question
                ytr = y[tr_i]; inner = group_folds(groups[tr_i], 3, rng)
                cvauc = [np.nanmean([auc(ytr[v], probe_scores(XL[li][tr_i][tt], ytr[tt], XL[li][tr_i][v])) for tt, v in inner]) for li in range(len(layers))]
                li = int(np.nanargmax(cvauc)); lay.append(layers[li]); Xl = XL[li][tr_i]
                oof = np.zeros(len(tr_i))                                  # honest training scores -> calibrate score to probability
                for tt, v in inner:
                    oof[v] = probe_scores(Xl[tt], ytr[tt], Xl[v])
                cal = LogisticRegression().fit(oof[:, None], ytr)
                p[te_i] = cal.predict_proba(probe_scores(Xl, ytr, XL[li][te_i])[:, None])[:, 1]
            out[f"p_{t}"] = p; out[f"ok_{t}"] = y
            print(f"  {t}: held-out AUROC {auc(y, p):.3f}  layers {lay}", flush=True)
        out.to_csv(a.save_scores, index=False); print("wrote", a.save_scores); return
    rng = np.random.default_rng(a.seed); rows, curves = [], {}
    for t in targets:
        y = items[f"ok_{t}"].values; res, curve, assessor, best_layers = [], [], [], []
        for r in range(a.repeats):
            ug = rng.permutation(np.unique(groups)); n_te = max(1, int(round(a.test_frac * len(ug))))
            te_g = set(ug[:n_te]); te = np.array([g in te_g for g in groups]); tr_i, te_i = np.where(~te)[0], np.where(te)[0]
            if len(set(y[tr_i])) < 2 or len(set(y[te_i])) < 2:
                continue
            cv = group_folds(groups[tr_i], 3, rng); per_layer = []; ytr = y[tr_i]; test_all = []   # (rng use identical with/without --assessor-only -> same splits)
            for li in ([] if a.assessor_only else range(len(layers))):
                Xtr_l = XL[li][tr_i]                                   # one (n_train, d) slice per layer, not the whole array
                s = [auc(ytr[v], probe_scores(Xtr_l[tt], ytr[tt], Xtr_l[v])) for tt, v in cv if len(set(ytr[tt])) == 2]
                per_layer.append(np.nanmean(s) if s else np.nan)
                test_all.append(auc(y[te_i], probe_scores(Xtr_l, ytr, XL[li][te_i])))
            if not a.assessor_only:
                best = int(np.nanargmax(per_layer)); best_layers.append(layers[best]); res.append(test_all[best]); curve.append(test_all)
            if E is not None:
                lr = LogisticRegression(max_iter=2000).fit(E[tr_i], y[tr_i]); assessor.append(auc(y[te_i], lr.predict_proba(E[te_i])[:, 1]))
        rows.append(dict(target=t, judge_accuracy=y.mean(), probe_auroc=np.nanmean(res) if res else np.nan, probe_sd=np.nanstd(res) if res else np.nan,
                         best_layer_mode=max(set(best_layers), key=best_layers.count) if best_layers else None,
                         assessor_auroc=np.nanmean(assessor) if assessor else np.nan, n_repeats=len(assessor if a.assessor_only else res)))
        curves[t] = np.nanmean(curve, axis=0) if curve else np.zeros(len(layers)); print(f"  done {t}: probe AUROC {rows[-1]['probe_auroc']:.3f}  assessor AUROC {rows[-1]['assessor_auroc']:.3f}", flush=True)
    R = pd.DataFrame(rows); print("\nAUROC of the question-level probe at the CV-chosen layer, held-out questions (0.5 = chance):"); print(R.round(3).to_string(index=False))
    print("\nTest AUROC by layer (mean over splits):"); print(pd.DataFrame(curves, index=layers).round(3).to_string())
    R.to_csv(a.out, index=False); pd.DataFrame(curves, index=layers).to_csv(a.out.replace(".csv", "_by_layer.csv"))


if __name__ == "__main__":
    main()
