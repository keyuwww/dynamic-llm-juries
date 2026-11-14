"""Per-answer held-out judge-direction score (raw dot product, direction learned on the other half) and unedited verdict
score, for local analyses (surface-clue baseline, direction-as-grader, disagreement escalation).
  python dir_dump.py <bench> > dump_<bench>.jsonl
"""
import json, sys
import numpy as np
sys.path.insert(0, ".")
from stretch_pipeline import center, dom
bench = sys.argv[1]
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
                mar[r["aid"]] = r["margins"]
    for i, x in enumerate(meta):
        mg = mar.get(x["aid"], {})
        print(json.dumps(dict(model=m, layer=L, aid=x["aid"], qid=x["qid"], gold=int(y[i]), half="h1" if h1[i] else "h2",
                              dirscore=round(float(s[i]), 5), verdict=mg.get("add:0.0"),
                              x11=mg.get("amplify:10.0"))))
