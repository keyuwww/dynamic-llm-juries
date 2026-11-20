"""Pool the nested surface check (nested_surface_modal.py) with the synchronised question bootstrap.

  python3 experiments/beyond_capability/nested_surface_analyze.py -> out_paper/nested_surface_check.json
Same quantities as paper_surface.py (gains over the verdict, residualized share of the direction's gain, paired
surface-minus-direction difference), but with layer, direction, surface model and residualizer all fitted without the
evaluated questions' labels.
"""
import json

import numpy as np

import allpairs_analyze as A
import sync_stats as S

METH = ("verdict", "direct", "surface", "dir_resid", "direct_inner", "resid_inner")


def main():
    R = json.load(open(A.HERE / "out_paper" / "nested_surface.json"))
    pairs, per = {}, {}
    for k, r in sorted(R.items()):
        j, b = k.split("|")
        P = r["perq"]
        qs = sorted(set.intersection(*[set(P[m]) for m in METH]))
        pairs[(j, b)] = {m: (qs, np.array([P[m][x] for x in qs])) for m in METH}
        tot = {m: np.array([P[m][x] for x in qs]).sum(0) for m in METH}
        per[k] = dict(folds=r["folds"], **{f"{m}|{part}": 100 * tot[m][2 * i] / tot[m][2 * i + 1] if tot[m][2 * i + 1] else None
                                           for m in METH for i, part in enumerate(("all", "same", "diff"))})
    stats = {}
    for part, col in (("all", (0, 1)), ("same", (2, 3)), ("diff", (4, 5))):
        stats |= {f"{m}|gain|{part}": S.auc_gain(m, col=col) for m in METH[1:]}
        stats |= {f"{m}|level|{part}": S.level(m, col=col) for m in METH}
        stats[f"surface_minus_direct|{part}"] = S.auc_gain("surface", base="direct", col=col)
        stats[f"resid_minus_direct|{part}"] = S.auc_gain("dir_resid", base="direct", col=col)
    est, draws = S.boot(pairs, stats)
    for part in ("all", "same", "diff"):
        est[f"resid_kept|{part}"] = S.ratio(draws, f"dir_resid|gain|{part}", f"direct|gain|{part}", est)
        est[f"resid_inner_kept|{part}"] = S.ratio(draws, f"resid_inner|gain|{part}", f"direct_inner|gain|{part}", est)
    r2 = [f["r2_inner"] for r in R.values() for f in r["folds"].values()]
    out = dict(n_pairs=len(pairs), pooled=est, pairs=per, r2_inner=dict(lo=min(r2), hi=max(r2)))
    json.dump(out, open(A.HERE / "out_paper" / "nested_surface_check.json", "w"), indent=1)
    print(len(pairs), "pairs")
    print({k: (round(v["g"], 2), round(v["lo"], 2), round(v["hi"], 2)) for k, v in est.items()})


if __name__ == "__main__":
    main()
