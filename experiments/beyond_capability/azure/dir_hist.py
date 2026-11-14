"""Per-answer scores for plotting where right and wrong answers sit: held-out position along the judge direction
("knows") and the unedited verdict score ("says"), each minus its question's average, by solved group.
  python dir_hist.py <bench> <solve-label json> > hist_<bench>.json
"""
import json, sys
import numpy as np
sys.path.insert(0, ".")
from stretch_pipeline import center, dom
bench, solf = sys.argv[1:3]
sols = json.load(open(solf))
out = {}
for m in ("qwen3.5-9b", "llama3.1-8b"):
    d = f"out_{bench}/{m}"
    H = np.load(f"{d}/hidden_{bench}.npy", mmap_mode="r")
    meta = [json.loads(l) for l in open(f"{d}/meta_{bench}.jsonl")]
    layers = json.load(open(f"{d}/layers_{bench}.json"))["layers"]
    ch = json.load(open(f"{d}/direction_choice_{bench}.json"))
    L = ch["layer"]; h1q = set(ch["h1"])
    y = np.array([x["gold"] for x in meta]); q = np.array([x["qid"] for x in meta])
    h1 = np.array([x in h1q for x in q])
    X = np.asarray(H[:, layers.index(L)], np.float32); Xc = center(X, q)
    s = np.zeros(len(y))
    for tr, te in ((h1, ~h1), (~h1, h1)):
        s[te] = X[te] @ dom(Xc[tr], y[tr])
    mar = {}
    for h in ("h1", "h2"):
        for l in open(f"{d}/steer_{bench}_{h}.jsonl"):
            r = json.loads(l)
            if r["dir"].startswith("Jc"):
                mar[r["aid"]] = r["margins"]["add:0.0"]
    v = np.array([mar[x["aid"]] for x in meta])
    def qc(a):
        a = a.copy()
        for g in set(q):
            k = q == g; a[k] -= a[k].mean()
        return a / a.std()
    sc, vc = qc(s), qc(v)
    sol = sols[m]
    out[m] = dict(layer=L, rows=[[int(y[i]), sol.get(q[i], -1), round(float(sc[i]), 4), round(float(vc[i]), 4)] for i in range(len(y))])
print(json.dumps(out))
