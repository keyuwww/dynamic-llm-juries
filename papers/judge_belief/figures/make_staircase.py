"""Figure 2: wrong answers approved by belief. (a) four judge families, thinking off; (b) the three Qwens with thinking
off vs on (same answers). Audited labels, stated verdict, 95% intervals resampling questions. Same rows and rules as
experiments/anchoring_early_answer/validation/paper_numbers.py and think_staircase.py.

  .venv/bin/python papers/judge_belief/figures/make_staircase.py -> papers/judge_belief/figures/staircase.pdf
"""
import collections
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
ANC = HERE.parents[2] / "experiments" / "anchoring_early_answer"
sys.path.insert(0, str(ANC / "validation"))
import paper_numbers as pn  # noqa: E402
import think_staircase as ts  # noqa: E402

INK, MUTED, GRID = "#1f2328", "#5b6470", "#e3e6ea"
COL = {"3 Qwens": "#2a78d6", "Nemotron-3-Super": "#1baf7a", "DeepSeek-V4.1-Flash": "#e87ba4", "Kimi-K2.6": "#eb6834",
       "Nemotron-3-Nano": "#6250d6"}
LAB = {"3 Qwens": "Qwen3.5-4B/9B, Qwen3.6-35B (pooled)", "Nemotron-3-Super": "Nemotron-3-Super-120B",
       "DeepSeek-V4.1-Flash": "DeepSeek-V4.1-Flash", "Kimi-K2.6": "Kimi-K2.6", "Nemotron-3-Nano": "Nemotron-3-Nano-30B"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7})
NB = 2000


def ci_bins(rows, key="y"):
    out = []
    for b in pn.BINS:
        g = [r for r in rows if r["b"] == b]
        by = collections.defaultdict(list)
        for r in g:
            by[r["qid"]].append(r[key])
        ks = list(by)
        rng = np.random.default_rng(0)
        est = np.mean([x for k in ks for x in by[k]])
        bs = [np.mean([x for i in rng.integers(0, len(ks), len(ks)) for x in by[ks[i]]]) for _ in range(NB)]
        out.append((100 * est, 100 * np.percentile(bs, 2.5), 100 * np.percentile(bs, 97.5), len(g)))
    return out


def draw(ax, rows, color, label, offset, key="y", ls="-", mfc=None):
    c = ci_bins(rows, key)
    x = np.arange(4) + offset
    y = [v[0] for v in c]
    ax.plot(x, y, ls, color=color, lw=1.6, label=label, zorder=3)
    ax.errorbar(x, y, yerr=[[v[0] - v[1] for v in c], [v[2] - v[0] for v in c]], fmt="o", ms=3.6, color=color,
                mfc=mfc or color, mec=color, mew=1.2, elinewidth=0.9, capsize=1.8, zorder=4)
    return c


def main():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.45), sharey=True, gridspec_kw=dict(wspace=0.08))
    print("panel a")
    for i, (name, R) in enumerate((n, pn.load(od, sfx)) for n, od, sfx in pn.FAM):
        W = [r for r in R if r["ok"] == 0 and r["audited"]]
        c = draw(a1, W, COL[name], LAB[name], (i - 2) * 0.05)
        print(name, [f"{v[0]:.0f}% n={v[3]}" for v in c])
    # panel b: same answers, thinking off vs on
    think = ts.load_think()
    raw = ts.jb_sign()
    R = pn.load("out", "")
    W = []
    for r in R:
        if r["ok"] != 0 or not r["audited"]:
            continue
        t = think.get((r["judge"], r["item"]))
        if not isinstance(t, int):
            continue
        if r["bench"] == "judgebench":
            import json
            m = raw.get((r["judge"], r["item"]), {}).get("C")
            if not m:
                continue
        W.append(r)
    # reuse think_staircase's own mapping for the verdicts (A/B -> approves the target)
    import json
    rows_full = {(x["judge"], x["item"]): x for x in json.load(open(ANC / "out" / "belief_rows_clean.json"))}
    for r in W:
        t = think[(r["judge"], r["item"])]
        if r["bench"] == "judgebench":
            m = raw[(r["judge"], r["item"])]["C"]
            t = t if rows_full[(r["judge"], r["item"])]["m_C"] / m > 0 else 1 - t
        r["on"] = t
    print("panel b n =", len(W))
    c0 = draw(a2, W, COL["3 Qwens"], "thinking off", -0.04, key="y")
    c1 = draw(a2, W, "#0d366b", "thinking on", 0.04, key="on", ls="--", mfc="white")
    print("off", [f"{v[0]:.0f}%" for v in c0], "on", [f"{v[0]:.0f}%" for v in c1])
    for ax, t in ((a1, "(a) Seven judges, four families, thinking off"), (a2, "(b) Three Qwens: thinking off vs on")):
        ax.set_xticks(range(4), ["0/7", "1–3", "4–6", "7/7"])
        ax.set_xlim(-0.35, 3.35)
        ax.set_ylim(0, 100)
        ax.grid(axis="y", color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(MUTED)
        ax.tick_params(colors=MUTED, labelcolor=INK)
        ax.set_title(t, fontsize=7.4, color=INK, loc="left")
        ax.set_xlabel("Belief (how many of the judge's 7 own answers reach it)", color=INK, fontsize=6.6)
        ax.legend(frameon=False, loc="upper left", fontsize=6.4, handlelength=1.8)
    a1.set_ylabel("Wrong answers approved (%)", color=INK)
    fig.savefig(HERE / "staircase.pdf", bbox_inches="tight", pad_inches=0.02)
    fig.savefig(HERE / "staircase.png", dpi=200, bbox_inches="tight", pad_inches=0.02)
    print("wrote", HERE / "staircase.pdf")


if __name__ == "__main__":
    main()
