"""Stage B analyses: stated confidence, verdict-token probability and resampling vs order flips.

Reads results/<run>/<bench>/judgments.jsonl from run_confidence.py (one row per judge x item x order; K samples).
Joins the stored 8-judge verdicts for the other judges' flips (Stage A signal).

  B0  parse rates; how often asking for confidence changed the verdict vs the stored run (sample 0)
  B-a own confidence vs own flips: is a judge less confident on pairs it flips?
  B-b confidence vs the best judge's confident errors (on its consistent pairs); calibration by confidence bin
  B-c confidence x detectability: per tercile of the best judge's confidence, error rate and AUROC of others' flips
  B-d combined alarm: best-judge confidence + others' pooled score, vs each alone, and catch at 18% flagged
  B-e others' confidence vs others' flips, for the judges in this run
  C1  (K > 1) resampling: own vote spread as confidence; repeatable vs one-off flips
Confidence measures per (judge, pair), averaged over both orders and samples:
  stated   mean stated confidence (0-100)
  token    mean verdict-token probability
  vote     share of the 2K sampled verdicts that pick the same answer (order-adjusted); 1 = fully stable
Usage: python conf_analysis.py <run> [bench ...]   e.g.  python conf_analysis.py confidence_pilot bffpair mtbhuman
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from flip_analysis import boot_auc, catch_at_rate, load  # noqa: E402
from order_consistency import auroc, pair_table  # noqa: E402


def read(run, bench):
    rows = [json.loads(l) for l in open(HERE / "results" / run / bench / "judgments.jsonl")]
    t = pd.DataFrame(rows)
    t["pair_id"] = t.item_id.str.rsplit("|", n=1).str[0]
    t["order"] = t.item_id.str.rsplit("|", n=1).str[1]
    if bench != "bffpair":     # xb items: order is encoded differently; map via the items table
        it = pd.read_pickle(HERE / "data" / f"{bench}_items.pkl").set_index("key")
        t["pair_id"] = t.item_id.map(it.pair_id)
        t["order"] = t.item_id.map(it.order).map({0: "ab", 1: "ba"})
    else:
        t["order"] = t.order.map({"ab": "ab", "ba": "ba"})
    return t


def per_pair(t):
    """One row per (judge, pair): confidence measures and sample-level flip info."""
    out = []
    for (j, p), x in t.groupby(["judge", "pair_id"]):
        if set(x.order) != {"ab", "ba"}:
            continue
        a, b = x[x.order == "ab"].iloc[0], x[x.order == "ba"].iloc[0]
        va, vb = a.verdicts, b.verdicts                       # 1 = first shown better
        K = min(len(va), len(vb))
        # pick of the 'ab'-first answer under each order: in 'ab' it is va; in 'ba' first shown is the other answer
        pick_a = [v for v in va[:K] if v is not None]
        pick_b = [1 - v for v in vb[:K] if v is not None]
        picks = pick_a + pick_b
        vote = abs(2 * np.mean(picks) - 1) if picks else np.nan            # 1 = always the same answer
        flips = [int(x1 is not None and x2 is not None and x1 == x2) for x1, x2 in zip(va[:K], vb[:K])]
        confs = [c for c in list(a.confs) + list(b.confs) if c is not None]
        toks = [c for c in list(a.p_verdicts) + list(b.p_verdicts) if c is not None]
        out.append(dict(judge=j, pair_id=p, K=K, stated=np.mean(confs) if confs else np.nan,
                        token=np.mean(toks) if toks else np.nan, vote=vote,
                        flip0=flips[0] if flips else np.nan, flip_share=np.mean(flips) if flips else np.nan,
                        v0_ab=va[0], v0_ba=vb[0]))
    return pd.DataFrame(out)


def run_bench(run, bench):
    t = read(run, bench)
    P = per_pair(t)
    df, target, J = load(bench)                               # stored 8-judge signals
    w = pair_table(bench, "none")
    stored = w.set_index(["pair_id", "judge"])
    res = dict(bench=bench, target=target, judges=sorted(P.judge.unique()), K=int(P.K.max()))
    # B0
    parse = t.verdicts.map(lambda v: np.mean([x is not None for x in v])).mean()
    conf_parse = t.confs.map(lambda v: np.mean([x is not None for x in v])).mean()
    ch = []
    for _, r in P.iterrows():
        if (r.pair_id, r.judge) in stored.index:
            s = stored.loc[(r.pair_id, r.judge)]
            ch += [int(r.v0_ab != s[0]), int(r.v0_ba != s[1])]
    res["B0"] = dict(parse=float(parse), conf_parse=float(conf_parse), verdict_changed_vs_stored=float(np.mean(ch)),
                     stated_spread=P.stated.describe()[["mean", "std", "min", "max"]].round(2).to_dict())
    # B-a own confidence vs own flips (sample-0 flip)
    ba = []
    for j, x in P.groupby("judge"):
        x = x.dropna(subset=["flip0"])
        ba.append(dict(judge=j, flip_rate=float(x.flip0.mean()),
                       auroc_stated=auroc(x.flip0.values.astype(int), -x.stated.values),
                       auroc_token=auroc(x.flip0.values.astype(int), -x.token.values),
                       auroc_vote=auroc(x.flip0.values.astype(int), -x.vote.values) if res["K"] > 1 else np.nan,
                       stated_if_flip=float(x.stated[x.flip0 == 1].mean()), stated_if_cons=float(x.stated[x.flip0 == 0].mean())))
    res["B_a"] = ba
    # B-b / B-c / B-d on the best judge (stored outcome so the target definition matches Stage A)
    T = P[P.judge == target].set_index("pair_id")
    if len(T):
        d = df[df.t_flip == 0].join(T[["stated", "token", "vote"]], how="inner")
        F = pd.read_csv(HERE / "results" / "flips" / f"features_{bench}.csv", index_col=0)
        g = F.loc[d.index, "group"].values
        y = d.t_conf_err.values.astype(int)
        res["B_b"] = dict(n=int(len(d)), errors=int(y.sum()),
                          stated=boot_auc(y, -d.stated.values, g), token=boot_auc(y, -d.token.values, g))
        if res["K"] > 1:
            res["B_b"]["vote"] = boot_auc(y, -d.vote.values + 1e-9 * np.random.default_rng(0).random(len(d)), g)
        cal = []
        for lo, hi in [(0, 80), (80, 90), (90, 95), (95, 101)]:
            m = (d.stated >= lo) & (d.stated < hi)
            if m.sum():
                cal.append(dict(stated=f"{lo}-{min(hi, 100)}", pairs=int(m.sum()), error_rate=float(y[m.values].mean())))
        res["B_b"]["calibration"] = cal
        # B-c: terciles of the best judge's own confidence (stated; vote if available)
        conf_col = "stated"
        rk = d[conf_col].rank(method="first")
        terc = pd.qcut(rk, 3, labels=["low", "mid", "high"])
        bc = []
        for lev in ["low", "mid", "high"]:
            m = (terc == lev).values
            bc.append(dict(confidence=lev, pairs=int(m.sum()), errors=int(y[m].sum()), error_rate=float(y[m].mean()),
                           auroc_others_flips=auroc(y[m], d.n_flip.values[m]),
                           auroc_pooled=auroc(y[m], d.eu.values[m])))
        res["B_c"] = dict(by=conf_col, rows=bc)
        # B-d combined: rank-average of (low own confidence) and (others' pooled score), per own-confidence measure
        oth = d.eu.rank(pct=True).values
        res["B_d"] = dict(others=boot_auc(y, oth, g), catch18_others=catch_at_rate(oth, y, .18), measures={})
        for mcol in ["stated", "token"] + (["vote"] if res["K"] > 1 else []):
            own = (-d[mcol].fillna(d[mcol].median())).rank(pct=True).values
            comb = (own + oth) / 2
            res["B_d"]["measures"][mcol] = dict(own=boot_auc(y, own, g), combined=boot_auc(y, comb, g),
                                                corr=float(np.corrcoef(own, oth)[0, 1]),
                                                catch18_own=catch_at_rate(own, y, .18),
                                                catch18_combined=catch_at_rate(comb, y, .18))
        # B-e others' confidence (judges in this run, excluding the target) vs their flips
        others = [j for j in res["judges"] if j != target]
        if others:
            O = P[P.judge.isin(others)].pivot_table(index="pair_id", columns="judge", values=["stated", "vote", "flip0"])
            O = O.reindex(d.index)
            O = O.fillna(O.mean())
            low_conf = (-O["stated"]).rank(pct=True).mean(1).values
            n_fl = O["flip0"].sum(1).values
            res["B_e"] = dict(checkers=others, others_low_stated=auroc(y, low_conf), others_flips=auroc(y, n_fl))
            if res["K"] > 1:
                res["B_e"]["others_low_vote"] = auroc(y, (1 - O["vote"]).mean(1).values)
        # C1 noise: repeatable flips (share of K sample pairings that flip) for the target and checkers
        if res["K"] > 1:
            Fs = P.pivot_table(index="pair_id", columns="judge", values="flip_share").reindex(d.index)
            F0 = P.pivot_table(index="pair_id", columns="judge", values="flip0").reindex(d.index)
            chk = [j for j in Fs.columns if j != target]
            res["C1"] = dict(
                flip_repeat_rate={j: float(((Fs[j] >= 2 / 3)[F0[j] == 1]).mean()) for j in Fs.columns},
                checkers_single_run=auroc(y, F0[chk].sum(1).values),
                checkers_all_samples=auroc(y, Fs[chk].sum(1).values),
                checkers_repeatable_only=auroc(y, (Fs[chk] >= 2 / 3).sum(1).values))
    return res


def fmt(t):
    return f"{t[0]:.2f} [{t[1]:.2f}, {t[2]:.2f}]"


def report(run, R):
    L = [f"# Stage B: confidence vs order flips ({run})", "",
         "Same pairwise prompts with a CONFIDENCE line; both orders; K samples per call. Outcome: the best judge's "
         "confident errors on its consistent pairs (stored run, as in Stage A). AUROC 0.5 = chance.", ""]
    for r in R:
        L += [f"## {r['bench']} (best judge {r['target']}; judges {', '.join(r['judges'])}; K = {r['K']})", "",
              f"- Parse rate {100 * r['B0']['parse']:.1f}%, confidence line present {100 * r['B0']['conf_parse']:.1f}%. "
              f"Asking for confidence changed {100 * r['B0']['verdict_changed_vs_stored']:.1f}% of verdicts vs the stored run. "
              f"Stated confidence: mean {r['B0']['stated_spread']['mean']}, sd {r['B0']['stated_spread']['std']}, "
              f"range {r['B0']['stated_spread']['min']}–{r['B0']['stated_spread']['max']}.", "",
              "**B-a: is a judge less confident on pairs it flips?** (AUROC of low confidence for its own flip)", "",
              pd.DataFrame(r["B_a"]).round(3).to_markdown(index=False), ""]
        if "B_b" in r:
            b = r["B_b"]
            L += [f"**B-b: does the best judge's own confidence flag its confident errors?** ({b['n']} pairs, "
                  f"{b['errors']} errors) stated {fmt(b['stated'])}; token {fmt(b['token'])}" +
                  (f"; vote spread {fmt(b['vote'])}" if "vote" in b else "") + ".", "",
                  pd.DataFrame(b["calibration"]).round(3).to_markdown(index=False), "",
                  f"**B-c: others' flips by the best judge's confidence ({r['B_c']['by']} terciles)**", "",
                  pd.DataFrame(r["B_c"]["rows"]).round(3).to_markdown(index=False), "",
                  f"**B-d: combined alarm.** Others' pooled score alone {fmt(r['B_d']['others'])} "
                  f"(catches {100 * r['B_d']['catch18_others']:.0f}% of errors at 18% flagged).", ""]
            L += ["| Own measure | Own AUROC | Combined with others | Correlation | Caught at 18%: own / combined |",
                  "|---|---|---|---|---|"]
            for mcol, v in r["B_d"]["measures"].items():
                L.append(f"| {mcol} | {fmt(v['own'])} | {fmt(v['combined'])} | {v['corr']:+.2f} | "
                         f"{100 * v['catch18_own']:.0f}% / {100 * v['catch18_combined']:.0f}% |")
            L.append("")
        if "B_e" in r:
            e = r["B_e"]
            L += [f"**B-e: checkers' confidence vs their flips** ({', '.join(e['checkers'])}): low stated confidence "
                  f"{e['others_low_stated']:.2f}; their flips {e['others_flips']:.2f}" +
                  (f"; low vote stability {e['others_low_vote']:.2f}" if "others_low_vote" in e else "") + ".", ""]
        if "C1" in r:
            c = r["C1"]
            L += ["**C1: noise.** Share of a judge's flips that repeat in at least 2 of 3 sample pairings: " +
                  ", ".join(f"{k} {100 * v:.0f}%" for k, v in c["flip_repeat_rate"].items()) +
                  f". Checkers' flips as an alarm: single run {c['checkers_single_run']:.2f}, all samples "
                  f"{c['checkers_all_samples']:.2f}, repeatable flips only {c['checkers_repeatable_only']:.2f}.", ""]
    return "\n".join(L)


def main():
    run = sys.argv[1]
    benches = sys.argv[2:] or ["bffpair", "judgebench", "alpacafarm", "mtbhuman"]
    R = [run_bench(run, b) for b in benches if (HERE / "results" / run / b / "judgments.jsonl").exists()]
    out = HERE / "results" / "flips"
    (out / f"stage_b_{run}.json").write_text(json.dumps(R, indent=1, default=float))
    txt = report(run, R)
    (out / f"stage_b_{run}.md").write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
