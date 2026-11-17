"""Baseline: read the correctness direction directly instead of stretching it into the verdict.

Per pair (same answers, same cross-fit direction, same layer the rule chose): ranking of
  says      the unedited verdict score
  stretch   the verdict score after stretching x11 (x4 / x21 also reported as best-of)
  direct    the answer's position along the direction (direct_readout_modal.py), at the chosen layer and the best layer
  sum       verdict score + direction position, each scaled by its within-question sd (no tuning)
on all pairs / not solved / same-model pairs (all, and not solved). Ranking = within-question AUROC x100;
differences with 95% intervals from 1000 paired resamples of questions.

  python3 experiments/beyond_capability/direct_vs_stretch.py -> out_allpairs/direct_vs_stretch.md, .json
"""
import json
from collections import defaultdict

import numpy as np

import allpairs_analyze as A

J11, J4, J21 = A.J11, A.J4, A.J21


def counts(rows, score, same_src=False):
    by = defaultdict(lambda: ([], []))
    for r in rows:
        by[(r["qid"], r["src"] if same_src else "")][r["gold"]].append(score(r))
    out = defaultdict(lambda: np.zeros(2))
    for (q, _), (neg, pos) in by.items():
        if pos and neg:
            a, b = np.array(pos)[:, None], np.array(neg)[None, :]
            out[q] += [(a > b).sum() + 0.5 * (a == b).sum(), a.size * b.size]
    return out


def compare(rows, scores, same_src=False, n=1000):
    """rankings x100 for each named score, and paired-bootstrap intervals for each minus 'stretch'."""
    C = {k: counts(rows, f, same_src) for k, f in scores.items()}
    qs = sorted(C["says"])
    if len(qs) < 5:
        return None
    M = {k: np.array([C[k][q] for q in qs]) for k in C}
    auc = lambda k, i: 100 * M[k][i, 0].sum() / M[k][i, 1].sum()  # noqa: E731
    rng = np.random.default_rng(0)
    idx = [rng.integers(0, len(qs), len(qs)) for _ in range(n)]
    res = {"nq": len(qs), **{k: float(auc(k, slice(None))) for k in M}}
    for base in ("stretch", "says"):
        for k in M:
            if k == base:
                continue
            d = [auc(k, i) - auc(base, i) for i in idx]
            res[f"{k}-{base}"] = dict(g=res[k] - res[base], lo=float(np.percentile(d, 2.5)), hi=float(np.percentile(d, 97.5)))
    return res


def main():
    R = json.load(open(A.D / "allpairs.json"))
    out, L = {}, []
    for k, o in R.items():
        if k.startswith("extra") or "layer" not in o:
            continue
        j, b = k.split("|")
        choice, final = A.load_pair(j, b)
        sweep = (j, b) in (("llama3.1-8b", "math"), ("llama3.2-3b", "mmlu"))
        f = (A.HERE / ("out_math/layer_sweep" if b == "math" else "out_mmlu/layer_sweep_llama3.2-3b") if sweep
             else A.D / f"{j}_{b}") / f"direct_{b}.json"
        P = json.load(open(f))
        Lc, Lb = str(o["layer"]), str(o["best_knows_layer"])
        if Lb not in P:
            Lb = Lc
        if sweep:  # load_pair drops the answer id for sweep pairs; rebuild the chosen layer's rows with it
            by = defaultdict(dict)
            for fs in sorted(f.parent.glob(f"sweep_{b}_L*.jsonl")):
                for l in open(fs):
                    r = json.loads(l)
                    if r["layer"] == o["layer"]:
                        m = r["margins"]
                        by[r["aid"]].update({"none": m["none"]} | {f"{r['dir']}:{x}": v for x, v in m.items() if x != "none"})
                        by[r["aid"]]["_m"] = dict(aid=r["aid"], qid=r["qid"], gold=r["gold"], src=r["src"])
            final = [dict(v.pop("_m"), margins=v) for v in by.values()]
        rows = [dict(r, pc=P[Lc][r["aid"]], pb=P[Lb][r["aid"]]) for r in final if r["aid"] in P[Lc]]
        # within-question sd of each score, for the untuned sum
        def wsd(key):
            byq = defaultdict(list)
            for r in rows:
                byq[r["qid"]].append(key(r))
            return np.sqrt(np.mean([np.var(v) for v in byq.values() if len(v) > 1]))
        sv, sp = wsd(lambda r: r["margins"]["none"]), wsd(lambda r: r["pc"])
        best = max(("x4", "x11", "x21"), key=lambda t: (o.get(f"all | {t}") or {"g": -99})["g"])
        bkey = {"x4": J4, "x11": J11, "x21": J21}[best]
        scores = {"says": lambda r: r["margins"]["none"], "stretch": lambda r: r["margins"][J11],
                  "stretch_best": lambda r: r["margins"][bkey],
                  "direct": lambda r: r["pc"], "direct_best_layer": lambda r: r["pb"],
                  "sum": lambda r: r["margins"]["none"] / sv + r["pc"] / sp}
        sol = A.labels(j, b)
        groups = {"all": (rows, False), "not solved": ([r for r in rows if sol.get(r["qid"]) == 0], False),
                  "same-model": (rows, True), "same-model, not solved": ([r for r in rows if sol.get(r["qid"]) == 0], True)}
        res = {g: compare(R_, scores, ss) for g, (R_, ss) in groups.items()}
        res.update(layer=int(Lc), best_layer=int(Lb), best_strength=best, n=len(rows), n_final=len(final),
                   status=o["status"], knows_at_layer=o.get("knows_at_layer"))
        out[k] = res
    json.dump(out, open(A.D / "direct_vs_stretch.json", "w"), indent=1)

    def c(x, key):
        return "–" if not x else f"{x[key]:.1f}"

    def d(x, key):
        if not x or key not in x:
            return "–"
        v = x[key]
        s = f"{v['g']:+.1f} [{v['lo']:+.1f}, {v['hi']:+.1f}]"
        return f"**{s}**" if v["lo"] > 0 or v["hi"] < 0 else s
    L += ["# Reading the direction directly vs stretching it into the verdict", "",
          "Ranking ×100 (50 = coin flip). Says = unedited verdict; Stretch = verdict after ×11 at the rule's layer; "
          "Direct = position along the same direction at the same layer; Sum = verdict + direction, each divided by its "
          "within-question spread. Differences are vs Stretch, 95% interval from resampling questions (bold = excludes 0).", ""]
    for g in ("all", "not solved", "same-model", "same-model, not solved"):
        L += [f"## {g}", "", "| Pair | Layer | Questions | Says | Stretch ×11 | Direct | Direct − Stretch | Direct, best layer | Sum − Stretch |",
              "|---|---|---|---|---|---|---|---|---|"]
        for k, r in out.items():
            x = r[g]
            j, b = k.split("|")
            L.append(f"| {A.NAME[j]}, {A.BNAME[b]} | {r['layer']}{'' if r['status'] == 'responds' else '*'} | "
                     f"{x['nq'] if x else '–'} | {c(x, 'says')} | {c(x, 'stretch')} | {c(x, 'direct')} | {d(x, 'direct-stretch')} | "
                     f"{c(x, 'direct_best_layer')} | {d(x, 'sum-stretch')} |")
        P = [r[g] for r in out.values() if r[g]]
        pd = A.pooled([p["direct-stretch"] for p in P])
        ps = A.pooled([p["sum-stretch"] for p in P])
        L += [f"| **Pooled** ({len(P)} pairs) | | | | | | {A.fmt(pd)} | | {A.fmt(ps)} |", ""]
    (A.D / "direct_vs_stretch.md").write_text("\n".join(L))
    print("\n".join(L))


def same_model_sets():
    """The dedicated same-model test sets (extra_<bench>.jsonl) with their direction positions (xdirect_<bench>.jsonl,
    from pair_pipeline.py --phase extra_direct). Every pair compares a right and a wrong answer by the same model."""
    sets = []
    for f in sorted(A.D.glob("*/extra_*.jsonl")):
        judge, bench = f.parent.name.rsplit("_", 1)
        xf = f.parent / f"xdirect_{bench}.jsonl"
        if not xf.exists():
            continue
        X = {r["aid"]: r for r in map(json.loads, open(xf))}
        R0 = [dict(r, pc=X[r["aid"]]["proj"], m2=X[r["aid"]]["margin"]) for r in map(json.loads, open(f)) if r["aid"] in X]
        agree = float(np.mean([abs(r["m2"] - r["margins"]["none"]) <= 0.5 for r in R0]))
        name = "all questions" if bench == "bbeh" else "8B's unsolved"
        sub = R0
        if judge != "llama3.1-8b" or bench == "bbeh":
            own = A.labels(judge, bench)
            if own:
                name, sub = "own unsolved", [r for r in R0 if own.get(r["qid"]) == 0]
        elif bench in ("mmlu", "math"):
            name = "own unsolved"
        sets.append((judge, bench, name, sub, agree, len(R0), len(X)))
    g8f = A.OUT / "egrades_sm_math_q8.jsonl"
    mf = A.D / "llama3.1-8b_math" / "extra_math.jsonl"
    xf = A.D / "llama3.1-8b_math" / "xdirect_math.jsonl"
    if g8f.exists() and xf.exists():  # strict: failed all 9 of its own tries
        k8 = defaultdict(list)
        for r in A.jl(g8f):
            if r["verdict"] is not None:
                k8[r["cache_key"].split("|")[1].split("#")[0]].append(int(r["verdict"]))
        X = {r["aid"]: r for r in map(json.loads, open(xf))}
        S = [dict(r, pc=X[r["aid"]]["proj"]) for r in map(json.loads, open(mf))
             if r["aid"] in X and r["qid"] in k8 and len(k8[r["qid"]]) >= 6 and sum(k8[r["qid"]]) == 0]
        sets.append(("llama3.1-8b", "math", "failed 9 of 9 own tries", S, None, None, None))
    out, L = {}, []
    for judge, bench, name, rows, agree, n0, nx in sets:
        def wsd(key):
            byq = defaultdict(list)
            for r in rows:
                byq[(r["qid"], r["src"])].append(key(r))
            return np.sqrt(np.mean([np.var(v) for v in byq.values() if len(v) > 1]))
        sv, sp = wsd(lambda r: r["margins"]["none"]), wsd(lambda r: r["pc"])
        scores = {"says": lambda r: r["margins"]["none"], "stretch": lambda r: r["margins"][J11],
                  "stretch_x4": lambda r: r["margins"][J4], "direct": lambda r: r["pc"],
                  "sum": lambda r: r["margins"]["none"] / sv + r["pc"] / sp}
        res = compare(rows, scores, same_src=True)
        if res:
            out[f"{judge}|{bench}|{name}"] = dict(res, margin_agree=agree, n_rows=n0, n_xdirect=nx)
    return out


def write_same_model(out):
    def d(x, key):
        v = x[key]
        s = f"{v['g']:+.1f} [{v['lo']:+.1f}, {v['hi']:+.1f}]"
        return f"**{s}**" if v["lo"] > 0 or v["hi"] < 0 else s
    L = ["", "## Same-model test sets (many right and wrong answers per model; questions the judge can't solve)", "",
         "Same columns as above, on the dedicated same-model sets of section 4 of the report (×4 shown because small "
         "judges do best there).", "",
         "| Judge, benchmark (questions) | Questions | Says | Stretch ×4 | Stretch ×11 | Direct | Stretch ×11 − Says | Direct − Says | Sum − Says | Direct − Stretch ×11 | Sum − Stretch ×11 |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    order = sorted(out, key=lambda k: ({"math": 0, "bbeh": 1, "mmlu": 2}[k.split("|")[1]], k))
    for k in order:
        x = out[k]
        j, b, nm = k.split("|")
        L.append(f"| {A.NAME[j]}, {A.BNAME[b]} ({nm}) | {x['nq']} | {x['says']:.1f} | {x['stretch_x4']:.1f} | "
                 f"{x['stretch']:.1f} | {x['direct']:.1f} | {d(x, 'stretch-says')} | {d(x, 'direct-says')} | {d(x, 'sum-says')} | "
                 f"{d(x, 'direct-stretch')} | {d(x, 'sum-stretch')} |")
    for b in ("math", "bbeh", "mmlu"):
        P = [out[k] for k in out if k.split("|")[1] == b and "9 of 9" not in k]
        if P:
            pf = lambda key: A.fmt(A.pooled([p[key] for p in P]))  # noqa: E731
            L.append(f"| **Pooled, {A.BNAME[b]}** ({len(P)} judges) | | | | | | {pf('stretch-says')} | {pf('direct-says')} | "
                     f"{pf('sum-says')} | {pf('direct-stretch')} | {pf('sum-stretch')} |")
    ag = [x["margin_agree"] for x in out.values() if x["margin_agree"] is not None]
    L += ["", f"Check: the readout pass reproduces the stretch run's unedited verdict score within 0.5 for "
              f"{100 * min(ag):.0f}–{100 * max(ag):.0f}% of answers per set."]
    return "\n".join(L)


if __name__ == "__main__":
    main()
    sm = same_model_sets()
    json.dump(sm, open(A.D / "direct_vs_stretch_same_model.json", "w"), indent=1)
    txt = write_same_model(sm)
    with open(A.D / "direct_vs_stretch.md", "a") as fh:
        fh.write(txt + "\n")
    print(txt)
