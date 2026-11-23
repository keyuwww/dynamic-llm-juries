"""Paper figures (PDF) from out_paper/results.json and the Llama-3.1-8B MATH layer sweep.

  python3 experiments/beyond_capability/paper_figures.py -> papers/judge_direction/fig_gap.pdf, fig_sm.pdf, fig_layers.pdf
"""
import json
import re

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import allpairs_analyze as A  # noqa: E402
from paper_data import BIG  # noqa: E402

OUTD = A.HERE.parents[1] / "papers" / "judge_direction"
R = json.load(open(A.HERE / "out_paper" / "results.json"))
# Okabe-Ito (colorblind-safe), fixed order
C = {"verdict": "#7f7f7f", "cot": "#E69F00", "x11": "#CC79A7", "direct": "#0072B2", "sum": "#009E73"}
NAMES = {"verdict": "Verdict", "cot": "Reason first", "x11": "Stretch ×11", "direct": "Direction", "sum": "Verdict + direction"}
SHORT = {"llama3.1-8b": "Llama-3.1-8B", "llama3.2-3b": "Llama-3.2-3B", "llama3.2-1b": "Llama-3.2-1B", "phi4-mini": "Phi-4-mini",
         "mistral-7b": "Mistral-7B", "granite3.3-8b": "Granite-3.3-8B", "qwen2.5-7b": "Qwen2.5-7B", "qwen3.5-4b": "Qwen3.5-4B", "llama3.1-70b": "Llama-3.1-70B"}
BN = {"mmlu": "MMLU-Redux", "math": "MATH", "bbeh": "BBEH"}
plt.rcParams.update({"font.size": 8, "font.family": "serif", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6, "pdf.fonttype": 42})


def fig_gap():
    """verdict vs direction ranking, every pair, main answer pool."""
    rows = []
    for b in ("mmlu", "math", "bbeh"):
        for k, v in R["pool"].items():
            j, bb = k.split("|")
            if bb == b and j not in BIG:
                rows.append((b, j, v["verdict"]["rank"], v["direct"]["rank"]))
    fig, ax = plt.subplots(figsize=(3.2, 3.6))
    y, ticks, labels, prev = 0, [], [], None
    for b, j, s, d in rows:
        if prev and b != prev:
            y += 0.8
        ax.plot([s, d], [y, y], color="#c8c8c8", lw=1.2, zorder=1)
        ax.scatter([s], [y], s=14, color=C["verdict"], zorder=2, label="Verdict" if y == 0 else None)
        ax.scatter([d], [y], s=14, color=C["direct"], zorder=2, label="Direction (hidden state)" if y == 0 else None)
        ticks.append(y)
        labels.append(f"{SHORT[j]} · {BN[b]}")
        prev, y = b, y + 1
    ax.axvline(50, color="#999999", lw=0.6, ls=":")
    ax.set_yticks(ticks, labels, fontsize=6.5)
    ax.invert_yaxis()
    ax.set_xlabel("AUROC ×100 (50 = chance)")
    ax.set_xlim(46, 72)
    ax.legend(frameon=False, fontsize=6.5, loc="lower center", bbox_to_anchor=(0.4, 1.0), ncol=2, handletextpad=0.2)
    fig.tight_layout()
    fig.savefig(OUTD / "fig_gap.pdf")


def fig_sm():
    """same-model pairs on questions the judge failed on a sampled attempt: absolute ranking per method, mean over judges."""
    methods = [m for m in ("verdict", "cot", "x11", "direct", "sum")]
    sets = [("math", "qwen3.5-4b"), ("math", "olmo2-7b"), ("bbeh", "qwen3.5-4b"), ("mmlu", "qwen3.5-4b"), ("mmlu", "olmo2-7b")]
    sets = [s for s in sets if any(k.split("|")[1:] == list(s) for k in R["sm"])]
    fig, ax = plt.subplots(figsize=(3.2, 2.2))
    w = 0.8 / len(methods)
    for i, m in enumerate(methods):
        xs, ys, es = [], [], []
        for x, (b, who) in enumerate(sets):
            # equal-weight mean over judges with its synchronised question-bootstrap 95% interval (paper_analysis.py)
            e = R["summary"].get(f"sm|{b}|{who}", {}).get("rank_level", {}).get(m)
            if not e:
                continue
            xs.append(x + (i - (len(methods) - 1) / 2) * w)
            ys.append(e["g"])
            es.append([e["g"] - e["lo"], e["hi"] - e["g"]])
        ax.bar(xs, np.array(ys) - 50, w * 0.9, bottom=50, color=C[m], label=NAMES[m], yerr=np.array(es).T,
               error_kw=dict(lw=0.6, capsize=0))
    ax.axhline(50, color="#555555", lw=0.6)
    who = {"qwen3.5-4b": "Qwen", "olmo2-7b": "OLMo"}
    sb = {"mmlu": "MMLU", "math": "MATH", "bbeh": "BBEH"}
    ax.set_xticks(range(len(sets)), [f"{sb[b]}\n{who[w_]}" for b, w_ in sets], fontsize=6.5)
    ax.set_xlabel("Benchmark and answering model", fontsize=6.5)
    ax.set_ylabel("Ranking (×100); 50 = chance")
    ax.set_ylim(40, 66)
    ax.legend(frameon=False, fontsize=6, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.22))
    fig.tight_layout()
    fig.savefig(OUTD / "fig_sm.pdf")


def fig_layers():
    """Llama-3.1-8B, MATH: what each layer's direction knows, how much the verdict responds, and the stretch gain."""
    txt = (A.HERE / "out_math" / "layer_sweep" / "layer_sweep.md").read_text().split("## solved")[0]
    L, K, S, G, Glo, Ghi = [], [], [], [], [], []
    for line in txt.splitlines():
        m = re.match(r"\| (\d+) \| ([\d.]+) \| ([\d.]+) \| .*? \| ([+-][\d.]+) \| ([+-][\d.]+) \[([+-][\d.]+), ([+-][\d.]+)\]", line)
        if m:
            L.append(int(m[1])), K.append(100 * float(m[2])), S.append(float(m[4]))
            G.append(float(m[5])), Glo.append(float(m[6])), Ghi.append(float(m[7]))
    says = 100 * float(re.search(r"\| \d+ \| [\d.]+ \| ([\d.]+) \|", txt)[1])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.3, 1.9))
    a1.plot(L, K, "-o", ms=3, lw=1.2, color=C["direct"], label="Direction")
    a1.axhline(says, color=C["verdict"], lw=1.2, ls="--", label="Verdict")
    a1.set_xlabel("Layer")
    a1.set_ylabel("Ranking ×100")
    a1.legend(frameon=False, fontsize=6.5)
    a2.bar(L, G, 1.4, color=[C["x11"] if s >= 0.05 else "#d9d9d9" for s in S])
    a2.errorbar(L, G, yerr=[np.array(G) - Glo, np.array(Ghi) - G], fmt="none", lw=0.6, color="#555555")
    a2.axhline(0, color="#555555", lw=0.6)
    a2.set_xlabel("Layer stretched (×11)")
    a2.set_ylabel("Ranking gain")
    for l_, s, hi in zip(L, S, Ghi):
        a2.text(l_, max(hi, 0) + 0.6, f"{s:+.2f}", ha="center", fontsize=5.5, color="#333333")
    a2.set_ylim(-7, 15)
    fig.tight_layout()
    fig.savefig(OUTD / "fig_layers.pdf")


if __name__ == "__main__":
    OUTD.mkdir(exist_ok=True)
    fig_gap()
    fig_layers()
    if R["sm"]:
        fig_sm()
    print("figures ->", OUTD)
