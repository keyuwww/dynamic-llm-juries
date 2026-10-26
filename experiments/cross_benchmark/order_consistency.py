"""Order consistency vs errors on pairwise benchmarks (stored verdicts, no new calls).

Every pair is judged in both orders. Per (judge, pair) the two verdicts are either
  consistent-right  (same answer both orders, and it is the gold one),
  consistent-wrong  (same answer both orders, the wrong one), or
  inconsistent      (the pick follows the position: exactly one of the two verdicts is wrong, by construction).
So "inconsistent pairs have a 50% verdict error rate" is automatic. The non-trivial questions are:
  1. How accurate is a judge on the pairs where it IS consistent, and how much coverage does dropping the
     inconsistent ones cost (abstain-on-flip)?
  2. Does a judge's inconsistency on a pair predict OTHER judges' errors there (an item-difficulty signal)?
     In particular: does the number of other judges that flip predict the best judge's errors (AUROC)?
  3. Does a reference answer (condition 'human') reduce flips?
Usage: python order_consistency.py [bench ...]   (default: bffpair judgebench alpacafarm mtbhuman)
Writes results/order_consistency.md
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
POOL = ["gpt-oss-120b", "gpt-oss-20b", "deepseek-v3.1", "qwen3.6-35b-a3b", "qwen3.5-9b", "qwen3.5-4b",
        "nemotron3-super-120b", "nemotron3-nano-30b"]
# short labels for tables and charts
SHORT = {"gpt-oss-120b": "oss-120b", "gpt-oss-20b": "oss-20b", "deepseek-v3.1": "deepseek", "qwen3.6-35b-a3b": "qwen-35b",
         "qwen3.5-9b": "qwen-9b", "qwen3.5-4b": "qwen-4b", "nemotron3-super-120b": "nem-super", "nemotron3-nano-30b": "nem-nano"}


def auroc(y, s):
    y, s = np.asarray(y), np.asarray(s, float)
    pos, neg = s[y == 1], s[y == 0]
    if not len(pos) or not len(neg):
        return float("nan")
    r = pd.Series(np.concatenate([pos, neg])).rank().values
    return (r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def pair_table(bench, condition):
    d = pd.read_pickle(HERE / "data" / f"{bench}_decisions.pkl")
    d = d[(d.condition == condition) & d.judge.isin(POOL) & (d.parsed == 1)]
    w = d.pivot_table(index=["pair_id", "judge"], columns="order", values="verdict").dropna().reset_index()
    g0 = d[d.order == 0].drop_duplicates("pair_id").set_index("pair_id").gold
    w["gold0"] = w.pair_id.map(g0)
    w["right0"] = (w[0] == w.gold0).astype(int)              # verdict in order 0 right?
    w["right1"] = (w[1] == 1 - w.gold0).astype(int)          # order 1 shows the pair swapped
    w["flip"] = (w.right0 != w.right1).astype(int)           # same position picked both times
    w["cons_right"] = ((w.right0 == 1) & (w.right1 == 1)).astype(int)
    w["cons_wrong"] = ((w.right0 == 0) & (w.right1 == 0)).astype(int)
    w["err"] = 2 - w.right0 - w.right1                       # verdict errors on the pair (0, 1, 2)
    return w


def analyse(bench):
    w = pair_table(bench, "none")
    if w.empty:
        return None
    acc = w.groupby("judge").apply(lambda x: 1 - x.err.sum() / (2 * len(x)))
    best = acc.idxmax()
    rows = []
    for j in acc.sort_values(ascending=False).index:
        x = w[w.judge == j]
        cons = x[x.flip == 0]
        rows.append(dict(judge=j, pairs=len(x), acc_all=acc[j], flip_rate=x.flip.mean(),
                         acc_consistent=cons.cons_right.mean(), wrong_both=x.cons_wrong.mean(),
                         share_errors_on_flips=x.err[x.flip == 1].sum() / max(x.err.sum(), 1)))
    per_judge = pd.DataFrame(rows)

    # cross-judge signal: other judges' flips on a pair vs the best judge's errors on that pair
    fl = w.pivot_table(index="pair_id", columns="judge", values="flip")
    er = w.pivot_table(index="pair_id", columns="judge", values="err")
    cr = w.pivot_table(index="pair_id", columns="judge", values="cons_wrong")
    others = [j for j in fl.columns if j != best]
    ok = fl[others + [best]].dropna().index
    n_flip_others = fl.loc[ok, others].sum(1)
    best_wrong_any = (er.loc[ok, best] > 0).astype(int)        # best judge wrong in at least one order
    best_wrong_both = cr.loc[ok, best].astype(int)             # best judge confidently wrong (both orders)
    by_k = pd.DataFrame({"k": n_flip_others, "wrong_any": best_wrong_any, "wrong_both": best_wrong_both,
                         "best_flip": fl.loc[ok, best]}).groupby("k").agg(
        pairs=("wrong_any", "size"), best_err_any=("wrong_any", "mean"), best_wrong_both=("wrong_both", "mean"),
        best_flip=("best_flip", "mean"))
    # does the signal catch the best judge's CONSISTENT (confident) errors, which its own flips cannot?
    best_consistent = fl.loc[ok, best] == 0
    au_conf = auroc(best_wrong_both[best_consistent], n_flip_others[best_consistent])

    # pairwise: P(judge B flips | judge A flips) vs base rate, averaged
    lift = []
    for a in fl.columns:
        for b in fl.columns:
            if a == b:
                continue
            m = fl[[a, b]].dropna()
            if m[a].sum() and m[b].mean():
                lift.append(m.loc[m[a] == 1, b].mean() / m[b].mean())

    ref = None
    try:
        h = pair_table(bench, "human")
        if not h.empty:
            ref = pd.DataFrame({"flip_none": w.groupby("judge").flip.mean(), "flip_ref": h.groupby("judge").flip.mean()})
    except Exception:  # noqa: BLE001 - benchmark without a reference condition
        pass
    return dict(bench=bench, best=best, per_judge=per_judge, by_k=by_k, au_conf=au_conf,
                n_best_cons=int(best_consistent.sum()), lift=float(np.mean(lift)) if lift else float("nan"), ref=ref,
                pairs=len(ok))


def fmt(df, pct=()):
    df = df.copy()
    for c in df.columns:
        if c in pct:
            df[c] = (100 * df[c]).map(lambda v: f"{v:.1f}")
    return df.to_markdown(index=df.index.name is not None)


def main():
    benches = sys.argv[1:] or ["bffpair", "judgebench", "alpacafarm", "mtbhuman"]
    out = ["# Order consistency vs errors (stored verdicts, no new calls)", "",
           "Each pair is judged in both orders. *Flip* = the judge picked the same position both times, so exactly one of its two verdicts is wrong by construction. Percentages are of pairs unless noted.", ""]
    for b in benches:
        r = analyse(b)
        if r is None:
            continue
        out += [f"## {b} ({r['pairs']} pairs with all 8 judges; best judge {r['best']})", "",
                "### Per judge", "",
                fmt(r["per_judge"].set_index("judge"), pct=("acc_all", "flip_rate", "acc_consistent", "wrong_both", "share_errors_on_flips")), "",
                "- `acc_consistent`: accuracy on the pairs where the judge did not flip (abstain-on-flip). `wrong_both`: share of pairs where it picked the wrong answer in both orders (a confident error).",
                "- `share_errors_on_flips`: share of the judge's verdict errors that sit on its flipped pairs.", "",
                f"### Do other judges' flips predict the best judge's errors? (best = {r['best']})", "",
                fmt(r["by_k"], pct=("best_err_any", "best_wrong_both", "best_flip")), "",
                f"- AUROC of 'number of other judges that flip' for the best judge's confident errors, among the {r['n_best_cons']} pairs where the best judge itself was consistent: **{r['au_conf']:.3f}**.",
                f"- Mean lift of P(judge B flips | judge A flips) over B's base flip rate, across judge pairs: **{r['lift']:.2f}x**.", ""]
        if r["ref"] is not None:
            out += ["### Flip rate without vs with the expert reference", "", fmt(r["ref"], pct=("flip_none", "flip_ref")), ""]
    p = HERE / "results" / "order_consistency.md"
    p.write_text("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main()
