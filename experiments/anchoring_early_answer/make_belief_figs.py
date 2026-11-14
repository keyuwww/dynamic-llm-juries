"""Figures for report_2026-11-09-kensho-belief-direction.md -> out/figs_belief/*.png

  fig1_belief_acceptance.png   acceptance by belief (wrong before reasoning / wrong at verdict / correct at verdict)
                               + share of candidates that are actually correct, by belief
  fig2_probe_by_position.png   held-out readability of belief by reasoning position (best layer), per judge and benchmark
  fig3_steering.png            change in acceptance per steering condition, by item group, 95% intervals
  fig4_confident.png           confident beliefs the judge accepted: right vs wrong AUROC, probe vs baselines

Numbers come from out/belief_rows.json, out/belief_probe_grid.md, out/belief_steering.md and out/confident_probe.md.

  python3 experiments/anchoring_early_answer/make_belief_figs.py
"""
import json
import re
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "figs_belief"
OUT.mkdir(parents=True, exist_ok=True)
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"  # categorical slots 1-3 (validated all-pairs)
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 11, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlecolor": INK,
                     "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
                     "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False})
BINS = ["0/7", "1–3", "4–6", "7/7"]


def binof(b):
    return 0 if b == 0 else 3 if b == 1 else 1 if b < 0.5 else 2


def grid(ax, axis="y"):
    ax.grid(axis=axis, color=GRID, lw=0.8)
    ax.set_axisbelow(True)


def fig1():
    R = json.load(open(HERE / "out" / "belief_rows.json"))
    q = np.array([f"{r['bench']}|{r['q'] or r['item'].rsplit('-', 1)[0]}" for r in R])
    b = np.array([binof(r["belief"]) for r in R])
    ok = np.array([r["target_ok"] for r in R])
    aA = np.array([np.nan if r["acc_A"] is None else r["acc_A"] for r in R], float)
    aC = np.array([np.nan if r["acc_C"] is None else r["acc_C"] for r in R], float)
    uq = np.unique(q)
    idx = {x: np.where(q == x)[0] for x in uq}
    rng = np.random.default_rng(0)
    boots = [np.concatenate([idx[x] for x in rng.choice(uq, len(uq))]) for _ in range(1000)]

    def stat(mask_fn, val):
        def f(ii):
            return [np.nanmean(val[ii][mask_fn(ii) & (b[ii] == k)]) for k in range(4)]
        est = np.array(f(np.arange(len(R))))
        bs = np.array([f(ii) for ii in boots])
        return est, np.nanpercentile(bs, 2.5, 0), np.nanpercentile(bs, 97.5, 0)

    series = [("Wrong answers, before reasoning", S1, stat(lambda ii: ok[ii] == 0, aA)),
              ("Wrong answers, at the verdict", S2, stat(lambda ii: ok[ii] == 0, aC)),
              ("Correct answers, at the verdict", S3, stat(lambda ii: ok[ii] == 1, aC))]
    share = stat(lambda ii: np.ones(len(ii), bool), ok.astype(float))
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(11, 4.3), gridspec_kw=dict(width_ratios=[1.35, 1]))
    x = np.arange(4)
    for name, c, (e, lo, hi) in series:
        ax.errorbar(x, 100 * e, yerr=[100 * (e - lo), 100 * (hi - e)], color=c, lw=2, marker="o", ms=8,
                    capsize=3, label=name, mec=SURF, mew=2)
        ax.annotate(f"{100 * e[-1]:.0f}%", (3, 100 * e[-1]), xytext=(10, 0), textcoords="offset points",
                    va="center", color=INK, fontsize=10)
        ax.annotate(f"{100 * e[0]:.0f}%", (0, 100 * e[0]), xytext=(-10, 0), textcoords="offset points",
                    va="center", ha="right", color=INK, fontsize=10)
    ax.set(xticks=x, xticklabels=BINS, ylim=(0, 100), xlim=(-0.5, 3.5), ylabel="Accepted by the judge (%)",
           xlabel="Belief: how many of 7 own answers reach this answer")
    ax.set_title("The judge accepts what it would answer itself", loc="left")
    ax.legend(loc="upper left", fontsize=9.5)
    grid(ax)
    e, lo, hi = share
    bx.bar(x, 100 * e, width=0.6, color=S1, yerr=[100 * (e - lo), 100 * (hi - e)], capsize=3,
           error_kw=dict(ecolor=INK2, lw=1))
    for i, v in enumerate(e):
        bx.annotate(f"{100 * v:.0f}%", (i, 100 * hi[i]), xytext=(0, 5), textcoords="offset points", ha="center",
                    color=INK, fontsize=10)
    bx.set(xticks=x, xticklabels=BINS, ylim=(0, 105), ylabel="Candidates that are actually correct (%)",
           xlabel="Belief")
    bx.set_title("…and its belief is usually right", loc="left")
    grid(bx)
    fig.text(0.01, 0.005, "Qwen3.5-4B / 9B / 3.6-35B, thinking off; RB2 Math + JudgeBench + BFF. Bars and whiskers: "
             "95% intervals, questions resampled.", color=INK2, fontsize=8.5)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "fig1_belief_acceptance.png", dpi=180)


def fig2():
    txt = (HERE / "out" / "belief_probe_grid.md").read_text()
    data = {}
    for block in txt.split("\n## ")[1:]:
        judge, bench = re.match(r"(\S+), (\S+):", block).groups()
        vals = {}
        for pos in ("A", "25", "50", "75", "C"):
            m = re.search(rf"^\| {pos} \|.*L\d+: ([0-9.]+) \|$", block, re.M)
            vals[pos] = float(m.group(1))
        held = re.search(r"Held-out \(nested\) score: ([0-9.]+)", block).group(1)
        data[(judge, bench)] = (vals, held)
    fig, axs = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    pos = ["A", "25", "50", "75", "C"]
    lab = ["A\n(before\nwriting)", "25%", "50%", "75%", "C\n(at the\nverdict)"]
    for ax, bench, title in zip(axs, ("rb2math", "bff"), ("RB2 Math", "BFF-Bench")):
        for judge, c, nm in (("qwen3.5-9b", S1, "Qwen3.5-9B"), ("qwen3.5-4b", S2, "Qwen3.5-4B")):
            v, held = data[(judge, bench)]
            y = [v[p] for p in pos]
            ax.plot(range(5), y, color=c, lw=2, marker="o", ms=8, mec=SURF, mew=2, label=f"{nm} (held-out {held})")
            ax.annotate(nm.split("-")[-1], (4, y[-1]), xytext=(8, 0), textcoords="offset points", va="center",
                        color=INK, fontsize=10)
        ax.axhline(0.5, color=INK2, lw=1, ls=":")
        ax.annotate("chance", (0, 0.5), xytext=(0, 4), textcoords="offset points", color=INK2, fontsize=9)
        ax.set(xticks=range(5), xticklabels=lab, ylim=(0.45, 1.0), xlim=(-0.3, 4.6))
        ax.set_title(title, loc="left")
        ax.legend(loc="upper left", fontsize=9)
        grid(ax)
    axs[0].set_ylabel("AUROC: believed vs never-reached\nwrong answers (best layer)")
    fig.suptitle("Belief is readable from the hidden state, most clearly near the verdict", x=0.01, ha="left",
                 fontweight="bold", color=INK, fontsize=12)
    fig.text(0.01, 0.005, "Ridge probe, 5-fold cross-validated by question, best layer per position. Held-out = "
             "nested choice of position and layer.", color=INK2, fontsize=8.5)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    fig.savefig(OUT / "fig2_probe_by_position.png", dpi=180)


def fig3():
    txt = (HERE / "out" / "belief_steering.md").read_text().split("## both")[1]
    rows = []
    for line in txt.splitlines():
        m = re.match(r"\| (\S+) \| (.*) \|$", line)
        if not m or m.group(1) in ("condition", "none", "---") or "not run" in line:
            continue
        cells = m.group(2).split(" | ")
        vals = []
        for c in cells[:3]:
            mm = re.search(r"\(([+-]\d+) \[([+-]\d+), ([+-]\d+)\]\)", c)
            vals.append(tuple(int(x) for x in mm.groups()))
        rows.append((m.group(1), vals))
    names = {"belief:-4": "belief −4", "belief:-6": "belief −6", "belief_orth:-6": "belief without correctness −6",
             "correct:-6": "\"is this right?\" −6", "random:-6": "random direction −6 (control)",
             "belief:4": "belief +4 (believe more)", "belief*0": "belief ×0 (removed)", "belief*-2": "belief ×−2",
             "belief*-5": "belief ×−5 (reversed)", "belief*5": "belief ×5 (amplified)",
             "belief_orth*-5": "belief w/o correctness ×−5", "correct*-5": "\"is this right?\" ×−5",
             "random*-5": "random ×−5 (control)"}
    fig, ax = plt.subplots(figsize=(10, 0.55 * len(rows) + 1.8))
    groups = [("Wrong, believed (68% accepted)", S2), ("Wrong, never reached (21%)", S1), ("Correct (85%)", S3)]
    for gi, (gname, c) in enumerate(groups):
        off = (gi - 1) * 0.22
        for ri, (cond, vals) in enumerate(rows):
            e, lo, hi = vals[gi]
            ax.errorbar(e, ri + off, xerr=[[e - lo], [hi - e]], color=c, marker="o", ms=8, capsize=2.5, lw=1.6,
                        mec=SURF, mew=1.5, label=gname if ri == 0 else None)
    ax.axvline(0, color=INK2, lw=1)
    ax.set(yticks=range(len(rows)), yticklabels=[names.get(r[0], r[0]) for r in rows],
           xlabel="Change in acceptance vs no push (percentage points)")
    ax.invert_yaxis()
    ax.set_title("Pushing along belief moves leniency, not the believed wrong answers", loc="left")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, fontsize=9.5, borderaxespad=1.8)
    grid(ax, "x")
    fig.text(0.01, 0.005, "Qwen3.5-9B, thinking off, RB2 Math + BFF (418 items), layers 14–26, held-out directions, "
             "greedy decoding. Whiskers: 95% intervals, questions resampled.", color=INK2, fontsize=8.5)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "fig3_steering.png", dpi=180)


def fig4():
    txt = (HERE / "out" / "confident_probe.md").read_text()
    data = []
    for block in txt.split("\n## ")[1:]:
        judge, bench = re.match(r"(\S+), (\S+):", block).groups()
        acc = block.split("Among the")[1]
        nw = re.match(r" \d+ confident answers the judge accepted \((\d+) wrong\)", acc).group(1)
        vals = {}
        for name in ("probe on this answer's state", "question-only probe", "judge's verdict at C"):
            m = re.search(rf"\| {re.escape(name)} \| ([0-9.]+) \[([0-9.]+), ([0-9.]+)\]", acc)
            vals[name] = tuple(float(x) for x in m.groups())
        lab = {"qwen3.5-9b": "Qwen3.5-9B", "qwen3.5-4b": "Qwen3.5-4B"}[judge]
        data.append((f"{lab}, {'RB2 Math' if bench == 'rb2math' else 'BFF'}\n({nw} wrong accepted)", vals))
    fig, ax = plt.subplots(figsize=(10, 4.4))
    sig = [("judge's verdict at C", "Judge's own verdict confidence", S1),
           ("question-only probe", "Question-only probe", S3),
           ("probe on this answer's state", "Probe on this answer", S2)]
    for si, (key, nm, c) in enumerate(sig):
        off = (si - 1) * 0.22
        for ri, (lab, vals) in enumerate(data):
            e, lo, hi = vals[key]
            ax.errorbar(e, ri + off, xerr=[[e - lo], [hi - e]], color=c, marker="o", ms=8, capsize=2.5, lw=1.6,
                        mec=SURF, mew=1.5, label=nm if ri == 0 else None)
    ax.axvline(0.5, color=INK2, lw=1, ls=":")
    ax.set(yticks=range(len(data)), yticklabels=[d[0] for d in data], xlim=(0.4, 1.0),
           xlabel="AUROC: right vs wrong, among confident answers the judge accepted")
    ax.invert_yaxis()
    ax.set_title("Confident wrong beliefs are partly visible, but mostly already in the verdict", loc="left")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, fontsize=9, borderaxespad=1.8)
    grid(ax, "x")
    fig.text(0.01, 0.005, "Answers with belief ≥ 4/7 that the judge accepted. Held-out questions; whiskers: 95% "
             "intervals, questions resampled. Dotted line: chance.\nQuestion-only probe = average state over "
             "all the question's candidates (no answer-specific information).", color=INK2, fontsize=8.5)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(OUT / "fig4_confident.png", dpi=180)


if __name__ == "__main__":
    for f in (fig1, fig2, fig3, fig4):
        f()
        print("wrote", f.__name__)
