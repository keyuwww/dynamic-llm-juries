"""Split the directions written by dir_analyze.py into steering jobs: directions learned on half 1 of the
questions steer the judge on half 2, and vice versa. Writes out_dirs/<key>/steer_<bench>_<half>_{dirs,ids}.json.

  python3 experiments/beyond_capability/dir_steer_prep.py --key qwen3.5-9b
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


CENTERED_LAYER = {"qwen3.5-9b": 26, "llama3.1-8b": 14}  # where the question-centred judge direction carries the most
                                                           # within-question signal on unsolved BBEH questions


def centered_dirs(key):
    """Directions from question-centred hidden states (each answer minus the mean of its question's answers), so
    they carry within-question information only. Learned on one half of the questions, for steering the other."""
    import numpy as np
    from dir_analyze import dom, load
    H, meta, layers = load(key, "main")
    L = CENTERED_LAYER[key]
    li = layers.index(L)
    spec = json.load(open(HERE / "out_dirs" / key / "directions_bbeh.json"))
    h1 = set(spec["h1"])
    rows = {m: {r["aid"]: i for i, r in enumerate(meta) if r["bench"] == "bbeh" and r["mode"] == m and r["src"] != key} for m in "JG"}
    common = sorted(set(rows["J"]) & set(rows["G"]))
    y = np.array([meta[rows["J"][a_]]["gold"] for a_ in common])
    q = np.array([meta[rows["J"][a_]]["qid"] for a_ in common])
    X = {m: np.asarray(H[[rows[m][a_] for a_ in common], li], np.float32) for m in "JG"}
    Xc = {}
    for m in "JG":
        Xc[m] = X[m].copy()
        for g in set(q):
            k = q == g
            Xc[m][k] -= X[m][k].mean(0)
    inh1 = np.array([x in h1 for x in q])
    rng = np.random.default_rng(1)
    out = {}
    for hname, mask in (("h1", inh1), ("h2", ~inh1)):
        for m in "JG":
            v = dom(Xc[m][mask], y[mask])
            pj = X["J"][mask] @ v
            out[f"{m}c_{hname}"] = dict(layer=L, vec=v.tolist(), mu=float(pj.mean()), sd=float(pj.std()))
        r_ = rng.normal(size=v.shape[0])
        r_ /= np.linalg.norm(r_)
        pj = X["J"][mask] @ r_
        out[f"Rc_{hname}"] = dict(layer=L, vec=r_.tolist(), mu=float(pj.mean()), sd=float(pj.std()))
    return out, h1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default="qwen3.5-9b")
    ap.add_argument("--centered", action="store_true", help="BBEH only: question-centred directions (steer_c_*)")
    a = ap.parse_args()
    if a.centered:
        d = HERE / "out_dirs" / a.key
        dirs, h1 = centered_dirs(a.key)
        with gzip.open(HERE / "inputs" / "dir_items.jsonl.gz", "rt") as f:
            rows = [r for r in map(json.loads, f) if r["mode"] == "J" and r["src"] != a.key and r["bench"] == "bbeh"]
        for learn, apply_ in (("h1", "h2"), ("h2", "h1")):
            json.dump({k: v for k, v in dirs.items() if k.endswith(learn)}, open(d / f"steer_c_bbeh_{apply_}_dirs.json", "w"))
            ids = [r["aid"] for r in rows if (r["qid"] in h1) == (apply_ == "h1")]
            json.dump(ids, open(d / f"steer_c_bbeh_{apply_}_ids.json", "w"))
            print("centred bbeh", apply_, len(ids))
        return
    d = HERE / "out_dirs" / a.key
    with gzip.open(HERE / "inputs" / "dir_items.jsonl.gz", "rt") as f:
        rows = [r for r in map(json.loads, f) if r["mode"] == "J" and r["src"] != a.key]
    for bench in ("bbeh", "rb2math"):
        spec = json.load(open(d / f"directions_{bench}.json"))
        h1 = set(spec["h1"])
        for learn, apply_ in (("h1", "h2"), ("h2", "h1")):
            dirs = {k: v for k, v in spec["dirs"].items() if k.endswith(learn)}
            ids = [r["aid"] for r in rows if r["bench"] == bench and ((r["qid"] in h1) == (apply_ == "h1"))]
            json.dump(dirs, open(d / f"steer_{bench}_{apply_}_dirs.json", "w"))
            json.dump(ids, open(d / f"steer_{bench}_{apply_}_ids.json", "w"))
            print(bench, apply_, len(ids), "items;", sorted(dirs))


if __name__ == "__main__":
    main()
