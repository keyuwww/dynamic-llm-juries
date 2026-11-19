"""Outer held-out evaluation of the full recipe (azure/cannon_outer/PROTOCOL.md): score every method on test answers,
pooled over the two folds, next to the paper's in-sample-selected numbers for the same pairs.

  python3 experiments/beyond_capability/outer_analyze.py -> out_paper/outer.json
Input: out_outer/<judge>_<bench>/outer_<bench>.json(l), pulled from Cannon (azure/cannon_outer/pull.sh).
"""
import json
from collections import defaultdict

import numpy as np

import allpairs_analyze as A
import sync_stats as S
from paper_analysis import per_group

D = A.HERE / "out_outer"
R = json.load(open(A.HERE / "out_paper" / "results.json"))
METH = ["verdict", "direct", "sum", "rule", "stretch", "random"]


def wsd(rows, key):
    by = defaultdict(list)
    for r in rows:
        by[r["qid"]].append(r[key])
    return float(np.sqrt(np.mean([np.var(v) for v in by.values() if len(v) > 1])))


def load(d, b):
    info = json.load(open(d / f"outer_{b}.json"))
    rows = []
    for l in open(d / f"outer_{b}.jsonl"):
        r = json.loads(l)
        f = info["folds"][r["fold"]]
        m = r["margins"]
        Ls = f"J:x11:{f['stretch_layer']}"
        rows.append(dict(qid=r["qid"], aid=r["aid"], gold=r["gold"], src=r["src"], verdict=m["none"],
                         direct=r["proj"][str(f["direct_layer"])], stretch=m[Ls], random=m["R:x11:Ls"],
                         rule=m[Ls] if f["eligible"] else m["none"],
                         **{f"L{L}": m[f"J:x11:{L}"] for L in info["candidate_layers"]}))
    sv, sd = wsd(rows, "verdict"), wsd(rows, "direct")
    for r in rows:
        r["sum"] = r["verdict"] / sv + r["direct"] / sd
    return info, rows


def main():
    pairs, per = {}, {}
    for d in sorted(D.glob("*_*")):
        j, b = d.name.rsplit("_", 1)
        if not (d / f"outer_{b}.jsonl").exists():
            continue
        info, rows = load(d, b)
        C = {m: per_group(rows, m, lambda r: r["qid"]) for m in METH}
        Ls = [f"L{L}" for L in info["candidate_layers"]]
        CL = {L: per_group(rows, L, lambda r: r["qid"]) for L in Ls}
        qs = sorted(set.intersection(*[set(c) for c in C.values()]))
        pairs[(j, b)] = {m: (qs, np.array([C[m][x] for x in qs])) for m in C}
        auc = lambda c: 100 * sum(c[x][0] for x in qs) / sum(c[x][1] for x in qs)  # noqa: E731
        layer_auc = {L: auc(CL[L]) for L in Ls}
        paper = R["pool"].get(f"{j}|{b}")
        per[f"{j}|{b}"] = dict(
            nq=len(qs), folds={k: {x: f[x] for x in ("eligible", "inner_gap", "direct_layer", "stretch_layer", "rule")}
                               for k, f in info["folds"].items()},
            rank={m: auc(C[m]) for m in METH}, posthoc_best_layer=max(layer_auc, key=layer_auc.get),
            posthoc_best_x11=max(layer_auc.values()),
            paper=dict(verdict=paper["verdict"]["rank"], direct=paper["direct"]["rank"], x11=paper["x11"]["rank"],
                       layer=paper["layer"]) if paper else None)
    stats = {f"{m}|gain": S.auc_gain(m) for m in METH if m != "verdict"} | {"verdict|level": S.level("verdict")}
    est, draws = S.boot(pairs, stats)
    est["rule_over_direct"] = S.ratio(draws, "rule|gain", "direct|gain", est)
    out = dict(pairs=per, pooled=est, n_pairs=len(pairs))
    json.dump(out, open(A.HERE / "out_paper" / "outer.json", "w"), indent=1)
    for k, v in per.items():
        p = v["paper"]
        print(f"{k:20s} " + " ".join(f"{m} {v['rank'][m]:.1f}" for m in METH) +
              f" | best-layer x11 {v['posthoc_best_x11']:.1f}" + (f" | paper: v {p['verdict']:.1f} d {p['direct']:.1f} x11 {p['x11']:.1f}" if p else " | paper: not stretched"))
    print({k: (round(x["g"], 2), round(x["lo"], 2), round(x["hi"], 2)) for k, x in est.items()})


if __name__ == "__main__":
    main()
