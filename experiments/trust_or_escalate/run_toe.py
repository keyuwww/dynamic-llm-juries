#!/usr/bin/env python3
"""
B6: Trust-or-Escalate, reproduced from data we already collected (no new API calls).

Trust-or-Escalate (Jung et al., ICLR 2025): a cheap judge answers alone unless its own
confidence falls below a calibrated threshold, in which case the question escalates to a
stronger (more expensive) judge. Coverage = share of questions the cheap tier handles alone.

We already have exactly the two tiers this needs, from the Exp 1 judge run
(experiments/jev_bff/run_jev_bff.py): the SAME item, judged twice --
  cheap tier   = noref  (judge sees only the conversation)
  strong tier  = ref    (judge also sees the expert reference answer -- much more accurate,
                         and more "expensive" in the sense that a reference answer must exist)
Confidence = |p - 0.5| * 2 (from the cheap/noref call). Below the threshold, the item
escalates to the strong/ref verdict instead of the cheap one.

This sweeps the confidence threshold and reports, at each coverage level: overall accuracy
and kappa of the resulting cascade, for both Jev and CLM, plus the two endpoints (tau=0:
never escalate, pure noref; tau=1: always escalate, pure ref).

Usage (repo root):
  uv run python experiments/trust_or_escalate/run_toe.py
Reads experiments/jev_bff/{jev,clm}_bff_results/items.csv
Writes experiments/trust_or_escalate/toe_curve.csv and summary.md
"""
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent


def kappa(y, yhat):
    n = len(y)
    if n == 0:
        return float("nan")
    po = sum(a == b for a, b in zip(y, yhat)) / n
    p1, q1 = sum(y) / n, sum(yhat) / n
    pe = p1 * q1 + (1 - p1) * (1 - q1)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def cascade_curve(items_csv, thresholds=None):
    thresholds = thresholds if thresholds is not None else [i / 20 for i in range(21)]
    df = pd.read_csv(items_csv)
    noref = df[df.cond == "noref"].set_index("qid_turn" if "qid_turn" in df.columns else df.columns[0])
    # items.csv doesn't have a shared per-turn key across cond rows other than (qid, turn); build one
    df["key"] = df["qid"].astype(str) + "-t" + df["turn"].astype(str)
    noref = df[df.cond == "noref"].set_index("key")
    ref = df[df.cond == "ref"].set_index("key")
    common = noref.index.intersection(ref.index)
    noref, ref = noref.loc[common], ref.loc[common]
    conf = (noref["p"] - 0.5).abs() * 2

    rows = []
    for tau in thresholds:
        escalate = conf < tau
        p_final = noref["p"].where(~escalate, ref["p"])
        y = noref["human"].tolist()  # same human label either way (same underlying item)
        yhat = [int(x >= 0.5) for x in p_final]
        acc = sum(a == b for a, b in zip(y, yhat)) / len(y)
        rows.append(dict(tau=tau, coverage=1 - escalate.mean(), escalation_rate=escalate.mean(),
                          accuracy=acc, kappa=kappa(y, yhat), n=len(y)))
    return pd.DataFrame(rows)


def main():
    out = HERE
    out.mkdir(parents=True, exist_ok=True)
    backends = {
        "jev": REPO / "experiments/jev_bff/jev_bff_results/items.csv",
        "clm": REPO / "experiments/jev_bff/clm_bff_results/items.csv",
    }
    all_curves = {}
    for name, path in backends.items():
        if not path.exists():
            print(f"skip {name}: {path} not found")
            continue
        all_curves[name] = cascade_curve(path)
        all_curves[name].to_csv(out / f"toe_curve_{name}.csv", index=False)

    L = ["# B6 Trust-or-Escalate: cheap (noref) -> strong (ref) cascade", "",
         "Reproduced from the Exp 1 judge data (same item judged both noref and ref) -- no new API "
         "calls. Confidence = |p-0.5|x2 from the cheap/noref call; below threshold tau, escalate to "
         "the ref verdict instead. tau=0 is pure noref (never escalate); tau=1 is pure ref (always "
         "escalate).", ""]
    for name, curve in all_curves.items():
        L += [f"## {name.upper()}", "",
              "| tau | Coverage | Escalation rate | Accuracy | Cohen's kappa | n |",
              "|---|---|---|---|---|---|"]
        for _, r in curve.iterrows():
            L.append(f"| {r.tau:.2f} | {r.coverage:.3f} | {r.escalation_rate:.3f} | {r.accuracy:.3f} | {r.kappa:.3f} | {int(r.n)} |")
        L.append("")
        # headline: coverage at which the cascade matches pure-ref accuracy/kappa (if it ever does)
        pure_ref = curve.iloc[-1]
        best_below = curve[curve.kappa >= pure_ref.kappa - 0.02]
        if len(best_below):
            cheapest = best_below.sort_values("coverage", ascending=False).iloc[0]
            L.append(f"Cheapest point within 0.02 kappa of pure-ref ({pure_ref.kappa:.3f}): "
                      f"tau={cheapest.tau:.2f}, coverage={cheapest.coverage:.3f}, kappa={cheapest.kappa:.3f}.")
        L.append("")
    (out / "summary.md").write_text("\n".join(L))
    print("\n".join(L))
    metrics = {name: curve.to_dict(orient="records") for name, curve in all_curves.items()}
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
