"""Is the judge direction benchmark-dependent? For one judge, learn the question-centred difference-of-means direction
(right minus wrong answers, judge prompt) on each benchmark and compare them at the same layer:
  - cosine between the directions of two benchmarks (noise ceiling: cosine between two random halves of one benchmark)
  - transfer: ranking (within-question AUROC) of benchmark B's answers by A's direction, vs B's own direction learned on
    the other half of B's questions (held out, so own vs borrowed is a fair fight).

Input: one or more  bench=hidden.npy:meta.jsonl:layers.json  specs (meta rows with mode 'J' are used; a spec may hold
several benchmarks, selected by the meta 'bench' field). Prints a markdown table per layer and writes JSON.

  python3 cross_bench_dirs.py --out out_checks/cross_dirs_llama.json \
      bbeh,rb2math=out_dirs/llama3.1-8b/hidden_main.npy:out_dirs/llama3.1-8b/meta_main.jsonl:out_dirs/llama3.1-8b/layers_main.json
"""
import argparse
import json
from collections import defaultdict

import numpy as np


def within_auc(y, s, q):
    by = defaultdict(lambda: ([], []))
    for yi, si, g in zip(y, s, q):
        by[g][int(yi)].append(si)
    num = den = 0.0
    for neg, pos in by.values():
        if pos and neg:
            P, N = np.array(pos)[:, None], np.array(neg)[None, :]
            num += (P > N).sum() + 0.5 * (P == N).sum()
            den += P.size * N.size
    return num / den if den else float("nan")


def center(X, q):
    Xc = X.copy()
    for g in np.unique(q):
        m = q == g
        Xc[m] -= X[m].mean(0)
    return Xc


def dom(Xc, y):
    d = Xc[y == 1].mean(0) - Xc[y == 0].mean(0)
    return d / (np.linalg.norm(d) + 1e-9)


def load(specs):
    data = {}
    for spec in specs:
        names, files = spec.split("=")
        hf, mf, lf = files.split(":")
        H = np.load(hf, mmap_mode="r")
        meta = [json.loads(l) for l in open(mf)]
        layers = json.load(open(lf))["layers"]
        for b in names.split(","):
            idx = [i for i, x in enumerate(meta) if x.get("mode", "J") == "J" and x.get("bench", b) == b]
            q = np.array([meta[i]["qid"] for i in idx])
            y = np.array([meta[i]["gold"] for i in idx])
            keep = np.array([len(set(y[q == g])) == 2 for g in q])  # questions with a right and a wrong answer
            idx = np.array(idx)[keep]
            data[b] = dict(H=H, idx=idx, q=q[keep], y=y[keep], layers=layers)
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("specs", nargs="+")
    ap.add_argument("--layers", default="", help="comma-separated layers to compare (default: all shared)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    data = load(a.specs)
    benches = list(data)
    shared = sorted(set.intersection(*[set(d["layers"]) for d in data.values()]))
    L_list = [int(x) for x in a.layers.split(",")] if a.layers else shared
    rng = np.random.default_rng(0)
    res = {}
    for L in L_list:
        X, Xc, dirs, halves = {}, {}, {}, {}
        for b, d in data.items():
            X[b] = np.asarray(d["H"][d["idx"], d["layers"].index(L)], np.float32)
            Xc[b] = center(X[b], d["q"])
            dirs[b] = dom(Xc[b], d["y"])
        r = {"n": {b: int(len(data[b]["y"])) for b in benches}}
        for b in benches:
            d = data[b]
            uq = np.unique(d["q"])
            owns, ceils = [], []
            for sd in range(10):  # mean over 10 random splits: one split is noisy on small benchmarks
                h1 = set(np.random.default_rng(sd).permutation(uq)[: len(uq) // 2])
                h = np.array([g in h1 for g in d["q"]])
                s = np.zeros(len(d["y"]))
                for tr, te in ((h, ~h), (~h, h)):
                    s[te] = X[b][te] @ dom(Xc[b][tr], d["y"][tr])
                owns.append(within_auc(d["y"], s, d["q"]))
                ceils.append(float(dom(Xc[b][h], d["y"][h]) @ dom(Xc[b][~h], d["y"][~h])))
            r[f"own|{b}"], r[f"own_sd|{b}"], r[f"ceiling|{b}"] = float(np.mean(owns)), float(np.std(owns)), float(np.mean(ceils))
        for A in benches:
            for B in benches:
                if A != B:
                    r[f"cos|{A}|{B}"] = float(dirs[A] @ dirs[B])
                    r[f"transfer|{A}->{B}"] = within_auc(data[B]["y"], X[B] @ dirs[A], data[B]["q"])
        res[L] = r
        print(f"\n### Layer {L}\n")
        print("| Direction from → used on | Cosine | Split-half ceiling (from / on) | Borrowed | Own (held out) |")
        print("|---|---|---|---|---|")
        for A in benches:
            for B in benches:
                if A != B:
                    print(f"| {A} → {B} | {r[f'cos|{A}|{B}']:.2f} | {r[f'ceiling|{A}']:.2f} / {r[f'ceiling|{B}']:.2f} | "
                          f"{r[f'transfer|{A}->{B}']:.3f} | {r[f'own|{B}']:.3f} |")
    json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
