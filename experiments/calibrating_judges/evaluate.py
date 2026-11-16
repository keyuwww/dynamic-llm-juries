#!/usr/bin/env python
"""Probe vs baselines, following arXiv 2512.22245.
Probe (A.5): one linear layer d -> 1 on the judge's last-token residual stream, MSE (= Brier) loss on the 0/1 label 'verdict is correct', AdamW lr 1e-4,
weight decay 0.01, batch 4, 10 epochs (HF Trainer default linear decay), output clipped to [0, 1] and used as the confidence. One probe per layer
(layer ablation, A.6); headline = a fixed middle layer (--layer) and also the layer picked on a validation split. Training set = the pooled
--train benchmarks (the paper pools PPE correctness + preference); in-distribution test = held-out questions of each; --ood benchmarks are never trained on.
3 random splits by question (--splits), averaged.
Baselines (Section 3): verbalized confidence (own run, confidence prompt); self-consistency: the greedy verdict, confidence = share of the N samples that agree;
majority: the majority verdict of the N samples, confidence = its share.
Metrics: Kuiper (W = score), ECE (10 bins), plus AUROC, Brier and accuracy."""
import argparse, json, os
import numpy as np, pandas as pd, torch
from metrics import kuiper, ece, auroc, brier, accuracy_at_thresholds, bin_stats


def train_probe(X, y, epochs=10, lr=1e-4, wd=0.01, bs=4, seed=0, standardize=False):
    mu, sd = (X.mean(0), X.std(0) + 1e-6) if standardize else (None, None)       # DEVIATION from the paper, off by default: z-score the features with the training mean / std
    if standardize:
        X = (X - mu) / sd
    torch.manual_seed(seed); g = torch.Generator().manual_seed(seed)
    lin = torch.nn.Linear(X.shape[1], 1); opt = torch.optim.AdamW(lin.parameters(), lr=lr, weight_decay=wd)
    X, y = torch.from_numpy(X), torch.from_numpy(y.astype(np.float32)); n = len(y); steps = epochs * ((n + bs - 1) // bs)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: max(0.0, 1.0 - s / steps))
    for _ in range(epochs):
        perm = torch.randperm(n, generator=g)
        for i in range(0, n, bs):
            idx = perm[i:i + bs]; loss = ((lin(X[idx]).squeeze(-1) - y[idx]) ** 2).mean(); opt.zero_grad(); loss.backward(); opt.step(); sched.step()
    lin.mu, lin.sd = mu, sd
    return lin


def predict(lin, X):
    if getattr(lin, "mu", None) is not None:
        X = (X - lin.mu) / lin.sd
    with torch.no_grad():
        return lin(torch.from_numpy(X)).squeeze(-1).clamp(0, 1).numpy()


def read_gen(path):
    return pd.read_json(path, lines=True, dtype={"item_id": str})


def baselines(items, verb, samp, greedy):
    """per-item (confidence, correct) for each baseline, indexed by item_id."""
    out = {}
    if verb is not None:
        v = verb[verb["sample"] == 0].set_index("item_id"); v = v[v["confidence"].notna()]
        out["verbalized"] = pd.DataFrame({"conf": v["confidence"], "ok": v["correct"]})
    if samp is not None:
        gv = greedy[greedy["sample"] == 0].set_index("item_id")["verdict"]; rows_c, rows_m, rows_s = {}, {}, {}
        for iid, d in samp.groupby("item_id"):
            vs = [x for x in d["verdict"].tolist() if x is not None and not (isinstance(x, float) and np.isnan(x))]; gold = d["gold"].iloc[0]; n = len(d)
            # semantic entropy (Kuhn et al. 2023) over the N samples; the verdicts are binary, so the meaning clusters are the verdict values (an unparsed sample is its own cluster).
            # score = 1 - H / ln 2 in [0, 1] (high = the samples agree); reported with AUROC only, it is not a probability.
            cl = [c for c in list(pd.Series(vs).value_counts().values) + [n - len(vs)] if c > 0]; pr = np.array(cl) / n; H = float(-(pr * np.log(pr)).sum())
            rows_s[iid] = (1.0 - H / np.log(2), int(iid in gv.index and gv[iid] == gold))
            if iid in gv.index and gv[iid] is not None and not (isinstance(gv[iid], float) and np.isnan(gv[iid])):
                rows_c[iid] = (sum(1 for x in vs if x == gv[iid]) / n, int(gv[iid] == gold))
            else:
                rows_c[iid] = (0.0, 0)
            if vs:
                cnt = pd.Series(vs).value_counts(); top = cnt[cnt == cnt.max()].index.tolist(); pick = gv[iid] if (iid in gv.index and gv[iid] in top) else top[0]
                rows_m[iid] = (cnt[pick] / n, int(pick == gold))
            else:
                rows_m[iid] = (0.0, 0)
        out["consistency"] = pd.DataFrame(rows_c, index=["conf", "ok"]).T; out["majority"] = pd.DataFrame(rows_m, index=["conf", "ok"]).T
        out["semantic_entropy (AUROC only)"] = pd.DataFrame(rows_s, index=["conf", "ok"]).T
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True, help="NAME=acts.npy,layers.json,items.csv,probe_gen.jsonl[,verbalized_gen.jsonl[,samples_gen.jsonl]]")
    ap.add_argument("--train", nargs="+", required=True); ap.add_argument("--ood", nargs="*", default=[]); ap.add_argument("--layer", type=int, default=16)
    ap.add_argument("--splits", type=int, default=3); ap.add_argument("--test-frac", type=float, default=0.2); ap.add_argument("--val-frac", type=float, default=0.15)
    ap.add_argument("--common", action="store_true", help="restrict every benchmark to the items where the judge finished and also answered the confidence prompt (same items for all methods)"); ap.add_argument("--standardize", action="store_true", help="DEVIATION: z-score the activations (training mean / std) before the probe"); ap.add_argument("--epochs", type=int, default=10); ap.add_argument("--out", default="results"); ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True); pd.set_option("display.width", 220)
    R = {}
    for spec in a.run:
        name, paths = spec.split("=", 1); p = paths.split(","); acts = np.load(p[0]).astype(np.float32); layers = json.load(open(p[1])); itm = pd.read_csv(p[2], dtype={"item_id": str})
        g = read_gen(p[3]); g0 = g[g["sample"] == 0].set_index("item_id"); y = g0.loc[itm["item_id"], "correct"].values.astype(int)
        base = baselines(itm, read_gen(p[4]) if len(p) > 4 and p[4] else None, read_gen(p[5]) if len(p) > 5 else None, g)
        ids = itm["item_id"].values; keep = np.ones(len(ids), dtype=bool)
        if a.common:                                                      # score every method on the same items: the judge finished (verdict parsed) and also gave a verdict + confidence in the confidence run
            vb = read_gen(p[4]).set_index("item_id") if len(p) > 4 and p[4] else None
            keep = g0.loc[ids, "verdict"].notna().values
            if vb is not None:
                vb = vb[~vb.index.duplicated()]; keep &= (vb["verdict"].notna() & vb["confidence"].notna()).reindex(ids).fillna(False).values.astype(bool)
            acts, itm, y = acts[keep], itm[keep].reset_index(drop=True), y[keep]; ids = ids[keep]
        R[name] = dict(acts=acts, layers=layers, ids=ids, groups=itm["group"].astype(str).values, y=y, base=base)
        print(f"{name}: {len(y)} items, verdict accuracy {y.mean():.3f}, baselines {list(base)}", flush=True)
    layers = R[a.train[0]]["layers"]; li_mid = layers.index(a.layer); rng = np.random.default_rng(a.seed)
    rows, bins_rows, thr_rows = [], [], []

    def add(method, test, split, conf, ok, layer=None):
        rows.append(dict(method=method, test=test, split=split, layer=layer, n=len(ok), accuracy=float(np.mean(ok)), kuiper=kuiper(conf, ok), ece=ece(conf, ok), brier=brier(conf, ok), auroc=auroc(conf, ok)))
        if split == 0:
            bins_rows.extend(dict(method=method, test=test, bin=m, count=c, mean_conf=f, accuracy=acc) for m, c, f, acc in bin_stats(conf, ok))
            thr_rows.extend(dict(method=method, test=test, threshold=t, share_kept=sk, accuracy_kept=acc) for t, sk, acc in accuracy_at_thresholds(conf, ok, [0.5, 0.6, 0.7, 0.8, 0.9]))

    layer_rows = []
    for s in range(a.splits):
        tr_idx, va_idx, te_idx = {}, {}, {}
        for nm in a.train:
            ug = rng.permutation(np.unique(R[nm]["groups"])); n_te = max(1, int(round(a.test_frac * len(ug)))); n_va = max(1, int(round(a.val_frac * (len(ug) - n_te))))
            te_g, va_g = set(ug[:n_te]), set(ug[n_te:n_te + n_va]); gr = R[nm]["groups"]
            te_idx[nm] = np.where([x in te_g for x in gr])[0]; va_idx[nm] = np.where([x in va_g for x in gr])[0]
            tr_idx[nm] = np.where([(x not in te_g) and (x not in va_g) for x in gr])[0]
        ytr = np.concatenate([R[nm]["y"][tr_idx[nm]] for nm in a.train]); yva = np.concatenate([R[nm]["y"][va_idx[nm]] for nm in a.train])
        const = float(ytr.mean()); tests = {nm: (R[nm], te_idx[nm]) for nm in a.train}; tests.update({nm: (R[nm], np.arange(len(R[nm]["y"]))) for nm in a.ood})
        scores = {}; val_brier = []
        for li, L in enumerate(layers):
            Xtr = np.concatenate([R[nm]["acts"][tr_idx[nm]][:, li] for nm in a.train]); lin = train_probe(Xtr, ytr, epochs=a.epochs, seed=a.seed + s, standardize=a.standardize)
            Xva = np.concatenate([R[nm]["acts"][va_idx[nm]][:, li] for nm in a.train]); val_brier.append(brier(predict(lin, Xva), yva))
            for t, (r, ix) in tests.items():
                conf = predict(lin, r["acts"][ix][:, li]); scores[(li, t)] = conf
                layer_rows.append(dict(split=s, layer=L, test=t, kuiper=kuiper(conf, r["y"][ix]), ece=ece(conf, r["y"][ix]), brier=brier(conf, r["y"][ix]), auroc=auroc(conf, r["y"][ix])))
        li_val = int(np.argmin(val_brier)); print(f"split {s}: validation-selected layer {layers[li_val]}", flush=True)
        for t, (r, ix) in tests.items():
            ok = r["y"][ix]
            add(f"probe (layer {a.layer})", t, s, scores[(li_mid, t)], ok, a.layer); add(f"probe (validation layer)", t, s, scores[(li_val, t)], ok, layers[li_val])
            add("constant (training accuracy)", t, s, np.full(len(ok), const), ok)
            for bname, df in r["base"].items():
                d = df.reindex(r["ids"][ix]).dropna()
                if len(d):
                    add(bname, t, s, d["conf"].values.astype(float), d["ok"].values.astype(int))
    res = pd.DataFrame(rows); summ = res.groupby(["test", "method"])[["n", "accuracy", "kuiper", "ece", "brier", "auroc"]].mean().round(4)
    print("\nCalibration (Kuiper, ECE: lower is better; AUROC: higher is better), mean over splits"); print(summ.to_string())
    lay = pd.DataFrame(layer_rows).groupby(["test", "layer"])[["kuiper", "ece", "brier", "auroc"]].mean().round(4)
    print("\nLayer ablation (probe, mean over splits)"); print(lay.to_string())
    summ.to_csv(os.path.join(a.out, "calibration_table.csv")); lay.to_csv(os.path.join(a.out, "layer_ablation.csv")); res.to_csv(os.path.join(a.out, "per_split.csv"), index=False)
    pd.DataFrame(bins_rows).to_csv(os.path.join(a.out, "reliability_bins.csv"), index=False); pd.DataFrame(thr_rows).to_csv(os.path.join(a.out, "accuracy_at_thresholds.csv"), index=False)


if __name__ == "__main__":
    main()
