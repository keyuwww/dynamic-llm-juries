"""Within-question test of "a believed wrong answer looks right inside the judge" (Nov 18).

The cosine between a belief direction and a correctness direction (dir_belief.py) turned out to be almost as high when
belief labels are shuffled within question (dir_belief_robust.py): it mostly reflects which questions the believed
answers come from. This test removes question composition: among WRONG answers to the SAME question, does the role's
correctness axis (right minus wrong, learned on the other half of the questions) score the believed answer (>= half of
the model's own answers reach it) above the never-reached one (0 of its answers)?

  pairwise AUROC = share of (believed, never-reached) pairs from the same question where the believed answer scores
                   higher; 0.5 = the axis ignores belief. Mean over 20 splits of the questions; 95% interval resampling
                   questions (one split). Also the same for the model's own verdict log-odds at "VERDICT:" (J, S, JX, JT):
                   the behavioural counterpart.

  python3 experiments/beyond_capability/dir_belief_within.py --key qwen3.5-9b --tags main,neutral,after
      -> out_dirs/belief_within_<key>.md
"""
import argparse
import collections
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dir_belief as db  # noqa: E402
from dir_analyze import center, dom  # noqa: E402
from dir_belief_robust import role_rows  # noqa: E402

S = 20
NB = 1000


def pairs_of(q, bel, sel):
    by = collections.defaultdict(lambda: ([], []))
    for i in np.where(sel)[0]:
        by[q[i]][0 if bel[i] == 1 else 1].append(i)
    return {k: v for k, v in by.items() if v[0] and v[1]}


def pair_auc(s, groups, keys=None):
    num = den = 0.0
    for k in (keys if keys is not None else groups):
        b, n = groups[k]
        d = s[np.array(b)][:, None] - s[np.array(n)][None, :]
        num += (d > 0).sum() + 0.5 * (d == 0).sum()
        den += d.size
    return num / den if den else np.nan


def boot_ci(s, groups, seed=0):
    ks = list(groups)
    rng = np.random.default_rng(seed)
    v = [pair_auc(s, groups, [ks[i] for i in rng.choice(len(ks), len(ks))]) for _ in range(NB)]
    return np.nanpercentile(v, [2.5, 97.5])


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
    layers = parts[0][2]
    L = [f"# Believed vs never-reached WRONG answers to the same question — {a.key}, BBEH, audited labels\n",
         "Pairwise AUROC within question (0.5 = no preference for the believed answer). 'axis' = the role's correctness "
         "direction (cross-fitted over question halves, mean of 20 splits; best layer = highest mean right-vs-wrong "
         "AUROC); 'verdict' = the model's own CORRECT-minus-INCORRECT log-odds at that position.\n",
         "| role | questions with both | pairs | axis, best layer (layer) | 95% CI | axis, mean over the top-third layers | "
         "verdict log-odds | 95% CI | belief direction: best layer (layer), mean over the correctness top third |",
         "|---|---|---|---|---|---|---|---|---|"]
    prof = {}
    for role in a.roles.split(","):
        if role not in rows:
            continue
        aids = [x for x in sorted(rows[role]) if not (rows[role][x][2]["gold"] == 0 and x in bad)]
        y = np.array([rows[role][x][2]["gold"] for x in aids])
        q = np.array([rows[role][x][2]["qid"] for x in aids])
        b = np.array([belief.get(x, np.nan) for x in aids], float)
        wrong = (y == 0) & ~np.isnan(b)
        bel = np.where(b >= thr - 1e-9, 1, np.where(b == 0, 0, -1))
        sel = wrong & (bel >= 0)
        groups = pairs_of(q, bel, sel)
        npairs = sum(len(v[0]) * len(v[1]) for v in groups.values())
        AUCrw = np.zeros((S, len(layers)))
        PA = np.zeros((S, len(layers)))
        PB = np.full((S, len(layers)), np.nan)  # the BELIEF direction (believed minus never, other half) within question
        SC = {}
        for li in range(len(layers)):
            X = np.stack([rows[role][x][0][rows[role][x][1], li] for x in aids]).astype(np.float32)
            Xc = center(X, q)
            for s in range(S):
                h = db.halves(q, seed=100 + s)
                sc = np.zeros(len(y))
                for tr, te in ((h, ~h), (~h, h)):
                    sc[te] = Xc[te] @ dom(Xc[tr], y[tr])
                AUCrw[s, li] = db.auc(y, sc)
                PA[s, li] = pair_auc(sc, groups)
                sb = np.zeros(len(y))
                for tr, te in ((h, ~h), (~h, h)):
                    st = sel & tr
                    sb[te] = Xc[te] @ dom(Xc[st], bel[st])
                PB[s, li] = pair_auc(sb, groups)
                if s == 0:
                    SC[li] = sc
        ma = AUCrw.mean(0)
        bl = int(np.argmax(ma))
        top = np.argsort(-ma)[: max(1, len(ma) // 3)]
        lo, hi = boot_ci(SC[bl], groups)
        m = np.array([rows[role][x][2].get("margin") if rows[role][x][2].get("margin") is not None else np.nan
                      for x in aids], float)
        if np.isfinite(m[sel]).all():
            va = pair_auc(m, groups)
            vlo, vhi = boot_ci(m, groups)
            vcell = f"{va:.2f} | [{vlo:.2f}, {vhi:.2f}]"
        else:
            vcell = "– | –"
        prof[role] = PA.mean(0)
        pbm = np.nanmean(PB, 0)
        beliefcell = f"{pbm.max():.2f} ({layers[int(np.nanargmax(pbm))]}), top-third {np.nanmean(pbm[top]):.2f}"
        L.append(f"| {role} {db.NAMES.get(role, '')} | {len(groups)} | {npairs} | {PA[:, bl].mean():.2f} ({layers[bl]}) | "
                 f"[{lo:.2f}, {hi:.2f}] | {PA[:, top].mean():.2f} | {vcell} | {beliefcell} |")
    L += ["", "## Pairwise AUROC of the correctness axis by layer (mean over splits)\n",
          "| layer | " + " | ".join(prof) + " |", "|---|" + "---|" * len(prof)]
    for li, layer in enumerate(layers):
        L.append(f"| {layer} | " + " | ".join(f"{prof[r][li]:.2f}" for r in prof) + " |")
    (HERE / "out_dirs" / f"belief_within_{a.key}.md").write_text("\n".join(L) + "\n")
    print("\n".join(L[:12]))


if __name__ == "__main__":
    db.NAMES.update({"JX": "judge after explanation", "JT": "judge after thinking"})
    main()
