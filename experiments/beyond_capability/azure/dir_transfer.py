"""Does a judge direction learned on one benchmark work on another? For each judge and each (source -> target) pair,
at the source's chosen layer: (1) cosine between the two benchmarks' directions (each learned on all its items),
(2) ranking of target answers scored with the SOURCE direction, vs (3) the target's own held-out direction at that
same layer. Ranking = within-question AUROC. Run in the cluster workdir (needs out_<bench>/<model>/hidden_*.npy).
"""
import json, sys
import numpy as np
sys.path.insert(0, ".")
from stretch_pipeline import within_auc, center, dom

def load(bench, m):
    d = f"out_{bench}/{m}"
    H = np.load(f"{d}/hidden_{bench}.npy", mmap_mode="r")
    meta = [json.loads(l) for l in open(f"{d}/meta_{bench}.jsonl")]
    layers = json.load(open(f"{d}/layers_{bench}.json"))["layers"]
    ch = json.load(open(f"{d}/direction_choice_{bench}.json"))
    y = np.array([x["gold"] for x in meta]); q = np.array([x["qid"] for x in meta])
    return H, layers, ch, y, q

def own_heldout(H, layers, L, y, q, h1q):
    X = np.asarray(H[:, layers.index(L)], np.float32); Xc = center(X, q)
    h1 = np.array([x in h1q for x in q]); s = np.zeros(len(y))
    for tr, te in ((h1, ~h1), (~h1, h1)):
        s[te] = X[te] @ dom(Xc[tr], y[tr])
    return within_auc(y, s, q)

for m in ["qwen3.5-9b", "llama3.1-8b"]:
    data = {b: load(b, m) for b in ("mmlu", "math")}
    for src, tgt in (("mmlu", "math"), ("math", "mmlu")):
        Hs, ls, chs, ys, qs = data[src]; Ht, lt, cht, yt, qt = data[tgt]
        L = chs["layer"]
        Xs = np.asarray(Hs[:, ls.index(L)], np.float32); vs = dom(center(Xs, qs), ys)
        Xt = np.asarray(Ht[:, lt.index(L)], np.float32); vt = dom(center(Xt, qt), yt)
        transfer = within_auc(yt, Xt @ vs, qt)
        own = own_heldout(Ht, lt, L, yt, qt, set(cht["h1"]))
        print(f"{m:12s} {src}->{tgt} layer {L:2d}: cosine {float(vs @ vt):+.2f}   target ranked with {src} direction {transfer:.3f}   "
              f"with its own (held-out) {own:.3f}   [target's own best layer {cht['layer']}: {cht['scores'][str(cht['layer'])]:.3f}]")
