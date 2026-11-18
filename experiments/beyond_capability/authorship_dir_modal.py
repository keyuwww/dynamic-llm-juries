"""Is there an authorship direction, is it shared, and how much of the correctness direction is it?  CPU only.

Per judge, MMLU-Redux and MATH pools (answers by Qwen3.5-4B, Nemotron-3-Super-120B, Qwen3.6-35B-A3B), at the pair's
best-ranking layer, cross-fit over the same two question halves as the paper (seed 0):
  correctness direction c  question-centred mean(right) - mean(wrong)                         (the paper's direction)
  authorship direction a   mean over (question, correctness) cells holding answers by both S and W of
                           (mean S state - mean W state): a paired difference between two models' answers that are
                           equally right or equally wrong, with no third model involved
                           a_top = Qwen3.6-35B (most accurate) vs Qwen3.5-4B (least); a_mid = Nemotron vs Qwen3.5-4B
Held-out measures:
  auth_auc     a_top separating Qwen3.6 from Qwen3.5-4B answers of equal correctness to the same question (50 = none)
  pair_transfer a_top separating Nemotron from Qwen3.5-4B (a different model pair)
  cos          cos(c, a_top), cos(a_top, a_mid)
  ranking      right-vs-wrong ranking by c and by c with the authorship plane (a_top, a_mid) projected out,
               on same-model and different-model pairs; and by the verdict
Across benchmarks (same judge, MMLU's best layer for both): a_top learned on MMLU -> auth_auc on MATH, cos of the
two benchmarks' a_top and c.

  MODAL_PROFILE=ingridchien .venv/bin/modal run experiments/beyond_capability/authorship_dir_modal.py
  -> out_paper/authorship_dir.json
"""
import json
import pathlib

import modal

app = modal.App("bc-authorship-dir")
vol = modal.Volume.from_name("dynamic-llm-juries-results")
ROOT = "/vol/beyond_capability_allpairs"
N_LAYERS = {"llama3.1-8b": 32, "llama3.2-3b": 28, "qwen3.5-4b": 32, "phi4-mini": 32, "mistral-7b": 32,
            "granite3.3-8b": 40, "llama3.2-1b": 16, "qwen2.5-7b": 28}
WEAK, MID, TOP = "qwen3.5-4b", "nemotron3-super-120b", "qwen3.6-35b-a3b"
img = modal.Image.debian_slim().pip_install("numpy")


def _load(judge, bench, L=None):
    import numpy as np
    d = pathlib.Path(f"{ROOT}/{judge}_{bench}")
    ch = json.load(open(d / f"choice_{bench}.json"))
    L = int(ch["best_knows_layer"]) if L is None else L
    nl = N_LAYERS[judge]
    kept = sorted(set(range(0, nl + 1, 2)) | {nl})
    H = np.load(d / f"hidden_{bench}.npy", mmap_mode="r")
    X = np.asarray(H[:, kept.index(L)], np.float32)
    meta = [json.loads(l) for l in open(d / f"meta_{bench}.jsonl")]
    return X, meta, L


def _prep(X, meta):
    import numpy as np
    y = np.array([m["gold"] for m in meta])
    q = np.array([m["qid"] for m in meta])
    s = np.array([m["src"] for m in meta])
    v = np.array([m["margin"] for m in meta], float)
    Xc, Xg = X.copy(), X.copy()
    for g in set(q):
        k = q == g
        Xc[k] -= X[k].mean(0)
        for t in (0, 1):
            kk = k & (y == t)
            if kk.any():
                Xg[kk] -= X[kk].mean(0)
    return y, q, s, v, Xc, Xg


def _unit(v):
    import numpy as np
    return v / (np.linalg.norm(v) + 1e-9)


def _paired_dir(X, q, y, s, mask, S, W):
    """mean over (question, correctness) cells that contain answers by both S and W of (mean S state - mean W state):
    a within-cell paired difference, so no third model enters."""
    import numpy as np
    diffs = []
    for g in set(q[mask]):
        for t in (0, 1):
            k = mask & (q == g) & (y == t)
            a, b = k & (s == S), k & (s == W)
            if a.any() and b.any():
                diffs.append(X[a].mean(0) - X[b].mean(0))
    return _unit(np.mean(diffs, 0)), len(diffs)


def _pair_auc(score, q, y, s, pos, neg):
    """within question and correctness class: P(score of a `pos`-model answer > score of a `neg`-model answer)."""
    import numpy as np
    num = den = 0.0
    for g in set(q):
        for t in (0, 1):
            k = (q == g) & (y == t)
            a, b = score[k & (s == pos)], score[k & (s == neg)]
            if len(a) and len(b):
                num += (a[:, None] > b[None, :]).sum() + 0.5 * (a[:, None] == b[None, :]).sum()
                den += len(a) * len(b)
    return 100 * num / den if den else None


def _rank(score, q, y, s):
    """right-vs-wrong ranking within question: all, same-model pairs, different-model pairs."""
    import numpy as np
    acc = {k: [0.0, 0.0] for k in ("all", "same", "diff")}
    for g in set(q):
        k = q == g
        P, N = np.where(k & (y == 1))[0], np.where(k & (y == 0))[0]
        if not len(P) or not len(N):
            continue
        w = (score[P][:, None] > score[N][None, :]) + 0.5 * (score[P][:, None] == score[N][None, :])
        same = s[P][:, None] == s[N][None, :]
        for name, m in (("all", np.ones_like(same)), ("same", same), ("diff", ~same)):
            acc[name][0] += w[m].sum()
            acc[name][1] += m.sum()
    return {k: (100 * a / b if b else None) for k, (a, b) in acc.items()}


@app.function(image=img, volumes={"/vol": vol}, timeout=3600, cpu=8, memory=65536)
def run(judge: str) -> dict:
    import numpy as np
    out = {"judge": judge}
    dirs = {}
    for bench in ("mmlu", "math"):
        d = pathlib.Path(f"{ROOT}/{judge}_{bench}")
        if not (d / f"hidden_{bench}.npy").exists() or not (d / f"choice_{bench}.json").exists():
            continue
        X, meta, L = _load(judge, bench)
        y, q, s, v, Xc, Xg = _prep(X, meta)
        uq = sorted(set(q))
        h1q = set(np.random.default_rng(0).permutation(uq)[: len(uq) // 2])
        h1 = np.array([x in h1q for x in q])
        sc = {k: np.zeros(len(y)) for k in ("c", "c_perp", "a_top", "a_mid")}
        cos = {"c_atop": [], "atop_amid": []}
        for tr in (h1, ~h1):
            te = ~tr
            c = _unit(Xc[tr][y[tr] == 1].mean(0) - Xc[tr][y[tr] == 0].mean(0))
            a_top, n_top = _paired_dir(X, q, y, s, tr, TOP, WEAK)
            a_mid, n_mid = _paired_dir(X, q, y, s, tr, MID, WEAK)
            Q, _ = np.linalg.qr(np.stack([a_top, a_mid], 1))
            c_perp = c - Q @ (Q.T @ c)
            for name, d in (("c", c), ("c_perp", c_perp), ("a_top", a_top), ("a_mid", a_mid)):
                sc[name][te] = X[te] @ d
            cos["c_atop"].append(float(c @ a_top))
            cos["atop_amid"].append(float(a_top @ a_mid))
        r = dict(layer=L, n=len(y),
                 auth_auc=_pair_auc(sc["a_top"], q, y, s, TOP, WEAK),
                 pair_transfer=_pair_auc(sc["a_top"], q, y, s, MID, WEAK),
                 c_auth_auc=_pair_auc(sc["c"], q, y, s, TOP, WEAK),
                 cperp_auth_auc=_pair_auc(sc["c_perp"], q, y, s, TOP, WEAK),
                 cos={k: float(np.mean(x)) for k, x in cos.items()},
                 rank={"verdict": _rank(v, q, y, s), "c": _rank(sc["c"], q, y, s), "c_perp": _rank(sc["c_perp"], q, y, s)})
        out[bench] = r
        # full-data directions at MMLU's layer for the cross-benchmark test
        if bench == "mmlu":
            Lm = L
        Xl, metal, _ = (X, meta, L) if bench == "mmlu" else _load(judge, bench, Lm) if "mmlu" in out else (None, None, None)
        if Xl is not None:
            yl, ql, sl, _, Xcl, Xgl = _prep(Xl, metal)
            dirs[bench] = dict(a=_paired_dir(Xl, ql, yl, sl, np.ones(len(yl), bool), TOP, WEAK)[0],
                               c=_unit(Xcl[yl == 1].mean(0) - Xcl[yl == 0].mean(0)), X=Xl, y=yl, q=ql, s=sl)
    if "mmlu" in dirs and "math" in dirs:
        A, B = dirs["mmlu"], dirs["math"]
        out["cross"] = dict(layer=Lm, cos_a=float(A["a"] @ B["a"]), cos_c=float(A["c"] @ B["c"]),
                            a_mmlu_on_math=_pair_auc(B["X"] @ A["a"], B["q"], B["y"], B["s"], TOP, WEAK),
                            a_math_on_mmlu=_pair_auc(A["X"] @ B["a"], A["q"], A["y"], A["s"], TOP, WEAK))
    return out


@app.local_entrypoint()
def main(judges: str = ""):
    here = pathlib.Path(__file__).resolve().parent
    f = here / "out_paper" / "authorship_dir.json"
    res = json.load(open(f)) if f.exists() else {}
    for r in run.map(judges.split(",") if judges else list(N_LAYERS), return_exceptions=True):
        if isinstance(r, Exception):
            print("FAILED", r)
            continue
        res[r["judge"]] = r
        print(json.dumps(r)[:600])
    json.dump(res, open(f, "w"), indent=1)
