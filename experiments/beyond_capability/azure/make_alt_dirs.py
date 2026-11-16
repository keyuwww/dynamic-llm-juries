"""Two alternative judge directions for stretching one judge on MMLU-Redux, to test whether the stretch gain needs
MMLU's own direction (which may carry "which model wrote it" and other MMLU-specific clues):

  Bm  borrowed: question-centred right-minus-wrong direction learned on ALL of another benchmark (MATH), at the layer
      the MMLU run chose. No MMLU answer is used to learn it, so it is the same for both halves.
  Sm  same-model: learned on MMLU, but only from contrasts between answers to the same question by the SAME answering
      model (centred within question+model; groups with both a right and a wrong answer only). Learned on one half of
      the MMLU questions and applied to the other, as the original direction.

mu / sd for each direction come from the projections of the learning half of MMLU (as stretch_pipeline.py does).
Writes <mmlu dir>/dirs_mmlualt_{h1,h2}.json and ids_mmlualt_{h1,h2}.json (copies of the original split), for
cannon_bigstretch.sh <model> <items> <mmlu dir> mmlualt 1,3,10 T  ->  steer_mmlualt_T_h{1,2}.jsonl.
Also prints held-out ranking (KNOWS) of Jc / Bm / Sm on MMLU (all answers and same-model pairs) and their cosines.

  python make_alt_dirs.py out_mmlu/llama3.1-8b out_math/llama3.1-8b math
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stretch_pipeline import center, dom  # noqa: E402
from screen_measure import auc_pairs  # noqa: E402


def load(d, tag, L):
    meta = [json.loads(l) for l in open(d / f"meta_{tag}.jsonl")]
    layers = json.load(open(d / f"layers_{tag}.json"))["layers"]
    X = np.asarray(np.load(d / f"hidden_{tag}.npy", mmap_mode="r")[:, layers.index(L)], np.float32)
    keep = np.array([m.get("mode", "J") == "J" for m in meta])
    meta = [m for m, k in zip(meta, keep) if k]
    return meta, X[keep]


def same_model_dir(X, y, g):
    Xc = center(X, g)
    mixed = np.zeros(len(y), bool)
    for k in np.unique(g):
        m = g == k
        if 0 < y[m].sum() < m.sum():
            mixed |= m
    return dom(Xc[mixed], y[mixed]), int(mixed.sum())


def main():
    md, sd_, stag = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    ch = json.load(open(md / "direction_choice_mmlu.json"))
    L = int(ch["layer"])
    meta, X = load(md, "mmlu", L)
    y = np.array([m["gold"] for m in meta])
    q = np.array([m["qid"] for m in meta])
    src = np.array([m["aid"].split("|")[1] for m in meta])
    qs = np.array([a + "|" + b for a, b in zip(q, src)])
    h1 = np.array([x in set(ch["h1"]) for x in q])
    Xc = center(X, q)

    smeta, SX = load(sd_, stag, L)
    sy = np.array([m["gold"] for m in smeta])
    sq = np.array([m["qid"] for m in smeta])
    bm = dom(center(SX, sq), sy)
    print(f"layer {L}; MMLU {len(y)} answers; {stag} {len(sy)} answers used for the borrowed direction")

    s = {k: np.zeros(len(y)) for k in ("Jc", "Bm", "Sm")}
    vecs = {}
    for learn, apply_, mask in (("h1", "h2", h1), ("h2", "h1", ~h1)):
        jc = dom(Xc[mask], y[mask])
        sm, n_sm = same_model_dir(X[mask], y[mask], qs[mask])
        print(f"  {learn}: same-model direction from {n_sm} answers in mixed question+model groups")
        te = ~mask
        for k, v in (("Jc", jc), ("Bm", bm), ("Sm", sm)):
            s[k][te] = X[te] @ v
            vecs.setdefault(k, []).append(v)
        dirs = {}
        for name, v in ((f"Bm_{stag}", bm), (f"Sm_{learn}", sm)):
            p = X[mask] @ v
            dirs[name] = dict(layer=L, vec=v.tolist(), mu=float(p.mean()), sd=float(p.std()))
        json.dump(dirs, open(md / f"dirs_mmlualt_{apply_}.json", "w"))
        src_ids = md / f"ids_mmlu_{apply_}.json"
        if src_ids.exists():
            shutil.copy(src_ids, md / f"ids_mmlualt_{apply_}.json")
        else:
            ids = [m["aid"] for m, inh1 in zip(meta, h1) if inh1 == (apply_ == "h1")]
            json.dump(ids, open(md / f"ids_mmlualt_{apply_}.json", "w"))

    print("\n| Direction | Held-out ranking, all answers | Held-out ranking, same-model pairs |")
    print("|---|---|---|")
    for k, lab in (("Jc", "MMLU's own (original)"), ("Bm", f"borrowed from {stag}"), ("Sm", "same-model pairs only")):
        print(f"| {lab} | {auc_pairs(y, s[k], q)[0]:.3f} | {auc_pairs(y, s[k], qs)[0]:.3f} |")
    print(f"| unedited verdict | – | – |")
    cos = lambda a, b: float(np.mean([u @ w for u, w in zip(a, b)]))  # noqa: E731
    print(f"\ncosine Jc-Bm {cos(vecs['Jc'], vecs['Bm']):.2f}, Jc-Sm {cos(vecs['Jc'], vecs['Sm']):.2f}, "
          f"Bm-Sm {cos(vecs['Bm'], vecs['Sm']):.2f}")


if __name__ == "__main__":
    main()
