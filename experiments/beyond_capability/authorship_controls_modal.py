"""Controls for the authorship analysis (reviewer D3). CPU only, from stored hidden states.

Per small judge, MMLU-Redux and MATH pools (answers by Qwen3.5-4B, Nemotron-3-Super-120B, Qwen3.6-35B-A3B), at the
pair's best-ranking layer, cross-fit over the paper's two question halves (seed 0). Every fit uses the training half.

  observed     c (question-centred correctness direction); a_top, a_mid (paired authorship directions, within question
               and correctness class); c_perp = c with span(a_top, a_mid) projected out
  perm         100 label permutations: answering-model labels shuffled within each (question, correctness) cell of the
               training half, the same paired fit, the same projection -> how much a 2-D subspace fitted the same way
               but without authorship removes
  iso          100 isotropic random 2-D subspaces (no labels) projected out of c
  balanced     c_gb: correctness direction centred within (question, answering model) instead of question: training
               uses only within-model right-vs-wrong contrasts
  holdout      for each answering model G: c fitted on the training half WITHOUT G's answers, scored on G's same-model
               right/wrong pairs in the test half; next to c fitted on all three models and the verdict, same pairs
Per-question AUROC sums (all / same-model / different-model pairs) are returned for c, c_perp, c_gb and the verdict, so
pooled numbers use the synchronised bootstrap locally (paper_authorship.py).

Llama-3.1-8B MATH and Llama-3.2-3B MMLU-Redux live in the older layer-sweep storage on the keyuwww volume:
  MODAL_PROFILE=keyuwww  .venv/bin/modal run experiments/beyond_capability/authorship_controls_modal.py --legacy
  MODAL_PROFILE=ingridchien .venv/bin/modal run experiments/beyond_capability/authorship_controls_modal.py
-> out_paper/authorship_controls.json
"""
import json
import pathlib

import modal

app = modal.App("bc-authorship-controls")
vol = modal.Volume.from_name("dynamic-llm-juries-results")
N_LAYERS = {"llama3.1-8b": 32, "llama3.2-3b": 28, "qwen3.5-4b": 32, "phi4-mini": 32, "mistral-7b": 32,
            "granite3.3-8b": 40, "llama3.2-1b": 16, "qwen2.5-7b": 28}
LEGACY = {("llama3.1-8b", "math"): "/vol/beyond_capability_layers/math",
          ("llama3.2-3b", "mmlu"): "/vol/beyond_capability_layers/mmlu3b"}
WEAK, MID, TOP = "qwen3.5-4b", "nemotron3-super-120b", "qwen3.6-35b-a3b"
GENS = (WEAK, MID, TOP)
img = modal.Image.debian_slim().pip_install("numpy")
N_PERM = 100


def _unit(v):
    import numpy as np
    return v / (np.linalg.norm(v) + 1e-9)


def _centre(X, keys):
    import numpy as np
    Xc = X.copy()
    for g in set(keys):
        k = keys == g
        Xc[k] -= X[k].mean(0)
    return Xc


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


def _perq(score, q, y, s, keep=None):
    """{qid: [num_all, den_all, num_same, den_same, num_diff, den_diff]} right-vs-wrong within question."""
    import numpy as np
    out = {}
    keep = np.ones(len(q), bool) if keep is None else keep
    for g in set(q[keep]):
        k = keep & (q == g)
        P, N = np.where(k & (y == 1))[0], np.where(k & (y == 0))[0]
        if not len(P) or not len(N):
            continue
        w = (score[P][:, None] > score[N][None, :]) + 0.5 * (score[P][:, None] == score[N][None, :])
        same = s[P][:, None] == s[N][None, :]
        out[str(g)] = [float(w.sum()), float(w.size), float(w[same].sum()), float(same.sum()), float(w[~same].sum()),
                       float((~same).sum())]
    return out


def _auc(perq, part=0):
    a = sum(v[2 * part] for v in perq.values())
    b = sum(v[2 * part + 1] for v in perq.values())
    return 100 * a / b if b else None


def _within_auc(y, s, q):
    import numpy as np
    num = den = 0.0
    for g in set(q):
        k = q == g
        a, b = s[k & (y == 1)], s[k & (y == 0)]
        if len(a) and len(b):
            num += (a[:, None] > b[None, :]).sum() + 0.5 * (a[:, None] == b[None, :]).sum()
            den += len(a) * len(b)
    return num / den


def _load(judge, bench):
    import numpy as np
    if (judge, bench) in LEGACY:
        d = pathlib.Path(LEGACY[(judge, bench)])
        kept = json.load(open(d / f"layers_{bench}.json"))["layers"]
        L = None
    else:
        d = pathlib.Path(f"/vol/beyond_capability_allpairs/{judge}_{bench}")
        nl = N_LAYERS[judge]
        kept = sorted(set(range(0, nl + 1, 2)) | {nl})
        L = int(json.load(open(d / f"choice_{bench}.json"))["best_knows_layer"])
    H = np.load(d / f"hidden_{bench}.npy", mmap_mode="r")
    meta = [json.loads(l) for l in open(d / f"meta_{bench}.jsonl")]
    return H, kept, meta, L


@app.function(image=img, volumes={"/vol": vol}, timeout=3 * 3600, cpu=8, memory=65536)
def run(judge: str, bench: str) -> dict:
    import numpy as np
    H, kept, meta, L = _load(judge, bench)
    y = np.array([m["gold"] for m in meta])
    q = np.array([m["qid"] for m in meta])
    s = np.array([m["src"] for m in meta])
    v = np.array([m["margin"] for m in meta], float)
    uq = sorted(set(q))
    h1q = set(np.random.default_rng(0).permutation(uq)[: len(uq) // 2])
    h1 = np.array([x in h1q for x in q])
    if L is None:  # legacy storage: best cross-fit layer, as pair_pipeline.py does
        best = {}
        for Lc in kept[1:-1]:
            X = np.asarray(H[:, kept.index(Lc)], np.float32)
            Xc = _centre(X, q)
            sc = np.zeros(len(y))
            for tr in (h1, ~h1):
                sc[~tr] = X[~tr] @ _unit(Xc[tr][y[tr] == 1].mean(0) - Xc[tr][y[tr] == 0].mean(0))
            best[Lc] = _within_auc(y, sc, q)
        L = max(best, key=best.get)
    X = np.asarray(H[:, kept.index(L)], np.float32)
    Xc = _centre(X, q)
    qs_key = np.array([f"{a}#{b}" for a, b in zip(q, s)])
    Xgb = _centre(X, qs_key)
    rng = np.random.default_rng(11)
    sc = {k: np.zeros(len(y)) for k in ("c", "c_perp", "c_gb")}
    perm_sc = np.zeros((N_PERM, len(y)))
    iso_sc = np.zeros((N_PERM, len(y)))
    ho = {G: {"c_ho": np.zeros(len(y)), "c_all": np.zeros(len(y))} for G in GENS}
    for tr in (h1, ~h1):
        te = ~tr
        c = _unit(Xc[tr][y[tr] == 1].mean(0) - Xc[tr][y[tr] == 0].mean(0))
        a_top, a_mid = _paired_dir(X, q, y, s, tr, TOP, WEAK), _paired_dir(X, q, y, s, tr, MID, WEAK)
        Q, _ = np.linalg.qr(np.stack([a_top, a_mid], 1))
        c_perp = c - Q @ (Q.T @ c)
        c_gb = _unit(Xgb[tr][y[tr] == 1].mean(0) - Xgb[tr][y[tr] == 0].mean(0))
        for k, d in (("c", c), ("c_perp", c_perp), ("c_gb", c_gb)):
            sc[k][te] = X[te] @ d
        # permutation null: shuffle answering-model labels within (question, correctness) cells of the training half
        cells = {}
        for i in np.where(tr)[0]:
            cells.setdefault((q[i], y[i]), []).append(i)
        for p in range(N_PERM):
            sp = s.copy()
            for idx in cells.values():
                sp[idx] = s[rng.permutation(idx)]
            Qp, _ = np.linalg.qr(np.stack([_paired_dir(X, q, y, sp, tr, TOP, WEAK), _paired_dir(X, q, y, sp, tr, MID, WEAK)], 1))
            perm_sc[p, te] = X[te] @ (c - Qp @ (Qp.T @ c))
            Qi, _ = np.linalg.qr(rng.normal(size=(X.shape[1], 2)))
            iso_sc[p, te] = X[te] @ (c - Qi @ (Qi.T @ c))
        # generator holdout: fit without G's answers (question-centred among the remaining answers)
        for G in GENS:
            m = tr & (s != G)
            Xm = _centre(X[m], q[m])
            d = _unit(Xm[y[m] == 1].mean(0) - Xm[y[m] == 0].mean(0))
            ho[G]["c_ho"][te] = X[te] @ d
            ho[G]["c_all"][te] = X[te] @ c
    perq = {k: _perq(x, q, y, s) for k, x in sc.items()}
    perq["verdict"] = _perq(v, q, y, s)
    perm_auc = [[_auc(_perq(perm_sc[p], q, y, s), part) for part in (0, 1, 2)] for p in range(N_PERM)]
    iso_auc = [[_auc(_perq(iso_sc[p], q, y, s), part) for part in (0, 1, 2)] for p in range(N_PERM)]
    hold = {}
    for G in GENS:
        keep = s == G  # same-model pairs of the held-out model only
        hold[G] = {k: _perq(ho[G][k], q, y, s, keep) for k in ("c_ho", "c_all")} | {"verdict": _perq(v, q, y, s, keep)}
    return dict(judge=judge, bench=bench, layer=L, n=len(y), perq=perq, perm_auc=perm_auc, iso_auc=iso_auc, holdout=hold)


@app.local_entrypoint()
def main(legacy: bool = False, only: str = ""):
    here = pathlib.Path(__file__).resolve().parent
    f = here / "out_paper" / "authorship_controls.json"
    res = json.load(open(f)) if f.exists() else {}
    jobs = list(LEGACY) if legacy else [(j, b) for j in N_LAYERS for b in ("mmlu", "math") if (j, b) not in LEGACY]
    if only:
        jobs = [x for x in jobs if f"{x[0]}|{x[1]}" in only.split(",")]
    for r in run.starmap(jobs, return_exceptions=True):
        if isinstance(r, Exception):
            print("FAILED", str(r)[:300])
            continue
        res[f"{r['judge']}|{r['bench']}"] = r
        P = r["perq"]
        print(r["judge"], r["bench"], "L", r["layer"], {k: round(_auc(P[k]), 1) for k in P},
              "perm mean", round(sum(x[0] for x in r["perm_auc"]) / len(r["perm_auc"]), 1), flush=True)
    json.dump(res, open(f, "w"))
