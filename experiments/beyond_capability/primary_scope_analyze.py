"""Pool the primary-scope analyses (primary_scope_modal.py + the stored outer evaluation) with the synchronised
question bootstrap. Every quantity is on the 12 primary pairs (or the 8 of them on MMLU-Redux and MATH, where
same-model pairs exist), on test answers of the paper's two outer folds, with every fit on the training half.

  python3 experiments/beyond_capability/primary_scope_analyze.py -> out_paper/primary_scope_check.json

  gains        direction, rule, stretch, random, verdict + direction (training-scaled and test-scaled), surface model,
               residualized direction, direction without authorship directions: all / same-model / different-model
  interaction  (gain on different-model pairs) - (gain on same-model pairs), paired over the same resamples
  incremental  pairwise logistic models fitted on training pairs: held-out ranking and log loss per pair
  overlap      share of test pairs ranked correctly by both / only one / neither of two scores (descriptive)
  review       fixed-budget error review: flag the lowest-scored k% of a pair's answers; share of wrong answers caught
  splits       direction gain over five further random outer splits (point estimates)
"""
import json
from collections import defaultdict

import numpy as np

import allpairs_analyze as A
import paper_data as D
import sync_stats as S

OUT = A.HERE / "out_paper"
PS = json.load(open(OUT / "primary_scope.json"))
PW = ("surface", "direct", "surface+direct", "verdict", "verdict+direct", "verdict+surface+direct")
BUDGETS = (10, 20, 30)


def perq(rows, key):
    by = defaultdict(list)
    for r in rows:
        by[r["qid"]].append(r)
    out = {}
    for g, rs in by.items():
        P = [r for r in rs if r["gold"] == 1]
        N = [r for r in rs if r["gold"] == 0]
        if not P or not N:
            continue
        v = [0.0] * 6
        for a in P:
            for b in N:
                w = 1.0 if a[key] > b[key] else 0.5 if a[key] == b[key] else 0.0
                k = 2 if a["src"] == b["src"] else 4
                v[0] += w; v[1] += 1; v[k] += w; v[k + 1] += 1
        out[g] = v
    return out


def outer_rows(j, b):
    info = json.load(open(A.HERE / "out_outer" / f"{j}_{b}" / f"outer_{b}.json"))
    sc = PS[f"{j}|{b}"]["folds"]
    rows = []
    for l in open(A.HERE / "out_outer" / f"{j}_{b}" / f"outer_{b}.jsonl"):
        r = json.loads(l)
        f = info["folds"][r["fold"]]
        m = r["margins"]
        Ls = f"J:x11:{f['stretch_layer']}"
        d = r["proj"][str(f["direct_layer"])]
        s = sc[r["fold"]]
        rows.append(dict(aid=r["aid"], qid=r["qid"], gold=r["gold"], src=r["src"], verdict=m["none"], direct=d, stretch=m[Ls],
                         random=m["R:x11:Ls"], rule=m[Ls] if f["eligible"] else m["none"],
                         sum_train=m["none"] / s["scale_verdict_train"] + d / s["scale_direct_train"]))
    return rows


def review_perq(rows, key):
    """flag the lowest-scored k% of the pair's answers (a fixed review budget); per question: wrong answers flagged,
    wrong answers, answers flagged. The threshold is the pair's own k-th percentile (label-free, held fixed in the
    bootstrap)."""
    x = np.array([r[key] for r in rows])
    out = {}
    for k in BUDGETS:
        t = np.percentile(x, k)
        by = defaultdict(lambda: [0.0, 0.0, 0.0])
        for r, s in zip(rows, x):
            v = by[r["qid"]]
            fl = s <= t
            v[0] += fl and r["gold"] == 0
            v[1] += r["gold"] == 0
            v[2] += fl
        out[k] = dict(by)
    return out


def main():
    pairs, mm_pairs, review, mismatch = {}, {}, {}, {}
    METH_O = ("verdict", "direct", "rule", "stretch", "random", "sum_train")
    METH_M = ("surface", "resid_inner", "direct_inner", "resid_full", "sum_test", "c_perp")
    for k, r in sorted(PS.items()):
        j, b = k.split("|")
        rows = outer_rows(j, b)
        P = {m: perq(rows, m) for m in METH_O}
        for m in METH_M:
            if r["perq"].get(m):
                P[m] = r["perq"][m]
        for m in PW:
            P[f"pw:{m}"] = r["perq"][f"pw:{m}"]
            P[f"ll:{m}"] = r["pw_loss"][m]
        # the Modal capture of Llama-3.1-8B MATH differs from the Cannon capture by a verdict tie on 6 of 602 questions
        nbad = sum(abs(P["verdict"][q][0] - r["perq"]["verdict"].get(q, [-1])[0]) > 1e-9 for q in P["verdict"])
        assert nbad <= 0.01 * len(P["verdict"]), (k, nbad)
        mismatch[k] = nbad
        names = [m for m in P if not m.startswith("ll:")]
        qs = sorted(set.intersection(*[set(P[m]) for m in names]))
        pairs[(j, b)] = {m: (qs, np.array([P[m][x] for x in qs])) for m in names}
        ql = sorted(set.intersection(*[set(P[f"ll:{m}"]) for m in PW]))
        for m in PW:
            pairs[(j, b)][f"ll:{m}"] = (ql, np.array([P[f"ll:{m}"][x] for x in ql]))
        if b in ("mmlu", "math"):
            mm_pairs[(j, b)] = pairs[(j, b)]
        R = {m: review_perq(rows, m) for m in ("verdict", "direct", "rule", "sum_train")}
        review[(j, b)] = {}
        for m, e in R.items():
            for kk, d in e.items():
                q2 = sorted(d)
                review[(j, b)][f"{m}@{kk}"] = (q2, np.array([d[x] for x in q2]))
    parts = (("all", (0, 1)), ("same", (2, 3)), ("diff", (4, 5)))

    def inter(m, base="verdict"):
        def f(T):
            if m not in T or T[m][3] == 0 or T[m][5] == 0:
                return None
            gs = T[m][2] / T[m][3] - T[base][2] / T[base][3]
            gd = T[m][4] / T[m][5] - T[base][4] / T[base][5]
            return 100 * (gd - gs)
        return f

    def ll(m):
        return lambda T: T[f"ll:{m}"][0] / T[f"ll:{m}"][1]

    def ll_diff(a, b):
        return lambda T: T[f"ll:{a}"][0] / T[f"ll:{a}"][1] - T[f"ll:{b}"][0] / T[f"ll:{b}"][1]

    gm = ("direct", "rule", "stretch", "random", "sum_train", "sum_test", "surface", "resid_inner", "direct_inner",
          "resid_full", "c_perp") + tuple(f"pw:{m}" for m in PW)
    stats = {}
    for part, col in parts:
        stats |= {f"{m}|gain|{part}": S.auc_gain(m, col=col) for m in gm}
        stats |= {f"{m}|level|{part}": S.level(m, col=col) for m in ("verdict",) + gm}
        stats[f"surface_minus_direct|{part}"] = S.auc_gain("surface", base="direct", col=col)
        stats[f"pw_sd_minus_s|{part}"] = S.auc_gain("pw:surface+direct", base="pw:surface", col=col)
        stats[f"pw_sd_minus_d|{part}"] = S.auc_gain("pw:surface+direct", base="pw:direct", col=col)
        stats[f"pw_vd_minus_v|{part}"] = S.auc_gain("pw:verdict+direct", base="pw:verdict", col=col)
        stats[f"pw_vsd_minus_vd|{part}"] = S.auc_gain("pw:verdict+surface+direct", base="pw:verdict+direct", col=col)
        stats[f"sumtrain_minus_sumtest|{part}"] = S.auc_gain("sum_train", base="sum_test", col=col)
    stats |= {f"ll|{m}": ll(m) for m in PW}
    stats |= {"ll|sd_minus_s": ll_diff("surface+direct", "surface"), "ll|sd_minus_d": ll_diff("surface+direct", "direct"),
              "ll|vd_minus_v": ll_diff("verdict+direct", "verdict"),
              "ll|vsd_minus_vd": ll_diff("verdict+surface+direct", "verdict+direct")}
    est, draws = S.boot(pairs, stats)
    for part in ("all", "same", "diff"):
        est[f"resid_inner_kept|{part}"] = S.ratio(draws, f"resid_inner|gain|{part}", f"direct_inner|gain|{part}", est)
        est[f"resid_full_kept|{part}"] = S.ratio(draws, f"resid_full|gain|{part}", f"direct|gain|{part}", est)
    est["rule_over_direct"] = S.ratio(draws, "rule|gain|all", "direct|gain|all", est)
    # the same quantities on the 8 MMLU-Redux / MATH pairs, plus the paired same/different interaction
    st2 = {}
    for part, col in parts:
        st2 |= {f"{m}|gain|{part}": S.auc_gain(m, col=col) for m in ("direct", "rule", "stretch", "surface", "resid_inner",
                                                                     "direct_inner", "c_perp", "sum_train")}
        st2 |= {f"{m}|level|{part}": S.level(m, col=col) for m in ("verdict", "direct", "surface")}
        st2[f"surface_minus_direct|{part}"] = S.auc_gain("surface", base="direct", col=col)
    st2 |= {f"{m}|diff_minus_same": inter(m) for m in ("direct", "rule", "stretch", "surface", "resid_inner", "c_perp")}
    est2, draws2 = S.boot(mm_pairs, st2)
    for part in ("all", "same", "diff"):
        est2[f"resid_inner_kept|{part}"] = S.ratio(draws2, f"resid_inner|gain|{part}", f"direct_inner|gain|{part}", est2)
        est2[f"c_perp_kept|{part}"] = S.ratio(draws2, f"c_perp|gain|{part}", f"direct|gain|{part}", est2)
    # reasoning first (no fitting; the pairs that have a reasoning run), on the questions where every answer has a score
    cot_pairs = {}
    for k in PS:
        j, b = k.split("|")
        cot = D._cot(A.D / f"{j}_{b}" / "cot_main.jsonl")
        if not cot:
            continue
        rows = [dict(r, cot=cot[r["aid"]]) for r in outer_rows(j, b) if r["aid"] in cot]
        Pc = {m: perq(rows, m) for m in ("verdict", "cot")}
        qs = sorted(set(Pc["verdict"]) & set(Pc["cot"]))
        cot_pairs[(j, b)] = {m: (qs, np.array([Pc[m][x] for x in qs])) for m in Pc}
    stc = {f"cot|gain|{part}": S.auc_gain("cot", col=col) for part, col in parts}
    est_cot, _ = S.boot(cot_pairs, stc)
    est_cot["n_pairs"] = len(cot_pairs)
    # per benchmark (4 judges each): authorship projection, surface, residualization
    per_bench = {}
    for bb in ("mmlu", "math", "bbeh"):
        sub = {k: v for k, v in pairs.items() if k[1] == bb}
        st4 = {f"{m}|gain|all": S.auc_gain(m) for m in ("direct", "surface", "resid_inner", "direct_inner", "c_perp", "rule")}
        st4["surface_minus_direct|all"] = S.auc_gain("surface", base="direct")
        st4 = {k: f for k, f in st4.items() if bb != "bbeh" or "c_perp" not in k}
        e4, d4 = S.boot(sub, st4)
        e4["resid_inner_kept|all"] = S.ratio(d4, "resid_inner|gain|all", "direct_inner|gain|all", e4)
        if bb != "bbeh":
            e4["c_perp_kept|all"] = S.ratio(d4, "c_perp|gain|all", "direct|gain|all", e4)
        per_bench[bb] = e4
    # fixed-budget review
    st3 = {}
    for kk in BUDGETS:
        for m in ("verdict", "direct", "rule", "sum_train"):
            st3[f"{m}@{kk}|caught"] = (lambda key: lambda T: 100 * T[key][0] / T[key][1])(f"{m}@{kk}")
            st3[f"{m}@{kk}|precision"] = (lambda key: lambda T: 100 * T[key][0] / T[key][2] if T[key][2] else None)(f"{m}@{kk}")
            if m != "verdict":
                st3[f"{m}@{kk}|caught_gain"] = (lambda a, b: lambda T: 100 * (T[a][0] / T[a][1] - T[b][0] / T[b][1]))(
                    f"{m}@{kk}", f"verdict@{kk}")
    est3, _ = S.boot(review, st3)
    # overlap (descriptive, equal-weight mean of shares over pairs)
    ov = {}
    for key in ("surface|direct", "verdict|direct", "verdict|surface"):
        for part in ("all", "same", "diff"):
            xs = [r["overlap"][key][part] for r in PS.values() if r["overlap"][key][part]["n"] > 0]
            ov[f"{key}|{part}"] = dict(k=len(xs), **{c: float(np.mean([x[c] / x["n"] for x in xs]))
                                                     for c in ("both", "a_only", "b_only", "neither")},
                                       corr=float(np.mean([x["corr"] for x in xs if x["corr"] is not None])))
    # repeated outer splits (direction only): equal-weight mean gain over the 12 pairs, per split
    spl = {}
    for seed in next(iter(PS.values()))["splits"]:
        gains = []
        for k, r in PS.items():
            d = r["splits"][seed]["direct"]
            v = r["perq"]["verdict"]
            qs = sorted(set(d) & set(v))
            gains.append(100 * (sum(d[x][0] for x in qs) / sum(d[x][1] for x in qs) - sum(v[x][0] for x in qs) / sum(v[x][1] for x in qs)))
        spl[seed] = float(np.mean(gains))
    lay = [r["splits"][s]["layers"][f] for r in PS.values() for s in r["splits"] for f in ("a", "b")]
    scales = {k: {f: {x: r["folds"][f][x] for x in ("scale_verdict_train", "scale_direct_train", "scale_verdict_test",
                                                    "scale_direct_test")} for f in r["folds"]} for k, r in PS.items()}
    r2 = [f["r2_inner"] for r in PS.values() for f in r["folds"].values()]
    out = dict(n_pairs=len(pairs), n_pairs_mm=len(mm_pairs), pooled=est, pooled_mm=est2, per_bench=per_bench, cot=est_cot, review=est3, overlap=ov,
               splits=dict(per_seed=spl, lo=min(spl.values()), hi=max(spl.values()), n_layer_choices=len(lay)),
               r2_inner=dict(lo=min(r2), hi=max(r2)), scales=scales,
               verdict_mismatch_questions=mismatch, n_questions={f"{j}|{b}": len(d["verdict"][0]) for (j, b), d in pairs.items()})
    json.dump(out, open(OUT / "primary_scope_check.json", "w"), indent=1)
    show = lambda e: {k: (round(v["g"], 2), round(v["lo"], 2), round(v["hi"], 2)) for k, v in e.items() if v}  # noqa: E731
    print("12 pairs", show(est))
    print("8 MMLU/MATH pairs", show(est2))
    print("review", show(est3))
    print("cot", est_cot)
    for bb, e in per_bench.items():
        print(bb, show(e))
    print("overlap", json.dumps(ov, indent=0)[:1500])
    print("splits", spl)


if __name__ == "__main__":
    main()
