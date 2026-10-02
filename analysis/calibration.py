"""
Calibration check for any probability-vs-outcome table (Jev judge verdicts, Jev certifier, ...).

"Is Jev's confidence honest?" -- when it says 0.9, is it right ~90% of the time?

Usage (standalone):
  uv run python analysis/calibration.py experiments/jev_bff/jev_bff_results/items.csv --prob p --label human --group cond
  uv run python analysis/calibration.py experiments/jev_router/jev_router_results/certifier_items.csv --prob p --label correct

Outputs a markdown report (and a reliability-diagram PNG if matplotlib is installed) next to the CSV.
"""
import argparse
from pathlib import Path

import pandas as pd


def reliability(y, p, bins=10):
    """Equal-width bins over [0, 1]. Returns (rows, ece, brier)."""
    df = pd.DataFrame({"y": list(y), "p": list(p)}).dropna()
    n = len(df)
    if n == 0:
        return [], float("nan"), float("nan")
    df["bin"] = (df["p"] * bins).clip(upper=bins - 1e-9).astype(int)
    rows, ece = [], 0.0
    for b in range(bins):
        s = df[df["bin"] == b]
        if len(s) == 0:
            continue
        conf, acc = s["p"].mean(), s["y"].mean()
        ece += len(s) / n * abs(acc - conf)
        rows.append(dict(bin=f"{b / bins:.1f}–{(b + 1) / bins:.1f}", n=len(s), mean_pred=conf, frac_true=acc, gap=acc - conf))
    brier = ((df["p"] - df["y"]) ** 2).mean()
    return rows, ece, brier


def report(df, prob="p", label="y", group=None, title="Calibration", png=None):
    groups = [(None, df)] if not group else list(df.groupby(group))
    L = [f"## {title}", "",
         "Reliability: within each confidence bin, how often the event is actually true. "
         "Perfect calibration ⇒ frac_true ≈ mean_pred. ECE = weighted average |gap| (lower is better). "
         "Brier = mean squared error of the probability (lower is better; 0.25 = coin flip).", ""]
    curves = []
    for g, s in groups:
        rows, ece, brier = reliability(s[label], s[prob])
        base = s[label].mean()
        L += [f"**{g if g is not None else 'all'}** — n={len(s)}, ECE={ece:.3f}, Brier={brier:.3f} "
              f"(constant-guess Brier={base * (1 - base):.3f})", "",
              "| Bin | n | Mean predicted | Fraction true | Gap |", "|---|---|---|---|---|"]
        L += [f"| {r['bin']} | {r['n']} | {r['mean_pred']:.2f} | {r['frac_true']:.2f} | {r['gap']:+.2f} |" for r in rows]
        L.append("")
        curves.append((g if g is not None else "all", rows))
    if png:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(4.5, 4.5))
            ax.plot([0, 1], [0, 1], ls="--", color="#999", lw=1, label="perfect")
            for name, rows in curves:
                ax.plot([r["mean_pred"] for r in rows], [r["frac_true"] for r in rows], marker="o", lw=1.5, label=str(name))
            ax.set_xlabel("Jev probability (binned mean)"); ax.set_ylabel("Fraction actually true")
            ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_title(title); ax.legend(frameon=False, fontsize=8)
            fig.tight_layout(); fig.savefig(png, dpi=150); plt.close(fig)
            L += [f"![reliability diagram]({Path(png).name})", ""]
        except ImportError:
            L += ["(Install matplotlib for a reliability-diagram PNG.)", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--prob", default="p")
    ap.add_argument("--label", default="human")
    ap.add_argument("--group", default=None)
    a = ap.parse_args()
    f = Path(a.csv)
    df = pd.read_csv(f)
    out = f.with_name(f.stem + "_calibration.md")
    out.write_text(report(df, a.prob, a.label, a.group, title=f"Calibration: {f.name}", png=f.with_name(f.stem + "_calibration.png")))
    print(out.read_text())


if __name__ == "__main__":
    main()
