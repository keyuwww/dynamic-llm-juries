"""Figures for the README, drawn from the cascade_results.csv / cascade_curves.csv / probe_seeds.csv written by cascade_eval.py.
The measure is plain: the accuracy of the whole cascade when the 20% of items the signal trusts least are escalated to the stronger judge, in accuracy points above what escalating
20% of the items at random would give."""
import os
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

here = os.path.dirname(os.path.abspath(__file__)); out = os.path.join(here, "figures"); os.makedirs(out, exist_ok=True)
RUNS = [("Qwen3.5-4B", "results_cascade_4b_v3"), ("Qwen3.5-9B", "results_cascade_9b_v3"), ("gpt-oss-20b", "results_cascade_oss_v3")]
BLUE, ORANGE, AQUA, GRAY, INK, INK2, GRID, SURF = "#2a78d6", "#eb6834", "#1baf7a", "#8b8a85", "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
                     "font.size": 9.5, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True})
BN = {"bff": "BFF-Bench", "rb2safety": "RewardBench-2 Safety", "judgebench": "JudgeBench"}
PROBE = "probe (paper's layer)"
NAME = {PROBE: "Probe (the judge's activations)", "consistency (N=10)": "10 reruns: agreement with itself", "semantic entropy (N=10)": "10 reruns: semantic entropy",
        "verbalized": "Stated confidence (0-100)", "cut-off only (free rule)": "Free rule: escalate if the output was cut off", "token log-prob (perplexity)": "Token probabilities: log-prob (perplexity)",
        "MaxProb (mean over tokens)": "Token probabilities: MaxProb", "energy (log-sum-exp)": "Token probabilities: energy", "token entropy": "Token probabilities: entropy",
        "verdict-token prob": "Token probabilities: verdict token", "other judges disagree": "Other judges disagree (needs 2-7 other judges)"}


def load():
    rows = []
    for L, d in RUNS:
        r = pd.read_csv(os.path.join(here, d, "cascade_results.csv")); r["L"] = L; rows.append(r)
    R = pd.concat(rows, ignore_index=True); R["t"] = R.target.apply(lambda s: "top3" if s.startswith("saved top-3") else ("best" if s.startswith("best saved") else "reasoning"))
    R = R[((R.bench != "judgebench") & (R.t == "top3")) | ((R.bench == "judgebench") & (R.t == "reasoning"))].copy().reset_index(drop=True)
    R["signal"] = R.signal.str.replace(r"other judges disagree.*", "other judges disagree", regex=True).str.replace(r"probe \(layer \d+, paper\)", PROBE, regex=True)
    for L, d in RUNS:                                      # the probe is trained once per seed: use the mean over seeds when the seed run recorded it (the other signals involve no training)
        S = pd.read_csv(os.path.join(here, d, "probe_seeds.csv"))
        if "acc20_mean" not in S:
            continue
        for i, r in R[(R.L == L) & (R.signal == PROBE)].iterrows():
            hit = S[(S.bench == r.bench) & (S.target == r.target[:60])]
            if len(hit):
                R.loc[i, "acc_at_20"] = hit["acc20_mean"].iloc[0]
    R = R[R.signal != "probe (validation layer)"].copy()
    R["rand20"] = R.L_only + 0.2 * (R.H_only - R.L_only); R["pts"] = (R.acc_at_20 - R.rand20) * 100
    return R


def kind(sig):
    if sig == PROBE:
        return "probe"
    if sig.startswith(("consistency", "semantic", "other judges")):
        return "extra"
    return "cheap"


def fig_by_judge(R):
    """Accuracy of the final verdicts with 20% escalated, for each cheap judge on each benchmark (no averaging). Short horizontal lines = reference points for that judge."""
    A = R.pivot_table(index=["bench", "L"], columns="signal", values="acc_at_20") * 100; base = R[R.signal == PROBE].set_index(["bench", "L"])[["L_only", "rand20", "H_only"]] * 100
    sigs = [(PROBE, "Probe", BLUE, "o"), ("verbalized", "Stated confidence", AQUA, "s"), ("consistency (N=10)", "10 reruns", ORANGE, "^"), ("cut-off only (free rule)", "Free cut-off rule", GRAY, "D")]
    judges = [L for L, _ in RUNS]; fig, axs = plt.subplots(1, 3, figsize=(13.8, 5.6))
    for ax, b in zip(axs, ["bff", "rb2safety", "judgebench"]):
        allv = [base.loc[(b, L)][c] for L in judges for c in ("L_only", "rand20", "H_only")] + [A.loc[(b, L), s] for L in judges for s, _, _, _ in sigs]; lo, hi = min(allv) - 1.5, max(allv) + 2.2
        for j, L in enumerate(judges):
            r = base.loc[(b, L)]
            for y, ls, lw in ((r.L_only, "--", 1.5), (r.rand20, ":", 2.0), (r.H_only, "-", 1.5)):
                ax.hlines(y, j - 0.42, j + 0.42, color=INK2, ls=ls, lw=lw, zorder=1)
            for k, (s_, lab, c, m) in enumerate(sigs):
                v = A.loc[(b, L), s_]; x = j + (k - 1.5) * 0.17; ax.scatter(x, v, s=105, color=c, marker=m, edgecolor=SURF, linewidth=1.0, zorder=3)
                if s_ == PROBE:
                    ax.text(x - 0.055, v, f"{v:.1f}", ha="right", va="center", fontsize=8.5, fontweight="bold", color=BLUE)
        ax.set_xticks(range(3)); ax.set_xticklabels(judges); ax.set_xlim(-0.55, 2.55); ax.set_ylim(lo, hi); ax.set_title(BN[b], loc="left", fontsize=11.5, pad=8); ax.grid(axis="x", visible=False)
        ax.set_ylabel("accuracy of the final verdicts (%)")
    from matplotlib.lines import Line2D
    fig.legend(handles=[Line2D([], [], color=INK2, ls="--", lw=1.5, label="cheap judge alone"), Line2D([], [], color=INK2, ls=":", lw=2.0, label="random 20% escalated"), Line2D([], [], color=INK2, ls="-", lw=1.5, label="stronger judge alone"),
                        Line2D([], [], marker="o", color="none", markerfacecolor=BLUE, markersize=9, label="probe (value shown)"), Line2D([], [], marker="s", color="none", markerfacecolor=AQUA, markersize=9, label="stated confidence"),
                        Line2D([], [], marker="^", color="none", markerfacecolor=ORANGE, markersize=9, label="10 reruns (about 12x cost)"), Line2D([], [], marker="D", color="none", markerfacecolor=GRAY, markersize=8, label="free cut-off rule")],
               loc="lower center", ncol=7, fontsize=8.6, frameon=False)
    fig.suptitle("Accuracy of the final verdicts with 20% escalated: each cheap judge on each benchmark", x=0.01, ha="left", fontsize=12); fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    fig.savefig(os.path.join(out, "fig1_accuracy_by_judge.png"), dpi=150); plt.close(fig)


def fig_curves():
    C = pd.read_csv(os.path.join(here, "results_cascade_4b_v3", "cascade_curves.csv")); R = pd.read_csv(os.path.join(here, "results_cascade_4b_v3", "cascade_results.csv"))
    pick = {"bff": "saved top-3", "rb2safety": "saved top-3", "judgebench": "Qwen3.5-9B"}; fig, axs = plt.subplots(1, 3, figsize=(11.5, 4.2))
    lines = [("probe (layer 16, paper)", "Probe", BLUE, "-"), ("consistency (N=10)", "10 reruns (12x cost)", ORANGE, "-"), ("token log-prob (perplexity)", "Token log-prob", AQUA, "-"),
             ("random escalation", "random escalation", INK2, "--"), ("oracle", "oracle (escalate exactly the 4B's errors)", "#b9b8b2", ":")]
    for ax, b in zip(axs, pick):
        tgt = [t for t in C[C.bench == b].target.unique() if t.startswith(pick[b])][0]; d = C[(C.bench == b) & (C.target == tgt)]; r = R[(R.bench == b) & (R.target == tgt)].iloc[0]
        for s, lab, c, ls in lines:
            x = d[d.signal == s]; ax.plot(x.rate * 100, x.acc, color=c, ls=ls, lw=2.0 if s.startswith(("probe", "consistency", "token")) else 1.3, label=lab)
        ax.axhline(r.H_only, color=INK, lw=1.0, alpha=0.55, label="stronger judge alone"); ax.axvline(20, color=INK2, lw=0.8, alpha=0.4)
        ax.set_title(f"{BN[b]}: 4B -> " + ("top-3 saved judges" if b != "judgebench" else "Qwen3.5-9B"), loc="left", fontsize=10); ax.set_xlabel("share of items escalated (%)"); ax.set_xlim(0, 100)
        ax.set_ylim(r.L_only - 0.02, max(r.H_only, d.acc.max()) + 0.02)
    axs[0].set_ylabel("accuracy of the cascade"); h, l = axs[0].get_legend_handles_labels(); fig.legend(h, l, loc="lower center", ncol=6, fontsize=8.5, frameon=False)
    fig.suptitle("Accuracy as more of the 4B's least-trusted verdicts go to the stronger judge (vertical line = 20%)", x=0.01, ha="left", fontsize=11); fig.tight_layout(rect=(0, 0.07, 1, 0.97))
    fig.savefig(os.path.join(out, "fig2_cascade_curves.png"), dpi=150); plt.close(fig)


def fig_layers(R):
    """Top: how well the probe separates right from wrong verdicts (AUROC) when read from each layer, per benchmark. Bottom: the error the validation rule looks at, and the layer it picks."""
    paper = {"Qwen3.5-4B": 16, "Qwen3.5-9B": 16, "gpt-oss-20b": 8}; col = {"bff": BLUE, "rb2safety": ORANGE, "judgebench": AQUA}
    have = [L for L, _ in RUNS if os.path.exists(os.path.join(here, "results_layer_sweep", f"layer_sweep_{L}.csv"))]
    if not have:
        return
    fig, axs = plt.subplots(2, len(have), figsize=(5.0 * len(have), 7.4), squeeze=False)
    for j, L in enumerate(have):
        D = pd.read_csv(os.path.join(here, "results_layer_sweep", f"layer_sweep_{L}.csv")); ax, bx = axs[0, j], axs[1, j]
        for b in ("bff", "rb2safety", "judgebench"):
            ax.plot(D.layer, D[f"{b}_auroc"], color=col[b], lw=2.2, marker="o", ms=3.5)
        ax.axhline(0.5, color=INK2, lw=1.0, ls="--"); ax.set_ylim(0.45, 1.0); ax.set_xlim(-0.5, D.layer.max() + 0.5); ax.set_title(L, loc="left", fontsize=12, pad=8)
        ax.set_ylabel("AUROC: right vs wrong verdicts\n(0.5 = coin flip, 1.0 = perfect)" if j == 0 else ""); ax.tick_params(labelbottom=False)
        ax.text(D.layer.max() * 0.5, 0.455, "coin flip (0.5)", ha="center", va="bottom", fontsize=8, color=INK2)
        bx.plot(D.layer, D.val_brier_mean, color=INK, lw=2.4); V = D[[f"val_brier_fold{k}" for k in range(5)]]; picks = [int(D.layer.iloc[int(V.iloc[:, k].values.argmin())]) for k in range(5)]
        for p in sorted(set(picks)):
            bx.scatter(p, float(D.val_brier_mean[D.layer == p].iloc[0]), marker="v", s=110 + 40 * picks.count(p), color=ORANGE, zorder=4, edgecolor=SURF, linewidth=1.0)
        bx.set_xlim(-0.5, D.layer.max() + 0.5); bx.set_xlabel("layer (0 = input, higher = deeper)"); bx.set_ylabel("validation error (Brier)\nlower = the rule prefers this layer" if j == 0 else "")
        for a_ in (ax, bx):
            a_.axvline(paper[L], color=INK, lw=1.0, ls=":", alpha=0.75)
    from matplotlib.lines import Line2D
    fig.legend(handles=[Line2D([], [], color=BLUE, lw=2.2, marker="o", ms=4, label="BFF"), Line2D([], [], color=ORANGE, lw=2.2, marker="o", ms=4, label="RewardBench-2 Safety"), Line2D([], [], color=AQUA, lw=2.2, marker="o", ms=4, label="JudgeBench"),
                        Line2D([], [], color=INK, lw=2.4, label="validation error (bottom row)"), Line2D([], [], color=ORANGE, marker="v", ls="none", markersize=9, label="layer the validation rule picks (bigger = more of the 5 folds)"),
                        Line2D([], [], color=INK, lw=1.0, ls=":", label="the paper's fixed layer")], loc="lower center", ncol=3, fontsize=9, frameon=False)
    fig.suptitle("The probe at each layer: how well it separates right from wrong verdicts, and which layer the validation rule picks", x=0.01, ha="left", fontsize=12); fig.tight_layout(rect=(0, 0.1, 1, 0.96), h_pad=2.5)
    fig.savefig(os.path.join(out, "fig3_layers.png"), dpi=150); plt.close(fig)


if __name__ == "__main__":
    R = load(); fig_by_judge(R); fig_curves(); fig_layers(R); print("saved", sorted(os.listdir(out)))
