"""One GPU job, three steps, for a benchmark's judging items (dir_capture.py format, judge role, thinking off):

  1. capture   hidden state at "VERDICT:" for every item, every 2nd layer      -> <out>/hidden_<tag>.npy, meta_<tag>.jsonl
  2. direction question-centred "right minus wrong" direction per layer, learned on one half of the questions; the
               layer is chosen by how well the direction ranks answers to the same question on the OTHER half
               (all questions; solve labels are not used here, so nothing about unsolved questions is peeked at)
  3. stretch   each half is steered with the direction learned on the other half: shift (add +-4/+-8 sd) and
               stretch (x1, x3, x10 around the mean), plus a random direction           -> <out>/steer_<tag>_h{1,2}.jsonl

  python stretch_pipeline.py --model Qwen/Qwen3.5-9B --items inputs/mmlu_full_items.jsonl.gz --out out_mmlu/qwen --tag mmlu
"""
import argparse
import collections
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def within_auc(y, s, q):
    by = collections.defaultdict(lambda: ([], []))
    for yi, si, g in zip(y, s, q):
        by[g][int(yi)].append(si)
    num = den = 0.0
    for neg, pos in by.values():
        for a in pos:
            for b in neg:
                num += 1.0 if a > b else 0.5 if a == b else 0.0
                den += 1
    return num / den if den else float("nan")


def center(X, q):
    Xc = X.copy()
    for g in set(q):
        k = q == g
        Xc[k] -= X[k].mean(0)
    return Xc


def dom(X, y):
    d = X[y == 1].mean(0) - X[y == 0].mean(0)
    return d / (np.linalg.norm(d) + 1e-9)


def run(cmd):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--items", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    if not (out / f"layers_{a.tag}.json").exists():
        run([py, str(HERE / "dir_capture.py"), "--phase", "capture", "--model", a.model, "--items", a.items,
             "--out", str(out), "--tag", a.tag])
    # ---- 2. directions
    H = np.load(out / f"hidden_{a.tag}.npy", mmap_mode="r")
    meta = [json.loads(l) for l in open(out / f"meta_{a.tag}.jsonl")]
    layers = json.load(open(out / f"layers_{a.tag}.json"))["layers"]
    y = np.array([m["gold"] for m in meta])
    q = np.array([m["qid"] for m in meta])
    uq = sorted(set(q))
    rng = np.random.default_rng(0)
    h1q = set(rng.permutation(uq)[: len(uq) // 2])
    h1 = np.array([x in h1q for x in q])
    scores = {}
    for li, l in enumerate(layers):
        if l == 0:
            continue
        X = np.asarray(H[:, li], np.float32)
        Xc = center(X, q)
        s = np.zeros(len(y))
        for tr, te in ((h1, ~h1), (~h1, h1)):
            s[te] = X[te] @ dom(Xc[tr], y[tr])
        scores[l] = within_auc(y, s, q)
        print(f"  layer {l}: held-out within-question AUROC {scores[l]:.3f}", flush=True)
    L = max(scores, key=scores.get)
    li = layers.index(L)
    X = np.asarray(H[:, li], np.float32)
    Xc = center(X, q)
    json.dump(dict(layer=L, scores=scores, h1=sorted(h1q)), open(out / f"direction_choice_{a.tag}.json", "w"), indent=1)
    print(f"chosen layer {L}", flush=True)
    for learn, apply_, mask in (("h1", "h2", h1), ("h2", "h1", ~h1)):
        v = dom(Xc[mask], y[mask])
        r = rng.normal(size=v.shape[0])
        r /= np.linalg.norm(r)
        dirs = {}
        for name, d in ((f"Jc_{learn}", v), (f"Rc_{learn}", r)):
            p = X[mask] @ d
            dirs[name] = dict(layer=L, vec=d.tolist(), mu=float(p.mean()), sd=float(p.std()))
        json.dump(dirs, open(out / f"dirs_{a.tag}_{apply_}.json", "w"))
        ids = [m["aid"] for m, inh1 in zip(meta, h1) if inh1 == (apply_ == "h1")]
        json.dump(ids, open(out / f"ids_{a.tag}_{apply_}.json", "w"))
    # ---- 3. steer
    for apply_ in ("h1", "h2"):
        if (out / f"steer_{a.tag}_{apply_}.jsonl").exists() and \
                sum(1 for _ in open(out / f"steer_{a.tag}_{apply_}.jsonl")) >= 2 * len(json.load(open(out / f"ids_{a.tag}_{apply_}.json"))):
            continue
        run([py, str(HERE / "dir_capture.py"), "--phase", "steer", "--model", a.model, "--items", a.items, "--out", str(out),
             "--tag", f"{a.tag}_{apply_}", "--directions", str(out / f"dirs_{a.tag}_{apply_}.json"),
             "--steer-ids", str(out / f"ids_{a.tag}_{apply_}.json"), "--alphas=-8,-4,0,4,8", "--betas=1,3,10"])  # "=" form: a value starting with "-" is not an option
    print("done: pipeline", flush=True)


if __name__ == "__main__":
    main()
