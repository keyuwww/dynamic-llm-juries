"""Explanatory analyses on the primary held-out scope (strict re-review of 2026-11-21, items D1, D2, D4, D5).

The primary evaluation (outer_analyze.py) covers 12 judge-benchmark pairs fixed before running: Llama-3.1-8B,
Qwen2.5-7B, Phi-4-mini and Granite-3.3-8B on MMLU-Redux, MATH and BBEH, with no selection on observed gain. The
surface, residualization and authorship analyses of the paper were run on the 19 pairs selected by an in-sample gap.
This job reruns them on the 12 primary pairs, with the same outer folds and the same readout layer as the primary
evaluation, and every fit on the training half of each fold. CPU only, from the stored hidden states.

Per pair and outer fold (the paper's two question halves, seed 0; the readout layer L_d is the one outer_pipeline.py
chose on that fold's training half, read from out_outer/<pair>/outer_<bench>.json):
  direct        projection on the class-mean direction fitted on the training half at L_d (must reproduce the stored
                outer projections; checked locally)
  scales (D4)   within-question SD of the verdict score and of the direction score on TRAINING answers (training
                projections), so verdict + direction can be scaled without test-set statistics
  inner         training answers scored by cross-fitted inner directions (inner split seed 1, as outer_pipeline.py);
                test answers scored by the mean of the two inner directions ("direct_inner")
  surface       least squares of within-question correctness on the 9 standardised surface features (training scales)
  resid_inner   direct_inner minus its linear prediction from the features (residualizer fitted to the inner
                cross-fitted training scores)
  c_perp        (MMLU-Redux, MATH) the direction with the two paired authorship directions (Qwen3.6-35B vs Qwen3.5-4B,
                Nemotron-3-Super vs Qwen3.5-4B; within question and correctness class, training half) projected out
  pairwise      incremental prediction (D2): logistic regression on within-question right-vs-wrong pairs (no
                intercept; inputs are score differences), fitted on training pairs with the inner cross-fitted
                direction scores, scored on test pairs: surface, direction, surface + direction, verdict, verdict +
                direction, verdict + surface + direction. Returns per-question AUROC sums and summed pairwise log loss.
  overlap       per test pair, whether surface and direction (and verdict and direction) rank it correctly
  splits        five further random outer splits (seeds 11..15), direction only, layer chosen by the inner split on
                the training half: per-question AUROC sums for the direction and the verdict (training-split stability)

  MODAL_PROFILE=ingridchien .venv/bin/modal run experiments/beyond_capability/primary_scope_modal.py
-> out_paper/primary_scope.json (analysed by primary_scope_analyze.py)
"""
import gzip
import json
import pathlib

import modal

HERE = pathlib.Path(__file__).resolve().parent
app = modal.App("bc-primary-scope")
vol = modal.Volume.from_name("dynamic-llm-juries-results")
N_LAYERS = {"llama3.1-8b": 32, "qwen2.5-7b": 28, "phi4-mini": 32, "granite3.3-8b": 40}
JUDGES = ("llama3.1-8b", "qwen2.5-7b", "phi4-mini", "granite3.3-8b")
BENCHES = ("mmlu", "math", "bbeh")
WEAK, MID, TOP = "qwen3.5-4b", "nemotron3-super-120b", "qwen3.6-35b-a3b"
FEAT = HERE / "out_paper" / "surface_features.json.gz"
SPLIT_SEEDS = (11, 12, 13, 14, 15)
PW = ("surface", "direct", "surface+direct", "verdict", "verdict+direct", "verdict+surface+direct")
img = modal.Image.debian_slim().pip_install("numpy")


def _unit(v):
    import numpy as np
    return v / (np.linalg.norm(v) + 1e-9)


def _centre(X, q):
    Xc = X.copy()
    for g in set(q):
        k = q == g
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


def _pairs(q, y, mask):
    """(i_right, j_wrong) index arrays for every within-question right-vs-wrong pair inside mask."""
    import numpy as np
    I, J = [], []
    for g in sorted(set(q[mask])):
        k = mask & (q == g)
        P, N = np.where(k & (y == 1))[0], np.where(k & (y == 0))[0]
        for i in P:
            for j in N:
                I.append(i)
                J.append(j)
    return np.array(I, int), np.array(J, int)


def _wauc(sr, sw):
    return (sr > sw) + 0.5 * (sr == sw)


def _perq(score, q, y, s, mask):
    """{qid: [num_all, den_all, num_same, den_same, num_diff, den_diff]}"""
    import numpy as np
    out = {}
    for g in set(q[mask]):
        k = mask & (q == g)
        P, N = np.where(k & (y == 1))[0], np.where(k & (y == 0))[0]
        if not len(P) or not len(N):
            continue
        w = _wauc(score[P][:, None], score[N][None, :])
        same = s[P][:, None] == s[N][None, :]
        out[str(g)] = [float(w.sum()), float(w.size), float(w[same].sum()), float(same.sum()), float(w[~same].sum()),
                       float((~same).sum())]
    return out


def _logit_fit(D, l2=1e-3, iters=50):
    """P(right above wrong) = sigmoid(D @ w), all targets 1 (pairs are ordered right minus wrong). Newton steps."""
    import numpy as np
    w = np.zeros(D.shape[1])
    for _ in range(iters):
        z = D @ w
        p = 1 / (1 + np.exp(-z))
        g = D.T @ (p - 1) / len(D) + l2 * w
        H = (D * (p * (1 - p))[:, None]).T @ D / len(D) + l2 * np.eye(D.shape[1])
        step = np.linalg.solve(H, g)
        w -= step
        if np.abs(step).max() < 1e-8:
            break
    return w


def _paired_dir(X, q, y, s, mask, S, W):
    import numpy as np
    diffs = []
    for g in set(q[mask]):
        for t in (0, 1):
            k = mask & (q == g) & (y == t)
            a, b = k & (s == S), k & (s == W)
            if a.any() and b.any():
                diffs.append(X[a].mean(0) - X[b].mean(0))
    return _unit(np.mean(diffs, 0))


def _wsd(x, q, mask):
    import numpy as np
    return float(np.sqrt(np.mean([np.var(x[mask & (q == g)]) for g in set(q[mask]) if (mask & (q == g)).sum() > 1])))


@app.function(image=img, volumes={"/vol": vol}, timeout=3 * 3600, cpu=8, memory=65536)
def run(judge: str, bench: str, feats: dict, layers: dict) -> dict:
    import numpy as np
    d = pathlib.Path(f"/vol/beyond_capability_allpairs/{judge}_{bench}")
    nl = N_LAYERS[judge]
    kept = sorted(set(range(0, nl + 1, 2)) | {nl})
    cand = [L for L in kept if 0 < L < nl]
    H = np.load(d / f"hidden_{bench}.npy", mmap_mode="r")
    meta = [json.loads(l) for l in open(d / f"meta_{bench}.jsonl")]
    missing = sum(m["aid"] not in feats for m in meta)
    y = np.array([m["gold"] for m in meta])
    q = np.array([m["qid"] for m in meta])
    s = np.array([m["src"] for m in meta])
    v = np.array([m["margin"] for m in meta], float)
    aid = [m["aid"] for m in meta]
    Z0 = _centre(np.array([feats.get(a, [0.0] * 9) for a in aid], float), q)
    Xs = {L: np.asarray(H[:, kept.index(L)], np.float32) for L in cand}
    Xcs = {L: _centre(Xs[L], q) for L in cand}
    yc = _centre(y.astype(float)[:, None], q)[:, 0]
    uq = sorted(set(q))
    ALL = np.ones(len(y), bool)

    def fit(L, mask):
        X = Xcs[L]
        return _unit(X[mask & (y == 1)].mean(0) - X[mask & (y == 0)].mean(0))

    def inner_masks(tr):
        trq = sorted(set(q[tr]))
        a_q = set(np.random.default_rng(1).permutation(trq)[: len(trq) // 2])
        in1 = tr & np.array([x in a_q for x in q])
        return in1, tr & ~in1

    h1q = set(np.random.default_rng(0).permutation(uq)[: len(uq) // 2])
    h1 = np.array([x in h1q for x in q])
    names = ("direct", "direct_inner", "surface", "resid_inner", "resid_full", "c_perp", "sum_train", "sum_test")
    out = {m: np.full(len(y), np.nan) for m in names}
    pw_score = {m: np.full(len(y), np.nan) for m in PW}
    folds, pw_loss, overlap = {}, {m: {} for m in PW}, {}
    for fold, te in (("h1", h1), ("h2", ~h1)):
        tr = ~te
        L = int(layers[fold])
        w_dir = fit(L, tr)
        p_all = Xs[L] @ w_dir
        out["direct"][te] = p_all[te]
        # D4: training-answer scales
        sv_tr, sd_tr = _wsd(v, q, tr), _wsd(p_all, q, tr)
        sv_te, sd_te = _wsd(v, q, te), _wsd(p_all, q, te)
        out["sum_train"][te] = v[te] / sv_tr + p_all[te] / sd_tr
        out["sum_test"][te] = v[te] / sv_te + p_all[te] / sd_te
        # inner cross-fitted training scores and the scale-matched test score
        in1, in2 = inner_masks(tr)
        w1, w2 = fit(L, in1), fit(L, in2)
        inner = np.zeros(len(y))
        inner[in2] = Xs[L][in2] @ w1
        inner[in1] = Xs[L][in1] @ w2
        dinner = (Xs[L] @ w1 + Xs[L] @ w2) / 2
        out["direct_inner"][te] = dinner[te]
        # surface model and residualizer (training half)
        sdz = Z0[tr].std(0) + 1e-9
        Z = Z0 / sdz
        wz, *_ = np.linalg.lstsq(Z[tr], yc[tr], rcond=None)
        out["surface"][te] = (Z @ wz)[te]
        din = _centre(inner[:, None], q)[:, 0]
        u, *_ = np.linalg.lstsq(Z[tr], din[tr], rcond=None)
        dic = _centre(dinner[:, None], q)[:, 0]
        out["resid_inner"][te] = (dic - Z @ u)[te]
        dfull_tr = _centre(np.where(tr, p_all, 0.0)[:, None], q)[:, 0]  # in-sample training projections (comparison)
        u2, *_ = np.linalg.lstsq(Z[tr], dfull_tr[tr], rcond=None)
        dc = _centre(p_all[:, None], q)[:, 0]
        out["resid_full"][te] = (dc - Z @ u2)[te]
        r2 = 1 - ((din[tr] - Z[tr] @ u) ** 2).sum() / (din[tr] ** 2).sum()
        # authorship directions projected out (MMLU-Redux and MATH pools only)
        if bench in ("mmlu", "math"):
            A = np.stack([_paired_dir(Xcs[L], q, y, s, tr, TOP, WEAK), _paired_dir(Xcs[L], q, y, s, tr, MID, WEAK)], 1)
            Qa, _ = np.linalg.qr(A)
            wp = w_dir - Qa @ (Qa.T @ w_dir)
            out["c_perp"][te] = (Xs[L] @ wp)[te]
        # D2: pairwise incremental prediction; training inputs use the inner cross-fitted direction scores
        Itr, Jtr = _pairs(q, y, tr)
        Ite, Jte = _pairs(q, y, te)
        base_tr = {"surface": Z @ wz, "direct": inner, "verdict": v}
        base_te = {"surface": Z @ wz, "direct": dinner, "verdict": v}
        # the surface score is a fitted combination; for the pairwise models use the raw standardised features instead
        cols_tr = {"surface": Z, "direct": inner[:, None], "verdict": v[:, None]}
        cols_te = {"surface": Z, "direct": dinner[:, None], "verdict": v[:, None]}
        wts = {}
        for m in PW:
            parts = m.split("+")
            Xtr = np.hstack([cols_tr[p] for p in parts])
            Xte = np.hstack([cols_te[p] for p in parts])
            sc = Xtr[Itr] - Xtr[Jtr]
            scale = sc.std(0) + 1e-9
            w = _logit_fit(sc / scale)
            wts[m] = (w / scale).tolist()
            pw_score[m][te] = (Xte @ (w / scale))[te]
            zte = (Xte[Ite] - Xte[Jte]) @ (w / scale)
            ll = np.logaddexp(0, -zte)  # -log sigmoid(z)
            for g, val in zip(q[Ite], ll):
                pw_loss[m].setdefault(str(g), [0.0, 0.0])
                pw_loss[m][str(g)][0] += float(val)
                pw_loss[m][str(g)][1] += 1.0
        del base_tr, base_te
        folds[fold] = dict(layer=L, n_train=int(tr.sum()), n_test=int(te.sum()), scale_verdict_train=sv_tr,
                           scale_direct_train=sd_tr, scale_verdict_test=sv_te, scale_direct_test=sd_te,
                           r2_inner=float(r2), pairwise_weights=wts)
    # overlap of correct rankings on test pairs (both folds)
    for a_name, b_name in (("surface", "direct"), ("verdict", "direct"), ("verdict", "surface")):
        sa = v if a_name == "verdict" else out[a_name]
        sb = out[b_name]
        I, J = _pairs(q, y, ALL)
        wa, wb = _wauc(sa[I], sa[J]), _wauc(sb[I], sb[J])
        same = s[I] == s[J]
        res = {}
        for part, k in (("all", np.ones(len(I), bool)), ("same", same), ("diff", ~same)):
            res[part] = dict(n=int(k.sum()), both=float((wa * wb)[k].sum()), a_only=float((wa * (1 - wb))[k].sum()),
                             b_only=float(((1 - wa) * wb)[k].sum()), neither=float(((1 - wa) * (1 - wb))[k].sum()),
                             corr=float(np.corrcoef(wa[k], wb[k])[0, 1]) if k.sum() > 2 else None)
        overlap[f"{a_name}|{b_name}"] = res
    # repeated outer splits, direction only
    splits = {}
    for seed in SPLIT_SEEDS:
        sq = set(np.random.default_rng(seed).permutation(uq)[: len(uq) // 2])
        hs = np.array([x in sq for x in q])
        sc = np.full(len(y), np.nan)
        chosen = {}
        for fold, te in (("a", hs), ("b", ~hs)):
            tr = ~te
            in1, in2 = inner_masks(tr)
            knows = {}
            for L in cand:
                t = np.zeros(len(y))
                t[in2] = Xs[L][in2] @ fit(L, in1)
                t[in1] = Xs[L][in1] @ fit(L, in2)
                knows[L] = _within_auc(y[tr], t[tr], q[tr])
            L = max(knows, key=knows.get)
            chosen[fold] = int(L)
            sc[te] = Xs[L][te] @ fit(L, tr)
        splits[str(seed)] = dict(layers=chosen, direct=_perq(sc, q, y, s, ALL))
    perq = {m: _perq(out[m], q, y, s, ~np.isnan(out[m])) for m in out}
    perq["verdict"] = _perq(v, q, y, s, ALL)
    perq |= {f"pw:{m}": _perq(pw_score[m], q, y, s, ALL) for m in PW}
    return dict(judge=judge, bench=bench, n=int(len(y)), missing_features=int(missing), folds=folds, perq=perq,
                pw_loss=pw_loss, overlap=overlap, splits=splits,
                direct_test={a: float(x) for a, x in zip(aid, out["direct"])})


@app.local_entrypoint()
def main(only: str = ""):
    F = json.load(gzip.open(FEAT, "rt"))["F"]
    jobs = [(j, b) for j in JUDGES for b in BENCHES]
    if only:
        jobs = [x for x in jobs if f"{x[0]}|{x[1]}" in only.split(",")]
    args = []
    for j, b in jobs:
        info = json.load(open(HERE / "out_outer" / f"{j}_{b}" / f"outer_{b}.json"))
        aids = {json.loads(l)["aid"] for l in open(HERE / "out_outer" / f"{j}_{b}" / f"outer_{b}.jsonl")}
        args.append((j, b, {a: F[a] for a in aids if a in F}, {k: f["direct_layer"] for k, f in info["folds"].items()}))
    f = HERE / "out_paper" / "primary_scope.json"
    res = json.load(open(f)) if f.exists() else {}
    for r in run.starmap(args, return_exceptions=True):
        if isinstance(r, Exception):
            print("FAILED", str(r)[:500], flush=True)
            continue
        res[f"{r['judge']}|{r['bench']}"] = r
        print(r["judge"], r["bench"], r["n"], "missing features", r["missing_features"],
              {k: (x["layer"], round(x["r2_inner"], 3)) for k, x in r["folds"].items()}, flush=True)
    json.dump(res, open(f, "w"))
