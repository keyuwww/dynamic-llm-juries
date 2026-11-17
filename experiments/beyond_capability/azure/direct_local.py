"""CPU, from a pair's stored hidden states (pair_pipeline.py): the direction position of every answer at the chosen
and the best-ranking layer (same cross-fit split as the pipeline) -> direct_<tag>.json, and the gap over 20 random
question splits at the best layer -> splits_<tag>.json. Same recipe as direct_readout_modal.py and
allpairs_modal.py --phase splits.

  python direct_local.py --out out70b/llama3.1-70b_mmlu --tag mmlu --n-layers 80
"""
import argparse
import json
from pathlib import Path

import numpy as np


def auc(s, y, q, uq):
    num = den = 0.0
    for g in uq:
        k = q == g
        a, b = s[k & (y == 1)], s[k & (y == 0)]
        if len(a) and len(b):
            num += (a[:, None] > b[None, :]).sum() + 0.5 * (a[:, None] == b[None, :]).sum()
            den += len(a) * len(b)
    return num / den


def project(X, Xc, y, h1):
    s = np.zeros(len(y))
    for mask in (h1, ~h1):
        v = Xc[mask][y[mask] == 1].mean(0) - Xc[mask][y[mask] == 0].mean(0)
        s[~mask] = X[~mask] @ (v / (np.linalg.norm(v) + 1e-9))
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--n-layers", type=int, required=True)
    a = ap.parse_args()
    d = Path(a.out)
    ch = json.load(open(d / f"choice_{a.tag}.json"))
    H = np.load(d / f"hidden_{a.tag}.npy", mmap_mode="r")
    meta = [json.loads(l) for l in open(d / f"meta_{a.tag}.jsonl")]
    kept = sorted(set(range(0, a.n_layers + 1, 2)) | {a.n_layers})
    y = np.array([m["gold"] for m in meta])
    q = np.array([m["qid"] for m in meta])
    uq = sorted(set(q))
    best = int(ch["best_knows_layer"])
    layers = sorted({best, int(ch.get("chosen_layer", best))})
    out, splits = {}, {}
    for L in layers:
        X = np.asarray(H[:, kept.index(L)], np.float32)
        Xc = X.copy()
        for g in uq:
            Xc[q == g] -= X[q == g].mean(0)
        h1q = set(np.random.default_rng(0).permutation(uq)[: len(uq) // 2])
        s = project(X, Xc, y, np.array([x in h1q for x in q]))
        out[str(L)] = {m["aid"]: float(x) for m, x in zip(meta, s)}
        if L == best:
            ks = []
            for seed in range(20):
                h1q = set(np.random.default_rng(seed).permutation(uq)[: len(uq) // 2])
                ks.append(auc(project(X, Xc, y, np.array([x in h1q for x in q])), y, q, uq))
            says = auc(np.array([m["margin"] for m in meta]), y, q, uq)
            splits = dict(layer=L, knows_mean=float(np.mean(ks)), knows_sd=float(np.std(ks)), knows_seed0=float(ks[0]),
                          says=float(says))
    json.dump(out, open(d / f"direct_{a.tag}.json", "w"))
    json.dump(splits, open(d / f"splits_{a.tag}.json", "w"), indent=1)
    print(d, layers, splits)


if __name__ == "__main__":
    main()
