#!/usr/bin/env python
"""Probe types from the literature, side by side, on the same judge activations (last token, after the verdict) and the same splits as the README.

For each cheap judge (Qwen3.5-4B, Qwen3.5-9B, gpt-oss-20b): training pooled over BFF + Safety + JudgeBench, 5 folds grouped by question
(same random stream as cascade_eval.oof_probe, seed 0). Probes (all fitted on the training folds only, scored on the held-out fold):
  linear_brier_mid    the paper's probe at its fixed middle layer (README baseline)
  logreg_mid          standardised features + logistic regression, regularisation chosen by inner 3-fold CV        (LLMs Encode Their Failures)
  mlp_mid             standardised features + one hidden layer of 256 units, early stopping                         (Reasoning Models Know When They're Right)
  diffmeans_mid       difference of the mean activation of right vs wrong verdicts; score = projection               (No Answer Needed)
  logreg_best_layer   logistic regression at every saved layer, the layer with the best inner-validation AUROC      (layer chosen on training data)
  logreg_avg_layers   logistic regression at every saved layer, probabilities averaged                               (read-outs combined across layers)
  pca_all_layers      all saved layers concatenated, PCA to 256 dims (fitted on training folds), logistic regression (Opening LLM Judges)
Baselines: verdict-only rule (random among items the judge marked 'correct'/'A'), random.
Metrics per benchmark: AUROC for 'verdict is right', accuracy with 20% escalated to the README's stronger judge (unfinished answers first).
Runs on Modal CPU (modal_generate.py::script)."""
import argparse, json, os, warnings
import numpy as np, pandas as pd, torch
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression, LogisticRegressionCV
from sklearn.metrics import roc_auc_score
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from evaluate import train_probe, predict
from cascade_eval import gen, load_run, BENCH
warnings.filterwarnings("ignore")


def acc20(score, ol, oh, fin):
    n = len(ol); m = int(round(0.2 * n)); k = np.where(~fin, -1e9, score) + 1e-9 * np.random.default_rng(1).random(n); e = np.zeros(n, bool); e[np.argsort(k, kind="stable")[:m]] = True
    return np.where(e, oh, ol).mean() * 100


def logreg(Xtr, ytr, Xte):
    sc = StandardScaler().fit(Xtr); m = LogisticRegressionCV(Cs=[1e-4, 1e-3, 1e-2, 1e-1, 1], cv=3, max_iter=2000, scoring="roc_auc").fit(sc.transform(Xtr), ytr)
    return m.predict_proba(sc.transform(Xte))[:, 1]


def logreg_fixed(Xtr, ytr, Xte, C=0.01):
    sc = StandardScaler().fit(Xtr); return LogisticRegression(C=C, max_iter=2000).fit(sc.transform(Xtr), ytr).predict_proba(sc.transform(Xte))[:, 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judges", default="Qwen3.5-4B:16:Qwen3.5-9B,Qwen3.5-9B:16:gpt-oss-20b,gpt-oss-20b:8:Qwen3.5-9B"); ap.add_argument("--results", default="local_results")
    ap.add_argument("--targets", default="targets/strong_judge_correct.json"); ap.add_argument("--threads", type=int, default=8); ap.add_argument("--out", default="results_probe_zoo")
    a = ap.parse_args(); torch.set_num_threads(a.threads); os.makedirs(a.out, exist_ok=True); TG = json.load(open(a.targets)); rows = []
    for spec in a.judges.split(","):
        j, layer, _ = spec.split(":"); layer = int(layer); A, Y, G, B, FIN, V, IDS = [], [], [], [], [], [], []
        for b in BENCH:
            _, p = load_run(a.results, j, b, "uncertainty__n1_t0.0"); itm = pd.read_csv(f"{p}_items.csv", dtype={"item_id": str}); L = gen(f"{p}_gen.jsonl").set_index("item_id").loc[itm["item_id"]]
            A.append(np.load(f"{p}_acts.npy").astype(np.float32)); layers = json.load(open(f"{p}_layers.json"))
            Y.append(L["correct"].values.astype(int)); FIN.append(L["verdict"].notna().values); V += list(L["verdict"].astype(str)); G += [f"{b}|{x}" for x in itm["group"].astype(str)]; B += [b] * len(itm); IDS += list(itm["item_id"])
        A = np.concatenate(A); Y = np.concatenate(Y); FIN = np.concatenate(FIN); G = np.array(G); B = np.array(B); V = np.array(V); IDS = np.array(IDS); li = layers.index(layer); nl = len(layers)
        rng = np.random.default_rng(0); ug = rng.permutation(np.unique(G)); fold_of = {g: i % 5 for i, g in enumerate(ug)}; f = np.array([fold_of[g] for g in G])
        S = {k: np.zeros(len(Y)) for k in ["linear_brier_mid", "logreg_mid", "mlp_mid", "diffmeans_mid", "logreg_best_layer", "logreg_avg_layers", "pca_all_layers"]}
        for k in range(5):
            te, tr = np.where(f == k)[0], np.where(f != k)[0]; Xm_tr, Xm_te = A[tr, li], A[te, li]
            S["linear_brier_mid"][te] = predict(train_probe(Xm_tr, Y[tr], seed=k), Xm_te)
            S["logreg_mid"][te] = logreg(Xm_tr, Y[tr], Xm_te)
            sc = StandardScaler().fit(Xm_tr); S["mlp_mid"][te] = MLPClassifier((256,), early_stopping=True, max_iter=300, random_state=k, alpha=1e-3).fit(sc.transform(Xm_tr), Y[tr]).predict_proba(sc.transform(Xm_te))[:, 1]
            d = Xm_tr[Y[tr] == 1].mean(0) - Xm_tr[Y[tr] == 0].mean(0); S["diffmeans_mid"][te] = Xm_te @ d
            gi = rng.permutation(np.unique(G[tr])); va_g = set(gi[:max(1, len(gi) // 6)]); va = tr[np.isin(G[tr], list(va_g))]; tr2 = tr[~np.isin(G[tr], list(va_g))]
            per_layer, val_auc = [], []
            for l in range(nl):
                val_auc.append(roc_auc_score(Y[va], logreg_fixed(A[tr2, l], Y[tr2], A[va, l])) if len(set(Y[va])) > 1 else 0.5)   # fixed C per layer (CV at every layer is too slow)
                per_layer.append(logreg_fixed(A[tr, l], Y[tr], A[te, l]))
            S["logreg_best_layer"][te] = per_layer[int(np.argmax(val_auc))]; S["logreg_avg_layers"][te] = np.mean(per_layer, 0)
            Xc_tr = A[tr].reshape(len(tr), -1); Xc_te = A[te].reshape(len(te), -1); sc2 = StandardScaler().fit(Xc_tr); pca = PCA(256, random_state=0).fit(sc2.transform(Xc_tr))
            S["pca_all_layers"][te] = LogisticRegression(C=0.01, max_iter=3000).fit(pca.transform(sc2.transform(Xc_tr)), Y[tr]).predict_proba(pca.transform(sc2.transform(Xc_te)))[:, 1]
            print(f"{j} fold {k} done (best layer {layers[int(np.argmax(val_auc))]})", flush=True)
        for b in BENCH:
            m = B == b; ol, fin = Y[m], FIN[m]; oh = np.array([TG[j][b][i] for i in IDS[m]]); good = (V[m] == "1.0") if b != "judgebench" else np.zeros(m.sum(), bool)
            vo = np.mean([acc20(np.where(good, 0, 1) + 0.5 * np.random.default_rng(s).random(m.sum()), ol, oh, fin) for s in range(100)])
            row = dict(judge=j, bench=b, random=(ol.mean() + 0.2 * (oh.mean() - ol.mean())) * 100, verdict_only=vo,
                       verdict_only_auroc=(roc_auc_score(ol[fin], (~good[fin]).astype(int)) if b != "judgebench" else np.nan))
            for nm, s in S.items():
                row[f"{nm}_acc20"] = acc20(s[m], ol, oh, fin); row[f"{nm}_auroc"] = roc_auc_score(ol, s[m])
            rows.append(row)
        pd.DataFrame(rows).to_csv(os.path.join(a.out, "probe_zoo.csv"), index=False)
    R = pd.DataFrame(rows); pd.set_option("display.width", 250)
    print(R[["judge", "bench", "random", "verdict_only"] + [c for c in R.columns if c.endswith("_acc20")]].round(1).to_string(index=False))
    print(R[["judge", "bench", "verdict_only_auroc"] + [c for c in R.columns if c.endswith("_auroc") and c != "verdict_only_auroc"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
