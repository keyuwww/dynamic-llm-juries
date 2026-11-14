"""Where the judge direction is, and what it separates.
 (1) direction_layers.png: held-out ranking of the judge direction at every 2nd layer (MMLU-Redux, MATH), each judge's
     chosen layer marked, with the verdict's own ranking as a dashed reference line.
 (2) direction_hist_mmlu.png: right vs wrong answers along the judge direction ("knows") and along the verdict score
     ("says"), each minus its question's average and scaled to unit spread; per judge, solved vs not solved.
Inputs: out_<bench>/<model>/direction_choice_<bench>.json, out_mmlu/hist_mmlu.json (azure/dir_hist.py on the cluster).

  python3 experiments/beyond_capability/plot_direction.py
"""
import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
MODELS = {"qwen3.5-9b": ("Qwen3.5-9B", "#2a78d6"), "llama3.1-8b": ("Llama-3.1-8B", "#eb6834")}
SAYS = {("mmlu", "qwen3.5-9b"): 0.674, ("mmlu", "llama3.1-8b"): 0.511, ("math", "qwen3.5-9b"): 0.663, ("math", "llama3.1-8b"): 0.541}
RIGHT, WRONG = "#1baf7a", "#e87ba4"  # categorical slots 3 and 5: right / wrong answers (blue/orange stay = models)
INK, INK2, GRID, BG = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2})


def style(ax):
    ax.set_facecolor(BG)
    ax.grid(color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)


def layers_plot(benches=(("mmlu", "MMLU-Redux"), ("math", "MATH")), fname="direction_layers.png"):
    fig, axes = plt.subplots(1, len(benches), figsize=(5 * len(benches) + 1.5 * (len(benches) == 1), 4.4), sharey=True,
                             facecolor=BG, squeeze=False)
    axes = axes[0]
    for ax, (bench, title) in zip(axes, benches):
        style(ax)
        ax.axhline(0.5, color=INK2, lw=1, ls=(0, (3, 3)))
        ax.text(0.5, 0.497, "chance", color=INK2, fontsize=8.5, va="top")
        for m, (nm, col) in MODELS.items():
            ch = json.load(open(HERE / f"out_{bench}/{m}/direction_choice_{bench}.json"))
            xs = sorted(int(k) for k in ch["scores"])
            ys = [ch["scores"][str(x)] for x in xs]
            ax.plot(xs, ys, color=col, lw=2, marker="o", ms=4, label=f"{nm}: judge direction (knows)")
            ax.axhline(SAYS[(bench, m)], color=col, lw=1.2, ls=(0, (4, 3)), label=f"{nm}: its verdict (says)")
            L = ch["layer"]
            ax.scatter([L], [ch["scores"][str(L)]], s=110, facecolor=BG, edgecolor=col, linewidth=2.2, zorder=5)
            ax.annotate(f"layer {L}", (L, ch["scores"][str(L)]), textcoords="offset points", xytext=(0, 9), ha="center",
                        fontsize=8.5, color=INK, fontweight="bold")
        ax.set_title(title, loc="left", color=INK, fontsize=11)
        ax.set_xlabel("layer (input → output)")
        ax.set_xlim(0, 33)
        ax.set_ylim(0.47, 0.75)
    axes[0].set_ylabel("ranking: right above wrong, same question\n(held-out, 0.50 = chance)")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, fontsize=8.5, loc="lower center", ncol=2, labelcolor=INK)
    fig.suptitle("Where the judge direction lives: how well each layer's direction ranks answers (circle = layer used)"
                 if len(benches) > 1 else "Where the judge direction lives (circle = layer used)",
                 x=0.01, ha="left", color=INK, fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0.11 if len(benches) > 1 else 0.12, 1, 0.94))
    fig.savefig(HERE / "out_mmlu" / fname, dpi=160, facecolor=BG)


def hist_plot():
    d = json.load(open(HERE / "out_mmlu/hist_mmlu.json"))
    fig, axes = plt.subplots(2, 4, figsize=(13, 5.8), sharex=True, facecolor=BG)
    bins = np.linspace(-3.5, 3.5, 36)
    for i, (m, (nm, col)) in enumerate(MODELS.items()):
        R = np.array(d[m]["rows"], dtype=float)  # gold, solved, direction, verdict
        for j, (sv, svn) in enumerate(((1, "solved"), (0, "not solved"))):
            for k, (ci, what) in enumerate(((2, f"knows: judge direction (layer {d[m]['layer']})"), (3, "says: verdict score"))):
                ax = axes[i, 2 * j + k]
                style(ax)
                S = R[R[:, 1] == sv]
                for g, c, lab in ((1, RIGHT, "right answers"), (0, WRONG, "wrong answers")):
                    x = np.clip(S[S[:, 0] == g, ci], -3.49, 3.49)
                    ax.hist(x, bins=bins, density=True, color=c, alpha=0.55, label=lab, edgecolor=BG, linewidth=0.5)
                    ax.axvline(np.median(x), color=c, lw=1.6)
                ax.set_title(f"{nm} · {svn}\n{what}", loc="left", fontsize=9, color=INK)
                ax.set_yticks([])
                if i == 1:
                    ax.set_xlabel("position vs the question's average (sd)")
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, fontsize=9, loc="lower center", ncol=2, labelcolor=INK)
    fig.suptitle("MMLU-Redux: where right and wrong answers sit, along the judge direction (knows) vs the verdict (says)",
                 x=0.01, ha="left", color=INK, fontsize=12, fontweight="bold")
    fig.text(0.01, 0.925, "Each answer's score minus its question's average, in standard deviations. Vertical line = median. "
             "The further apart green and pink are, the better right and wrong answers are separated.", fontsize=9, color=INK2)
    fig.tight_layout(rect=(0, 0.06, 1, 0.91))
    fig.savefig(HERE / "out_mmlu/direction_hist_mmlu.png", dpi=160, facecolor=BG)


if __name__ == "__main__":
    layers_plot()
    layers_plot((("mmlu", "MMLU-Redux"),), "direction_layers_mmlu_only.png")
    hist_plot()
    print("ok")
