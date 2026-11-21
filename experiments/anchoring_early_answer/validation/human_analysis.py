"""Analysis of the HUMAN label check (Nov 21 strict review, item B1), ready before any labels exist. CPU only.

Inputs: one of the three blinded packages and the readers' labels. Labels come either from the annotation page's
database (export with ArtifactData action "list", collection "labels", out_dir=<dir>: one JSON file per label) or
from a JSONL file with one {"n", "label", "annotator"} object per line (the original-study package has no page).
Label values: clearly_wrong | actually_correct | ambiguous. No model output may be entered as a human label.

Consensus per item: the first two readers (not adjudicators) if they agree; otherwise the adjudicator's label
(--adjudicators); otherwise "unresolved" (reported, never imputed).

Reports, per package:
  1. Reader agreement on items both readers labelled (raw and Cohen's kappa).
  2. Human consensus x model auditor table per belief stratum (auditor LABEL_OK = clearly wrong, LABEL_WRONG =
     actually correct, CONTESTED = ambiguous).
  3. Human dispute rate (actually correct or ambiguous) per stratum, and population estimates weighted by stratum
     size (key.json); 95% intervals resample items within strata (2,000 draws). The auditor's rate on the same items
     is shown beside it. The enriched sample is never used unweighted for a population rate.
  4. Replications only: the pre-specified slope / observed rates with every SAMPLED response relabelled by the human
     consensus (unsampled responses keep the complete audit's label); responses humans call actually correct,
     ambiguous or unresolved are dropped, as the audit-filtered analysis drops non-clearly-wrong ones.

  python validation/human_analysis.py --package math --labels <dir or .jsonl> [--adjudicators id1,id2]
  python validation/human_analysis.py --package math --simulate     (plumbing test on SYNTHETIC labels; writes to
                                                                       the scratch dir given by --out only)
"""
import argparse
import collections
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

V = Path(__file__).resolve().parent
HERE = V.parent
PKG = {"math": HERE / "replication_math" / "human_package", "mmlupro": HERE / "replication" / "human_package",
       "original": V / "human_package"}
AUD = {"LABEL_OK": "clearly_wrong", "LABEL_WRONG": "actually_correct", "CONTESTED": "ambiguous"}
VALS = ["clearly_wrong", "actually_correct", "ambiguous"]
NB = 2000


def _mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    spec.loader.exec_module(m)
    return m


def key_items(pkg):
    k = json.load(open(PKG[pkg] / "key.json"))
    items = {}
    for it in k["items"]:
        if pkg == "original":  # A: high-belief reclassifications, B: auditor disagreements, C: stratified retained
            grp = it["reason"].split("|")[0]
            stratum = it["reason"].split("|", 1)[1] if grp == "C" else {"A": "A reclassified", "B": "B disagree"}[grp]
            items[it["n"]] = dict(id=it["item"], stratum=stratum, auditor=AUD.get(it["glm"]), weighted=grp == "C")
        else:
            items[it["n"]] = dict(id=it["qid"], stratum=it["stratum"], auditor=AUD.get(it["auditor"]), weighted=True)
    if pkg == "original":
        pop = {s: v["population"] for s, v in k["strata"].items()}
        smp = {s: v["sampled"] for s, v in k["strata"].items()}
    else:
        pop, smp = k["population"], k["sampled"]
    return items, pop, smp


def read_labels(path):
    p = Path(path)
    if p.is_dir():
        L = [json.load(open(f)) for f in sorted(p.rglob("*.json"))]
        L = [x.get("data", x) for x in L]  # an export may wrap the fields
    else:
        L = [json.loads(l) for l in open(p) if l.strip()]
    bad = [x for x in L if x.get("label") not in VALS]
    if bad:
        raise SystemExit(f"{len(bad)} labels with unknown values, e.g. {bad[0]}")
    return L


def consensus(labels, adjudicators):
    by = collections.defaultdict(dict)
    for x in sorted(labels, key=lambda x: x.get("saved_at", "")):
        by[int(x["n"])][x["annotator"]] = x["label"]  # a reader's latest label wins
    out, pairs = {}, []
    for n, d in by.items():
        readers = [a for a in d if a not in adjudicators]
        adj = [d[a] for a in d if a in adjudicators]
        if len(readers) >= 2:
            a, b = d[readers[0]], d[readers[1]]
            pairs.append((a, b))
            out[n] = a if a == b else (adj[0] if adj else "unresolved")
        elif len(readers) == 1:
            out[n] = "single reader"  # not yet double-read: reported, not used
    return out, pairs


def kappa(pairs):
    if not pairs:
        return float("nan"), float("nan")
    a, b = zip(*pairs)
    po = np.mean([x == y for x, y in pairs])
    pe = sum(np.mean([x == v for x in a]) * np.mean([y == v for y in b]) for v in VALS)
    return float(po), float((po - pe) / (1 - pe)) if pe < 1 else float("nan")


def weighted_rates(items, cons, pop, smp, seed=0):
    """Dispute rate per stratum (human and auditor, same items) and the population-weighted estimate."""
    S = collections.defaultdict(list)
    for n, it in items.items():
        if it["weighted"] and cons.get(n) in VALS:
            S[it["stratum"]].append((int(cons[n] != "clearly_wrong"), int(it["auditor"] != "clearly_wrong")))
    def est(D):
        w = {s: pop[s] for s in D if D[s]}
        tot = sum(w.values())
        return np.array([sum(w[s] * np.mean([x[k] for x in D[s]]) for s in w) / tot for k in (0, 1)])
    rng = np.random.default_rng(seed)
    e = est(S)
    B = np.array([est({s: [v[i] for i in rng.integers(0, len(v), len(v))] for s, v in S.items()}) for _ in range(NB)])
    lo, hi = np.percentile(B, [2.5, 97.5], axis=0)
    per = {s: dict(n=len(v), population=pop[s], sampled=smp.get(s), human=float(np.mean([x[0] for x in v])),
                   auditor=float(np.mean([x[1] for x in v]))) for s, v in sorted(S.items())}
    return per, dict(human=float(e[0]), human_ci=[float(lo[0]), float(hi[0])], auditor=float(e[1]),
                     auditor_ci=[float(lo[1]), float(hi[1])], strata_with_labels=len(S), strata=len(pop))


def relabelled(pkg, items, cons):
    """Replications: the confirmatory analysis with sampled responses relabelled by humans."""
    if pkg == "math":
        M = _mod("math_analyze", HERE / "replication_math" / "analyze_math.py")
        A = M.A
        audit = {r["qid"]: r["verdict"] for r in A.load(M.DATA / "audit.jsonl")}
        R, _ = M.rows(80, 1800, audit)
    else:
        A = _mod("rep_analyze", HERE / "replication" / "analyze.py")
        A.LENIENT = True
        audit = {r["qid"]: r["verdict"] for f in ("audit.jsonl", "audit_extra.jsonl") for r in A.load(A.DATA / f)}
        R, _ = A.rows(80, 6000, audit)
    hum = {items[n]["id"]: c for n, c in cons.items() if n in items}
    keep, changed = [], set()
    for r in R:
        lab = hum.get(r["qid"])
        if lab is not None:
            if (lab == "clearly_wrong") != (r["audit"] == "LABEL_OK"):
                changed.add(r["qid"])
            if lab == "clearly_wrong":
                keep.append(r)
        elif r["audit"] == "LABEL_OK":
            keep.append(r)
    e, lo, hi = A.boot(keep, lambda X: A.ols(X, ["belief"], [lambda r: r["judge"]]))
    rates = {b: (len(S), float(np.mean([r["y"] for r in S])) if S else None)
             for b in A.BINS for S in [[r for r in keep if r["b"] == b]]}
    return dict(judgments=len(keep), responses_relabelled=len(changed), slope=float(e[0]), lo=float(lo[0]),
                hi=float(hi[0]), rates=rates)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", choices=list(PKG), required=True)
    ap.add_argument("--labels")
    ap.add_argument("--adjudicators", default="")
    ap.add_argument("--simulate", action="store_true", help="SYNTHETIC labels to test the code; never a result")
    ap.add_argument("--out", default=None, help="output directory (default: the package folder)")
    a = ap.parse_args()
    items, pop, smp = key_items(a.package)
    adj = set(filter(None, a.adjudicators.split(",")))
    if a.simulate:  # two synthetic readers copy the auditor, the second flips every 7th item; synthetic adjudicator
        rng = np.random.default_rng(0)
        labels = []
        for n, it in items.items():
            labels.append(dict(n=n, annotator="SIM_reader1", label=it["auditor"] or "ambiguous"))
            labels.append(dict(n=n, annotator="SIM_reader2",
                               label=VALS[rng.integers(3)] if n % 7 == 0 else (it["auditor"] or "ambiguous")))
            if n % 7 == 0:
                labels.append(dict(n=n, annotator="SIM_adjudicator", label=it["auditor"] or "ambiguous"))
        adj = {"SIM_adjudicator"}
        if not a.out:
            raise SystemExit("--simulate needs --out (a scratch directory): synthetic output must not sit in the repo")
    else:
        labels = read_labels(a.labels)
    cons, pairs = consensus(labels, adj)
    po, k = kappa(pairs)
    conf = collections.defaultdict(collections.Counter)
    for n, c in cons.items():
        conf[items[n]["stratum"]][(c, items[n]["auditor"])] += 1
    per, overall = weighted_rates(items, cons, pop, smp)
    out = dict(package=a.package, synthetic=a.simulate, items=len(items), labels=len(labels),
               items_with_consensus=sum(c in VALS for c in cons.values()),
               unresolved=sum(c == "unresolved" for c in cons.values()),
               single_reader=sum(c == "single reader" for c in cons.values()), reader_agreement=po, kappa=k,
               confusion={s: {f"{h} | auditor {au}": v for (h, au), v in c.items()} for s, c in sorted(conf.items())},
               dispute_by_stratum=per, population_estimate=overall)
    if a.package != "original" and out["items_with_consensus"]:
        out["relabelled_analysis"] = relabelled(a.package, items, cons)
    dst = Path(a.out) if a.out else PKG[a.package]
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "human_results.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    tag = " (SYNTHETIC LABELS: plumbing test, not a result)" if a.simulate else ""
    L = [f"# Human label check: {a.package}{tag}\n",
         f"{out['labels']} labels on {len(items)} items; consensus on {out['items_with_consensus']}, unresolved "
         f"{out['unresolved']}, single reader {out['single_reader']}. Reader agreement {po:.2f}, kappa {k:.2f} "
         f"({len(pairs)} double-read items).\n", "## Human consensus x auditor, per stratum\n"]
    for s, c in out["confusion"].items():
        L.append(f"- {s}: " + "; ".join(f"{h}: {v}" for h, v in sorted(c.items())))
    L += ["", "## Dispute rate (actually correct or ambiguous), human vs auditor on the same items\n",
          "| stratum | labelled | population | human | auditor |", "|---|---|---|---|---|"]
    for s, d in per.items():
        L.append(f"| {s} | {d['n']} | {d['population']} | {100 * d['human']:.0f}% | {100 * d['auditor']:.0f}% |")
    o = overall
    L += ["", f"Population estimate (weighted by stratum size; {o['strata_with_labels']} of {o['strata']} strata "
              f"labelled): human {100 * o['human']:.1f}% [{100 * o['human_ci'][0]:.1f}, {100 * o['human_ci'][1]:.1f}], "
              f"auditor {100 * o['auditor']:.1f}% [{100 * o['auditor_ci'][0]:.1f}, {100 * o['auditor_ci'][1]:.1f}]."]
    if "relabelled_analysis" in out:
        r = out["relabelled_analysis"]
        L += ["", f"## Confirmatory analysis with human labels on the sampled responses\n",
              f"{r['judgments']} judgments ({r['responses_relabelled']} responses change label): slope "
              f"{100 * r['slope']:+.0f} [{100 * r['lo']:+.0f}, {100 * r['hi']:+.0f}]; rates by bin " +
              ", ".join(f"{b} {100 * v:.0f}% (n={n})" for b, (n, v) in r["rates"].items() if v is not None)]
    (dst / "human_results.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
