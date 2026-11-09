#!/usr/bin/env python
"""Cross-judge summary of the cascade experiment: for each cheap judge x benchmark, the share of the oracle's gain each signal captures (target = the strongest available:
the saved top-3 vote on BFF / RewardBench-2 Safety, the other reasoning judge on JudgeBench), the mean over the settings, and the extra generation each signal needs."""
import sys
import pandas as pd

COST = {"probe (paper's layer)": "1x", "probe (validation layer)": "1x", "verbalized": "1x", "cut-off only (free rule)": "1x", "token log-prob (perplexity)": "1x", "token entropy": "1x",
        "MaxProb (mean over tokens)": "1x", "energy (log-sum-exp)": "1x", "verdict-token prob": "1x", "consistency (N=10)": "~12x", "semantic entropy (N=10)": "~12x"}


def main(dirs):
    rows = []
    for L, d in dirs:
        r = pd.read_csv(f"{d}/cascade_results.csv"); r["L"] = L; rows.append(r)
    R = pd.concat(rows); R["t"] = R.target.apply(lambda s: "top3" if s.startswith("saved top-3") else ("best" if s.startswith("best saved") else "reasoning"))
    sel = R[((R.bench != "judgebench") & (R.t == "top3")) | ((R.bench == "judgebench") & (R.t == "reasoning"))].copy()
    sel["signal"] = sel.signal.str.replace(r"other judges disagree.*", "other judges disagree (needs 2-7 other judges)", regex=True).str.replace(r"probe \(layer \d+, paper\)", "probe (paper's layer)", regex=True)
    P = sel.pivot_table(index="signal", columns=["L", "bench"], values="share_of_oracle"); P["mean"] = P.mean(1); P["extra cost"] = [COST.get(i, "needs other judges" if i.startswith("other") else "") for i in P.index]
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print("SHARE OF THE ORACLE'S GAIN (higher is better), sorted by the mean over all settings\n"); print(P.sort_values("mean", ascending=False).round(2).to_string())
    G = sel.pivot_table(index="signal", columns=["L", "bench"], values="gain_over_random"); G["mean"] = G.mean(1)
    print("\nGAIN OVER RANDOM ESCALATION (accuracy points)\n"); print(G.sort_values("mean", ascending=False).round(3).to_string())


if __name__ == "__main__":
    main([a.split("=") for a in sys.argv[1:]])
