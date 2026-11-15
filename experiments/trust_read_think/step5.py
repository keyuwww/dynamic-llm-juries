#!/usr/bin/env python3
"""
Step 5 of Trust / Read / Think: the literature's probes on our judge, how few labels they need, and a label-free router.
All on the saved Step 1 data (Qwen3.5-4B, verdict position, thinking off); no GPU.

Part A: which probe reads the hidden state best, and with how many gold labels?
  probes (single layer unless noted)
    dim        class-balanced difference of means, score = projection         (No Answer Needed, 2509.10625)
    logreg     standardize + L2 logistic, C = 0.3                              (our Step 2 probe; Calibrating LLM Judges-style)
    failures   no-intercept L2 logistic on raw states, alpha in {1..1e4} by inner CV   (LLMs Encode Their Failures, 2602.09924)
    pca48      PCA to 48 components (fit in the fold) + L2 logistic            (Opening LLM Judges, 2609.32407)
    lens       logit lens: the CORRECT - INCORRECT logit read at each of the 32 layers, then L2 logistic on those 32
               numbers                                                         (Opening LLM Judges)
    multi      layers 8, 12, ..., 32 concatenated, PCA 64 + L2 logistic         (SWIFT-style all-layer read, 2505.12225)
  label budgets: 25 / 50 / 100 / 200 / all gold labels from the training folds (3 random draws each)
  layer: picked by 3-fold inner CV of the dim probe on the labelled items (25 labels: the best layer on the other
         three benchmarks, so no target labels are spent on it)
  targets: good    the response is good (same-source AUROC, as before)
           wrong   the gut verdict is wrong (plain AUROC): the escalation target most papers use
  surface control: a probe on 5 surface features only (log length, newlines, digit share, markdown share, refusal
           words), and the logreg probe with those features regressed out of the hidden state (Opening LLM Judges)

Part B: a label-free router. Target: does Think@1,024 flip the gut verdict? Needs thinking on some items, no gold labels.
  signals  uncertainty     1 - |2 P_gut - 1|                                (baseline: Step 3)
           lens_wobble     how much the logit-lens verdict moves over layers 16-32 (no training)
           flip_probe      logreg / dim probe on the hidden state, trained on k thought items (25 / 50 / 100 / all)
           flip_probe+unc  average of the two ranks (probe score, uncertainty)
  scored by AUROC for flips and for gut errors, and by routing: think on the top q% by signal, keep the gut elsewhere.

  .venv/bin/python experiments/trust_read_think/step5.py
"""
import json
import re
import warnings
from pathlib import Path

import numpy as np
from joblib import Parallel, delayed
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
import step2
from step2 import BENCHES, strata_auc

HERE = Path(__file__).resolve().parent
from paths import RAW, RES, ITEMS  # noqa: E402
CAND = [8, 12, 16, 20, 24, 28, 32]
BUDGETS = (25, 50, 100, 200, "all")
SEEDS = 3
TB = 1024
QS = (0.1, 0.2, 0.3, 0.5)
REFUSAL = re.compile(r"\b(I can(no|')t|I cannot|I won't|I'm sorry|I am sorry|unable to (help|assist|provide))", re.I)


# ----------------------------------------------------------------------------- features
def lens_feats(hs, W):
    """(N, 32) logit-lens CORRECT - INCORRECT logits at layers 1..32. HF's last hidden state is already normed."""
    g, u, eps = W["gain"], W["u"], float(W["eps"])
    h = hs[:, 1:].astype(np.float32)
    rms = np.sqrt((h ** 2).mean(-1, keepdims=True) + eps)
    out = ((h / rms) * g) @ u
    out[:, -1] = h[:, -1] @ u
    return out


def surface(texts):
    def resp(t):
        # the graded response is the last block of the prompt; take the text after the last response marker if present
        for m in ("[ASSISTANT]", "[RESPONSE]", "Response:", "RESPONSE"):
            if m in t:
                t = t.rsplit(m, 1)[1]
                break
        return t
    rows = []
    for t in texts:
        r = resp(t)
        n = max(len(r), 1)
        rows.append([np.log(n), r.count("\n") / n * 100, sum(c.isdigit() for c in r) / n,
                     sum(c in "*#|`" for c in r) / n, float(bool(REFUSAL.search(r[:500])))])
    return np.array(rows, np.float32)


# ----------------------------------------------------------------------------- probes
def dim_fit(X, y):
    mu1, mu0 = X[y == 1].mean(0), X[y == 0].mean(0)
    w = mu1 - mu0
    w = w / (np.linalg.norm(w) + 1e-8)
    mid = (mu1 + mu0) / 2
    return lambda Z: (Z - mid) @ w


def lr(C=0.3):
    return make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=3000))


def fit_predict(method, Xtr, ytr, Xte, Ltr=None, Lte=None, Mtr=None, Mte=None, g_tr=None):
    if method == "dim":
        return dim_fit(Xtr, ytr)(Xte)
    if method == "logreg":
        return lr().fit(Xtr, ytr).predict_proba(Xte)[:, 1]
    if method == "failures":
        best, bs = 1.0, -1
        if len(ytr) >= 30:
            folds = list(GroupKFold(3).split(Xtr, ytr, g_tr))
            for a in (1, 10, 100, 1000, 10000):
                s = np.zeros(len(ytr))
                ok = True
                for i, j in folds:
                    if len(np.unique(ytr[i])) < 2:
                        ok = False
                        break
                    s[j] = LogisticRegression(C=1 / a, fit_intercept=False, max_iter=3000).fit(Xtr[i], ytr[i]) \
                        .decision_function(Xtr[j])
                sc = roc_auc_score(ytr, s) if ok else -1
                if sc > bs:
                    best, bs = a, sc
        return LogisticRegression(C=1 / best, fit_intercept=False, max_iter=3000).fit(Xtr, ytr).decision_function(Xte)
    if method == "pca48":
        k = min(48, len(ytr) - 1)
        return make_pipeline(StandardScaler(), PCA(k, random_state=0), LogisticRegression(C=0.3, max_iter=3000)) \
            .fit(Xtr, ytr).predict_proba(Xte)[:, 1]
    if method == "lens":
        return lr().fit(Ltr, ytr).predict_proba(Lte)[:, 1]
    if method == "multi":
        k = min(64, len(ytr) - 1)
        return make_pipeline(StandardScaler(), PCA(k, random_state=0), LogisticRegression(C=0.3, max_iter=3000)) \
            .fit(Mtr, ytr).predict_proba(Mte)[:, 1]
    raise ValueError(method)


METHODS = ("dim", "logreg", "failures", "pca48", "lens", "multi")


def scaled(L, n_layers):
    """A layer given for the 32-layer Qwen judges, moved to the same relative depth in a judge with n_layers."""
    return max(1, min(n_layers, int(round(L * n_layers / 32))))


def pick_layer(HS, y, g, fallback):
    nL = HS.shape[1] - 1
    cand = sorted({scaled(L, nL) for L in CAND})          # identical to CAND for 32-layer judges
    fallback = scaled(fallback, nL)
    if len(y) < 50 or len(np.unique(y)) < 2:
        return fallback
    folds = list(GroupKFold(3).split(HS[:, 0], y, g))
    best, bs = fallback, -1
    for L in cand:
        s = np.zeros(len(y))
        ok = True
        for a, b in folds:
            if len(np.unique(y[a])) < 2:
                ok = False
                break
            s[b] = dim_fit(HS[a, L], y[a])(HS[b, L])
        if ok and len(np.unique(y)) == 2:
            sc = roc_auc_score(y, s)
            if sc > bs:
                best, bs = L, sc
    return best


def subsample(tr, k, g, rng):
    """k labelled items from the training indices, drawn by whole questions."""
    if k == "all" or k >= len(tr):
        return tr
    groups = rng.permutation(np.unique(g[tr]))
    pick, n = [], 0
    for q in groups:
        ii = tr[g[tr] == q]
        pick.append(ii)
        n += len(ii)
        if n >= k:
            break
    return np.concatenate(pick)[:k] if n > k else np.concatenate(pick)


def run_cell(b, d, target, method, k, seed, fallback):
    """Out-of-fold scores for one (target, method, budget, seed)."""
    y = d["y"] if target == "good" else d["wrong"]
    g, HS, LN, MU = d["group"], d["hs"], d["lens"], d["multi"]
    rng = np.random.default_rng(seed)
    out = np.full(len(y), np.nan)
    for tr, te in GroupKFold(5).split(HS[:, 0], y, g):
        lab = subsample(tr, k, g, rng)
        if len(np.unique(y[lab])) < 2 or min(np.bincount(y[lab])) < 2:
            continue
        L = pick_layer(HS[lab], y[lab], g[lab], fallback)
        out[te] = fit_predict(method, HS[lab, L], y[lab], HS[te, L], LN[lab], LN[te], MU[lab], MU[te], g[lab])
    return out


def score(target, s, d):
    m = ~np.isnan(s)
    if target == "good":
        return strata_auc(s[m], d["y"][m], d["strata"][m])
    return roc_auc_score(d["wrong"][m], s[m])


def main():
    D = step2.load()
    W = {k: np.array(v, np.float32) for k, v in json.loads((RAW / "lens_weights.json").read_text()).items()}
    s2 = json.loads((RES / "step2.json").read_text())
    items = [json.loads(l) for l in open(ITEMS / "items.jsonl")]
    for b in BENCHES:
        d = D[b]
        d["lens"] = lens_feats(d["hs"], W)
        d["multi"] = d["hs"][:, [8, 12, 16, 20, 24, 28, 32]].reshape(len(d["y"]), -1)
        d["surf"] = surface([it["text"] for it in items if it["bench"] == b])
        d["gv"] = (d["gut"] > 0.5).astype(int)
        d["wrong"] = (d["gv"] != d["y"]).astype(int)
        d["tv"] = (d["think"][TB] > 0.5).astype(int)
        d["flip"] = (d["gv"] != d["tv"]).astype(int)
        chk = 1 / (1 + np.exp(-d["lens"][:, -1]))
        print(b, "lens check: last-layer lens vs gut P, max abs diff", round(float(np.abs(chk - d["gut"]).max()), 4),
              flush=True)

    res = {}
    for b in BENCHES:
        d = D[b]
        fb = s2[b]["transfer_layer"]
        fb = min(CAND, key=lambda L: abs(L - fb))
        r = dict(n=len(d["y"]), trust=dict(good=round(float(strata_auc(d["gut"], d["y"], d["strata"])), 3),
                                           wrong=round(float(roc_auc_score(d["wrong"], 1 - np.abs(2 * d["gut"] - 1))), 3)))
        # ---- Part A: methods x budgets x targets
        jobs = [(t, m, k, s) for t in ("good", "wrong") for m in METHODS for k in BUDGETS
                for s in (range(SEEDS) if k != "all" else [0])]
        outs = Parallel(n_jobs=-1)(delayed(run_cell)(b, d, t, m, k, s, fb) for t, m, k, s in jobs)
        A = {}
        for (t, m, k, s), o in zip(jobs, outs):
            A.setdefault(t, {}).setdefault(m, {}).setdefault(str(k), []).append(score(t, o, d))
        r["probes"] = {t: {m: {k: [round(float(np.mean(v)), 3), round(float(np.std(v)), 3)] for k, v in mk.items()}
                           for m, mk in tm.items()} for t, tm in A.items()}
        # ---- surface control (all labels)
        y, g = d["y"], d["group"]
        surf_oof, resid_oof = np.zeros(len(y)), np.zeros(len(y))
        L = int(np.argmax(s2[b]["curve"])) + 1
        for tr, te in GroupKFold(5).split(d["hs"][:, 0], y, g):
            surf_oof[te] = lr(1.0).fit(d["surf"][tr], y[tr]).predict_proba(d["surf"][te])[:, 1]
            S1 = np.c_[d["surf"], np.ones(len(y))]
            beta, *_ = np.linalg.lstsq(S1[tr], d["hs"][tr, L], rcond=None)
            Xr = d["hs"][:, L] - S1 @ beta
            resid_oof[te] = lr().fit(Xr[tr], y[tr]).predict_proba(Xr[te])[:, 1]
        r["surface"] = dict(surface_only=round(float(strata_auc(surf_oof, y, d["strata"])), 3),
                            surface_only_plain=round(float(roc_auc_score(y, surf_oof)), 3),
                            logreg_residualized=round(float(strata_auc(resid_oof, y, d["strata"])), 3), layer=L)

        # ---- Part B: label-free flip router
        unc = 1 - np.abs(2 * d["gut"] - 1)
        late = d["lens"][:, 15:]                          # layers 16..32
        wobble = (np.abs(np.diff(np.sign(late), axis=1)) > 0).sum(1) + 0.01 * late.std(1)
        sig = {"uncertainty": unc, "lens_wobble": wobble}
        flip, wrong = d["flip"], d["wrong"]
        Lf = 20
        for k in (25, 50, 100, "all"):
            vals_p = []
            for seed in range(SEEDS if k != "all" else 1):
                rng = np.random.default_rng(seed)
                p = np.full(len(y), 0.5)
                for tr, te in GroupKFold(5).split(d["hs"][:, 0], flip, g):
                    lab = subsample(tr, k, g, rng)
                    if len(np.unique(flip[lab])) < 2 or min(np.bincount(flip[lab])) < 2:
                        continue
                    p[te] = lr().fit(d["hs"][lab, Lf], flip[lab]).predict_proba(d["hs"][te, Lf])[:, 1]
                vals_p.append(p)
            sig[f"flip_probe_{k}"] = np.mean(vals_p, 0)
            pm = sig[f"flip_probe_{k}"]
            sig[f"flip_probe+unc_{k}"] = (np.argsort(np.argsort(pm)) + np.argsort(np.argsort(unc))) / (2 * len(y))
        r["router_auc"] = {name: dict(flip=round(float(roc_auc_score(flip, s)), 3),
                                      gut_wrong=round(float(roc_auc_score(wrong, s)), 3)) for name, s in sig.items()}
        gv, tv = d["gv"], d["tv"]

        def route(s, q):
            k = int(round(q * len(y)))
            v = gv.copy()
            o = np.argsort(-s, kind="stable")[:k]
            v[o] = tv[o]
            return float((v == y).mean())
        rnd = [np.mean([route(np.random.default_rng(i).random(len(y)), q) for i in range(200)]) for q in QS]
        r["routing"] = dict(qs=QS, gut=round(float((gv == y).mean()), 3), think=round(float((tv == y).mean()), 3),
                            random=[round(float(x), 3) for x in rnd],
                            **{name: [round(route(s, q), 3) for q in QS] for name, s in sig.items()})
        res[b] = r
        print(b, json.dumps(r), flush=True)
    (RES / "step5.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
