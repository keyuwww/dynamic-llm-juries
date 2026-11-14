"""Escalation check: Llama-8B grades every answer; 20% of its verdicts go to Qwen-9B (stronger here). Which 20%?
Trust signals (lowest trust escalated first), all fitted on one half of the questions and applied to the other:
  random | verdict confidence (|log-odds|) | direction disagrees with verdict | surface clues disagree | consensus disagrees
Accuracy and balanced accuracy of the final verdicts vs the answer key, MMLU-Redux and MATH.
  python3 experiments/beyond_capability/check_escalate.py -> out_checks/escalate.md
"""
import gzip, json
import numpy as np
from sklearn.linear_model import LogisticRegression
from check_surface import HERE, OUT, features, consensus, qcenter

def run(bench, itemf, frac=0.2, rng=np.random.default_rng(0)):
    items = {json.loads(l)["aid"]: json.loads(l) for l in gzip.open(HERE / "inputs" / itemf)}
    F, C = features(items), consensus(items)
    dump = [json.loads(x) for x in open(OUT / f"dump_{bench}.jsonl")]
    D = {m: {r["aid"]: r for r in dump if r["model"] == m} for m in ("llama3.1-8b", "qwen3.5-9b")}
    aids = [a for a in D["llama3.1-8b"] if a in D["qwen3.5-9b"] and a in items]
    L = [D["llama3.1-8b"][a] for a in aids]
    y = np.array([r["gold"] for r in L]); h1 = np.array([r["half"] == "h1" for r in L])
    vL = np.array([r["verdict"] for r in L], float); vQ = np.array([D["qwen3.5-9b"][a]["verdict"] for a in aids], float)
    predL, predQ = (vL > 0).astype(int), (vQ > 0).astype(int)
    pv = 1 / (1 + np.exp(-np.clip(vL, -30, 30)))
    def fit_prob(X):
        p = np.zeros(len(y))
        for tr, te in ((h1, ~h1), (~h1, h1)):
            p[te] = LogisticRegression(max_iter=2000).fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
        return p
    d = np.array([r["dirscore"] for r in L])[:, None]
    X = np.array([F[a] for a in aids]); X = (X - X.mean(0)) / (X.std(0) + 1e-9)
    trust = {
        "random": rng.random(len(y)),
        "verdict confidence": np.abs(vL),
        "direction disagrees": -np.abs(fit_prob(d) - pv),
        "surface clues disagree": -np.abs(fit_prob(X) - pv),
        "consensus disagrees (label-free)": -np.abs(np.array([C[a] for a in aids]) - pv),
    }
    def score(pred):
        acc = (pred == y).mean(); tpr = pred[y == 1].mean(); tnr = 1 - pred[y == 0].mean()
        return 100 * acc, 100 * (tpr + tnr) / 2
    k = int(frac * len(y))
    rows = [("Llama-8B alone", *score(predL)), ("Qwen-9B alone", *score(predQ))]
    for name, t in trust.items():
        esc = np.argsort(t)[:k]; pred = predL.copy(); pred[esc] = predQ[esc]
        rows.append((f"escalate 20%: {name}", *score(pred)))
    out = [f"## {bench} ({len(y)} answers)", "", "| Final verdicts | Accuracy % | Balanced accuracy % |", "|---|---|---|"]
    out += [f"| {n} | {a:.1f} | {b:.1f} |" for n, a, b in rows]
    return "\n".join(out)

txt = "\n\n".join(run(b, f) for b, f in (("mmlu", "mmlu_full_items.jsonl.gz"), ("math", "math_full_items.jsonl.gz")))
(OUT / "escalate.md").write_text(txt + "\n"); print(txt)
