"""Effort justification ("IKEA effect") check, no new runs: is a WRONG candidate the judge believes accepted more when the
judge's own solves that reached that answer were LONGER (more work), at the same belief?

effort = log mean length (tokens) of the judge's own solves that reached the candidate's answer, minus log mean length of
all its solves on that question (so "this answer took more work than my other attempts", not "hard question").
Linear probability model, accept at the verdict (acc_C) ~ belief + effort, judge fixed effects, among wrong candidates the
judge reached at least once; RB2 Math + BFF (GLM matches); 95% intervals resample questions.

  python3 experiments/anchoring_early_answer/effort_split.py
"""
import collections
import gzip
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SRC = HERE / "out"


def load(p):
    return [json.loads(l) for l in open(p)] if p.exists() else []


def main():
    rows = [r for r in json.load(open(SRC / "belief_rows.json")) if r["bench"] in ("rb2math", "bff")]
    with gzip.open(HERE / "inputs" / "readout_jobs.jsonl.gz", "rt") as f:
        jobs = {(j["judge"], j["item_id"]): j for j in map(json.loads, f) if j["bench"] in ("rb2math", "bff")}
    own = collections.defaultdict(dict)
    for s in load(SRC / "solves_k.jsonl") + load(SRC / "solves_k_rerun.jsonl"):
        own[(s["model"], s["qid"])][s["sample"]] = s
    glm = {r["cache_key"]: r["verdict"] for r in load(SRC / "matches_glm5.3-flash_k.jsonl")}
    glm.update({r["cache_key"]: r["verdict"] for r in load(SRC / "matches_glm5.3-flash_k_rerun.jsonl")})
    X = []
    for r in rows:
        if r["target_ok"] or r["acc_C"] is None or not r["belief"] > 0:
            continue
        j = jobs[(r["judge"], r["item"])]
        sol = own[(r["judge"], j["qid"])]
        same = [o["n_out"] for s, o in sol.items() if s >= 1 and glm.get(f"{r['judge']}|{j['item_id']}|0|s{s}") == "SAME"]
        allx = [o["n_out"] for s, o in sol.items() if s >= 1]
        if not same:
            continue
        X.append(dict(judge=r["judge"], q=j["qid"], acc=r["acc_C"], belief=r["belief"],
                      effort=np.log(np.mean(same)) - np.log(np.mean(allx)), bench=r["bench"]))
    print(f"{len(X)} wrong candidates the judge reached at least once")
    judges = sorted({x["judge"] for x in X})

    def fit(ii):
        y = np.array([X[i]["acc"] for i in ii], float)
        Z = np.column_stack([[X[i]["belief"] for i in ii], [X[i]["effort"] for i in ii]]
                            + [[float(X[i]["judge"] == jd) for i in ii] for jd in judges])
        return np.linalg.lstsq(Z, y, rcond=None)[0][:2]

    b = fit(range(len(X)))
    qs = np.array([x["q"] for x in X])
    u = sorted(set(qs))
    idx = {q: np.where(qs == q)[0] for q in u}
    rng = np.random.default_rng(0)
    B = np.array([fit(np.concatenate([idx[q] for q in rng.choice(u, len(u))])) for _ in range(1000)])
    lo, hi = np.percentile(B, [2.5, 97.5], axis=0)
    sd = np.std([x["effort"] for x in X])
    print(f"belief 0 -> 1: {100 * b[0]:+.0f} points [{100 * lo[0]:+.0f}, {100 * hi[0]:+.0f}]")
    print(f"effort +1 sd ({sd:.2f} log units, i.e. x{np.exp(sd):.2f} longer): {100 * b[1] * sd:+.1f} points "
          f"[{100 * lo[1] * sd:+.1f}, {100 * hi[1] * sd:+.1f}]")
    for name, m in (("longer than its other attempts", lambda x: x["effort"] > 0),
                    ("shorter than its other attempts", lambda x: x["effort"] <= 0)):
        S = [x for x in X if m(x)]
        print(f"  {name}: n={len(S)}, accept {100 * np.mean([x['acc'] for x in S]):.0f}%, "
              f"mean belief {np.mean([x['belief'] for x in S]):.2f}")


if __name__ == "__main__":
    main()
