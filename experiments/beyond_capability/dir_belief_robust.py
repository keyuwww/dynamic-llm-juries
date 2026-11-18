"""Robustness of the belief-vs-correctness cosine (Nov 18). dir_belief.py reports ONE random split of the questions and
the single layer where the role's correctness direction scores best; on Qwen3.6-35B that pick flips between layers
12 and 24 with the split and the cosine with it (0.80 vs 0.41). This script reports, per role and layer:

  auc     right-vs-wrong AUROC of the role's correctness direction (direction from one half of the questions, scored on
          the other), mean over S splits
  cos     cosine(belief direction, correctness direction) on DISJOINT halves of the questions (belief from one half,
          correctness from the other, both ways averaged), mean and sd over S splits
  null    the same cosine with belief labels shuffled among the wrong answers (within question), mean and 95th pct:
          how much overlap appears with no belief signal at all
and a summary per role: the layer band where correctness is best read (top third of layers by mean auc), the mean
cosine over that band, and the per-split best-layer cosine (median and range).

Belief = BBEH, the model's 5 own answers; believed >= half, never reached = 0; wrong answers only; audited labels.

  python3 experiments/beyond_capability/dir_belief_robust.py --key qwen3.5-9b --tags main,neutral,after
      -> out_dirs/belief_robust_<key>.md (+ .json)
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dir_belief as db  # noqa: E402
from dir_analyze import center, cos, dom  # noqa: E402

S = 20


def role_rows(key, parts, roles):
    rows = {}
    for H, meta, _ in parts:
        for i, m in enumerate(meta):
            if m["bench"] == "bbeh" and m["mode"] in roles and m["src"] != key and not m.get("skipped"):
                rows.setdefault(m["mode"], {})[m["aid"]] = (H, i, m)
    return rows


def analyse(key, parts, role, rows, belief, thr, bad):
    aids = sorted(rows[role])
    aids = [x for x in aids if not (rows[role][x][2]["gold"] == 0 and x in bad)]
    y = np.array([rows[role][x][2]["gold"] for x in aids])
    q = np.array([rows[role][x][2]["qid"] for x in aids])
    b = np.array([belief.get(x, np.nan) for x in aids], float)
    wrong = (y == 0) & ~np.isnan(b)
    bel = np.where(b >= thr - 1e-9, 1, np.where(b == 0, 0, -1))
    sel = wrong & (bel >= 0)
    layers = parts[0][2]
    nL = len(layers)
    AUC = np.full((S, nL), np.nan)
    COS = np.full((S, nL), np.nan)
    NUL = np.full((S, nL), np.nan)
    for li in range(nL):
        X = np.stack([rows[role][x][0][rows[role][x][1], li] for x in aids]).astype(np.float32)
        Xc = center(X, q)
        for s in range(S):
            h = db.halves(q, seed=100 + s)
            sc = np.zeros(len(y))
            for tr, te in ((h, ~h), (~h, h)):
                sc[te] = Xc[te] @ dom(Xc[tr], y[tr])
            AUC[s, li] = db.auc(y, sc)
            sa, sb = sel & h, sel & ~h
            COS[s, li] = np.mean([cos(dom(Xc[sa], bel[sa]), dom(Xc[~h], y[~h])),
                                  cos(dom(Xc[sb], bel[sb]), dom(Xc[h], y[h]))])
            # null: shuffle believed / never-reached labels among the selected wrong answers, within question
            rng = np.random.default_rng(1000 + s)
            bl = bel.copy()
            idx = np.where(sel)[0]
            for qq in np.unique(q[idx]):
                j = idx[q[idx] == qq]
                bl[j] = bl[rng.permutation(j)]
            if (bl[sel] == 1).sum() < 5:
                continue
            NUL[s, li] = np.mean([cos(dom(Xc[sa], bl[sa]), dom(Xc[~h], y[~h])),
                                  cos(dom(Xc[sb], bl[sb]), dom(Xc[h], y[h]))])
    return dict(layers=layers, n=len(aids), n_bel=int((sel & (bel == 1)).sum()), n_never=int((sel & (bel == 0)).sum()),
                auc=AUC.tolist(), cos=COS.tolist(), null=NUL.tolist())


def summary(r):
    A, C, N = (np.array(r[k]) for k in ("auc", "cos", "null"))
    ma = np.nanmean(A, 0)
    top = np.argsort(-ma)[: max(1, len(ma) // 3)]
    band_cos = np.nanmean(C[:, top], 1)  # per split, mean over the band
    band_null = np.nanmean(N[:, top], 1)
    best = [C[s, int(np.nanargmax(A[s]))] for s in range(A.shape[0])]
    return dict(band=[r["layers"][i] for i in sorted(top)], band_auc=float(np.mean(ma[top])),
                band_cos=float(np.mean(band_cos)), band_cos_sd=float(np.std(band_cos)),
                band_null=float(np.nanmean(band_null)), band_null_p95=float(np.nanpercentile(N[:, top], 95)),
                best_med=float(np.median(best)), best_lo=float(np.min(best)), best_hi=float(np.max(best)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--tags", required=True)
    ap.add_argument("--roles", default="J,N,S,G,JX,JT")
    a = ap.parse_args()
    parts = [db.load(a.key, t) for t in a.tags.split(",")]
    belief, thr = db.beliefs(a.key, "bbeh")
    bad = db.audited_bad("bbeh")
    rows = role_rows(a.key, parts, a.roles.split(","))
    out, L = {}, [f"# Belief vs correctness directions, robustness — {a.key}, BBEH, audited labels\n",
                  f"{S} random splits of the questions. Band = top third of layers by mean right-vs-wrong AUROC. "
                  "cos = cosine(belief direction, correctness direction) built on disjoint halves of the questions. "
                  "null = same with belief labels shuffled within question.\n",
                  "| role | answers | believed / never | band (layers) | AUROC in band | **cos in band** (sd over splits) | "
                  "null mean (95th pct) | per-split best layer: median [min, max] |", "|---|---|---|---|---|---|---|---|"]
    for role in a.roles.split(","):
        if role not in rows:
            continue
        r = analyse(a.key, parts, role, rows, belief, thr, bad)
        sm = summary(r)
        out[role] = dict(r, summary=sm)
        L.append(f"| {role} {db.NAMES.get(role, '')} | {r['n']} | {r['n_bel']} / {r['n_never']} | {sm['band']} | "
                 f"{sm['band_auc']:.2f} | **{sm['band_cos']:+.2f}** ({sm['band_cos_sd']:.2f}) | "
                 f"{sm['band_null']:+.2f} ({sm['band_null_p95']:+.2f}) | {sm['best_med']:+.2f} [{sm['best_lo']:+.2f}, "
                 f"{sm['best_hi']:+.2f}] |")
    L += ["", "## Per layer (mean over splits): AUROC / cos / null\n",
          "| layer | " + " | ".join(out) + " |", "|---|" + "---|" * len(out)]
    layers = parts[0][2]
    for li, layer in enumerate(layers):
        cells = []
        for role, r in out.items():
            A, C, N = (np.array(r[k]) for k in ("auc", "cos", "null"))
            cells.append(f"{np.nanmean(A[:, li]):.2f} / {np.nanmean(C[:, li]):+.2f} / {np.nanmean(N[:, li]):+.2f}")
        L.append(f"| {layer} | " + " | ".join(cells) + " |")
    (HERE / "out_dirs" / f"belief_robust_{a.key}.md").write_text("\n".join(L) + "\n")
    json.dump(out, open(HERE / "out_dirs" / f"belief_robust_{a.key}.json", "w"))
    print("\n".join(L))


if __name__ == "__main__":
    db.NAMES.update({"JX": "judge after explanation", "JT": "judge after thinking"})
    main()
