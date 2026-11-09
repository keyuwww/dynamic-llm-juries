"""Inputs for the Azure steering run (no API calls): the thinking-on "this answer is right" direction (Jt), learned on
question half h1 from the start-of-thinking states (out_dirs/qwen3.5-9b/hidden_think.npy, question-centred, layer 18),
a random control direction (Rt), and ~200 judge items from half h2 on questions with both right and wrong answers
(about 2/3 on questions Qwen-9B cannot solve). Writes azure/inputs/steer_think_{dirs,ids}.json.

  python3 experiments/beyond_capability/azure/prep_think.py
"""
import collections
import json
import shutil
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BC = HERE.parent
sys.path.insert(0, str(BC))
from dir_analyze import center, dom, load, solved_labels  # noqa: E402

LAYER, N_UNSOLVED, N_SOLVED = 18, 135, 65


def main():
    H, meta, layers = load("qwen3.5-9b", "think")
    sol = solved_labels("qwen3.5-9b")
    h1 = set(json.load(open(BC / "out_dirs" / "qwen3.5-9b" / "directions_bbeh.json"))["h1"])
    idx = np.array([i for i, r in enumerate(meta) if r["bench"] == "bbeh" and r["src"] != "qwen3.5-9b"])
    y = np.array([meta[i]["gold"] for i in idx])
    q = np.array([meta[i]["qid"] for i in idx])
    X = np.asarray(H[idx, layers.index(LAYER)], np.float32)
    m = np.array([x in h1 for x in q])
    v = dom(center(X, q)[m], y[m])
    rng = np.random.default_rng(2)
    r = rng.normal(size=v.shape[0])
    r /= np.linalg.norm(r)
    dirs = {name: dict(layer=LAYER, vec=d.tolist(), mu=float((X[m] @ d).mean()), sd=float((X[m] @ d).std()))
            for name, d in (("Jt", v), ("Rt", r))}
    # items: half h2, questions with both a right and a wrong answer
    by_q = collections.defaultdict(list)
    for i, qq in zip(idx, q):
        if qq not in h1:
            by_q[qq].append(meta[i])
    mixed = [qq for qq, rows in by_q.items() if len({x["gold"] for x in rows}) == 2 and sol.get(("bbeh", qq)) in (0, 1)]
    rng.shuffle(mixed)
    ids, n = [], {0: 0, 1: 0}
    for qq in mixed:
        s = sol[("bbeh", qq)]
        cap = N_UNSOLVED if s == 0 else N_SOLVED
        if n[s] + len(by_q[qq]) <= cap:
            ids += [x["aid"] for x in by_q[qq]]
            n[s] += len(by_q[qq])
    out = HERE / "inputs"
    out.mkdir(exist_ok=True)
    json.dump(dirs, open(out / "steer_think_dirs.json", "w"))
    json.dump(ids, open(out / "steer_think_ids.json", "w"))
    shutil.copy(BC / "inputs" / "dir_items.jsonl.gz", out / "dir_items.jsonl.gz")
    shutil.copy(BC / "dir_capture.py", HERE / "dir_capture.py")
    print(f"{len(ids)} items ({n[0]} on unsolved, {n[1]} on solved questions); Jt sd {dirs['Jt']['sd']:.3f}")


if __name__ == "__main__":
    main()
