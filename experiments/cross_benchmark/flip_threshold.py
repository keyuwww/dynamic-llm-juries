"""Best judge's error rate by how many of the other 7 judges flip (stored verdicts, no new calls).

For each pairwise benchmark and two targets (the benchmark's best judge, and gpt-oss-120b everywhere), under two
conditions: (a) pairs where the target is consistent, error = wrong in both orders; (b) all pairs, error = wrong
in at least one order, so the target's own flips count. For k = 0..7: error rate and pair count among pairs where
>= k other judges flip, among pairs where exactly k flip, and the share of all errors caught.
Usage: python flip_threshold.py -> results/flips/flip_threshold.{md,json}
"""
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from order_consistency import POOL, pair_table  # noqa: E402

BENCHES = ["bffpair", "judgebench", "alpacafarm", "mtbhuman"]


def curve(w, target, all_pairs=False):
    """all_pairs=False: pairs where the target is consistent; outcome = wrong in both orders.
    all_pairs=True: every pair; outcome = wrong in at least one order (a pair the target flips always counts)."""
    fl = w.pivot_table(index="pair_id", columns="judge", values="flip")
    cw = w.pivot_table(index="pair_id", columns="judge", values="cons_wrong")
    J = [j for j in POOL if j in fl.columns]
    ok = fl[J].dropna().index
    others = [j for j in J if j != target]
    d = pd.DataFrame({"k": fl.loc[ok, others].sum(1).astype(int), "err": cw.loc[ok, target],
                      "tflip": fl.loc[ok, target]})
    if all_pairs:
        d["err"] = ((d.err == 1) | (d.tflip == 1)).astype(int)
    else:
        d = d[d.tflip == 0]
    rows = []
    for k in range(len(others) + 1):
        ge, eq = d[d.k >= k], d[d.k == k]
        rows.append(dict(k=k, pairs_ge=int(len(ge)), err_ge=float(ge.err.mean()) if len(ge) else None,
                         errors_ge=int(ge.err.sum()), pairs_eq=int(len(eq)),
                         err_eq=float(eq.err.mean()) if len(eq) else None, share_ge=float(len(ge) / len(d)),
                         recall_ge=float(ge.err.sum() / max(d.err.sum(), 1))))
    own = dict(flip_rate=float(d.tflip.mean()), errors_on_own_flips=float(d.err[d.tflip == 1].sum() / max(d.err.sum(), 1)))
    return dict(target=target, n=int(len(d)), base=float(d.err.mean()), rows=rows, own=own)


def main():
    out, L = {}, ["# Best judge's error rate by number of other judges flipping", "",
                  "`best` / `gpt-oss-120b`: pairs where the target is consistent; error = wrong in both orders. "
                  "`*_all`: every pair; error = wrong in at least one order (pairs the target flips count).", ""]
    for b in BENCHES:
        w = pair_table(b, "none")
        acc = w.groupby("judge").apply(lambda x: 1 - x.err.sum() / (2 * len(x)))
        best = acc.idxmax()
        out[b] = {"best": curve(w, best), "gpt-oss-120b": curve(w, "gpt-oss-120b"),
                  "best_all": curve(w, best, True), "gpt-oss-120b_all": curve(w, "gpt-oss-120b", True)}
        for tag, c in out[b].items():
            L += [f"## {b}: target {c['target']} ({tag}); {c['n']} pairs, base error {100 * c['base']:.1f}%", "",
                  "| ≥k others flip | pairs | share of pairs | errors | error rate | share of all errors | exactly k: pairs | exactly k: error rate |",
                  "|---|---|---|---|---|---|---|---|"]
            for r in c["rows"]:
                f = lambda v: "–" if v is None else f"{100 * v:.1f}%"
                L.append(f"| {r['k']} | {r['pairs_ge']} | {f(r['share_ge'])} | {r['errors_ge']} | {f(r['err_ge'])} | "
                         f"{f(r['recall_ge'])} | {r['pairs_eq']} | {f(r['err_eq'])} |")
            L.append("")
    p = HERE / "results" / "flips"
    (p / "flip_threshold.json").write_text(json.dumps(out, indent=1))
    (p / "flip_threshold.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
