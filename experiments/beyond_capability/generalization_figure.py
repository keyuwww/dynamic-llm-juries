"""Does stretching the judge direction generalise? Gain in the verdict's ranking from stretching x11, all answers,
for every judge x benchmark we ran, next to the two things that predict it: the knows-vs-says gap and whether the
verdict responds to pushes along the direction.

Numbers (ranking = within-question AUROC x100; gain = x11 minus unedited; 95% CI by resampling questions):
  gains and sensitivity: out_strength_select.md (strength_select.py); Qwen3.5-4B: out_mmlu/qwen3.5-4b/prereg_outcome.md
  knows: held-out direction ranking at the steered layer (direction_choice_*.json, one split of the questions; BBEH:
         mean over 20 random splits from out_dirs/<model>/hidden_main.npy, because BBEH's single-split value swings
         0.57-0.68 for Llama and 0.53-0.65 for Qwen); says: unedited verdict ranking.

  python3 experiments/beyond_capability/generalization_figure.py -> generalization.png, generalization.md
"""
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "interp" / "slide_figs"))
from slide_figure import BG, BEFORE, BLUE, GRID, INK, INK2, RED, load_slide_font  # noqa: E402

# benchmark, judge, knows, says, sensitivity, gain, lo, hi, why
ROWS = [
    ("MMLU-Redux", "Llama-3.1-8B", .635, .511, .13, 7.0, 5.1, 8.9, "gap, verdict responds*"),
    ("MMLU-Redux", "Qwen3.5-9B", .683, .673, .26, 0.5, -0.6, 1.7, "no gap"),
    ("MMLU-Redux", "Qwen3.5-4B (preregistered)", .622, .610, .13, -0.4, -1.5, 0.8, "no gap"),
    ("BBEH", "Llama-3.1-8B", .633, .557, .02, 6.3, 3.2, 9.6, "gap, verdict responds weakly†"),
    ("BBEH", "Qwen3.5-9B", .601, .616, .15, 1.2, -2.1, 4.7, "no gap"),
    ("MATH", "Llama-3.1-8B", .680, .541, -.04, 1.4, -0.4, 3.3, "gap, but verdict doesn't respond"),
    ("MATH", "Qwen3.5-9B", .712, .663, .43, 2.2, 0.2, 4.1, "small gap, small gain"),
    ("RB2 Safety", "Llama-3.1-8B", .987, .959, .21, -6.3, -8.2, -4.6, "×11 overshoots (×4: +1.0)"),
    ("RB2 Safety", "Qwen3.5-9B", .977, .964, -.01, 0.1, -0.3, 0.4, "no gap, doesn't respond"),
]


def main():
    plt.rcParams.update({"font.family": load_slide_font(), "font.size": 10.5, "axes.edgecolor": INK2,
                         "xtick.color": INK2, "ytick.color": INK})
    fig = plt.figure(figsize=(14, 7.2), facecolor=BG)
    ax = fig.add_axes([0.2, 0.17, 0.34, 0.66])
    ax.set_facecolor(BG)
    ys, y, last = [], 0.0, None
    for r in ROWS:
        if r[0] != last and last is not None:
            y += 0.7
        ys.append(y)
        last = r[0]
        y += 1
    ys = -np.array(ys)
    for yi, r in zip(ys, ROWS):
        g, lo, hi = r[5], r[6], r[7]
        col = BLUE if lo > 0 else RED if hi < 0 else BEFORE
        ax.barh(yi, g, height=0.62, color=col, edgecolor=BG, lw=1.5, zorder=3)
        ax.plot([lo, hi], [yi, yi], color=INK, lw=1.2, zorder=4)
        for e in (lo, hi):
            ax.plot([e, e], [yi - 0.13, yi + 0.13], color=INK, lw=1.2, zorder=4)
        tx = hi + 0.4 if g >= 0 else lo - 0.4
        ax.text(tx, yi, f"{g:+.1f}".replace("-", "−"), va="center", ha="left" if g >= 0 else "right", fontsize=10,
                color=INK, fontweight="bold" if col != BEFORE else "normal")
    ax.axvline(0, color=INK2, lw=1, zorder=2)
    ax.set_xlim(-11, 12)
    ax.set_ylim(ys[-1] - 0.7, 0.7)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.set_yticks(ys)
    ax.set_yticklabels([r[1] for r in ROWS])
    ax.set_xlabel("Gain in ranking from stretching ×11 (points, 95% CI)", color=INK2)
    # benchmark headers
    seen = set()
    for yi, r in zip(ys, ROWS):
        if r[0] not in seen:
            seen.add(r[0])
            fig.text(0.012, ax.transData.transform((0, yi + 0.62))[1] / fig.dpi / fig.get_figheight(), r[0],
                     fontsize=11.5, fontweight="bold", color=INK, va="center")
    # right-hand columns
    cols = [(0.585, "Knows", lambda r: f"{r[2]:.2f}"), (0.645, "Says", lambda r: f"{r[3]:.2f}"),
            (0.705, "Gap", lambda r: f"{100 * (r[2] - r[3]):+.0f}"),
            (0.765, "Verdict\nresponds", lambda r: "no" if r[4] <= 0 else "weakly" if r[4] < 0.05 else "yes"),
            (0.835, "Why", lambda r: r[8])]
    top = ax.transData.transform((0, 0.7))[1] / fig.dpi / fig.get_figheight()
    for x, head, f in cols:
        fig.text(x, top + 0.005, head, fontsize=10, color=INK2, fontweight="bold", va="bottom",
                 ha="left" if head == "Why" else "center")
        for yi, r in zip(ys, ROWS):
            yy = ax.transData.transform((0, yi))[1] / fig.dpi / fig.get_figheight()
            s = f(r)
            bold = head == "Gap" and 100 * (r[2] - r[3]) >= 8
            fig.text(x, yy, s, fontsize=10, va="center", ha="left" if head == "Why" else "center",
                     color=INK if head != "Why" else INK2, fontweight="bold" if bold else "normal")
    fig.text(0.012, 0.95, "Stretching helps only where the judge knows more than it says, and its verdict listens",
             fontsize=15, fontweight="bold", color=INK)
    fig.text(0.012, 0.905, "All answers, ×11. Knows = ranking from the judge direction alone; says = ranking from the "
             "unedited verdict; gap = knows − says (points). Ranking: right above wrong answer to the same question; "
             "0.50 = chance.", fontsize=10, color=INK2)
    fig.legend(handles=[Patch(color=BLUE, label="Clearly helps"), Patch(color=BEFORE, label="No clear change"),
                        Patch(color=RED, label="Clearly hurts")], loc="lower left", bbox_to_anchor=(0.2, 0.06),
               ncol=3, frameon=False, fontsize=10, handlelength=1.2)
    fig.text(0.012, 0.034, "* MMLU-Redux Llama: the gain holds on questions it can solve (+6 with same-model pairs). On questions it can't "
             "solve it disappears (+0.3): it came from recognising which model wrote the answer.", fontsize=9, color=INK2)
    fig.text(0.012, 0.012, "† BBEH has only one answer per model per question, so the same-model check can't be run there.",
             fontsize=9, color=INK2)
    out = HERE / "generalization.png"
    fig.savefig(out, dpi=200, facecolor=BG)
    md = ["| Benchmark | Judge | Knows | Says | Gap | Verdict responds (sensitivity) | Gain at ×11 [95% CI] | Why |",
          "|---|---|---|---|---|---|---|---|"]
    for r in ROWS:
        md.append(f"| {r[0]} | {r[1]} | {r[2]:.2f} | {r[3]:.2f} | {100 * (r[2] - r[3]):+.0f} | {r[4]:.2f} | "
                  f"{r[5]:+.1f} [{r[6]:+.1f}, {r[7]:+.1f}] | {r[8]} |")
    (HERE / "generalization.md").write_text("\n".join(md) + "\n")
    print(out)


if __name__ == "__main__":
    main()
