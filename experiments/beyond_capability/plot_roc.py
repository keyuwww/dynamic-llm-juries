"""ROC curves of the judge's verdict before vs after stretching the judge direction (x11), per judge and solved /
not solved. Score = the verdict margin (log-prob CORRECT minus INCORRECT); the dot marks the judge's actual
verdict (margin > 0), i.e. the TPR / FPR in the report table. Pools answers across questions, so the AUROC in the
legend is the ordinary (pooled) one, not the within-question ranking in the table.

  python3 experiments/beyond_capability/plot_roc.py --bench mmlu --stem mmlu_full
"""
import argparse
import json
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from stretch_analyze import solve_labels  # noqa: E402

BEFORE, AFTER = "#2a78d6", "#eb6834"  # categorical slots 1-2 of the reference palette
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
NAMES = {"qwen3.5-9b": "Qwen3.5-9B", "llama3.1-8b": "Llama-3.1-8B"}


def roc(y, s):
    y, s = np.asarray(y), np.asarray(s)
    o = np.argsort(-s, kind="mergesort")
    y, s = y[o], s[o]
    last = np.r_[np.diff(s) != 0, True]  # one point per distinct threshold
    tp, fp = np.cumsum(y)[last], np.cumsum(1 - y)[last]
    tpr, fpr = np.r_[0, tp / y.sum()], np.r_[0, fp / (1 - y).sum()]
    return fpr, tpr, np.trapezoid(tpr, fpr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", default="mmlu")
    ap.add_argument("--stem", default="mmlu_full")
    a = ap.parse_args()
    bdir = HERE / f"out_{a.bench}"
    plt.rcParams.update({"font.size": 10, "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2,
                         "ytick.color": INK2, "font.family": "sans-serif"})
    fig, axes = plt.subplots(2, 2, figsize=(9, 9.4), facecolor="#fcfcfb")
    for i, model in enumerate(("qwen3.5-9b", "llama3.1-8b")):
        rows = [json.loads(l) for p in sorted((bdir / model).glob(f"steer_{a.bench}_h*.jsonl")) for l in open(p)]
        rows = [r for r in rows if r["dir"].startswith("Jc_")]
        sol = solve_labels(a.stem, model, bdir)
        groups = ((1, "solved"), (0, "not solved")) if sol else ((None, "all questions"),)
        if not sol:
            axes[i, 1].axis("off")
            axes[i, 1].text(0.5, 0.5, f"{NAMES[model]}: solved / not solved split\npending (its own answers are still generating)",
                            ha="center", va="center", color=INK2, fontsize=9.5)
        for j, (sv, nm) in enumerate(groups):
            ax = axes[i, j]
            ax.set_facecolor("#fcfcfb")
            S = [r for r in rows if sv is None or sol.get(r["qid"]) == sv]
            y = [r["gold"] for r in S]
            dots = {}
            ax.plot([0, 1], [0, 1], color=INK2, lw=1, ls=(0, (3, 3)), zorder=1)
            ax.text(0.62, 0.55, "chance", color=INK2, fontsize=8.5, rotation=45, rotation_mode="anchor")
            for k, col, lab in (("add:0.0", BEFORE, "before"), ("amplify:10.0", AFTER, "after stretch ×11")):
                s = [r["margins"][k] for r in S]
                fpr, tpr, auc = roc(y, s)
                ax.plot(fpr, tpr, color=col, lw=2, label=f"{lab}  (AUROC {auc:.2f})", zorder=3)
                yy, ss = np.array(y), np.array(s) > 0  # the judge's actual verdict
                pt = (ss[yy == 0].mean(), ss[yy == 1].mean())
                dots[k] = (pt, np.array(s))
                ax.scatter(*pt, s=64, color=col, edgecolor="#fcfcfb", linewidth=2, zorder=4)
                ax.annotate(f"{'before' if k == 'add:0.0' else 'after'}: TPR {pt[1]:.0%}\nFPR {pt[0]:.0%}", pt,
                            textcoords="offset points", xytext=(8, -30) if k == "add:0.0" else ((-8, 8) if pt[1] < 0.85 else (-14, -14)),
                            ha="left" if k == "add:0.0" else "right", fontsize=8.5,
                            color=INK, bbox=dict(boxstyle="round,pad=0.2", fc="#fcfcfb", ec="none", alpha=0.85), zorder=5)
            # the unedited judge made exactly as strict on wrong answers as the stretched one (same FPR): hollow dot
            (fa, ta), _ = dots["amplify:10.0"]
            b = dots["add:0.0"][1]
            yy = np.array(y)
            t = min(np.unique(b), key=lambda c: abs((b[yy == 0] > c).mean() - fa))
            m = ((b[yy == 0] > t).mean(), (b[yy == 1] > t).mean())
            ax.plot([fa, fa], [m[1], ta], color=INK2, lw=1, ls=(0, (2, 2)), zorder=3)
            ax.scatter(*m, s=56, facecolor="#fcfcfb", edgecolor=BEFORE, linewidth=2, zorder=4)
            ax.annotate(f"no edit, equally strict:\nTPR {m[1]:.0%}  ({round(100 * ta) - round(100 * m[1]):+d} for stretch)", m,
                        textcoords="offset points", xytext=(8, -26), fontsize=8, color=INK2,
                        bbox=dict(boxstyle="round,pad=0.2", fc="#fcfcfb", ec="none", alpha=0.85), zorder=5)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.set_aspect("equal")
            ax.grid(color=GRID, lw=0.8)
            ax.set_axisbelow(True)
            for sp in ("top", "right"):
                ax.spines[sp].set_visible(False)
            ax.set_title(f"{NAMES[model]} · {nm}  ({len(S):,} answers)", fontsize=10.5, color=INK, loc="left")
            ax.set_xlabel("FPR: share of wrong answers accepted")
            ax.set_ylabel("TPR: share of right answers accepted")
            ax.legend(loc="lower right", frameon=False, fontsize=9, labelcolor=INK)
    fig.suptitle(f"Judging {'MMLU-Redux' if a.bench == 'mmlu' else a.bench.upper()} answers: verdict ROC before vs after "
                 "stretching the judge direction", x=0.02, ha="left", fontsize=12.5, color=INK, fontweight="bold")
    fig.text(0.02, 0.945, "Curve: every threshold on the verdict score.  Filled dot: the judge's actual CORRECT / INCORRECT verdict.\n"
             "Hollow dot: the unedited judge with its cutoff moved to be as strict on wrong answers as the stretched one.\n"
             "Random direction not drawn (it lies on 'before').  AUROC here pools all answers; the report's 'ranking' "
             "compares answers to the same question.",
             fontsize=8.8, color=INK2, va="top")
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    out = bdir / f"roc_{a.bench}.png"
    fig.savefig(out, dpi=160, facecolor=fig.get_facecolor())
    print(out)


if __name__ == "__main__":
    main()
