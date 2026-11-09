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


def _ref_lines(ax, cheap, rand, strong, top_labels=True):
    for x, lab, ls, lw in ((cheap, "cheap judge alone", "--", 1.2), (rand, "random 20% escalated", ":", 1.6), (strong, "stronger judge alone", "-", 1.2)):
        ax.axvline(x, color=INK2, ls=ls, lw=lw, alpha=0.8, zorder=1)
    return [(cheap, "cheap judge alone", "right", 0.0), (rand, "random 20% escalated", "left", 0.0), (strong, "stronger judge alone", "center", 0.75)]


def fig_overview(R):
    """Accuracy of the final verdicts when the 20% least-trusted verdicts are escalated, averaged over the 9 settings, with the reference points drawn as vertical lines."""
    P = R.groupby("signal").acc_at_20.mean() * 100; base = R[R.signal == PROBE]; cheap, rand, strong = base.L_only.mean() * 100, base.rand20.mean() * 100, base.H_only.mean() * 100
    P = P.sort_values(); fig, ax = plt.subplots(figsize=(9.8, 6.2)); col = {"probe": BLUE, "extra": ORANGE, "cheap": GRAY}
    COSTTAG = {"consistency (N=10)": "about 12x cost", "semantic entropy (N=10)": "about 12x cost", "other judges disagree": "needs other judges"}
    marks = _ref_lines(ax, cheap, rand, strong)
    for i, sname in enumerate(P.index):
        ax.hlines(i, 70, P[sname], color=GRID, lw=1.0, zorder=1); ax.scatter(P[sname], i, s=150, color=col[kind(sname)], zorder=3, edgecolor=SURF, linewidth=1.2)
        ax.text(P[sname] + 0.25, i, f"{P[sname]:.1f}%", va="center", fontsize=9.5, fontweight="bold" if kind(sname) == "probe" else "normal", color=INK, bbox=dict(facecolor=SURF, edgecolor="none", pad=1.2), zorder=4)
    ax.set_yticks(range(len(P))); ax.set_yticklabels([NAME[s].replace(" (needs 2-7 other judges)", "") + "   [" + COSTTAG.get(s, "no extra cost") + "]" for s in P.index])
    ax.set_xlim(75.5, 84.5); ax.set_ylim(-0.7, len(P) + 1.6); ax.grid(axis="y", visible=False); ax.set_xlabel("accuracy of the final verdicts (%), average over 9 settings (3 judges x 3 benchmarks)")
    for x, lab, ha, dy in marks:
        ax.text(x + (-0.08 if ha == "right" else 0.08 if ha == "left" else 0), len(P) - 0.15 + dy, lab, ha=ha, va="bottom", fontsize=8.5, color=INK2)
    fig.suptitle("Accuracy of the final verdicts when the 20% least-trusted verdicts are escalated", x=0.01, ha="left", fontsize=12, y=0.985)
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([], [], marker="o", color="none", markerfacecolor=BLUE, markersize=10, label="probe on the judge's activations"), Line2D([], [], marker="o", color="none", markerfacecolor=GRAY, markersize=10, label="other signals, no extra cost"),
                       Line2D([], [], marker="o", color="none", markerfacecolor=ORANGE, markersize=10, label="signals that need 10 reruns or other judges")], loc="upper center", bbox_to_anchor=(0.42, -0.1), ncol=1, fontsize=9, frameon=False)
    fig.tight_layout(rect=(0, 0, 1, 0.96)); fig.savefig(os.path.join(out, "fig1_accuracy_overview.png"), dpi=150); plt.close(fig)


def fig_by_bench(R):
    """Same view per benchmark: accuracy (%) of the final verdicts, averaged over the 3 cheap judges of that benchmark."""
    sigs = [(PROBE, "Probe", BLUE), ("consistency (N=10)", "10 reruns", ORANGE), ("other judges disagree", "Other judges disagree", ORANGE), ("token log-prob (perplexity)", "Token probabilities", GRAY),
            ("verbalized", "Stated confidence", GRAY), ("cut-off only (free rule)", "Free cut-off rule", GRAY)]
    fig, axs = plt.subplots(1, 3, figsize=(13.2, 4.8), sharey=True)
    for ax, b in zip(axs, ["bff", "rb2safety", "judgebench"]):
        d = R[R.bench == b]; base = d[d.signal == PROBE]; cheap, rand, strong = base.L_only.mean() * 100, base.rand20.mean() * 100, base.H_only.mean() * 100; marks = _ref_lines(ax, cheap, rand, strong)
        vals = [d[d.signal == s].acc_at_20.mean() * 100 for s, _, _ in sigs]; lo, hi = min(vals + [cheap, rand, strong]) - 1.5, max(vals + [cheap, rand, strong]) + 2.0
        for i, ((s, lab, c), v) in enumerate(zip(sigs, vals)):
            y = len(sigs) - 1 - i; ax.hlines(y, lo, v, color=GRID, lw=1.0, zorder=1); ax.scatter(v, y, s=130, color=c, zorder=3, edgecolor=SURF, linewidth=1.2); ax.text(v + (hi - lo) * 0.02, y, f"{v:.1f}", va="center", fontsize=9, fontweight="bold" if s == PROBE else "normal", bbox=dict(facecolor=SURF, edgecolor="none", pad=1.0), zorder=4)
        ax.set_xlim(lo, hi); ax.set_ylim(-0.7, len(sigs) + 1.5); ax.set_yticks(range(len(sigs))); ax.set_yticklabels([lab for _, lab, _ in sigs][::-1]); ax.grid(axis="y", visible=False); ax.set_title(BN[b], loc="left", fontsize=11, pad=8)
        ax.set_xlabel("accuracy of the final verdicts (%)")
        ax.set_ylim(-0.7, len(sigs) - 0.3)
    from matplotlib.lines import Line2D
    fig.legend(handles=[Line2D([], [], color=INK2, ls="--", lw=1.4, label="cheap judge alone"), Line2D([], [], color=INK2, ls=":", lw=1.8, label="random 20% escalated"), Line2D([], [], color=INK2, ls="-", lw=1.4, label="stronger judge alone"),
                        Line2D([], [], marker="o", color="none", markerfacecolor=BLUE, markersize=9, label="probe"), Line2D([], [], marker="o", color="none", markerfacecolor=ORANGE, markersize=9, label="needs 10 reruns or other judges"),
                        Line2D([], [], marker="o", color="none", markerfacecolor=GRAY, markersize=9, label="other signals, no extra cost")], loc="lower center", ncol=6, fontsize=8.8, frameon=False)
    fig.suptitle("Accuracy with 20% escalated, by benchmark (average of the 3 cheap judges). The probe wins only on RewardBench-2", x=0.01, ha="left", fontsize=11.5); fig.tight_layout(rect=(0, 0.08, 1, 0.95))
    fig.savefig(os.path.join(out, "fig2_accuracy_by_benchmark.png"), dpi=150); plt.close(fig)


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
    fig.savefig(os.path.join(out, "fig3_cascade_curves.png"), dpi=150); plt.close(fig)


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
    fig.savefig(os.path.join(out, "fig4_layers.png"), dpi=150); plt.close(fig)


if __name__ == "__main__":
    R = load(); fig_overview(R); fig_by_bench(R); fig_curves(); fig_layers(R); print("saved", sorted(os.listdir(out)))
