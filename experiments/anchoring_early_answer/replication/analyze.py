"""Confirmatory analyses of the fresh-question replication, exactly as fixed in PROTOCOL.md (written before data).

  python analyze.py --start 80 --n N      (the confirmatory range; the pilot 0..79 is reported separately)
Writes results_<start>_<n>.json and .md next to this file.
"""
import argparse
import collections
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
JUDGES = ["qwen3.6-35b-a3b", "qwen3.5-9b", "deepseek-v4.1-flash", "kimi-k2.6"]
BINS = ["0/7", "1-3", "4-6", "7/7"]
NB = 2000


def load(p):
    return [json.loads(l) for l in open(p)] if p.exists() else []


def lenient_letter(t):
    """POST HOC (after the confirmatory results were seen): many own answers write the letter spaced, repeated the
    wrong number of times, bolded, boxed, as "the answer is (X)", or alone on the last line. Used only for the
    labelled sensitivity analysis (--lenient), never for the confirmatory results."""
    import re
    if not t or not t.strip():
        return None
    x = re.findall(r"\b([A-J])\1{4}\b", t)
    if x:
        return x[-1]
    tail = t.strip()[-400:]
    for pat in [r"(?<![A-Za-z])([A-J])(?:[\s,\.\*]*\1){2,}(?![A-Za-z])", r"\\boxed\{\s*\(?([A-J])\)?\s*\}",
                r"answer is[:\s]*\**\s*\(?([A-J])\)?(?![A-Za-z])", r"\*\*\(?([A-J])\)?\*\*", r"\n\s*\(?([A-J])\)?\s*$"]:
        m = re.findall(pat, tail)
        if m:
            return m[-1]
    return None


LENIENT = False


def binof(b):
    k = round(7 * b)
    return "0/7" if k == 0 else "1-3" if k <= 3 else "4-6" if k <= 6 else "7/7"


def demean(v, fes, tol=1e-10, cap=20000):
    v = np.asarray(v, float).copy()
    for _ in range(cap):
        old = v.copy()
        for inv in fes:
            v = v - (np.bincount(inv, v) / np.maximum(np.bincount(inv), 1))[inv]
        if np.abs(v - old).max() < tol:
            break
    return v


def ols(R, xcols, fe):
    fes = [np.unique([f(r) for r in R], return_inverse=True)[1] for f in fe]
    y = demean([r["y"] for r in R], fes)
    X = np.column_stack([demean([r[c] for r in R], fes) for c in xcols])
    return np.linalg.lstsq(X, y, rcond=None)[0]


def boot(R, f, seed=0):
    by = collections.defaultdict(list)
    for r in R:
        by[r["qid"]].append(r)
    qs = list(by)
    rng = np.random.default_rng(seed)
    est = np.atleast_1d(f(R))
    d = []
    for _ in range(NB):
        smp = [r for i in rng.choice(len(qs), len(qs)) for r in by[qs[i]]]
        try:
            d.append(np.atleast_1d(f(smp)))
        except Exception:  # noqa: BLE001
            pass
    lo, hi = np.nanpercentile(np.array(d), [2.5, 97.5], axis=0)
    return est.tolist(), lo.tolist(), hi.tolist()


def stair(R):
    return [float(np.mean([r["y"] for r in R if r["b"] == b])) if any(r["b"] == b for r in R) else float("nan") for b in BINS]


def rows(start, n, audit=None):
    pairs = {p["qid"]: p for p in load(DATA / "pairs.jsonl") if start <= p["order"] < start + n}
    J = {(r["model"], r["qid"]): r for r in load(DATA / "judge.jsonl")}
    S = {(r["model"], r["qid"]): r for r in load(DATA / "solve.jsonl")}
    out, miss = [], collections.Counter()
    for qid, p in pairs.items():
        for j in JUDGES:
            jr, sr = J.get((j, qid)), S.get((j, qid))
            if not jr or not sr:
                miss["not run"] += 1
                continue
            if jr["verdict"] is None:
                miss["verdict unparsed"] += 1
                continue
            letters = [lenient_letter(t) for t in sr["texts"]] if LENIENT else sr["letters"]
            L = [x for x in letters[1:] if x]
            if len(L) < 5:
                miss["< 5 own answers with a letter"] += 1
                continue
            b = sum(x == p["wrong_letter"] for x in L) / len(L)
            bo = sum(x == p["gold"] for x in L) / len(L)
            out.append(dict(judge=j, qid=qid, item=qid, y=int(jr["verdict"] == p["wrong_pos"]), belief=b, belief_other=bo,
                            b=binof(b), match0=int(letters[0] == p["wrong_letter"]), n_votes=len(L),
                            audit=(audit or {}).get(qid)))
    return out, miss


def analyses(R):
    JFE = [lambda r: r["judge"]]
    res = dict(n=len(R), questions=len({r["qid"] for r in R}), approval=float(np.mean([r["y"] for r in R])),
               bin_counts={b: sum(r["b"] == b for r in R) for b in BINS}, staircase=stair(R))
    res["slope_judgeFE"] = boot(R, lambda X: ols(X, ["belief"], JFE))
    res["gap_7_minus_0"] = boot(R, lambda X: stair(X)[3] - stair(X)[0])
    res["per_judge"] = {j: dict(n=sum(r["judge"] == j for r in R), staircase=stair([r for r in R if r["judge"] == j]),
                                bin_counts={b: sum(r["judge"] == j and r["b"] == b for r in R) for b in BINS},
                                slope=boot([r for r in R if r["judge"] == j], lambda X: ols(X, ["belief"], JFE)))
                        for j in JUDGES}
    res["same_candidate"] = boot(R, lambda X: ols(X, ["belief"], [lambda r: r["item"], lambda r: r["judge"]]))
    res["target_and_competitor"] = boot(R, lambda X: ols(X, ["belief", "belief_other"], JFE))
    res["one_sample_vs_belief"] = boot(R, lambda X: ols(X, ["match0", "belief"], JFE))
    return res


def fmt(t, i=0):
    return f"{100 * t[0][i]:+.1f} [{100 * t[1][i]:+.1f}, {100 * t[2][i]:+.1f}]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--lenient", action="store_true", help="post-hoc sensitivity: lenient letter parsing")
    a = ap.parse_args()
    global LENIENT
    LENIENT = a.lenient
    tag = "_lenient" if a.lenient else ""
    audit = {r["qid"]: r["verdict"] for r in load(DATA / "audit.jsonl")}
    R, miss = rows(a.start, a.n, audit)
    out = dict(range=[a.start, a.start + a.n], excluded=dict(miss), all=analyses(R))
    # 5. label sensitivity: drop wrong responses the auditor does not call clearly wrong (only believed >= 4/7 were audited)
    keep = [r for r in R if r["audit"] in (None, "LABEL_OK")]
    out["audit_counts"] = dict(collections.Counter(audit.get(q) for q in {r["qid"] for r in R} if q in audit))
    out["audited"] = analyses(keep)
    (HERE / f"results_{a.start}_{a.n}{tag}.json").write_text(json.dumps(out, indent=1) + "\n")
    L = [f"# Fresh-question replication (MMLU-Pro, questions {a.start}..{a.start + a.n - 1})"
         + (" -- POST-HOC LENIENT LETTER PARSING (sensitivity only)" if a.lenient else "") + "\n",
         f"Excluded judgments: {dict(miss)}. Audit verdicts on wrong responses believed >= 4/7: {out['audit_counts']}\n"]
    for part in ("all", "audited"):
        A = out[part]
        L += [f"## {'All pairs (MMLU-Pro key)' if part == 'all' else 'Audit-filtered'}: {A['n']} judgments, {A['questions']} questions\n",
              "| judge | n | 0/7 | 1-3 | 4-6 | 7/7 | linear slope (judge FE) |", "|---|---|---|---|---|---|---|"]
        for j, d in A["per_judge"].items():
            s = " | ".join(f"{100 * v:.0f} ({d['bin_counts'][b]})" if v == v else f"- ({d['bin_counts'][b]})"
                           for v, b in zip(d["staircase"], BINS))
            L.append(f"| {j} | {d['n']} | {s} | {fmt(d['slope'])} |")
        s = " | ".join(f"{100 * v:.0f} ({A['bin_counts'][b]})" if v == v else "-" for v, b in zip(A["staircase"], BINS))
        L.append(f"| pooled | {A['n']} | {s} | {fmt(A['slope_judgeFE'])} |")
        L += ["", f"- 7/7 minus 0/7 (pooled): {fmt(A['gap_7_minus_0'])}",
              f"- same candidate across judges (candidate + judge FE): {fmt(A['same_candidate'])}",
              f"- target belief {fmt(A['target_and_competitor'], 0)}, competitor belief {fmt(A['target_and_competitor'], 1)} (judge FE)",
              f"- one-sample label {fmt(A['one_sample_vs_belief'], 0)}, belief {fmt(A['one_sample_vs_belief'], 1)} (judge FE)", ""]
    (HERE / f"results_{a.start}_{a.n}{tag}.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
