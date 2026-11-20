"""Nested check of the surface residualization (future_paper_improvements.md, direction paper, priority 1).

In paper_surface.py the direction scores are cross-fitted over the two question halves, and the residualizer is then
cross-fitted over the same halves. The residualizer trained on half A uses half-A direction scores, which were fitted
with half-B labels, and is applied to half B: the composed procedure can see the evaluated labels. Here every fit of
the composed procedure stays inside the outer training half:

  outer folds  the paper's two question halves (seed 0); each is the test half once
  on the training half only
    layer       inner split of the training questions (seed 1): each candidate layer's cross-fitted ranking; the best
    direction   class-mean difference after centring by question, on the whole training half, at that layer
    surface     least squares of within-question correctness on the standardised features (scales from the training half)
    residualizer least squares of the INNER cross-fitted direction scores (training half) on the same features
  on the test half: direction score, surface score, direction score minus its feature prediction, verdict
  scale-matched variant (direct_inner, resid_inner): the test answers are scored by the two inner directions (mean of
    the two projections), the same directions that produced the residualizer's training targets
Centring within question uses no labels. Per-question AUROC sums (all / same-model / different-model pairs) come back,
pooled locally with the synchronised bootstrap (nested_surface_analyze.py).

  .venv/bin/python experiments/beyond_capability/nested_surface_modal.py --features   # local: out_paper/surface_features.json.gz
  MODAL_PROFILE=ingridchien .venv/bin/modal run experiments/beyond_capability/nested_surface_modal.py
  MODAL_PROFILE=keyuwww     .venv/bin/modal run experiments/beyond_capability/nested_surface_modal.py --legacy
-> out_paper/nested_surface.json
"""
import gzip
import json
import pathlib
import sys

import modal

HERE = pathlib.Path(__file__).resolve().parent
app = modal.App("bc-nested-surface")
vol = modal.Volume.from_name("dynamic-llm-juries-results")
N_LAYERS = {"llama3.1-8b": 32, "llama3.2-3b": 28, "qwen3.5-4b": 32, "phi4-mini": 32, "mistral-7b": 32,
            "granite3.3-8b": 40, "llama3.2-1b": 16, "qwen2.5-7b": 28}
LEGACY = {("llama3.1-8b", "math"): "/vol/beyond_capability_layers/math",
          ("llama3.2-3b", "mmlu"): "/vol/beyond_capability_layers/mmlu3b"}
FEAT = HERE / "out_paper" / "surface_features.json.gz"
img = modal.Image.debian_slim().pip_install("numpy")


def _unit(v):
    import numpy as np
    return v / (np.linalg.norm(v) + 1e-9)


def _centre(X, keys):
    Xc = X.astype(float).copy() if X.dtype != "float32" else X.copy()
    for g in set(keys):
        k = keys == g
        Xc[k] -= X[k].mean(0)
    return Xc


def _within_auc(y, s, q):
    num = den = 0.0
    for g in set(q):
        k = q == g
        a, b = s[k & (y == 1)], s[k & (y == 0)]
        if len(a) and len(b):
            num += (a[:, None] > b[None, :]).sum() + 0.5 * (a[:, None] == b[None, :]).sum()
            den += len(a) * len(b)
    return num / den if den else 0.5


def _perq(score, q, y, s, keep):
    out = {}
    for g in set(q[keep]):
        k = keep & (q == g)
        import numpy as np
        P, N = np.where(k & (y == 1))[0], np.where(k & (y == 0))[0]
        if not len(P) or not len(N):
            continue
        w = (score[P][:, None] > score[N][None, :]) + 0.5 * (score[P][:, None] == score[N][None, :])
        same = s[P][:, None] == s[N][None, :]
        out[str(g)] = [float(w.sum()), float(w.size), float(w[same].sum()), float(same.sum()), float(w[~same].sum()),
                       float((~same).sum())]
    return out


@app.function(image=img, volumes={"/vol": vol}, timeout=3 * 3600, cpu=8, memory=65536)
def run(judge: str, bench: str, feats: dict) -> dict:
    import numpy as np
    if (judge, bench) in LEGACY:
        d = pathlib.Path(LEGACY[(judge, bench)])
        kept = json.load(open(d / f"layers_{bench}.json"))["layers"]
    else:
        d = pathlib.Path(f"/vol/beyond_capability_allpairs/{judge}_{bench}")
        nl = N_LAYERS[judge]
        kept = sorted(set(range(0, nl + 1, 2)) | {nl})
    H = np.load(d / f"hidden_{bench}.npy", mmap_mode="r")
    meta = [json.loads(l) for l in open(d / f"meta_{bench}.jsonl")]
    idx = np.array([i for i, m in enumerate(meta) if m["aid"] in feats])
    meta = [meta[i] for i in idx]
    y = np.array([m["gold"] for m in meta])
    q = np.array([m["qid"] for m in meta])
    s = np.array([m["src"] for m in meta])
    v = np.array([m["margin"] for m in meta], float)
    Z0 = _centre(np.array([feats[m["aid"]] for m in meta], float), q)
    cand = [L for L in kept if 0 < L < max(kept)]
    Xs = {L: np.asarray(H[idx, kept.index(L)], np.float32) for L in cand}
    Xcs = {L: _centre(Xs[L], q) for L in cand}
    uq = sorted(set(q))
    h1 = np.isin(q, list(np.random.default_rng(0).permutation(uq)[: len(uq) // 2]))
    out = {m: np.zeros(len(y)) for m in ("direct", "surface", "dir_resid", "direct_inner", "resid_inner")}
    folds = {}

    def fit_dir(L, mask):
        X = Xcs[L]
        return _unit(X[mask & (y == 1)].mean(0) - X[mask & (y == 0)].mean(0))
    for name, te in (("h1", h1), ("h2", ~h1)):
        tr = ~te
        trq = sorted(set(q[tr]))
        a_q = set(np.random.default_rng(1).permutation(trq)[: len(trq) // 2])
        in1 = tr & np.isin(q, list(a_q))
        in2 = tr & ~in1
        inner, knows = {}, {}
        for L in cand:
            sc = np.zeros(len(y))
            for learn, apply in ((in1, in2), (in2, in1)):
                sc[apply] = Xs[L][apply] @ fit_dir(L, learn)
            inner[L], knows[L] = sc, _within_auc(y[tr], sc[tr], q[tr])
        L = max(knows, key=knows.get)
        dte = Xs[L] @ fit_dir(L, tr)
        sd = Z0[tr].std(0) + 1e-9
        Z = Z0 / sd
        yc = _centre(y.astype(float)[:, None], q)[:, 0]
        w, *_ = np.linalg.lstsq(Z[tr], yc[tr], rcond=None)
        din = _centre(inner[L][:, None], q)[:, 0]
        u, *_ = np.linalg.lstsq(Z[tr], din[tr], rcond=None)
        dc = _centre(dte[:, None], q)[:, 0]
        # scale-matched variant: test answers scored by the same two inner directions whose cross-fitted training
        # scores the residualizer was fitted to (mean of the two projections), then residualized with the same u
        dinner = (Xs[L] @ fit_dir(L, in1) + Xs[L] @ fit_dir(L, in2)) / 2
        dic = _centre(dinner[:, None], q)[:, 0]
        out["direct_inner"][te] = dinner[te]
        out["resid_inner"][te] = dic[te] - Z[te] @ u
        out["direct"][te] = dte[te]
        out["surface"][te] = Z[te] @ w
        out["dir_resid"][te] = dc[te] - Z[te] @ u
        r2 = 1 - ((din[tr] - Z[tr] @ u) ** 2).sum() / (din[tr] ** 2).sum()
        folds[name] = dict(layer=int(L), inner_knows=float(knows[L]), r2_inner=float(r2))
    keep = np.ones(len(y), bool)
    perq = {m: _perq(out[m], q, y, s, keep) for m in out} | {"verdict": _perq(v, q, y, s, keep)}
    return dict(judge=judge, bench=bench, n=int(len(y)), folds=folds, perq=perq)


def features():
    """local: surface features of every answer in the 19 small-judge main-pool pairs, keyed by answer id."""
    sys.path.insert(0, str(HERE))
    import paper_surface as PS
    from paper_data import BIG, pool_sets
    F = {}
    for b, f in PS.FILES.items():
        for l in gzip.open(HERE / "inputs" / f, "rt"):
            r = json.loads(l)
            if r["mode"] == "J":
                F[r["aid"]] = [float(x) for x in PS.feats(PS.answer_text(r))]
    pairs = {f"{j}|{b}": [r["aid"] for r in o["rows"] if r["aid"] in F] for (j, b), o in pool_sets().items() if j not in BIG}
    json.dump(dict(pairs=pairs, F=F), gzip.open(FEAT, "wt"))
    print(f"{FEAT}: {len(pairs)} pairs, {len(F)} answers")


@app.local_entrypoint()
def main(legacy: bool = False, only: str = ""):
    D = json.load(gzip.open(FEAT, "rt"))
    F = D["F"]
    jobs = [tuple(k.split("|")) for k in D["pairs"]]
    jobs = [x for x in jobs if (x in LEGACY) == legacy]
    if only:
        jobs = [x for x in jobs if f"{x[0]}|{x[1]}" in only.split(",")]
    args = [(j, b, {a: F[a] for a in D["pairs"][f"{j}|{b}"]}) for j, b in jobs]
    f = HERE / "out_paper" / "nested_surface.json"
    res = json.load(open(f)) if f.exists() else {}
    for r in run.starmap(args, return_exceptions=True):
        if isinstance(r, Exception):
            print("FAILED", str(r)[:300], flush=True)
            continue
        res[f"{r['judge']}|{r['bench']}"] = r
        print(r["judge"], r["bench"], r["n"], r["folds"], flush=True)
    json.dump(res, open(f, "w"))


if __name__ == "__main__" and "--features" in sys.argv:
    features()
