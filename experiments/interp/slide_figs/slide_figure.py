"""One slide figure, in the same style as stretch_curve.py (beyond_capability): off-white surface, light grid,
categorical palette, legend at the bottom.

A (two panels): agreement with human labels (Cohen's kappa) of each judge's final verdict (grey) vs its best earlier
   layer read with the logit lens (colour). The layer is picked on one random half of the items and scored on the
   other half; mean over 200 splits (held_out_final_vs_layer.json; same protocol as held_out_significance.py).
   Clearly better = at least +0.05 kappa and better in >= 95% of splits. BFF = our rubric; Qwen3.6-35B = real rubric.
B: Ingrid's weight edit (Qwen3.5-0.8B; approach from Takehi, Teoh, Zhang & Khattab, "Sparks of Weight-Space
   Programming: LLMs can natively read & write neural network weights", Nov 2026; "Hidden Judge Knowledge Pilot", branch ingrid/weight-space-judge): judge AUROC
   on held-out items before vs after the edit; dashed mark = what layer 14 already knows on Safety.

  python3 experiments/interp/slide_figs/slide_figure.py   -> slide_figure.png
"""
import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

HERE = Path(__file__).resolve().parent
INK, INK2, GRID, BG = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
BEFORE, BLUE, BLUE_SOFT, RED, AQUA = "#c9c8c2", "#2a78d6", "#a9c8ee", "#e34948", "#1baf7a"
JUDGES = [("qwen3.5-4b", "Qwen3.5-4B"), ("gpt-oss-120b", "gpt-oss-120b"), ("nvidia-nemotron-3-nano-30b-a3b-bf16", "Nemotron Nano 30B"),
          ("qwen3.6-35b-a3b", "Qwen3.6-35B"), ("nvidia-nemotron-3-super-120b-a12b-bf16", "Nemotron Super 120B"),
          ("gpt-oss-20b", "gpt-oss-20b"), ("qwen3.5-9b", "Qwen3.5-9B")]
KEY = {"Safety": lambda m: f"rb2safety|{m}",
       "BFF": lambda m: f"bff_rules|{m}" if m != "qwen3.6-35b-a3b" else f"bff_rules2_rules|{m}"}


def load_slide_font():
    """Helvetica Neue (closest installed match to the slide's Inter). matplotlib only reads face 0 of the system .ttc,
    so copy the regular and bold faces to a temp folder and register them."""
    import tempfile
    from matplotlib import font_manager as fm
    try:
        from fontTools.ttLib import TTCollection
        tmp = Path(tempfile.gettempdir()) / "slide_fonts"
        tmp.mkdir(exist_ok=True)
        for i in (0, 1):
            out = tmp / f"HelveticaNeue_{i}.ttf"
            if not out.exists():
                TTCollection("/System/Library/Fonts/HelveticaNeue.ttc").fonts[i].save(out)
            fm.fontManager.addfont(str(out))
        return "Helvetica Neue"
    except Exception:
        return "DejaVu Sans"


def style(ax):
    ax.set_facecolor(BG)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)


def main():
    ho = json.load(open(HERE / "held_out_final_vs_layer.json"))
    plt.rcParams.update({"font.family": load_slide_font(), "font.size": 10.5, "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2,
                         "ytick.color": INK})
    fig = plt.figure(figsize=(16, 6.4), facecolor=BG)
    gs = fig.add_gridspec(1, 4, width_ratios=[1, 1, 0.42, 1], wspace=0.06, left=0.115, right=0.985, top=0.76, bottom=0.17)
    axA = [fig.add_subplot(gs[0, 0])]
    axA.append(fig.add_subplot(gs[0, 1], sharey=axA[0]))
    axB = fig.add_subplot(gs[0, 3])
    h = 0.36
    y = np.arange(len(JUDGES))[::-1]
    for ax, (bk, title) in zip(axA, (("Safety", "RewardBench 2 Safety"), ("BFF", "BFF-Bench (finance)"))):
        n_clear = 0
        for yi, (m, _) in zip(y, JUDGES):
            r = ho[KEY[bk](m)]
            ok = r["gap"] >= 0.05 and r["pos"] >= 0.95 * r["n"]
            worse = r["gap"] <= -0.05 and r["pos"] <= 0.05 * r["n"]
            n_clear += ok
            col = BLUE if ok else (RED if worse else BLUE_SOFT)
            ax.barh(yi + h / 2 + 0.01, r["final"], h, color=BEFORE, zorder=2)
            ax.barh(yi - h / 2 - 0.01, r["layer"], h, color=col, zorder=2)
            lab = f"{r['gap']:+.2f}" if abs(r["gap"]) >= 0.02 else "no change"
            ax.text(max(r["final"], r["layer"], 0) + 0.025, yi, lab, va="center", fontsize=10 if (ok or worse) else 9,
                    color=INK if (ok or worse) else INK2, fontweight="bold" if (ok or worse) else "normal")
        ax.axvline(0, color=INK2, lw=1)
        ax.set_xlim(-0.08, 1.12)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_xticklabels(["0\n(chance)", "0.25", "0.5", "0.75", "1\n(perfect)"])
        ax.set_xlabel("agreement with human labels (Cohen's κ)")
        ax.set_title(title, loc="left", color=INK, fontsize=11.5, pad=20)
        ax.text(0, 1.012, f"earlier layer clearly better for {n_clear} of 7 judges", transform=ax.transAxes,
                fontsize=9.5, color=BLUE, va="bottom")
        style(ax)
    axA[0].set_yticks(y)
    axA[0].set_yticklabels([n for _, n in JUDGES], fontsize=10.5)
    axA[0].set_ylim(-0.6, len(JUDGES) - 0.4)
    plt.setp(axA[1].get_yticklabels(), visible=False)
    # B
    rows = [("Safety\n(edited for this)", 0.51, 0.95), ("BFF finance\n(not targeted)", 0.71, 0.46),
            ("JudgeBench\n(not targeted)", 0.55, 0.53)]
    yb = np.arange(len(rows))[::-1]
    hb = 0.34
    for yi, (name, b, a) in zip(yb, rows):
        col = AQUA if a - b > 0.05 else (RED if a - b < -0.05 else BEFORE)
        axB.barh(yi + hb / 2 + 0.01, b, hb, color=BEFORE, zorder=2)
        axB.barh(yi - hb / 2 - 0.01, a, hb, color=col, zorder=2, hatch=None if col != BEFORE else "///", edgecolor=BG)
        axB.text(b + 0.012, yi + hb / 2 + 0.01, f"{b:.2f}", va="center", fontsize=9.5, color=INK2)
        axB.text(a + 0.012, yi - hb / 2 - 0.01, f"{a:.2f}", va="center", fontsize=10, color=INK, fontweight="bold")
    ys = yb[0]
    axB.plot([0.97, 0.97], [ys - 0.45, ys + 0.45], color=INK, lw=1.8, ls=(0, (2, 2)), zorder=3)
    axB.text(0.965, ys + 0.47, "layer 14 already\nknows 0.97", ha="right", va="bottom", fontsize=9, color=INK)
    axB.axvline(0.5, color=INK2, lw=1, ls=(0, (3, 3)), zorder=3)
    axB.text(0.505, -0.55, "chance", color=INK2, fontsize=8.5, va="bottom")
    axB.set_yticks(yb)
    axB.set_yticklabels([r[0] for r in rows], fontsize=10.5)
    axB.set_ylim(-0.6, len(rows) - 0.1)
    axB.set_xlim(0, 1.08)
    axB.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    axB.set_xlabel("judge AUROC on held-out items (0.5 = guessing)")
    axB.set_title("Qwen3.5-0.8B, edited for Safety", loc="left", color=INK, fontsize=11.5, pad=20)
    axB.text(0, 1.012, "ordinary text also gets worse (Wikipedia loss 3.30 to 4.29)", transform=axB.transAxes,
             fontsize=9.5, color=RED, va="bottom")
    style(axB)
    fig.text(0.012, 0.95, "A. Reading an earlier layer instead of the final verdict (7 judges)", fontsize=13,
             fontweight="bold", color=INK)
    fig.text(0.012, 0.905, "Best layer picked on half the items, scored on the other half (mean of 200 splits). "
             "Clearly better = at least +0.05 and better in ≥95% of splits.", fontsize=9.5, color=INK2)
    pB = axB.get_position()
    fig.text(pB.x0 - 0.085, 0.95, "B. Editing the weights to use that knowledge", fontsize=13, fontweight="bold", color=INK)
    fig.text(pB.x0 - 0.085, 0.925, "One small judge. Weight-editing approach from Takehi, Teoh, Zhang & Khattab (2026),\n"
             "\u201cSparks of Weight-Space Programming: LLMs can natively read &\n"
             "write neural network weights.\u201d",
             fontsize=9.5, color=INK2, va="top", linespacing=1.4)
    handles = [Patch(color=BEFORE, label="final verdict / before edit"), Patch(color=BLUE, label="best earlier layer: clearly better"),
               Patch(color=BLUE_SOFT, label="best earlier layer: no clear difference"), Patch(color=RED, label="worse"),
               Patch(color=AQUA, label="after edit: better")]
    fig.legend(handles=handles, frameon=False, fontsize=9.5, loc="lower center", ncol=5, labelcolor=INK,
               bbox_to_anchor=(0.5, 0.0))
    fig.savefig(HERE / "slide_figure.png", dpi=180, facecolor=BG)
    print(HERE / "slide_figure.png")


if __name__ == "__main__":
    main()
