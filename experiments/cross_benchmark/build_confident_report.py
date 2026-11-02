"""Build reports/confident-errors.html from the Study A / B outputs.

Reads results/confident_errors/ (summary.json, A3_gaps.csv, A4_rows.csv, A5_rows.csv, coded.csv, robustness.csv,
probes/*.json) and injects one JSON blob into the template report_templates/confident_errors.html.
Usage: python build_confident_report.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
R = HERE / "results" / "confident_errors"
TEMPLATE = HERE / "report_templates" / "confident_errors.html"
OUT = HERE.parents[1] / "reports" / "confident-errors.html"
LEVELS = ["low", "mid", "high"]


def clean(x):
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, list):
        return [clean(v) for v in x]
    if isinstance(x, float):
        return None if np.isnan(x) else round(x, 4)
    if isinstance(x, (np.floating, np.integer)):
        return clean(x.item())
    return x


def main():
    S = json.load(open(R / "summary.json"))
    D = {}
    # A0 + A2 per scheme
    D["A0"] = {s: S[s]["A0"] for s in ("third", "risk", "fixed")}
    D["A2"] = {s: S[s]["A2"] for s in ("third", "risk", "fixed")}
    # A3 gaps
    g = pd.read_csv(R / "A3_gaps.csv")
    D["A3"] = g.to_dict(orient="records")
    # A4 / A5 (primary scheme), mean over judge x benchmark with spread
    a4 = pd.read_csv(R / "A4_rows.csv")
    agg = a4.groupby("level")[["auc_token", "auc_stated"]].agg(["mean", "std", "count"]).reindex(LEVELS)
    agg.columns = [f"{a}_{b}" for a, b in agg.columns]
    D["A4"] = agg.reset_index().to_dict(orient="records")
    a5 = pd.read_csv(R / "A5_rows.csv")
    a5 = a5[a5.split == "all W"]
    D["A5"] = a5.groupby(["signal", "level"]).auc.agg(["mean", "std", "count"]).reset_index().to_dict(orient="records")
    # coding
    c = pd.read_csv(R / "coded.csv")
    wrong = c[c.judge_verdict != c.gold]
    D["coding_types"] = pd.crosstab(wrong.cell, wrong.error_type).reset_index().to_dict(orient="records")
    yes = lambda s: float((s.dropna() == "yes").mean())  # noqa: E731
    D["coding"] = c.groupby("cell").agg(
        n=("code_id", "size"), gold_q=("gold_questionable", yes), noticed=("noticed_decisive_difference", yes),
        hedge=("hedging_or_self_correction", yes), close=("says_answers_close", yes),
        reads_high=("perceived_confidence", lambda s: float((s.dropna() == "high").mean())),
        reads_low=("perceived_confidence", lambda s: float((s.dropna() == "low").mean()))).reset_index() \
        .to_dict(orient="records")
    D["robust"] = pd.read_csv(R / "robustness.csv").to_dict(orient="records")
    # probes
    D["probes"] = {}
    for f in sorted((R / "probes").glob("*.json")):
        D["probes"][f.stem] = json.load(open(f))
    blob = json.dumps(clean(D), separators=(",", ":"), default=str)
    text_js = TEMPLATE.with_name("confident_errors_text.js")
    btext = text_js.read_text() if text_js.exists() else ""
    OUT.write_text(TEMPLATE.read_text().replace("__DATA__", blob).replace("__BTEXT__", btext))
    print("wrote", OUT, len(blob) // 1000, "KB data; probes:", list(D["probes"]))


if __name__ == "__main__":
    main()
