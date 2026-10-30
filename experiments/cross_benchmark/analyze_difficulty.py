"""Test 3 analysis: do judges' explicit predictions of expert difficulty flag the expert's errors?

Outcome: the best judge is wrong in at least one order (all pairs, stored run).
Per predicting judge j (6 judges still on Tinker), AUROC of three "this will be hard for the expert" scores:
  explicit_q   100 - j's predicted P(expert right), question only (no answers shown)
  explicit_qa  100 - j's predicted P(expert right), question + both answers
  implicit     j's low stated confidence on its own verdict (confidence run, mean of both orders)
All three are scored on the same pairs (those with a qa prediction).
Also: AUROC of explicit_qa on the pairs j itself gets right (does it predict beyond its own failure), the
correlation between explicit_qa and implicit, and a pooled score = mean within-judge rank over the predictors
that are not the expert (single, unweighted average).
Usage: python analyze_difficulty.py -> results/flips/difficulty_prediction.{json,md}
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from conf_analysis import per_pair, read  # noqa: E402
from flip_analysis import load  # noqa: E402
from order_consistency import SHORT, auroc, pair_table  # noqa: E402

BENCHES = ["bffpair", "judgebench", "alpacafarm", "mtbhuman"]
OUT = HERE / "results" / "flips"


def main():
    rows, pooled = [], []
    for b in BENCHES:
        df, best, _ = load(b)
        w = pair_table(b, "none")
        wrong = (w.pivot_table(index="pair_id", columns="judge", values="err") > 0).astype(float).dropna()
        yb = wrong[best]
        d = HERE / "results" / "difficulty" / b
        t = pd.DataFrame([json.loads(l) for l in open(d / "judgments.jsonl")]).drop_duplicates("cache_key", keep="last")
        q2 = json.load(open(d / "pair_to_question.json"))
        tq = t[t.variant == "q"].pivot_table(index="key", columns="judge", values="pred")
        ta = t[t.variant == "qa"].pivot_table(index="key", columns="judge", values="pred")
        idx = wrong.index
        eq = pd.DataFrame({j: [tq[j].get(q2.get(p)) if j in tq else np.nan for p in idx] for j in ta.columns}, index=idx)
        ea = ta.reindex(idx)
        conf = per_pair(read("confidence", b)).pivot_table(index="pair_id", columns="judge", values="stated").reindex(idx)
        judges = list(ea.columns)
        for j in judges:
            r = dict(bench=b, judge=j, short=SHORT[j], is_best=j == best)
            for name, s in [("explicit_q", 100 - eq[j]), ("explicit_qa", 100 - ea[j]), ("implicit", -conf.get(j))]:
                if s is None:
                    r[name] = np.nan
                    continue
                m = s.notna() & ea[j].notna()   # same pairs for all three scores
                r[name] = auroc(yb[m].values, s[m].values)
                r[f"n_{name}"] = int(m.sum())
            s = 100 - ea[j]
            mr = s.notna() & (wrong[j] == 0)
            r["explicit_qa_when_right"] = auroc(yb[mr].values, s[mr].values)
            mi = s.notna() & conf[j].notna() if j in conf else s.notna() & False
            r["rho_qa_vs_implicit"] = float(stats.spearmanr(s[mi], -conf[j][mi])[0]) if mi.sum() > 10 else np.nan
            r["rho_q_vs_qa"] = float(stats.spearmanr((100 - eq[j])[s.notna() & eq[j].notna()],
                                                     s[s.notna() & eq[j].notna()])[0])
            r["mean_pred_qa"] = float(ea[j].mean())
            r["share_pred_ge_90"] = float((ea[j] >= 90).mean())
            rows.append(r)
        # pooled over predictors that are not the expert (mean within-judge rank)
        preds = [j for j in judges if j != best]
        P = {}
        for name, frame in [("explicit_q", 100 - eq[preds]), ("explicit_qa", 100 - ea[preds]),
                            ("implicit", -conf[[j for j in preds if j in conf]])]:
            score = frame.rank(pct=True).mean(1)
            m = score.notna()
            P[name] = auroc(yb[m].values, score[m].values)
        pooled.append(dict(bench=b, expert=best, predictors=len(preds), **P))
    T, Pd = pd.DataFrame(rows), pd.DataFrame(pooled)
    nb = T[~T.is_best]
    summ = {f"mean_{c}": float(nb[c].mean()) for c in ["explicit_q", "explicit_qa", "implicit", "explicit_qa_when_right",
                                                      "rho_qa_vs_implicit", "rho_q_vs_qa"]}
    summ["qa_minus_implicit_wilcoxon_p"] = float(stats.wilcoxon(nb.explicit_qa - nb.implicit).pvalue)
    summ["q_above_0_5_sign_p"] = float(stats.binomtest(int((nb.explicit_q > .5).sum()), len(nb), .5, alternative="greater").pvalue)
    (OUT / "difficulty_prediction.json").write_text(json.dumps(dict(summary=summ, rows=rows, pooled=pooled), indent=1, default=float))
    L = ["# Explicit predictions of expert difficulty vs implicit doubt", "",
         "AUROC for the best judge's errors (wrong in either order, all pairs); 0.5 = chance. explicit_q = question only; "
         "explicit_qa = with both answers; implicit = the judge's low stated confidence on its own verdict.", "",
         "## Summary (non-expert predictors)", "", "\n".join(f"- {k}: {v:.3f}" for k, v in summ.items()), "",
         "## Per judge", "", T.drop(columns=["judge"]).round(3).to_markdown(index=False), "",
         "## Pooled over non-expert predictors (mean within-judge rank)", "", Pd.round(3).to_markdown(index=False), ""]
    (OUT / "difficulty_prediction.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
