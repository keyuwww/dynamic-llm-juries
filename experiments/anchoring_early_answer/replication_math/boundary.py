"""Math replication as a boundary result (Nov 21 strict review, item B3). CPU only; POST HOC.

Reports what the audited data directly show, without the slope's extrapolation to an unsupported 7/7 endpoint:
  - approval rate per belief bin with judgment, unique-candidate and unique-question counts and 95% intervals
    (question-cluster bootstrap, 2,000 draws), under the answer key and under audited labels
  - binary contrast: any own answer matching the candidate (belief > 0) vs none, pooled with judge fixed effects
    (linear probability model) and as raw rates, with intervals
In this replication each question yields one pair, so candidates and questions coincide.

  python boundary.py   -> boundary.{json,md}
"""
import json

import numpy as np

import analyze_math as M

A = M.A


def rates(R, seed=0):
    out = {}
    for b in A.BINS:
        S = [r for r in R if r["b"] == b]
        if not S:
            out[b] = dict(n=0)
            continue
        e, lo, hi = A.boot(S, lambda X: np.array([np.mean([r["y"] for r in X])]), seed)
        out[b] = dict(n=len(S), candidates=len({r["qid"] for r in S}), approved=int(sum(r["y"] for r in S)),
                      rate=float(e[0]), lo=float(lo[0]), hi=float(hi[0]))
    return out


def anymatch(R):
    X = [dict(r, any=int(r["belief"] > 0)) for r in R]
    e, lo, hi = A.boot(X, lambda Z: A.ols(Z, ["any"], [lambda r: r["judge"]]))
    pos = [r["y"] for r in X if r["any"]]
    neg = [r["y"] for r in X if not r["any"]]
    return dict(effect=float(e[0]), lo=float(lo[0]), hi=float(hi[0]), n_any=len(pos), rate_any=float(np.mean(pos)),
                cand_any=len({r["qid"] for r in X if r["any"]}), n_none=len(neg), rate_none=float(np.mean(neg)))


def main():
    audit = {r["qid"]: r["verdict"] for r in A.load(M.DATA / "audit.jsonl")}
    R, _ = M.rows(80, 1800, audit)
    out = {}
    for lab, S in (("key", R), ("audited", [r for r in R if r["audit"] == "LABEL_OK"])):
        out[lab] = dict(n=len(S), candidates=len({r["qid"] for r in S}), bins=rates(S), any_match=anymatch(S),
                        per_judge_any={j: anymatch([r for r in S if r["judge"] == j]) for j in A.JUDGES})
    (M.HERE / "boundary.json").write_text(json.dumps(out, indent=1) + "\n")
    L = ["# Math replication: observed rates and any-match contrast (post hoc)\n"]
    for lab, v in out.items():
        L += [f"## {lab}: {v['n']} judgments, {v['candidates']} candidates\n",
              "| bin | judgments | candidates | approved | rate [95%] |", "|---|---|---|---|---|"]
        for b, d in v["bins"].items():
            L.append(f"| {b} | {d['n']} | {d.get('candidates', 0)} | {d.get('approved', 0)} | " +
                     (f"{100 * d['rate']:.1f} [{100 * d['lo']:.1f}, {100 * d['hi']:.1f}] |" if d["n"] else "– |"))
        a = v["any_match"]
        L += ["", f"- any match vs none (judge FE): {100 * a['effect']:+.1f} [{100 * a['lo']:+.1f}, {100 * a['hi']:+.1f}]; "
                  f"rates {100 * a['rate_any']:.1f}% ({a['n_any']} judgments, {a['cand_any']} candidates) vs "
                  f"{100 * a['rate_none']:.1f}% ({a['n_none']})"]
        for j, a in v["per_judge_any"].items():
            L.append(f"  - {j}: {100 * a['effect']:+.1f} [{100 * a['lo']:+.1f}, {100 * a['hi']:+.1f}]; "
                     f"{100 * a['rate_any']:.1f}% (n={a['n_any']}) vs {100 * a['rate_none']:.1f}% (n={a['n_none']})")
        L.append("")
    (M.HERE / "boundary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
