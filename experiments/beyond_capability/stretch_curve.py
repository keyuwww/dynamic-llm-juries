"""How the judge's ranking changes with stretch strength (x1 = no edit, x2, x4, x11 from stretch_pipeline.py; x21, x31,
x51, x101 from cannon_bigstretch.sh), per judge, solved vs not solved, judge direction vs random direction.
Ranking = within-question AUROC of the verdict margin; 95% intervals resample whole questions.
-> out_<bench>/stretch_curve_<bench>.md and .png

  python3 experiments/beyond_capability/stretch_curve.py --bench mmlu --stem mmlu_full
"""
import argparse
import collections
import json
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bc_load import boot_ci, metrics, within_auc  # noqa: E402
from stretch_analyze import solve_labels  # noqa: E402

COL = {"qwen3.5-9b": "#2a78d6", "llama3.1-8b": "#eb6834"}  # categorical slots 1-2
NAMES = {"qwen3.5-9b": "Qwen3.5-9B", "llama3.1-8b": "Llama-3.1-8B"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def load(bdir, model, bench):
    """aid|dir-kind -> row with merged margins from the normal and the 'big' stretch runs."""
    by = {}
    for p in sorted((bdir / model).glob(f"steer_{bench}_h*.jsonl")) + sorted((bdir / model).glob(f"steer_{bench}_big_h*.jsonl")):
        for l in open(p):
            r = json.loads(l)
            k = (r["aid"], r["dir"][:2])
            if k in by:
                by[k]["margins"].update(r["margins"])
            else:
                by[k] = r
    return list(by.values())


def factor(key):
    return 1 + float(key.split(":")[1]) if key.startswith("amplify") else 1.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", default="mmlu")
    ap.add_argument("--stem", default="mmlu_full")
    a = ap.parse_args()
    bdir = HERE / f"out_{a.bench}"
    groups = ((1, "solved"), (0, "not solved"))
    L = [f"# Ranking vs stretch strength — {a.bench}\n",
         "Ranking = within-question AUROC (0.50 = chance) [95% CI]; balanced accuracy in brackets after it. "
         "×1 = no edit. Judge direction unless marked random.\n"]
    res = collections.defaultdict(dict)
    for model in ("qwen3.5-9b", "llama3.1-8b"):
        rows = load(bdir, model, a.bench)
        if not rows:
            continue
        sol = solve_labels(a.stem, model, bdir)
        keys = sorted({k for r in rows for k in r["margins"] if k == "add:0.0" or k.startswith("amplify")}, key=factor)
        L.append(f"\n## {NAMES[model]}\n")
        L.append("| Stretch | " + " | ".join(f"{nm}: judge" for _, nm in groups) + " | " + " | ".join(f"{nm}: random" for _, nm in groups) + " |")
        L.append("|---|" + "---|" * 4)
        for k in keys:
            cells = []
            for dn in ("Jc", "Rc"):
                for sv, nm in groups:
                    S = [r for r in rows if r["dir"].startswith(dn) and sol.get(r["qid"]) == sv and k in r["margins"]]
                    if not S:
                        cells.append("–")
                        continue
                    auc = lambda rr: within_auc([r["gold"] for r in rr], [r["margins"][k] for r in rr], [r["qid"] for r in rr])[0]  # noqa: E731
                    v = auc(S)
                    lo, hi = boot_ci(S, auc, n=300)
                    bal = metrics([dict(qid=r["qid"], gold=r["gold"], v=int(r["margins"][k] > 0)) for r in S])["bal"]
                    res[(model, dn, sv)][factor(k)] = (v, lo, hi)
                    cells.append(f"{v:.2f} [{lo:.2f}, {hi:.2f}] ({bal:.2f})")
            L.append(f"| ×{factor(k):g} | " + " | ".join(cells) + " |")
    (bdir / f"stretch_curve_{a.bench}.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    # ---- plot: one panel per solved group; judge direction solid with 95% band, random dashed
    plt.rcParams.update({"font.size": 10, "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2})
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), sharey=True, facecolor="#fcfcfb")
    for ax, (sv, nm) in zip(axes, groups):
        ax.set_facecolor("#fcfcfb")
        ax.axhline(0.5, color=INK2, lw=1, ls=(0, (3, 3)))
        ax.text(1.05, 0.503, "chance", color=INK2, fontsize=8.5, va="bottom")
        for model in ("qwen3.5-9b", "llama3.1-8b"):
            for dn in ("Jc", "Rc"):
                d = res.get((model, dn, sv))
                if not d:
                    continue
                xs = sorted(d)
                ys = [d[x][0] for x in xs]
                if dn == "Jc":
                    ax.fill_between(xs, [d[x][1] for x in xs], [d[x][2] for x in xs], color=COL[model], alpha=0.13, lw=0)
                    ax.plot(xs, ys, color=COL[model], lw=2, marker="o", ms=5, label=f"{NAMES[model]}: judge direction")
                    ax.annotate(f"{NAMES[model].split('-')[0].replace('3.5', '').replace('3.1', '')}", (xs[-1], ys[-1]),
                                textcoords="offset points", xytext=(6, -3), fontsize=9, color=INK)
                else:
                    ax.plot(xs, ys, color=COL[model], lw=1.2, ls=(0, (4, 3)), alpha=0.8, label=f"{NAMES[model]}: random direction")
        ax.set_xscale("log")
        xt = sorted({x for k, d in res.items() for x in d})
        ax.set_xticks(xt)
        ax.set_xticklabels([f"×{x:g}" for x in xt])
        ax.minorticks_off()
        ax.grid(color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.set_title(f"{nm} questions", loc="left", color=INK, fontsize=11)
        ax.set_xlabel("stretch strength along the judge direction (log scale)")
    axes[0].set_ylabel("ranking: right above wrong, same question\n(within-question AUROC)")
    axes[1].legend(frameon=False, fontsize=8.5, loc="upper left", labelcolor=INK)
    fig.suptitle(f"{'MMLU-Redux' if a.bench == 'mmlu' else a.bench.upper()}: judge ranking vs stretch strength "
                 "(band = 95% CI)", x=0.01, ha="left", color=INK, fontsize=12.5, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(bdir / f"stretch_curve_{a.bench}.png", dpi=160, facecolor=fig.get_facecolor())
    print(bdir / f"stretch_curve_{a.bench}.png")


if __name__ == "__main__":
    main()
