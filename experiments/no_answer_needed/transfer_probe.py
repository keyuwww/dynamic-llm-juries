#!/usr/bin/env python
"""The paper's headline test (arXiv 2509.10625): does a probe trained on one dataset predict correctness on a different one?
Train on SOURCE benchmark (layer chosen by question-grouped 5-fold CV on the source only), score every TARGET item with that
direction, report AUROC against the target's real labels. No target labels are used. Baseline = the paper's 'assessor':
logistic regression on question-text embeddings, same train/test. Run both directions (BFF->RB2, RB2->BFF)."""
import argparse, json
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from probe_analysis import probe_scores, auc, group_folds


def load(acts, layers, items):
    X = np.load(acts).astype(np.float32); L = json.load(open(layers)); df = pd.read_csv(items)
    return [np.ascontiguousarray(X[:, i, :]) for i in range(len(L))], L, df


def emb_for(path, ids_path, item_ids):
    ids = pd.read_parquet(ids_path)["item_id"].tolist(); pos = {i: k for k, i in enumerate(ids)}
    return np.load(path)[[pos[i] for i in item_ids]]


def main():
    ap = argparse.ArgumentParser()
    for s in ("src", "tgt"):
        ap.add_argument(f"--{s}-acts", required=True); ap.add_argument(f"--{s}-layers", required=True); ap.add_argument(f"--{s}-items", required=True)
        ap.add_argument(f"--{s}-emb"); ap.add_argument(f"--{s}-emb-ids")
    ap.add_argument("--n-boot", type=int, default=1000); ap.add_argument("--seed", type=int, default=0); ap.add_argument("--out", default="transfer.csv")
    a = ap.parse_args(); pd.set_option("display.width", 200)
    XS, LS, S = load(a.src_acts, a.src_layers, S_ := a.src_items); XT, LT, T = load(a.tgt_acts, a.tgt_layers, a.tgt_items)
    assert LS == LT, "source and target must use the same layers"
    judges = [c[3:] for c in S.columns if c.startswith("ok_") and c in T.columns]
    gs, gt = S["group"].astype(str).values, T["group"].astype(str).values; rng = np.random.default_rng(a.seed)
    ES = EA = None
    if a.src_emb:
        ES = emb_for(a.src_emb, a.src_emb_ids, S["item_id"]); ET = emb_for(a.tgt_emb, a.tgt_emb_ids, T["item_id"])
    ug = np.unique(gt); idx_by_g = {g: np.where(gt == g)[0] for g in ug}
    boots = [np.concatenate([idx_by_g[g] for g in rng.choice(ug, len(ug))]) for _ in range(a.n_boot)]
    rows, curves = [], {}
    for j in judges:
        ys, yt = S[f"ok_{j}"].values, T[f"ok_{j}"].values; folds = group_folds(gs, 5, rng)
        cv = [np.nanmean([auc(ys[v], probe_scores(XS[li][tt], ys[tt], XS[li][v])) for tt, v in folds if len(set(ys[tt])) == 2]) for li in range(len(LS))]
        best = int(np.nanargmax(cv)); sc = probe_scores(XS[best], ys, XT[best]); pa = auc(yt, sc)
        ci = np.nanpercentile([auc(yt[i], sc[i]) for i in boots], [2.5, 97.5])
        curves[j] = [auc(yt, probe_scores(XS[li], ys, XT[li])) for li in range(len(LS))]
        row = dict(judge=j, layer_chosen_on_source=LS[best], transfer_auroc=pa, ci_lo=ci[0], ci_hi=ci[1])
        if ES is not None:
            aa = auc(yt, LogisticRegression(max_iter=2000).fit(ES, ys).predict_proba(ET)[:, 1]); row["assessor_transfer_auroc"] = aa
        rows.append(row)
    R = pd.DataFrame(rows); print(f"\nTRAIN on source, TEST on target ({len(T)} target items, {len(ug)} questions). AUROC, 0.5 = chance:"); print(R.round(3).to_string(index=False))
    print(f"\nmean probe {R.transfer_auroc.mean():.3f}" + (f"   mean assessor {R.assessor_transfer_auroc.mean():.3f}" if ES is not None else ""))
    print("\nTarget AUROC by layer (probe direction learned on source):"); print(pd.DataFrame(curves, index=LS).round(3).to_string())
    R.to_csv(a.out, index=False)


if __name__ == "__main__":
    main()
