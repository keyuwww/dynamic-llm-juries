"""Outer held-out evaluation of the full recipe (cannon_outer/PROTOCOL.md). Needs the pair's capture
(hidden_<tag>.npy + meta_<tag>.jsonl from `pair_pipeline.py --phase pair --capture-only`) in --out.

For each outer fold (test = one of the paper's two question halves, seed 0; train = the other), every choice uses the
training half only: directions, inner ranking per layer (training questions split in two, seed 1), gap eligibility,
direct-readout layer, push test on 400 training answers, stretch layer. Then on every test answer: x11 along the
training direction at every candidate layer, and at the chosen stretch layer also a random direction x11 and +-8 sd.
-> outer_<tag>.json (choices per fold) and outer_<tag>.jsonl (one row per answer, as a test answer of its fold)
"""
import argparse
import json
from pathlib import Path

import numpy as np

from dir_capture import build_ids
from pair_pipeline import Judge, load_items, within_auc


def centre(X, q):
    Xc = X.copy()
    for g in set(q):
        k = q == g
        Xc[k] -= X[k].mean(0)
    return Xc


def unit_dir(Xc, y, mask):
    v = Xc[mask][y[mask] == 1].mean(0) - Xc[mask][y[mask] == 0].mean(0)
    return v / (np.linalg.norm(v) + 1e-9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--items", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--n-push", type=int, default=400)
    ap.add_argument("--limit", type=int, default=0, help="smoke: only the first N test answers per fold")
    ap.add_argument("--name", default="outer", help="output file prefix (smoke runs: outer_smoke)")
    a = ap.parse_args()
    import torch
    out = Path(a.out)
    H = np.load(out / f"hidden_{a.tag}.npy", mmap_mode="r")
    meta = [json.loads(l) for l in open(out / f"meta_{a.tag}.jsonl")]
    J = Judge(a.model, use_cache=not a.no_cache)
    rows = load_items(a.items)
    ids_all = [build_ids(J.tok, r) for r in rows]
    keep = [i for i, x in enumerate(ids_all) if len(x) < J.ctx - 8]
    rows, ids_all = [rows[i] for i in keep][: len(meta)], [ids_all[i] for i in keep][: len(meta)]
    assert [r["aid"] for r in rows] == [m["aid"] for m in meta], "capture and items are not in the same order"
    n = len(J.layers)
    kept = sorted(set(range(0, n + 1, 2)) | {n})
    cand = [L for L in kept if 0 < L < n]
    y = np.array([m["gold"] for m in meta])
    q = np.array([m["qid"] for m in meta])
    marg = np.array([m["margin"] for m in meta])
    uq = sorted(set(q))
    h1q = set(np.random.default_rng(0).permutation(uq)[: len(uq) // 2])
    h1 = np.array([x in h1q for x in q])
    Xs = {L: np.asarray(H[:, kept.index(L)], np.float32) for L in cand}
    Xcs = {L: centre(Xs[L], q) for L in cand}
    info, rows_out = {"n_answers": len(meta), "candidate_layers": cand, "folds": {}}, {}
    for fold, te in (("h1", h1), ("h2", ~h1)):
        tr = ~te
        # 1. directions on the training half
        dirs = {}
        for L in cand:
            v = unit_dir(Xcs[L], y, tr)
            r = np.random.default_rng(5000 + L + (fold == "h2")).normal(size=v.shape[0])
            r /= np.linalg.norm(r)
            for name, d in (("J", v), ("R", r)):
                p = Xs[L][tr] @ d
                dirs[(L, name)] = (d, float(p.mean()), float(p.std()))
        # 2. inner ranking on training questions only
        trq = sorted(set(q[tr]))
        a_q = set(np.random.default_rng(1).permutation(trq)[: len(trq) // 2])
        in1 = tr & np.array([x in a_q for x in q])
        in2 = tr & ~in1
        knows = {}
        for L in cand:
            s = np.zeros(len(y))
            for learn, apply in ((in1, in2), (in2, in1)):
                s[apply] = Xs[L][apply] @ unit_dir(Xcs[L], y, learn)
            knows[L] = within_auc(y[tr], s[tr], q[tr])
        says = within_auc(y[tr], marg[tr], q[tr])
        Ld = max(knows, key=knows.get)
        gap = 100 * (knows[Ld] - says)
        # 3. push test on training answers (no labels)
        idx_tr = np.where(tr)[0]
        sub = sorted(np.random.default_rng(2 + (fold == "h2")).choice(idx_tr, min(a.n_push, len(idx_tr)), replace=False).tolist())
        dm = {L: 0.0 for L in cand}
        tdirs = {k: (torch.tensor(d, dtype=torch.float32, device="cuda"), mu, sd) for k, (d, mu, sd) in dirs.items()}

        def edit(L, name, kind, s):
            v, mu, sd = tdirs[(L, name)]
            return dict(L=L, kind=kind, s=s, v=v, mu=mu, sd=sd)
        for j, i in enumerate(sub):
            cache = J.prepare(ids_all[i])
            for L in cand:
                lo = J.read(ids_all[i], cache, edit(L, "J", "add", -8.0))[0]
                hi = J.read(ids_all[i], cache, edit(L, "J", "add", 8.0))[0]
                dm[L] += hi - lo
            del cache
            if (j + 1) % 100 == 0:
                print(f"  push {a.tag} {fold}: {j + 1}/{len(sub)}", flush=True)
        wsd = float(np.sqrt(np.mean([np.var(marg[tr & (q == g)]) for g in trq if (tr & (q == g)).sum() > 1])))
        sens = {L: dm[L] / len(sub) / 16 / wsd for L in cand}
        resp = [L for L in cand if sens[L] >= 0.05]
        Ls = max(resp, key=knows.get) if resp else Ld
        info["folds"][fold] = dict(n_train=int(tr.sum()), n_test=int(te.sum()), inner_knows=knows, inner_says=says,
                                   inner_gap=gap, eligible=gap > 5, direct_layer=Ld, sensitivity=sens,
                                   responding=resp, stretch_layer=Ls, rule="responds" if resp else "no layer responds")
        print(f"  {a.tag} fold {fold}: inner SAYS {says:.3f}, best inner KNOWS {knows[Ld]:.3f} at {Ld}, gap {gap:+.1f}, "
              f"responding {resp}, stretch layer {Ls}", flush=True)
        json.dump(info, open(out / f"{a.name}_{a.tag}.json", "w"), indent=1)
        # 4. test answers
        idx_te = np.where(te)[0][: a.limit or None]
        for j, i in enumerate(idx_te):
            cache = J.prepare(ids_all[i])
            res = {"none": float(marg[i])}
            for L in cand:
                res[f"J:x11:{L}"] = J.read(ids_all[i], cache, edit(L, "J", "amplify", 10.0))[0]
            res["R:x11:Ls"] = J.read(ids_all[i], cache, edit(Ls, "R", "amplify", 10.0))[0]
            res["J:add-8:Ls"] = J.read(ids_all[i], cache, edit(Ls, "J", "add", -8.0))[0]
            res["J:add+8:Ls"] = J.read(ids_all[i], cache, edit(Ls, "J", "add", 8.0))[0]
            del cache
            proj = {str(L): float(Xs[L][i] @ dirs[(L, "J")][0]) for L in cand}
            rows_out[int(i)] = {k: meta[i][k] for k in ("qid", "aid", "gold", "src")} | dict(fold=fold, margins=res, proj=proj)
            if (j + 1) % 200 == 0:
                print(f"  test {a.tag} {fold}: {j + 1}/{len(idx_te)}", flush=True)
    with open(out / f"{a.name}_{a.tag}.jsonl", "w") as fh:
        for i in sorted(rows_out):
            fh.write(json.dumps(rows_out[i]) + "\n")
    print(f"done: outer {a.tag}", flush=True)


if __name__ == "__main__":
    main()
