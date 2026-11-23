"""Analyse the controlled-edit test (PROTOCOL.md): pair accuracy (original above edited) per readout and judge, pooled
over the four judges with the synchronised question bootstrap; the surface model fitted on each fold's training half
of the MATH main pool; a check that the re-scored originals reproduce the stored primary-evaluation scores.

  python3 experiments/beyond_capability/edit_test/edit_analyze.py -> edit_test/results.json
"""
import gzip
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BC = HERE.parent
sys.path.insert(0, str(BC))
import paper_surface as PS  # noqa: E402
import sync_stats as S  # noqa: E402

READ = ("verdict", "direct", "rule", "stretch", "surface")


def surface_models(pairs):
    """per fold: least-squares surface model on the MATH main pool's training half (as primary_scope_modal.py),
    applied to original and edited answers (centred within the pair, so only the difference matters)."""
    F = json.load(gzip.open(BC / "out_paper" / "surface_features.json.gz", "rt"))["F"]
    rows = [json.loads(l) for l in open(BC / "out_outer" / "llama3.1-8b_math" / "outer_math.jsonl")]
    q = np.array([r["qid"] for r in rows])
    y = np.array([r["gold"] for r in rows], float)
    Z0 = np.array([F[r["aid"]] for r in rows], float)
    fold = np.array([r["fold"] for r in rows])  # the fold in which the question is a test question

    def centre(X):
        X = X.copy()
        for g in set(q):
            k = q == g
            X[k] -= X[k].mean(0)
        return X
    Zc, yc = centre(Z0), centre(y[:, None])[:, 0]
    W = {}
    for f in ("h1", "h2"):
        tr = fold != f
        sd = Zc[tr].std(0) + 1e-9
        w, *_ = np.linalg.lstsq(Zc[tr] / sd, yc[tr], rcond=None)
        W[f] = (w, sd)
    qfold = dict(zip(q, fold))
    out = {}
    for p in pairs:
        w, sd = W[qfold[p["qid"]]]
        fo, fe = np.array(PS.feats(p["original"])), np.array(PS.feats(p["edited"]))
        m = (fo + fe) / 2
        out[p["qid"]] = (float(((fo - m) / sd) @ w), float(((fe - m) / sd) @ w))
    return out, qfold


def main(which="test"):
    P = [json.loads(l) for l in open(HERE / f"pairs_{which}.jsonl")]
    keep = None
    rf = HERE / f"reader_{which}.json"
    R = json.load(open(rf)) if rf.exists() else None
    SC = json.load(open(HERE / f"scores_{which}.json"))
    surf, qfold = surface_models(P)
    res, pairs_all, pairs_reader, repro = {}, {}, {}, {}
    for j, rows in SC.items():
        by = {}
        for r in rows:
            by.setdefault(r["qid"], {})[r["kind"]] = r
        stored = {}
        for l in open(BC / "out_outer" / f"{j}_math" / "outer_math.jsonl"):
            o = json.loads(l)
            stored[o["aid"]] = o
        info = json.load(open(BC / "out_outer" / f"{j}_math" / "outer_math.json"))
        dv, dd, ds = [], [], []
        per = {m: {} for m in READ}
        for p in P:
            o, e = by[p["qid"]]["original"], by[p["qid"]]["edited"]
            st = stored[p["aid"]]
            f = info["folds"][st["fold"]]
            assert st["fold"] == o["fold"]
            dv.append(abs(o["verdict"] - st["margins"]["none"]))
            dd.append(abs(o["direct"] - st["proj"][str(f["direct_layer"])]))
            ds.append(abs(o["stretch"] - st["margins"][f"J:x11:{f['stretch_layer']}"]))
            for m in READ:
                a, b = (surf[p["qid"]] if m == "surface" else (o[m], e[m]))
                w = 1.0 if a > b else 0.5 if a == b else 0.0
                per[m][p["qid"]] = [w, 1.0]
        repro[j] = dict(verdict_max=max(dv), direct_max=max(dd), stretch_max=max(ds),
                        stretch_share_exact=float(np.mean(np.array(ds) < 1e-9)))
        res[j] = {m: 100 * np.mean([v[0] for v in per[m].values()]) for m in READ}
        qs = sorted(per["verdict"])
        pairs_all[(j, "math")] = {m: (qs, np.array([per[m][x] for x in qs])) for m in READ}
        if R:
            qr = [x for x in qs if R.get(x, {}).get("pass")]
            pairs_reader[(j, "math")] = {m: (qr, np.array([per[m][x] for x in qr])) for m in READ}
    stats = {f"{m}|level": S.level(m) for m in READ}
    stats |= {f"{m}|gain": S.auc_gain(m) for m in READ if m != "verdict"}
    est, _ = S.boot(pairs_all, stats)
    out = dict(n_pairs=len(P), per_judge=res, pooled=est, reproduce=repro,
               len_ratio=dict(min=min(p["len_ratio"] for p in P), max=max(p["len_ratio"] for p in P)),
               sim_median=float(np.median([p["sim"] for p in P])),
               halves={h: sum(qfold[p["qid"]] == h for p in P) for h in ("h1", "h2")})
    if R:
        est_r, _ = S.boot(pairs_reader, stats)
        out["pooled_reader_pass"] = est_r
        out["n_reader_pass"] = sum(1 for p in P if R.get(p["qid"], {}).get("pass"))
        out["reader_counts"] = {k: sum(1 for v in R.values() if v.get(k)) for k in ("pass", "no_error", "cue", "partial")}
    log = json.load(open(HERE / f"log_{which}.json"))["summary"]
    out["build"] = log
    json.dump(out, open(HERE / f"results_{which}.json", "w"), indent=1)
    show = lambda e: {k: (round(v["g"], 1), round(v["lo"], 1), round(v["hi"], 1)) for k, v in e.items()}  # noqa: E731
    print(json.dumps(res, indent=1))
    print(show(est))
    if R:
        print("reader pass", out["n_reader_pass"], show(est_r))
    print(repro)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "test")
