"""No-cost follow-ups to Stage A (stored verdicts).

1. Unflaggable errors: the best judge's confident errors where no other judge flips or disagrees. Dumps them with
   the question, both answers (truncated), gold, and controls for hand inspection.
2. AlpacaFarm by human vote margin: does the flip signal hold on pairs where the 4 human votes were unanimous
   (3-1 or 4-0) vs split 2-2? Separates contested labels from real errors.
Usage: python flip_followups.py  -> results/flips/unflaggable.md, results/flips/alpaca_margin.md
"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from flip_analysis import load  # noqa: E402
from order_consistency import auroc  # noqa: E402

OUT = HERE / "results" / "flips"


def unflaggable():
    L = ["# Confident errors no other judge flags (stored verdicts)", "",
         "Best judge wrong in both orders, and none of the other 7 judges flips or disagrees (all 7 consistently "
         "share the wrong pick). Gold = the human-preferred answer.", ""]
    for b in ["bffpair", "judgebench", "alpacafarm", "mtbhuman"]:
        df, target, J = load(b)
        it = pd.read_pickle(HERE / "data" / f"{b}_items.pkl")
        it = it[it.order == 0].drop_duplicates("pair_id").set_index("pair_id")
        F = pd.read_csv(OUT / f"features_{b}.csv", index_col=0)
        m = (df.t_flip == 0) & (df.t_conf_err == 1) & (df.n_flip == 0) & (df.n_dis == 0)
        L += [f"## {b} (best judge {target}): {int(m.sum())} of {int(((df.t_flip == 0) & (df.t_conf_err == 1)).sum())} "
              f"confident errors", ""]
        for pid in df.index[m]:
            r = it.loc[pid]
            gold = "A (first shown)" if r.gold == 1 else "B (second shown)"
            f = F.loc[pid]
            q = str(r.question)[:500].replace("\n", " ")
            a = str(r.resp_a)[:400].replace("\n", " ")
            bb = str(r.resp_b)[:400].replace("\n", " ")
            extra = f", human margin {f.human_margin:.2f}" if "human_margin" in F.columns else ""
            L += [f"### {pid}", f"- category {r.category}; gold {gold}; length gap {f.len_gap:.2f}; similarity {f.sim:.2f}; "
                  f"same final number {int(f.same_final_number)}{extra}",
                  f"- **Question:** {q}", f"- **A:** {a}", f"- **B:** {bb}", ""]
    (OUT / "unflaggable.md").write_text("\n".join(L))
    return L


def alpaca_margin():
    df, target, J = load("alpacafarm")
    F = pd.read_csv(OUT / "features_alpacafarm.csv", index_col=0)
    d = df[df.t_flip == 0].join(F[["human_margin"]])
    rows = []
    for name, m in [("unanimous 4-0", d.human_margin == 1), ("3-1", d.human_margin == 0.5), ("split 2-2", d.human_margin == 0)]:
        x = d[m]
        if len(x) < 10:
            continue
        y = x.t_conf_err.values.astype(int)
        rows.append(dict(votes=name, pairs=len(x), conf_err_rate=y.mean(), auroc_flips=auroc(y, x.n_flip.values),
                         auroc_disagree=auroc(y, x.n_dis.values), auroc_pooled=auroc(y, x.eu.values),
                         mean_flips=x.n_flip.mean()))
    t = pd.DataFrame(rows)
    txt = ["# AlpacaFarm: flip signal by human vote margin", "",
           "4 crowd votes per pair. Best judge " + target + "; consistent pairs only.", "",
           t.round(3).to_markdown(index=False), ""]
    (OUT / "alpaca_margin.md").write_text("\n".join(txt))
    return txt


if __name__ == "__main__":
    u = unflaggable()
    print("\n".join(x for x in u if x.startswith("## ")))
    print("\n".join(alpaca_margin()))
