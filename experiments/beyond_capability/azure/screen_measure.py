"""Screen candidate judges for a preregistered test where the gap rule predicts a GAIN from stretching.
Uses only the capture + shift-only run of stretch_pipeline.py (--betas=), no stretching. Per judge, all answers:

  KNOWS     held-out ranking of the judge direction (within-question AUROC) at the chosen layer: the pipeline's split
            (what the rule was fitted with) and the mean over 10 random splits (more stable)
  SAYS      ranking of the unedited verdict score (log P(CORRECT) - log P(INCORRECT) after "VERDICT:")
  GAP       KNOWS - SAYS, points
  RESPONDS  share accepted at shift +8 sd minus at -8 sd
  SENS      verdict change per 1 sd pushed (from +-4 sd) / verdict's within-question sd; formula strength 1 + 1/SENS
  same-model KNOWS / SAYS: only pairs of answers to the same question by the same answering model (removes the
            "which model wrote it" clue that faked the unsolved-question gain for Llama-3.1-8B)
  PREDICTED gain at x11 = 0.5 x GAP if RESPONDS >= 0.10, else < 3 (the rule as preregistered for Qwen3.5-4B)

  python screen_measure.py out_mmlu/llama3.2-3b out_mmlu/phi4-mini ...   (run in the Cannon folder) -> prints markdown
"""
import collections
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stretch_pipeline import center, dom  # noqa: E402


def auc_pairs(y, s, g):
    """within-group AUROC (vectorised); g = group key per row (question, or question+source)."""
    by = collections.defaultdict(lambda: ([], []))
    for yi, si, gi in zip(y, s, g):
        by[gi][int(yi)].append(si)
    num = den = 0.0
    for neg, pos in by.values():
        if pos and neg:
            P, N = np.array(pos)[:, None], np.array(neg)[None, :]
            num += (P > N).sum() + 0.5 * (P == N).sum()
            den += P.size * N.size
    return num / den if den else float("nan"), int(den)


def measure(d, tag="mmlu"):
    d = Path(d)
    meta = [json.loads(l) for l in open(d / f"meta_{tag}.jsonl")]
    layers = json.load(open(d / f"layers_{tag}.json"))["layers"]
    ch = json.load(open(d / f"direction_choice_{tag}.json"))
    L = int(ch["layer"])
    H = np.load(d / f"hidden_{tag}.npy", mmap_mode="r")
    X = np.asarray(H[:, layers.index(L)], np.float32)
    y = np.array([m["gold"] for m in meta])
    q = np.array([m["qid"] for m in meta])
    src = np.array([m["aid"].split("|")[1] for m in meta])
    qs = np.array([a + "|" + b for a, b in zip(q, src)])
    Xc = center(X, q)

    def heldout(h1q):
        h1 = np.array([x in h1q for x in q])
        s = np.zeros(len(y))
        for tr, te in ((h1, ~h1), (~h1, h1)):
            s[te] = X[te] @ dom(Xc[tr], y[tr])
        return s

    s_pipe = heldout(set(ch["h1"]))
    uq = np.unique(q)
    split_knows = [auc_pairs(y, heldout(set(np.random.default_rng(sd).permutation(uq)[: len(uq) // 2])), q)[0]
                   for sd in range(10)]
    mar = {}
    for h in ("h1", "h2"):
        for l in open(d / f"steer_{tag}_{h}.jsonl"):
            r = json.loads(l)
            if r["dir"].startswith("Jc"):
                mar[r["aid"]] = r["margins"]
    M = lambda k: np.array([mar[m["aid"]][k] for m in meta])  # noqa: E731
    v0, vm8, vp8, vm4, vp4 = M("add:0.0"), M("add:-8.0"), M("add:8.0"), M("add:-4.0"), M("add:4.0")
    byq = collections.defaultdict(list)
    for qi, v in zip(q, v0):
        byq[qi].append(v)
    sens = float(np.mean((vp4 - vm4) / 8) / np.sqrt(np.mean([np.var(v) for v in byq.values() if len(v) > 1])))
    knows, _ = auc_pairs(y, s_pipe, q)
    says, npairs = auc_pairs(y, v0, q)
    k_sm, n_sm = auc_pairs(y, s_pipe, qs)
    s_sm, _ = auc_pairs(y, v0, qs)
    responds = float((vp8 > 0).mean() - (vm8 > 0).mean())
    gap = 100 * (knows - says)
    return dict(judge=d.name, layer=L, n_layers=json.load(open(d / f"layers_{tag}.json")).get("n_layers"),
                answers=len(y), questions=len(uq), pairs=npairs,
                knows=knows, knows_10split=float(np.mean(split_knows)), knows_10split_sd=float(np.std(split_knows)),
                says=says, gap=gap, gap_10split=100 * (np.mean(split_knows) - says),
                same_model_knows=k_sm, same_model_says=s_sm, same_model_gap=100 * (k_sm - s_sm), same_model_pairs=n_sm,
                responds=responds, accept_m8=float((vm8 > 0).mean()), accept_0=float((v0 > 0).mean()),
                accept_p8=float((vp8 > 0).mean()), sens=sens, strength=(1 + 1 / sens) if sens > 0 else None,
                corr=float(np.corrcoef(s_pipe, v0)[0, 1]),
                predicted=0.5 * gap if responds >= 0.10 else None)


def main():
    res = [measure(d) for d in sys.argv[1:]]
    print("| Judge | Layer | Knows (pipeline split / 10-split mean) | Says | Gap | Same-model knows / says (gap) | "
          "Responds (accept −8 → +8 sd) | Sensitivity → strength | Direction–verdict corr. | Predicted gain ×11 |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in res:
        pred = f"{r['predicted']:+.1f}" if r["predicted"] is not None else "< 3 (doesn't respond)"
        st = f"×{r['strength']:.0f}" if r["strength"] else "none"
        print(f"| {r['judge']} | {r['layer']}/{r['n_layers']} | {r['knows']:.3f} / {r['knows_10split']:.3f}±{r['knows_10split_sd']:.3f} | "
              f"{r['says']:.3f} | {r['gap']:+.1f} | {r['same_model_knows']:.3f} / {r['same_model_says']:.3f} ({r['same_model_gap']:+.1f}) | "
              f"{r['responds']:.2f} ({r['accept_m8']:.0%} → {r['accept_p8']:.0%}; unedited {r['accept_0']:.0%}) | "
              f"{r['sens']:.2f} → {st} | {r['corr']:.2f} | {pred} |")
    json.dump(res, open("screen_measure.json", "w"), indent=1)


if __name__ == "__main__":
    main()
