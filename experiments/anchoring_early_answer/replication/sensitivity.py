"""Parser and label sensitivity of the fresh-question replication (Nov 20 review). CPU only; POST HOC.

Crosses the two letter parsers (strict = pre-registered five-letter string; lenient = added after seeing results)
with three label sets:
  key         MMLU-Pro answer key (pre-registered primary)
  high_audit  key, dropping wrong responses Kimi-K3.1-Pro did not call clearly wrong, where only responses some
              judge believes >= 4/7 under the strict parser were audited (pre-registered analysis 5)
  full_audit  the same drop, with every one of the 1,336 wrong responses audited (audit.jsonl + audit_extra.jsonl)
Labels are per candidate: a dropped response is dropped for every judge.
Also tabulates auditor verdicts by the highest belief any judge has in the response (lenient parser).

  python sensitivity.py      -> sensitivity.json, sensitivity.md
"""
import collections
import json

import numpy as np

import analyze as A

OUT = A.HERE


def audit_maps():
    first = {r["qid"]: r["verdict"] for r in A.load(A.DATA / "audit.jsonl")}
    extra = {r["qid"]: r["verdict"] for r in A.load(A.DATA / "audit_extra.jsonl")}
    return first, {**first, **extra}, {r["qid"]: r["stratum"] for r in A.load(A.DATA / "audit_extra.jsonl")}


def run(lenient, audit, label_drop):
    A.LENIENT = lenient
    R, miss = A.rows(80, 6000, audit)
    if label_drop:
        R = [r for r in R if r["audit"] in (None, "LABEL_OK")] if label_drop == "high" else \
            [r for r in R if r["audit"] == "LABEL_OK"]
    res = A.analyses(R)
    return dict(excluded=dict(miss), **res)


def max_bins(lenient):
    A.LENIENT = lenient
    R, _ = A.rows(80, 6000, None)
    m = {}
    for r in R:
        k = round(7 * r["belief"])
        m[r["qid"]] = max(m.get(r["qid"], -1), k)
    return m


def main():
    first, full, stratum = audit_maps()
    out = {}
    for parser in ("strict", "lenient"):
        len_ = parser == "lenient"
        out[f"{parser}|key"] = run(len_, None, None)
        out[f"{parser}|high_audit"] = run(len_, first, "high")
        out[f"{parser}|full_audit"] = run(len_, full, "full")
    pairs = [p["qid"] for p in A.load(A.DATA / "pairs.jsonl") if 80 <= p["order"] < 6080]
    mb = max_bins(True)
    tab = collections.defaultdict(collections.Counter)
    for q in pairs:
        b = mb.get(q)
        g = "no judge with 5 own answers" if b is None else "0/7" if b == 0 else "1-3" if b <= 3 else "4-6" if b <= 6 else "7/7"
        tab[g][full.get(q)] += 1
    out["audit_by_max_belief_lenient"] = {g: dict(c) for g, c in tab.items()}
    out["audit_coverage"] = dict(responses=len(pairs), audited=sum(q in full for q in pairs),
                                 no_verdict=sum(full.get(q) is None for q in pairs),
                                 extra_strata=dict(collections.Counter(stratum.values())))
    (OUT / "sensitivity.json").write_text(json.dumps(out, indent=1) + "\n")
    f = A.fmt
    L = ["# Replication: parser x label sensitivity (post hoc)\n",
         "| parser | labels | n | 0/7 | 1-3 | 4-6 | 7/7 | gap 7-0 | slope | same candidate | competitor | 8th answer |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, v in out.items():
        if "|" not in k:
            continue
        p, lab = k.split("|")
        st = " | ".join(f"{100 * x:.0f}" for x in v["staircase"])
        L.append(f"| {p} | {lab} | {v['n']} | {st} | {f(v['gap_7_minus_0'])} | {f(v['slope_judgeFE'])} | "
                 f"{f(v['same_candidate'])} | {f(v['target_and_competitor'], 1)} | {f(v['one_sample_vs_belief'], 0)} |")
    L += ["", "Per-judge n and slope:", ""]
    for k, v in out.items():
        if "|" in k:
            L.append(f"- {k}: " + "; ".join(f"{j} n={d['n']} {f(d['slope'])}" for j, d in v["per_judge"].items()))
    L += ["", f"Audit coverage: {out['audit_coverage']}", "",
          "Auditor verdicts by highest belief of any judge (lenient):"]
    for g, c in out["audit_by_max_belief_lenient"].items():
        L.append(f"- {g}: {c}")
    (OUT / "sensitivity.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
