"""Inputs for steering the judge's belief while it writes its reasoning (cannon_belief/steer.py, GPU).

Judge: Qwen3.5-9B, thinking off (the pool setting), RB2 Math and BFF. The layer and positions come from the
position x layer probe grid (belief_probe_grid.py): belief is most readable at layers ~17-25 during and at the end of
the reasoning, so directions are fitted at LAYER on the pooled 25/50/75/C states (cannon_belief/out/<judge>/).

Held out: questions are split in two halves per benchmark; an item is steered with the direction fitted on the OTHER
half. Directions (unit vectors in the raw residual space, ridge weights mapped back from standardized space):
  belief    ridge  hidden -> belief (share of 7 own solves reaching the candidate's answer), all candidates
  correct   ridge  hidden -> gold (the "is this right?" direction, same method)
  belief_orth  belief with the correctness direction projected out (belief that is not "this is right")
  random    a fixed random unit vector
Push = alpha * sd, with sd = SD of the projection on the BELIEF direction, so all three push the same distance.

Items: every wrong & believed (>= 4/7) candidate, and fixed random samples of wrong & never-reached (0/7) and of
correct candidates, with the pool prompt.

  python3 experiments/anchoring_early_answer/belief_steer_prep.py                  # Qwen3.5-9B
  python3 experiments/anchoring_early_answer/belief_steer_prep.py llama3.1-8b      # -> steer_items_llama3.1-8b...
Each direction also stores mu / sd_own: mean and SD of the fitting half's projection on it (for scaling, steer.py x*lam).
"""
import sys
import gzip
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
JUDGE = sys.argv[1] if len(sys.argv) > 1 else "qwen3.5-9b"
LAYERS, POOL, N_NEVER, N_CORRECT = list(range(14, 27)), ("25", "50", "75", "C"), 80, 80
TAG = "" if JUDGE == "qwen3.5-9b" else f"_{JUDGE}"
ROWS = "belief_rows.json" if JUDGE.startswith("qwen") else f"belief_rows_{JUDGE}.json"
PROMPTS_OF = JUDGE if JUDGE.startswith("qwen") else "qwen3.5-4b"  # judge prompts are judge-independent
LAYER = 20  # the layer reported in the printout; directions are written for every layer in LAYERS


def unit(v):
    return v / np.linalg.norm(v)


def ridge_w(X, y, lam=1.0):
    mu, sd = X.mean(0), X.std(0) + 1e-6
    Z = (X - mu) / sd
    a = np.linalg.solve(Z @ Z.T + lam * Z.shape[1] * np.eye(len(Z)), y - y.mean())
    return (Z.T @ a) / sd


def main():
    B = {(r["judge"], r["item"]): r for r in json.load(open(HERE / "out" / ROWS))}
    D = HERE / "cannon_belief" / "out" / JUDGE
    meta = [json.loads(l) for l in open(D / "meta_ckpt.jsonl")]
    H = np.load(D / "hidden_ckpt.npy", mmap_mode="r")
    with gzip.open(HERE / "inputs" / "readout_jobs.jsonl.gz", "rt") as f:
        jobs = {j["item_id"]: j for j in map(json.loads, f) if j["judge"] == PROMPTS_OF}
    dirs, items, rv = {}, [], unit(np.random.default_rng(1).standard_normal(H.shape[2]))
    rng = np.random.default_rng(0)
    for bench in ("rb2math", "bff"):
        rows = [(i, B[(JUDGE, m["item_id"])]) for i, m in enumerate(meta)
                if m["bench"] == bench and m["ckpt"] in POOL and (JUDGE, m["item_id"]) in B]
        idx = [i for i, _ in rows]
        R = [r for _, r in rows]
        y = np.array([r["belief"] for r in R])
        gold = np.array([r["target_ok"] for r in R])
        q = np.array([r["q"] or r["item"].rsplit("-", 1)[0] for r in R])
        uq = sorted(set(q))
        half_of = dict(zip(rng.permutation(uq), np.arange(len(uq)) % 2))
        half = np.array([half_of[x] for x in q])
        bel, nev = (gold == 0) & (y >= 4 / 7), (gold == 0) & (y == 0)
        for lay in LAYERS:
          X = np.asarray(H[idx, lay], np.float64)
          for h in (0, 1):
              m = half == h
              vb, vc = unit(ridge_w(X[m], y[m])), unit(ridge_w(X[m], gold[m].astype(float)))
              sd = float((X[m] @ vb).std())
              te = (half == 1 - h) & (bel | nev)
              held = roc_auc_score(bel[te], X[te] @ vb)
              vo = unit(vb - (vb @ vc) * vc)  # belief with the correctness direction projected out
              held_o = roc_auc_score(bel[te], X[te] @ vo)
              pass
              for name, v in (("belief", vb), ("belief_orth", vo), ("correct", vc), ("random", rv)):
                  p = X[m] @ v
                  dirs[f"{bench}|{name}|h{h}|L{lay}"] = dict(layer=lay, vec=v.tolist(), sd=sd, mu=float(p.mean()),
                                                             sd_own=float(p.std()))
              if lay == LAYER or lay in (14, 26):
                  print(f"L{lay} {bench} half {h}: held-out AUROC {held:.2f}, cos(belief, correct) {vb @ vc:.2f}, sd {sd:.2f}")
        # one row per candidate (the pooled states repeat each candidate 4 times)
        cand = {}
        for r, hh in zip(R, half):
            cand[r["item"]] = (r, int(hh))
        keys = sorted(cand)
        perm = [keys[i] for i in rng.permutation(len(keys))]
        believed = [k for k in keys if cand[k][0]["target_ok"] == 0 and cand[k][0]["belief"] >= 4 / 7]
        never = [k for k in perm if cand[k][0]["target_ok"] == 0 and cand[k][0]["belief"] == 0][:N_NEVER]
        correct = [k for k in perm if cand[k][0]["target_ok"] == 1][:N_CORRECT]
        for grp, ks in (("wrong_believed", believed), ("wrong_never", never), ("correct", correct)):
            for k in ks:
                r, hh = cand[k]
                items.append(dict(aid=f"{bench}|{k}", bench=bench, q=r["q"] or k.rsplit("-", 1)[0], half=hh,
                                  dir_half=1 - hh, group=grp, belief=r["belief"], gold=r["target_ok"],
                                  messages=jobs[k]["messages"], pool_spoken=r["spoken"]))
        print(bench, {g: sum(1 for x in items if x["bench"] == bench and x["group"] == g)
                      for g in ("wrong_believed", "wrong_never", "correct")})
    out = HERE / "cannon_belief"
    with gzip.open(out / f"steer_items{TAG}.jsonl.gz", "wt") as f:
        f.write("".join(json.dumps(x) + "\n" for x in items))
    (out / f"steer_dirs{TAG}.json").write_text(json.dumps(dirs))


if __name__ == "__main__":
    main()
