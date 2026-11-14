"""Two slide figures.

1. layer_vs_final.png: for each judge, agreement with the human label (Cohen's kappa) of its final verdict (grey) vs the
   best single layer read with the logit lens (blue), on RB2 Safety and BFF. The layer is picked on one random half of
   the items and scored on the other half; mean over 200 splits (seed 0), same protocol as held_out_significance.py.
   Data: held_out_final_vs_layer.json (BFF = our rubric "rules" fields; Qwen3.6-35B-A3B only has the real-rubric run).
2. weight_edit.png: Ingrid's weight-edit pilot (Qwen3.5-0.8B; numbers from "Hidden Judge Knowledge Pilot",
   branch ingrid/weight-space-judge, experiments/weight_space/): held-out AUROC before vs after the edit.

  python3 experiments/interp/slide_figs/make_figs.py
"""
import json
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")
HERE = Path(__file__).resolve().parent
INK, INK2, INK3, GRID = "#0E1E33", "#44546A", "#8A96A8", "#E3E8EF"
GREY, BLUE, RED, GREEN = "#AEB8C6", "#2F5FE0", "#C2412D", "#2E9A57"
plt.rcParams.update({"font.family": "Helvetica Neue", "font.size": 11, "text.color": INK, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK, "axes.edgecolor": GRID})

JUDGES = [("qwen3.5-4b", "Qwen3.5-4B"), ("gpt-oss-120b", "gpt-oss-120b"), ("nvidia-nemotron-3-nano-30b-a3b-bf16", "Nemotron-3 Nano 30B"),
          ("qwen3.6-35b-a3b", "Qwen3.6-35B"), ("nvidia-nemotron-3-super-120b-a12b-bf16", "Nemotron-3 Super 120B"),
          ("gpt-oss-20b", "gpt-oss-20b"), ("qwen3.5-9b", "Qwen3.5-9B")]


def clear(r):  # a gain we count: >= 0.05 kappa and the layer wins on >= 95% of the held-out splits
    return r["gap"] >= 0.05 and r["pos"] >= 0.95 * r["n"]


def fig_layers():
    d = json.load(open(HERE / "held_out_final_vs_layer.json"))
    key = {"Safety": lambda m: f"rb2safety|{m}",
           "BFF": lambda m: f"bff_rules|{m}" if m != "qwen3.6-35b-a3b" else f"bff_rules2_rules|{m}"}
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.4), sharey=True, facecolor="white")
    for ax, (bench, sub) in zip(axes, (("Safety", "RewardBench 2 Safety"), ("BFF", "BFF-Bench (finance)"))):
        n_clear = 0
        for i, (m, name) in enumerate(JUDGES):
            r = d[key[bench](m)]
            y = len(JUDGES) - 1 - i
            f, l = r["final"], r["layer"]
            ok = clear(r)
            n_clear += ok
            worse = r["gap"] < -0.05 and r["pos"] <= 0.05 * r["n"]
            col = BLUE if ok else (RED if worse else INK3)
            ax.plot([f, l], [y, y], color=col if ok or worse else GRID, lw=3 if ok else 2, solid_capstyle="round", zorder=1)
            ax.scatter(f, y, s=90, color=GREY, edgecolor="white", lw=1.5, zorder=3)
            ax.scatter(l, y, s=90, color=col if (ok or worse) else "white", edgecolor=col, lw=1.8, zorder=4)
            lab = f"{r['gap']:+.2f}" if abs(r["gap"]) >= 0.02 else "±0"
            x_txt = max(f, l) + 0.035
            ax.text(x_txt, y, lab, va="center", ha="left", fontsize=10.5, color=col if (ok or worse) else INK3,
                    fontweight="bold" if ok else "normal")
        ax.axvline(0, color=INK3, lw=1, ls=(0, (3, 3)), zorder=0)
        ax.set_xlim(-0.12, 1.08)
        ax.set_ylim(-0.7, len(JUDGES) - 0.3)
        ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
        ax.set_xticklabels(["0\nchance", "0.2", "0.4", "0.6", "0.8", "1.0\nperfect"])
        ax.grid(axis="x", color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(length=0)
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.set_title(f"{sub}", loc="left", fontsize=13, fontweight="bold", color=INK, pad=22)
        ax.text(0, 1.015, f"a layer before the last is clearly better for {n_clear} of 7 judges", transform=ax.transAxes, fontsize=10.5,
                color=BLUE, va="bottom")
        ax.set_xlabel("agreement with human labels (Cohen's κ)", fontsize=10.5)
    axes[0].set_yticks(range(len(JUDGES)))
    axes[0].set_yticklabels([n for _, n in JUDGES][::-1], fontsize=11.5)
    # legend
    h = [plt.Line2D([], [], marker="o", ls="", ms=9, mfc=GREY, mec="white", label="final verdict"),
         plt.Line2D([], [], marker="o", ls="", ms=9, mfc=BLUE, mec=BLUE, label="best earlier layer: clearly better"),
         plt.Line2D([], [], marker="o", ls="", ms=9, mfc="white", mec=INK3, label="no clear difference"),
         plt.Line2D([], [], marker="o", ls="", ms=9, mfc=RED, mec=RED, label="worse")]
    fig.legend(handles=h, loc="lower center", ncol=4, frameon=False, fontsize=10.5, bbox_to_anchor=(0.5, 0.0))
    fig.text(0.01, 0.075, "Best layer picked on half of the items, scored on the other half (mean of 200 random splits). "
             "Clearly better = at least +0.05 κ and better in ≥95% of splits.", fontsize=9, color=INK2)
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    fig.savefig(HERE / "layer_vs_final.png", dpi=200, facecolor="white")


def fig_edit():
    # Ingrid's pilot: Qwen3.5-0.8B, held-out test items; AUROC (0.5 = guessing)
    rows = [("Safety", "edited for this", 0.51, 0.95, 0.97), ("BFF finance", "not targeted", 0.71, 0.46, None),
            ("JudgeBench", "not targeted", 0.55, 0.53, None)]
    fig, ax = plt.subplots(figsize=(7.2, 4.6), facecolor="white")
    for i, (name, sub, b, a, knows) in enumerate(rows):
        y = len(rows) - 1 - i
        col = GREEN if a - b > 0.05 else (RED if a - b < -0.05 else INK3)
        if knows is not None:
            ax.scatter(knows, y, marker="|", s=500, color=INK, lw=2.2, zorder=2)
            ax.text(knows, y + 0.3, f"middle layer\nknows {knows:.2f}", ha="center", va="bottom", fontsize=9.5, color=INK)
        ax.annotate("", xy=(a, y), xytext=(b, y), arrowprops=dict(arrowstyle="-|>,head_width=0.35,head_length=0.6",
                                                                   color=col, lw=3, shrinkA=7, shrinkB=6), zorder=3)
        ax.scatter(b, y, s=110, color=GREY, edgecolor="white", lw=1.5, zorder=4)
        ax.scatter(a, y, s=110, color=col, edgecolor="white", lw=1.5, zorder=4)
        off = 0.022
        box = dict(boxstyle="square,pad=0.08", fc="white", ec="none")
        ax.text(b + (off if b > a else -off), y - 0.28, f"{b:.2f}", ha="center", fontsize=10, color=INK2, bbox=box)
        ax.text(a, y - 0.28, f"{a:.2f}", ha="center", fontsize=10.5, color=col, fontweight="bold", bbox=box)
        if abs(a - b) <= 0.05:
            ax.text(max(a, b) + 0.03, y, "no real change", va="center", fontsize=10, color=INK3)
    ax.axvline(0.5, color=INK3, lw=1, ls=(0, (3, 3)), zorder=0)
    ax.text(0.503, len(rows) - 0.3, "chance", ha="left", va="top", fontsize=9, color=INK3)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([f"{n}\n{s}" for n, s, *_ in rows][::-1], fontsize=11.5)
    for lab, (n, s, *_) in zip(ax.get_yticklabels(), rows[::-1]):
        lab.set_fontweight("bold" if s == "edited for this" else "normal")
    ax.set_xlim(0.38, 1.02)
    ax.set_ylim(-0.75, len(rows) - 0.25)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xlabel("judge AUROC on held-out items (0.5 = guessing, 1 = perfect)", fontsize=10.5)
    ax.set_title("Weight edit on Qwen3.5-0.8B: grey = before, colour = after", loc="left", fontsize=12.5,
                 fontweight="bold", pad=12)
    fig.text(0.01, 0.01, "The same edit also makes ordinary text harder to predict (Wikipedia loss rises from 3.30 to 4.29).",
             fontsize=9.5, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(HERE / "weight_edit.png", dpi=200, facecolor="white")




def fig_combined():
    """One wide figure: A = final verdict vs best earlier layer (Safety, BFF), B = weight edit."""
    d = json.load(open(HERE / "held_out_final_vs_layer.json"))
    key = {"Safety": lambda m: f"rb2safety|{m}",
           "BFF": lambda m: f"bff_rules|{m}" if m != "qwen3.6-35b-a3b" else f"bff_rules2_rules|{m}"}
    fig = plt.figure(figsize=(17, 6.2), facecolor="white")
    gs = fig.add_gridspec(1, 4, width_ratios=[1, 1, 0.55, 1.1], wspace=0.08, left=0.125, right=0.985, top=0.80, bottom=0.2)
    axA = [fig.add_subplot(gs[0, 0])]
    axA.append(fig.add_subplot(gs[0, 1], sharey=axA[0]))
    axB = fig.add_subplot(gs[0, 3])
    for ax, (bench, sub) in zip(axA, (("Safety", "RewardBench 2 Safety"), ("BFF", "BFF-Bench (finance)"))):
        n_clear = 0
        for i, (m, name) in enumerate(JUDGES):
            r = d[key[bench](m)]
            y = len(JUDGES) - 1 - i
            f, l = r["final"], r["layer"]
            ok = clear(r)
            n_clear += ok
            worse = r["gap"] < -0.05 and r["pos"] <= 0.05 * r["n"]
            col = BLUE if ok else (RED if worse else INK3)
            ax.plot([f, l], [y, y], color=col if ok or worse else GRID, lw=3 if ok else 2, solid_capstyle="round", zorder=1)
            ax.scatter(f, y, s=80, color=GREY, edgecolor="white", lw=1.5, zorder=3)
            ax.scatter(l, y, s=80, color=col if (ok or worse) else "white", edgecolor=col, lw=1.8, zorder=4)
            lab = f"{r['gap']:+.2f}" if abs(r["gap"]) >= 0.02 else "±0"
            ax.text(max(f, l) + 0.035, y, lab, va="center", ha="left", fontsize=10.5,
                    color=col if (ok or worse) else INK3, fontweight="bold" if ok else "normal")
        ax.axvline(0, color=INK3, lw=1, ls=(0, (3, 3)), zorder=0)
        ax.set_xlim(-0.12, 1.12)
        ax.set_ylim(-0.6, len(JUDGES) - 0.4)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_xticklabels(["0\nchance", "0.25", "0.5", "0.75", "1\nperfect"])
        ax.set_title(sub, loc="left", fontsize=12.5, color=INK, pad=24)
        ax.text(0, 1.015, f"clearly better for {n_clear} of 7 judges", transform=ax.transAxes, fontsize=10.5, color=BLUE, va="bottom")
        ax.set_xlabel("agreement with human labels (κ)", fontsize=10.5)
    axA[0].set_yticks(range(len(JUDGES)))
    axA[0].set_yticklabels([n for _, n in JUDGES][::-1], fontsize=11.5)
    plt.setp(axA[1].get_yticklabels(), visible=False)
    # B: weight edit
    rows = [("Safety", "edited for this", 0.51, 0.95, 0.97), ("BFF finance", "not targeted", 0.71, 0.46, None),
            ("JudgeBench", "not targeted", 0.55, 0.53, None)]
    box = dict(boxstyle="square,pad=0.08", fc="white", ec="none")
    for i, (name, sub, b, a, knows) in enumerate(rows):
        y = len(rows) - 1 - i
        col = GREEN if a - b > 0.05 else (RED if a - b < -0.05 else INK3)
        if knows is not None:
            axB.scatter(knows, y, marker="|", s=500, color=INK, lw=2.2, zorder=2)
            axB.text(knows, y + 0.28, f"layer 14\nknows {knows:.2f}", ha="center", va="bottom", fontsize=9.5, color=INK)
        axB.annotate("", xy=(a, y), xytext=(b, y), arrowprops=dict(arrowstyle="-|>,head_width=0.35,head_length=0.6",
                                                                    color=col, lw=3, shrinkA=7, shrinkB=6), zorder=3)
        axB.scatter(b, y, s=100, color=GREY, edgecolor="white", lw=1.5, zorder=4)
        axB.scatter(a, y, s=100, color=col, edgecolor="white", lw=1.5, zorder=4)
        axB.text(b + (0.022 if b > a else -0.022), y - 0.27, f"{b:.2f}", ha="center", fontsize=10, color=INK2, bbox=box)
        axB.text(a, y - 0.27, f"{a:.2f}", ha="center", fontsize=10.5, color=col, fontweight="bold", bbox=box)
        if abs(a - b) <= 0.05:
            axB.text(max(a, b) + 0.03, y, "no real change", va="center", fontsize=10, color=INK3)
        axB.text(0.36, y, f"{name}\n{sub}", ha="right", va="center", fontsize=11.5, color=INK,
                 fontweight="bold" if knows is not None else "normal", transform=axB.transData)
    axB.axvline(0.5, color=INK3, lw=1, ls=(0, (3, 3)), zorder=0)
    axB.text(0.503, len(rows) - 0.32, "chance", ha="left", va="top", fontsize=9, color=INK3)
    axB.set_yticks([])
    axB.set_xlim(0.38, 1.02)
    axB.set_ylim(-0.6, len(rows) - 0.3)
    axB.set_xticks([0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    axB.set_xlabel("judge AUROC on held-out items (0.5 = guessing)", fontsize=10.5)
    axB.set_title("Qwen3.5-0.8B · grey = before, colour = after", loc="left", fontsize=12.5, color=INK, pad=24)
    axB.text(0, 1.015, "Wikipedia loss also rises from 3.30 to 4.29", transform=axB.transAxes, fontsize=10.5, color=RED, va="bottom")
    for ax in axA + [axB]:
        ax.grid(axis="x", color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(length=0)
        for sp in ax.spines.values():
            sp.set_visible(False)
    # section headers
    pA, pB = axA[1].get_position(), axB.get_position()
    xd = pA.x1 + 0.025
    fig.text(0.012, 0.95, "A   Reading an earlier layer instead of the final verdict", fontsize=14.5, fontweight="bold", color=INK)
    fig.text(0.012, 0.905, "7 judges · layer picked on half the items, scored on the other half (200 splits)", fontsize=10.5, color=INK2)
    fig.text(xd + 0.012, 0.95, "B   Editing the weights to use that layer", fontsize=14.5, fontweight="bold", color=INK)
    fig.text(xd + 0.012, 0.905, "one small judge · RewardBench 2 Safety only", fontsize=10.5, color=INK2)
    fig.add_artist(plt.Line2D([xd] * 2, [0.08, 0.97], color=GRID, lw=1.2, transform=fig.transFigure))
    h = [plt.Line2D([], [], marker="o", ls="", ms=9, mfc=GREY, mec="white", label="final verdict / before edit"),
         plt.Line2D([], [], marker="o", ls="", ms=9, mfc=BLUE, mec=BLUE, label="earlier layer, clearly better (≥ +0.05, ≥95% of splits)"),
         plt.Line2D([], [], marker="o", ls="", ms=9, mfc="white", mec=INK3, label="no clear difference"),
         plt.Line2D([], [], marker="o", ls="", ms=9, mfc=RED, mec=RED, label="worse")]
    fig.legend(handles=h, loc="lower left", ncol=4, frameon=False, fontsize=10.5, bbox_to_anchor=(0.005, 0.0))
    fig.savefig(HERE / "combined.png", dpi=200, facecolor="white")
    print(HERE / "combined.png")


if __name__ == "__main__":
    fig_layers()
    fig_edit()
    fig_combined()
