"""Figure for report_2026-11-16-stretch-recipe.md: ranking gain from stretching x11 at the rule-chosen layer, every
judge x benchmark pair with a gap (all answer pairs, and same-model pairs on questions the judge cannot solve where
available), with the random-direction control. Data: out_allpairs/allpairs.json (allpairs_analyze.py).

  python3 experiments/beyond_capability/recipe_figure.py -> out_allpairs/recipe_gains.png
"""
import json
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "interp" / "slide_figs"))
from slide_figure import BG, BEFORE, BLUE, INK, INK2, RED, load_slide_font  # noqa: E402

NAME = {"llama3.1-8b": "Llama-3.1-8B", "llama3.2-3b": "Llama-3.2-3B", "qwen3.5-4b": "Qwen3.5-4B",
        "phi4-mini": "Phi-4-mini", "mistral-7b": "Mistral-7B", "granite3.3-8b": "Granite-3.3-8B"}
BN = {"mmlu": "MMLU", "math": "MATH", "bbeh": "BBEH"}


def main():
    R = json.load(open(HERE / "out_allpairs" / "allpairs.json"))
    rows = []
    for b in ("mmlu", "math", "bbeh"):
        for j in NAME:
            o = R.get(f"{j}|{b}", {})
            if o.get("all | x11"):
                rows.append((b, j, o))
    plt.rcParams.update({"font.family": load_slide_font(), "font.size": 10, "axes.edgecolor": INK2,
                         "xtick.color": INK2, "ytick.color": INK})
    fig = plt.figure(figsize=(8.2, 0.36 * len(rows) + 1.6), facecolor=BG)
    ax = fig.add_axes([0.25, 0.1, 0.71, 0.78])
    ax.set_facecolor(BG)
    y, ys, last, labels = 0.0, [], None, []
    for b, j, o in rows:
        if last is not None and b != last:
            y += 0.6
        ys.append(-y)
        last = b
        y += 1
        tag = "" if o["status"] == "responds" else " *"
        labels.append(f"{BN[b]} · {NAME[j]}{tag}")
    for yi, (b, j, o) in zip(ys, rows):
        g = o["all | x11"]
        col = BLUE if g["lo"] > 0 else RED if g["hi"] < 0 else BEFORE
        ax.plot([g["lo"], g["hi"]], [yi, yi], color=col, lw=2.2, solid_capstyle="round", zorder=3)
        ax.plot(g["g"], yi, "o", ms=7, color=col, mec=BG, mew=1.5, zorder=4)
        r = o.get("all | random x11")
        if r:
            ax.plot(r["g"], yi, "x", ms=6, color=INK2, mew=1.4, zorder=4)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Ranking gain from stretching ×11 at the rule's layer (×100, 95% CI)")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.plot([], [], "o", color=BLUE, label="judge direction (CI above 0)")
    ax.plot([], [], "o", color=BEFORE, label="judge direction (CI includes 0)")
    ax.plot([], [], "x", color=INK2, label="random direction")
    ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.01), ncol=3, frameon=False, fontsize=8.5)
    fig.text(0.25, 0.015, "* no layer responds; stretched at the highest-knows layer", fontsize=8.5, color=INK2)
    out = HERE / "out_allpairs" / "recipe_gains.png"
    fig.savefig(out, dpi=200, facecolor=BG)
    print(out)


if __name__ == "__main__":
    main()
