"""Which judges catch which judges' errors, and is it reciprocal? (stored verdicts, no new calls)

Pairwise benchmarks only (each pair judged in both orders). For a target judge j we look at its CONFIDENT errors
(wrong in both orders), on the pairs where j is consistent. A checker judge i can signal such an error two ways:
  flip      i picks the same position in both orders (unsure)
  disagree  i is consistent and picks the other answer (i is right in both orders)
For each ordered pair (checker i -> target j):
  catch_flip      P(i flips | j confidently wrong)
  lift_flip       catch_flip / P(i flips | j right)
  auroc_flip      AUROC of the binary flag "i flips" for j's confident errors
  catch_any       P(i flips or disagrees | j confidently wrong)
  false_any       P(i flips or disagrees | j right)          (cost of using i as an alarm for j)
Similarity between i and j: error phi over both-order verdicts, and verdict agreement.
Reciprocity: correlation of each matrix with its transpose; mean |M_ij - M_ji|.
Usage: python judge_pairs.py   -> results/flips/judge_pairs.md, results/flips/judge_pairs.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from order_consistency import POOL, pair_table  # noqa: E402

BENCHES = ["bffpair", "judgebench", "alpacafarm", "mtbhuman"]
SHORT = {"gpt-oss-120b": "oss-120b", "gpt-oss-20b": "oss-20b", "deepseek-v3.1": "deepseek", "qwen3.6-35b-a3b": "qwen-35b",
         "qwen3.5-9b": "qwen-9b", "qwen3.5-4b": "qwen-4b", "nemotron3-super-120b": "nem-super", "nemotron3-nano-30b": "nem-nano"}


def matrices(bench):
    w = pair_table(bench, "none")
    fl = w.pivot_table(index="pair_id", columns="judge", values="flip")
    cw = w.pivot_table(index="pair_id", columns="judge", values="cons_wrong")
    crt = w.pivot_table(index="pair_id", columns="judge", values="cons_right")
    e0 = w.pivot_table(index="pair_id", columns="judge", values="right0").rsub(1)
    e1 = w.pivot_table(index="pair_id", columns="judge", values="right1").rsub(1)
    J = [j for j in POOL if j in fl.columns]
    acc = {j: 1 - (e0[j].mean() + e1[j].mean()) / 2 for j in J}
    M = {k: pd.DataFrame(np.nan, index=J, columns=J) for k in
         ["catch_flip", "lift_flip", "auroc_flip", "catch_any", "false_any", "phi", "agree"]}
    for i in J:
        for j in J:
            if i == j:
                continue
            m = pd.concat([fl[i], fl[j], cw[j], crt[i], crt[j], cw[i], e0[i], e0[j], e1[i], e1[j]], axis=1,
                          keys=["fi", "fj", "wj", "ri", "rj", "wi", "e0i", "e0j", "e1i", "e1j"]).dropna()
            cons_j = m[m.fj == 0]
            wrong, right = cons_j[cons_j.wj == 1], cons_j[cons_j.wj == 0]
            if len(wrong) < 5 or len(right) < 5:
                continue
            tpr, fpr = wrong.fi.mean(), right.fi.mean()
            M["catch_flip"].loc[i, j] = tpr
            M["lift_flip"].loc[i, j] = tpr / fpr if fpr else np.nan
            M["auroc_flip"].loc[i, j] = (tpr + 1 - fpr) / 2
            flag_w = (wrong.fi == 1) | (wrong.ri == 1)
            flag_r = (right.fi == 1) | (right.wi == 1)
            M["catch_any"].loc[i, j] = flag_w.mean()
            M["false_any"].loc[i, j] = flag_r.mean()
            ei = np.r_[m.e0i.values, m.e1i.values]
            ej = np.r_[m.e0j.values, m.e1j.values]
            M["phi"].loc[i, j] = np.corrcoef(ei, ej)[0, 1]
            M["agree"].loc[i, j] = (ei == ej).mean()
    return J, acc, M


def reciprocity(A):
    v = A.values
    mask = ~np.eye(len(v), dtype=bool) & ~np.isnan(v) & ~np.isnan(v.T)
    return float(np.corrcoef(v[mask], v.T[mask])[0, 1]), float(np.nanmean(np.abs(v - v.T)[mask]))


def best_pairs(J, acc, M, k=5):
    """Mutual catching: rank unordered pairs by the mean of catch_any both ways, net of false alarms."""
    rows = []
    for a in range(len(J)):
        for b in range(a + 1, len(J)):
            i, j = J[a], J[b]
            ca, cb = M["catch_any"].loc[i, j], M["catch_any"].loc[j, i]
            fa, fb = M["false_any"].loc[i, j], M["false_any"].loc[j, i]
            if np.isnan([ca, cb, fa, fb]).any():
                continue
            rows.append(dict(pair=f"{SHORT[i]} + {SHORT[j]}", i_catches_j=ca, j_catches_i=cb, mean_catch=(ca + cb) / 2,
                             mean_false=(fa + fb) / 2, net=(ca + cb - fa - fb) / 2, phi=M["phi"].loc[i, j],
                             acc_gap=abs(acc[i] - acc[j])))
    return pd.DataFrame(rows).sort_values("net", ascending=False)


def pct(df):
    return (100 * df).round(1)


def main():
    out = ["# Judge pairs: who catches whose confident errors (stored verdicts, no new calls)", "",
           "Target judge j = column, checker i = row. Confident error = j wrong in both orders, counted on pairs where j "
           "is consistent. In-sample, no CIs.", ""]
    summary = {}
    for b in BENCHES:
        J, acc, M = matrices(b)
        ren = lambda d: d.rename(index=SHORT, columns=SHORT)
        rf, df_ = reciprocity(M["auroc_flip"])
        ra, da = reciprocity(M["catch_any"])
        # does catching follow similarity or checker strength?
        flat = []
        for i in J:
            for j in J:
                if i != j and not np.isnan(M["auroc_flip"].loc[i, j]):
                    flat.append(dict(i=i, j=j, auroc_flip=M["auroc_flip"].loc[i, j], catch_any=M["catch_any"].loc[i, j],
                                     false_any=M["false_any"].loc[i, j], phi=M["phi"].loc[i, j], acc_i=acc[i], acc_j=acc[j]))
        f = pd.DataFrame(flat)
        sp = lambda x, y: float(f[[x, y]].corr(method="spearman").iloc[0, 1])
        bp = best_pairs(J, acc, M)
        summary[b] = dict(recip_flip=rf, asym_flip=df_, recip_any=ra, asym_any=da,
                          rho_flip_phi=sp("auroc_flip", "phi"), rho_flip_acc_i=sp("auroc_flip", "acc_i"),
                          rho_flip_acc_j=sp("auroc_flip", "acc_j"), rho_any_phi=sp("catch_any", "phi"),
                          rho_false_acc_i=sp("false_any", "acc_i"),
                          acc={SHORT[j]: acc[j] for j in J},
                          matrices={k: ren(v).round(4).to_dict() for k, v in M.items()},
                          best_pairs=bp.head(8).round(4).to_dict(orient="records"))
        accs = ", ".join(f"{SHORT[j]} {100 * acc[j]:.1f}" for j in sorted(J, key=lambda x: -acc[x]))
        out += [f"## {b}", "", f"Accuracy (both orders): {accs}", "",
                "### AUROC of checker i's flips for target j's confident errors (0.5 = chance)", "",
                ren(M["auroc_flip"]).round(2).to_markdown(), "",
                "### Share of j's confident errors flagged by i (flip or consistent disagreement), %", "",
                pct(ren(M["catch_any"])).to_markdown(), "",
                "### False-alarm rate: share of j's correct pairs flagged by i, %", "",
                pct(ren(M["false_any"])).to_markdown(), "",
                "### Error correlation (phi) between judges", "", ren(M["phi"]).round(2).to_markdown(), "",
                "### Reciprocity and what catching follows", "",
                f"- Correlation of the flip-AUROC matrix with its transpose: **{rf:.2f}** (mean |i→j − j→i| = {df_:.3f}).",
                f"- Same for catch-any: **{ra:.2f}** (mean |i→j − j→i| = {100 * da:.1f} pts).",
                f"- Spearman, flip-AUROC vs error phi: {summary[b]['rho_flip_phi']:+.2f}; vs checker accuracy: "
                f"{summary[b]['rho_flip_acc_i']:+.2f}; vs target accuracy: {summary[b]['rho_flip_acc_j']:+.2f}.",
                f"- Spearman, catch-any vs phi: {summary[b]['rho_any_phi']:+.2f}; false alarms vs checker accuracy: "
                f"{summary[b]['rho_false_acc_i']:+.2f}.", "",
                "### Best mutual pairs (mean of catch-any both ways minus mean false alarms)", "",
                bp.head(8).assign(**{c: (100 * bp.head(8)[c]).round(1) for c in
                                     ["i_catches_j", "j_catches_i", "mean_catch", "mean_false", "net", "acc_gap"]},
                                  phi=bp.head(8).phi.round(2)).to_markdown(index=False), ""]
    d = HERE / "results" / "flips"
    d.mkdir(parents=True, exist_ok=True)
    (d / "judge_pairs.md").write_text("\n".join(out))
    (d / "judge_pairs.json").write_text(json.dumps(summary, indent=1))
    print("\n".join(out))


if __name__ == "__main__":
    main()
