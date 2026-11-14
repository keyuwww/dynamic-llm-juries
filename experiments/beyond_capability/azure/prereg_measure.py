"""Pre-registration measurements for a new judge (no stretching): from the shift-only run of stretch_pipeline.py,
(1) KNOWS = held-out ranking of the judge direction, (2) SAYS = ranking of the unedited verdict score, (3) RESPONDS =
how much shifting the state -8 -> +8 sd changes the share of answers accepted (all answers), (4) correlation between
verdict score and direction. Per group: all / solved / not solved, also excluding the judge's own candidate answers.
  python prereg_measure.py <model> <bench> <solve-label json>  -> prints JSON
"""
import json, sys
import numpy as np
sys.path.insert(0, ".")
from stretch_pipeline import within_auc, center, dom
m, bench, solf = sys.argv[1:4]
sol = json.load(open(solf))[m]
d = f"out_{bench}/{m}"
H = np.load(f"{d}/hidden_{bench}.npy", mmap_mode="r")
meta = [json.loads(l) for l in open(f"{d}/meta_{bench}.jsonl")]
layers = json.load(open(f"{d}/layers_{bench}.json"))["layers"]
ch = json.load(open(f"{d}/direction_choice_{bench}.json"))
L = ch["layer"]; h1q = set(ch["h1"])
y = np.array([x["gold"] for x in meta]); q = np.array([x["qid"] for x in meta])
src = np.array([x["aid"].split("|")[1] for x in meta])
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
v0 = np.array([mar[x["aid"]]["add:0.0"] for x in meta])
vm = np.array([mar[x["aid"]]["add:-8.0"] for x in meta]); vp = np.array([mar[x["aid"]]["add:8.0"] for x in meta])
out = dict(model=m, bench=bench, layer=L, direction_heldout_all=ch["scores"][str(L)] if str(L) in ch["scores"] else ch["scores"][L])
for own_nm, keep in (("with own answers", np.ones(len(y), bool)), ("without own answers", src != m)):
    for nm, g in (("all", np.ones(len(y), bool)), ("solved", np.array([sol.get(x) == 1 for x in q])), ("not solved", np.array([sol.get(x) == 0 for x in q]))):
        k = keep & g
        out[f"{own_nm} | {nm}"] = dict(n=int(k.sum()), questions=int(len(set(q[k]))),
            knows=round(within_auc(y[k], s[k], q[k]), 3), says=round(within_auc(y[k], v0[k], q[k]), 3),
            corr=round(float(np.corrcoef(s[k], v0[k])[0, 1]), 2),
            accept_at_minus8=round(float((vm[k] > 0).mean()), 3), accept_at_0=round(float((v0[k] > 0).mean()), 3),
            accept_at_plus8=round(float((vp[k] > 0).mean()), 3))
print(json.dumps(out, indent=1))
