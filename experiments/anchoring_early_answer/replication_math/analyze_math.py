"""Analyses of the math replication, as fixed in PROTOCOL.md (identical to ../replication/analyze.py; only the
answer field differs: integers instead of letters).

  python analyze_math.py --start 80 --n N     -> results_<start>_<n>.json / .md
"""
import argparse
import collections
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
_spec = importlib.util.spec_from_file_location("rep_analyze", HERE.parent / "replication" / "analyze.py")
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)
JUDGES, BINS = A.JUDGES, A.BINS


def rows(start, n, audit=None):
    pairs = {p["qid"]: p for p in A.load(DATA / "pairs.jsonl") if start <= p["order"] < start + n}
    J = {(r["model"], r["qid"]): r for r in A.load(DATA / "judge.jsonl")}
    S = {(r["model"], r["qid"]): r for r in A.load(DATA / "solve.jsonl")}
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
            L = [x for x in sr["answers"][1:] if x is not None]
            if len(L) < 5:
                miss["< 5 own answers parsed"] += 1
                continue
            b = sum(x == p["wrong_answer"] for x in L) / len(L)
            bo = sum(x == p["gold"] for x in L) / len(L)
            out.append(dict(judge=j, qid=qid, item=qid, y=int(jr["verdict"] == p["wrong_pos"]), belief=b, belief_other=bo,
                            b=A.binof(b), match0=int(sr["answers"][0] == p["wrong_answer"]), n_votes=len(L),
                            audit=(audit or {}).get(qid)))
    return out, miss


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, required=True)
    ap.add_argument("--n", type=int, required=True)
    a = ap.parse_args()
    audit = {r["qid"]: r["verdict"] for r in A.load(DATA / "audit.jsonl")}
    R, miss = rows(a.start, a.n, audit)
    out = dict(range=[a.start, a.start + a.n], excluded=dict(miss), all=A.analyses(R))
    qids = {p["qid"] for p in A.load(DATA / "pairs.jsonl") if a.start <= p["order"] < a.start + a.n}
    out["audit_counts"] = dict(collections.Counter(audit.get(q) for q in qids))
    if audit:
        out["audited"] = A.analyses([r for r in R if r["audit"] == "LABEL_OK"])  # every response audited
        mb = {}
        for r in R:
            mb[r["qid"]] = max(mb.get(r["qid"], -1), round(7 * r["belief"]))
        tab = collections.defaultdict(collections.Counter)
        for q in qids:
            b = mb.get(q)
            g = "no judge with 5 answers" if b is None else "0/7" if b == 0 else "1-3" if b <= 3 else "4-6" if b <= 6 else "7/7"
            tab[g][audit.get(q)] += 1
        out["audit_by_max_belief"] = {g: dict(c) for g, c in tab.items()}
    (HERE / f"results_{a.start}_{a.n}.json").write_text(json.dumps(out, indent=1) + "\n")
    f = A.fmt
    L = [f"# Math replication (DAPO-Math, questions {a.start}..{a.start + a.n - 1})\n",
         f"Excluded judgments: {dict(miss)}. Audit verdicts: {out['audit_counts']}\n"]
    for part in [p for p in ("all", "audited") if p in out]:
        X = out[part]
        L += [f"## {'Answer key' if part == 'all' else 'Audit-filtered (all responses audited)'}: {X['n']} judgments, "
              f"{X['questions']} questions\n", "| judge | n | 0/7 | 1-3 | 4-6 | 7/7 | slope (judge FE) |",
              "|---|---|---|---|---|---|---|"]
        for j, d in X["per_judge"].items():
            s = " | ".join(f"{100 * v:.0f} ({d['bin_counts'][b]})" if v == v else f"- ({d['bin_counts'][b]})"
                           for v, b in zip(d["staircase"], BINS))
            L.append(f"| {j} | {d['n']} | {s} | {f(d['slope'])} |")
        s = " | ".join(f"{100 * v:.0f} ({X['bin_counts'][b]})" if v == v else "-" for v, b in zip(X["staircase"], BINS))
        L += [f"| pooled | {X['n']} | {s} | {f(X['slope_judgeFE'])} |", "",
              f"- 7/7 minus 0/7: {f(X['gap_7_minus_0'])}", f"- same candidate: {f(X['same_candidate'])}",
              f"- target {f(X['target_and_competitor'], 0)}, competitor {f(X['target_and_competitor'], 1)}",
              f"- one-sample label {f(X['one_sample_vs_belief'], 0)}, belief {f(X['one_sample_vs_belief'], 1)}", ""]
    if "audit_by_max_belief" in out:
        L += ["Auditor verdicts by highest belief:"] + [f"- {g}: {c}" for g, c in out["audit_by_max_belief"].items()]
    (HERE / f"results_{a.start}_{a.n}.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
