"""Fixed-effect checks for the belief paper (reviewer item B1, Nov 18). CPU only, existing judgments.

Rows: audited wrong-answer judgments of all seven judges, approval = the STATED verdict for every judge
(paper_numbers.load). For four specifications:
  J    judge(-by-benchmark) fixed effects                    pooled linear belief slope
  JQ   judge-by-question fixed effects                       within-question (difficulty) test
  CJ   candidate + judge-by-benchmark fixed effects          same candidate, different judges
  CJQ  candidate + judge-by-question fixed effects           most restrictive
we report (1) the slope from 60 alternating-projection sweeps (the code used for the paper), (2) the exact slope from
a dummy-variable least-squares solve, (3) sweeps needed to converge to 1e-10, (4) rows, groups, identifying groups and
the share of belief variance left after the fixed effects; then question-cluster bootstrap intervals (1,000 draws,
all judges of a question kept together) overall, leaving out one judge family at a time, and per benchmark.
Also checks ids: no duplicated (judge, candidate) rows; candidate ids are shared across families (same text).
Writes validation/fe_checks.json and .md.
"""
import collections
import json
import sys
from pathlib import Path

import numpy as np

V = Path(__file__).resolve().parent
sys.path.insert(0, str(V))
import paper_numbers as P  # noqa: E402

NB = 1000
SPECS = {
    "J": lambda r: [f"{r['bench']}|{r['judge']}"],
    "JQ": lambda r: [f"{r['judge']}|{r['qid']}"],
    "CJ": lambda r: [f"{r['bench']}|{r['item']}", f"{r['bench']}|{r['judge']}"],
    "CJQ": lambda r: [f"{r['bench']}|{r['item']}", f"{r['judge']}|{r['qid']}"],
}


def codes(R, spec):
    keys = [SPECS[spec](r) for r in R]
    return [np.unique([k[i] for k in keys], return_inverse=True)[1] for i in range(len(keys[0]))]


def demean(v, fes, sweeps=None, tol=1e-10, cap=100000):
    v = np.asarray(v, float).copy()
    n = 0
    while True:
        old = v.copy()
        for inv in fes:
            v = v - (np.bincount(inv, v) / np.maximum(np.bincount(inv), 1))[inv]
        n += 1
        if sweeps is not None and n >= sweeps:
            return v, n
        if sweeps is None and (np.abs(v - old).max() < tol or n >= cap):
            return v, n


def slope_iter(R, spec, sweeps=60):
    fes = codes(R, spec)
    y, _ = demean([r["y"] for r in R], fes, sweeps)
    x, _ = demean([r["belief"] for r in R], fes, sweeps)
    return float(x @ y / (x @ x))


def slope_exact(R, spec):
    fes = codes(R, spec)
    cols = [np.eye(inv.max() + 1)[inv] for inv in fes]
    D = np.hstack(cols)
    X = np.column_stack([np.array([r["belief"] for r in R]), D])
    y = np.array([r["y"] for r in R], float)
    return float(np.linalg.lstsq(X, y, rcond=None)[0][0])


def describe(R, spec):
    fes = codes(R, spec)
    x = np.array([r["belief"] for r in R])
    xd, n_conv = demean(x, fes, None)
    yd, n_conv_y = demean([r["y"] for r in R], fes, None)
    last = fes[-1] if spec in ("J", "JQ") else fes[0]
    groups = collections.defaultdict(list)
    for i, g in enumerate(last):
        groups[g].append(i)
    ident = [g for g in groups.values() if len(g) > 1 and np.ptp(x[g]) > 0]
    return dict(rows=len(R), groups=len(groups), identifying_groups=len(ident),
                identifying_questions=len({R[i]["qid"] for g in ident for i in g}),
                residual_belief_var_share=float(xd.var() / x.var()), sweeps_to_converge=int(max(n_conv, n_conv_y)),
                slope_60=slope_iter(R, spec, 60), slope_converged=float(xd @ yd / (xd @ xd)), slope_exact=slope_exact(R, spec))


def boot(R, f, seed=0):
    by = collections.defaultdict(list)
    for r in R:
        by[r["qid"]].append(r)
    qs = list(by)
    rng = np.random.default_rng(seed)
    d = []
    for _ in range(NB):
        smp = [r for i in rng.choice(len(qs), len(qs)) for r in by[qs[i]]]
        try:
            d.append(f(smp))
        except Exception:  # noqa: BLE001
            pass
    return float(f(R)), float(np.nanpercentile(d, 2.5)), float(np.nanpercentile(d, 97.5))


def main():
    R = []
    for fam, od, sfx in P.FAM:
        for r in P.load(od, sfx):
            if not r["ok"] and r["audited"]:
                R.append(dict(r, fam=fam))
    out = {"n": len(R)}
    # id checks
    dup = collections.Counter((r["judge"], r["item"]) for r in R)
    out["duplicate_rows"] = sum(v > 1 for v in dup.values())
    fams_per_item = collections.defaultdict(set)
    for r in R:
        fams_per_item[(r["bench"], r["item"])].add(r["fam"])
    out["candidates"] = len(fams_per_item)
    out["candidates_in_2plus_families"] = sum(len(v) > 1 for v in fams_per_item.values())
    qid_bench = collections.defaultdict(set)
    for r in R:
        qid_bench[r["qid"]].add(r["bench"])
    out["qids_spanning_benchmarks"] = sum(len(v) > 1 for v in qid_bench.values())
    out["describe"] = {s: describe(R, s) for s in SPECS}
    print(json.dumps(out, indent=1), flush=True)
    est = lambda s: (lambda X: slope_iter(X, s, None))  # iterate to convergence (tol 1e-10)
    out["boot"] = {s: boot(R, est(s)) for s in SPECS}
    out["lofo"] = {s: {fam: boot([r for r in R if r["fam"] != fam], est(s)) for fam, _, _ in P.FAM} for s in ("J", "JQ", "CJ")}
    out["per_bench"] = {s: {b: boot([r for r in R if r["bench"] == b], est(s)) for b in ("rb2math", "judgebench", "bff")}
                        for s in ("J", "JQ", "CJ")}
    out["per_family_JQ"] = {fam: boot([r for r in R if r["fam"] == fam], est("JQ")) for fam, _, _ in P.FAM}
    (V / "fe_checks.json").write_text(json.dumps(out, indent=1) + "\n")
    f = lambda t: f"{100 * t[0]:+.1f} [{100 * t[1]:+.1f}, {100 * t[2]:+.1f}]"
    L = ["# Fixed-effect checks (stated verdict, audited wrong answers, all seven judges)\n",
         f"Rows {out['n']}; duplicated (judge, candidate) rows {out['duplicate_rows']}; candidates {out['candidates']} "
         f"({out['candidates_in_2plus_families']} judged by 2+ families); question ids spanning benchmarks {out['qids_spanning_benchmarks']}.\n",
         "| spec | groups | identifying groups (questions) | belief variance left | sweeps to 1e-10 | slope, 60 sweeps | converged | exact | 95% CI (1,000 question draws) |",
         "|---|---|---|---|---|---|---|---|---|"]
    for s, d in out["describe"].items():
        L.append(f"| {s} | {d['groups']} | {d['identifying_groups']} ({d['identifying_questions']}) | {d['residual_belief_var_share']:.2f} | "
                 f"{d['sweeps_to_converge']} | {100 * d['slope_60']:+.2f} | {100 * d['slope_converged']:+.2f} | {100 * d['slope_exact']:+.2f} | {f(out['boot'][s])} |")
    L.append("\n## Leave one family out\n\n| left out | J | JQ | CJ |\n|---|---|---|---|")
    for fam, _, _ in P.FAM:
        L.append(f"| {fam} | {f(out['lofo']['J'][fam])} | {f(out['lofo']['JQ'][fam])} | {f(out['lofo']['CJ'][fam])} |")
    L.append("\n## Per benchmark\n\n| benchmark | J | JQ | CJ |\n|---|---|---|---|")
    for b in ("rb2math", "judgebench", "bff"):
        L.append(f"| {b} | {f(out['per_bench']['J'][b])} | {f(out['per_bench']['JQ'][b])} | {f(out['per_bench']['CJ'][b])} |")
    L.append("\n## Within question (JQ), per family, stated verdict\n")
    L += [f"- {fam}: {f(v)}" for fam, v in out["per_family_JQ"].items()]
    (V / "fe_checks.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
