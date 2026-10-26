"""Can a weaker judge's uncertainty flag the best judge's confident errors? (no new calls)

For every judge j on each pairwise benchmark:
  acc            j's own accuracy (stored run, both orders)
  flag_conf      AUROC of j's low stated confidence (confidence run, mean of both orders) for the best judge's
                 confident errors, on pairs where the best judge is consistent (stored run)
  flag_flip      AUROC of j flipping (stored run) for the same errors
  self_conf      AUROC of j's low stated confidence for j's own errors in the confidence run (wrong in at least one
                 order), i.e. does j know when it is itself wrong
AUROC of a single signal does not depend on how scores are scaled or ranked, so no cohort-dependent ranking is used.
Usage: python judge_uncertainty.py -> results/flips/judge_uncertainty.{json,md}
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from conf_analysis import per_pair, read  # noqa: E402
from flip_analysis import load  # noqa: E402
from order_consistency import POOL, SHORT, auroc, pair_table  # noqa: E402

BENCHES = ["bffpair", "judgebench", "alpacafarm", "mtbhuman"]


def main():
    rows = []
    for b in BENCHES:
        df, target, J = load(b)
        w = pair_table(b, "none")
        acc = w.groupby("judge").apply(lambda x: 1 - x.err.sum() / (2 * len(x)))
        fl = w.pivot_table(index="pair_id", columns="judge", values="flip")
        t = read("confidence", b)
        P = per_pair(t)
        conf = P.pivot_table(index="pair_id", columns="judge", values="stated")
        # own errors in the confidence run: wrong in at least one order (gold refers to the 'ab' presentation)
        g = t.drop_duplicates("item_id").set_index("item_id")
        t["right"] = (t.verdict == t.gold).astype(float).where(t.verdict.notna())
        own_wrong = t.groupby(["judge", "pair_id"]).right.min().unstack(0).rsub(1)
        cons = df[df.t_flip == 0]
        y = cons.t_conf_err.astype(int)
        for j in [x for x in POOL if x in conf.columns]:
            c = conf[j].reindex(cons.index)
            m = c.notna()
            f = fl[j].reindex(cons.index)
            ow = own_wrong[j].reindex(conf.index)
            mm = ow.notna() & conf[j].notna()
            rows.append(dict(bench=b, judge=j, short=SHORT[j], is_best=j == target, acc=float(acc[j]),
                             flag_conf=float(auroc(y[m].values, -c[m].values)),
                             flag_flip=float(auroc(y[f.notna()].values, f.dropna().values)) if j != target else np.nan,
                             self_conf=float(auroc(ow[mm].values.astype(int), -conf[j][mm].values)),
                             self_error_rate=float(ow[mm].mean())))
    T = pd.DataFrame(rows)
    nb = T[~T.is_best]
    sp = lambda a, b_: float(nb[[a, b_]].corr(method="spearman").iloc[0, 1])
    summary = dict(rho_acc_flag_conf=sp("acc", "flag_conf"), rho_acc_flag_flip=sp("acc", "flag_flip"),
                   rho_acc_self_conf=float(T[["acc", "self_conf"]].corr(method="spearman").iloc[0, 1]),
                   share_flag_conf_above_0_6=float((nb.flag_conf > 0.6).mean()),
                   mean_flag_conf_weak=float(nb[nb.acc < nb.groupby("bench").acc.transform("median")].flag_conf.mean()),
                   mean_flag_conf_strong=float(nb[nb.acc >= nb.groupby("bench").acc.transform("median")].flag_conf.mean()))
    out = HERE / "results" / "flips"
    (out / "judge_uncertainty.json").write_text(json.dumps(dict(rows=rows, summary=summary), indent=1, default=float))
    L = ["# Each judge's accuracy vs its ability to flag the best judge's confident errors", "",
         "AUROC 0.5 = chance. flag_* = for the best judge's confident errors; self_conf = for the judge's own errors.", "",
         T.drop(columns=["judge"]).round(3).to_markdown(index=False), "",
         "Spearman across non-best judges (32 - 4 = 28 judge-benchmark points): " +
         ", ".join(f"{k} {v:+.2f}" for k, v in summary.items()), ""]
    (out / "judge_uncertainty.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
