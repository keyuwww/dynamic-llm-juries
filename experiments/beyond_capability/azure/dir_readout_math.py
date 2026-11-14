# Run on the cluster workdir (needs out_math/<model>/hidden_math.npy) with sol_math.json = {model: {qid: 0/1}} from stretch_analyze.solve_labels.
# Held-out readout of the judge direction (chosen layer), split by whether the judge solves the question,
# next to the verdict's own ranking. Same halves and direction recipe as stretch_pipeline.py.
import json, sys, collections
import numpy as np
sys.path.insert(0, ".")
from stretch_pipeline import within_auc, center, dom
sol = json.load(open("sol_math.json"))
for m in ["qwen3.5-9b", "llama3.1-8b"]:
    d = f"out_math/{m}"
    H = np.load(f"{d}/hidden_math.npy", mmap_mode="r")
    meta = [json.loads(l) for l in open(f"{d}/meta_math.jsonl")]
    layers = json.load(open(f"{d}/layers_math.json"))["layers"]
    ch = json.load(open(f"{d}/direction_choice_math.json"))
    L = ch["layer"]; h1q = set(ch["h1"])
    y = np.array([x["gold"] for x in meta]); q = np.array([x["qid"] for x in meta])
    h1 = np.array([x in h1q for x in q])
    X = np.asarray(H[:, layers.index(L)], np.float32); Xc = center(X, q)
    s = np.zeros(len(y))
    for tr, te in ((h1, ~h1), (~h1, h1)):
        s[te] = X[te] @ dom(Xc[tr], y[tr])
    st = {}
    for l in open(f"{d}/steer_math_h1.jsonl"):
        r = json.loads(l)
        if r["dir"].startswith("Jc"): st[r["aid"]] = r["margins"]["add:0.0"]
    for l in open(f"{d}/steer_math_h2.jsonl"):
        r = json.loads(l)
        if r["dir"].startswith("Jc"): st[r["aid"]] = r["margins"]["add:0.0"]
    v = np.array([st[x["aid"]] for x in meta])
    for nm, mask in (("all", np.ones(len(y), bool)), ("solved", np.array([sol[m].get(x) == 1 for x in q])), ("not solved", np.array([sol[m].get(x) == 0 for x in q]))):
        corr = np.corrcoef(s[mask], v[mask])[0, 1]
        print(f"{m:12s} {nm:10s} direction readout {within_auc(y[mask], s[mask], q[mask]):.3f}   verdict {within_auc(y[mask], v[mask], q[mask]):.3f}   corr(direction, verdict score) {corr:.2f}")
