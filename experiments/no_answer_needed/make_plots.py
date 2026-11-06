"""Plots for the README. Numbers are copied from the outputs of compare_signals.py, routing_eval.py and
transfer_probe.py (the score files themselves are not in the repo)."""
import os
import numpy as np
import matplotlib.pyplot as plt

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures"); os.makedirs(out, exist_ok=True)
PROBE, DIS = "C0", "C1"
judges = ["deepseek-v3.1", "gpt-oss-120b", "gpt-oss-20b", "nemotron3-nano", "nemotron3-super", "qwen3.5-4b", "qwen3.5-9b", "qwen3.6-35b"]

# ---- Plot 1: how well does each reliability score rank 'judge is right' above 'judge is wrong'? (AUROC, held-out questions)
order = ["gpt-oss-120b", "gpt-oss-20b", "deepseek-v3.1", "qwen3.6-35b", "qwen3.5-4b", "nemotron3-super", "qwen3.5-9b", "nemotron3-nano"]
P1 = {"BFF-Bench": dict(probe=[.596, .590, .651, .598, .676, .666, .635, .656], dis=[.701, .759, .776, .818, .842, .843, .847, .872], old=(.60, .66)),
      "RewardBench-2 Safety": dict(probe=[.790, .752, .790, .781, .784, .784, .764, .672], dis=[.768, .694, .827, .829, .820, .815, .764, .770], old=(.70, .71))}
fig, axs = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)
for ax, (name, d) in zip(axs, P1.items()):
    x = np.arange(8); ax.axhspan(*d["old"], color="0.85", zorder=0, label="earlier reliability scores (kNN, EmbedLLM, IRT) range")
    ax.bar(x, d["probe"], .55, color=PROBE, label="activation probe"); ax.scatter(x, d["dis"], marker="D", color="k", zorder=3, s=26, label="other judges disagree (needs all judges run)")
    ax.axhline(.5, color="k", lw=1, ls="--"); ax.set_xticks(x); ax.set_xticklabels(order, rotation=35, ha="right", fontsize=8); ax.set_ylim(.4, 1.0)
    ax.set_title(f"{name}: probe mean {np.mean(d['probe']):.2f}, disagreement mean {np.mean(d['dis']):.2f}", fontsize=10)
axs[0].set_ylabel("AUROC for 'this judge is right'\n(dashed = coin flip, axis starts at 0.4)"); axs[0].legend(fontsize=7, loc="upper left")
fig.suptitle("Plot 1: how well each reliability score separates right from wrong (held-out questions)", fontsize=11)
fig.tight_layout(); fig.savefig(os.path.join(out, "plot1_reliability_score.png"), dpi=130); plt.close(fig)

# ---- Plot 2: routing, accuracy vs cost per item
alphas = [1.0, 0.9, 0.8, 0.65, 0.5, 0.35, 0.2]
R = {"BFF-Bench": dict(
        single={"gpt-oss-120b": (.00072, .8540), "gpt-oss-20b": (.00044, .8257), "deepseek-v3.1": (.00261, .8061), "qwen3.6-35b": (.00125, .7647), "qwen3.5-4b": (.00073, .7451),
                "nemotron3-super": (.00095, .7407), "qwen3.5-9b": (.00144, .7386), "nemotron3-nano": (.00029, .6667)}, top3=(.00377, .8736),
        probe=([.000934, .000699, .000589, .000453, .000407, .000392, .000335], [.8410, .8388, .8431, .8344, .8170, .8148, .7364]),
        ctrl=([.001025, .000731, .000622, .000530, .000453, .000390, .000343], [.7892, .7913, .7932, .7944, .7874, .7706, .7223])),
     "RewardBench-2 Safety": dict(
        single={"gpt-oss-120b": (.00072, .7794), "gpt-oss-20b": (.00044, .8467), "deepseek-v3.1": (.00261, .7289), "qwen3.6-35b": (.00125, .7261), "qwen3.5-4b": (.00073, .7317),
                "nemotron3-super": (.00095, .7406), "qwen3.5-9b": (.00144, .7856), "nemotron3-nano": (.00029, .7861)}, top3=(.00217, .8411),
        probe=([.000566, .000448, .000427, .000410, .000370, .000313, .000290], [.8528, .8561, .8500, .8461, .8311, .8033, .7861]),
        ctrl=([.001060, .000754, .000621, .000504, .000425, .000356, .000314], [.7715, .7848, .7928, .8038, .8094, .8101, .7954]))}
fig, axs = plt.subplots(1, 2, figsize=(13, 5))
for ax, (name, d) in zip(axs, R.items()):
    for j, (c, a) in d["single"].items():
        ax.scatter(c * 1e3, a, color="0.55", s=28); ax.annotate(j, (c * 1e3, a), fontsize=6.5, color="0.35", xytext=(3, 3), textcoords="offset points")
    ax.scatter(d["top3"][0] * 1e3, d["top3"][1], marker="D", color="k", s=45, label="static top-3 vote", zorder=3)
    ax.plot(np.array(d["ctrl"][0]) * 1e3, d["ctrl"][1], "--o", color=DIS, ms=4, lw=1.2, label="same routing rule, scores shuffled (no information)")
    ax.plot(np.array(d["probe"][0]) * 1e3, d["probe"][1], "-o", color=PROBE, ms=5, lw=2, label="routed by the probe")
    ax.set_xlabel("cost per item (thousandths of a dollar, log scale)"); ax.set_title(name, fontsize=10); ax.set_xscale("log"); ax.set_xticks([.3, .5, 1, 2, 4]); ax.set_xticklabels(["0.3", "0.5", "1", "2", "4"]); ax.minorticks_off()
axs[0].set_ylabel("verdict accuracy"); axs[0].legend(fontsize=7.5, loc="lower right")
fig.suptitle("Plot 2: sending each item to the judge the probe thinks is right (up and left is better)", fontsize=11)
fig.tight_layout(); fig.savefig(os.path.join(out, "plot2_routing.png"), dpi=130); plt.close(fig)

# ---- Plot 3: does the probe work on a different benchmark? (mean over the 8 judges)
fig, ax = plt.subplots(figsize=(8.5, 4.6)); groups = ["scored on BFF-Bench", "scored on RewardBench-2 Safety"]
vals = {"probe trained on the same benchmark": ([.633, .765], PROBE), "probe trained on the OTHER benchmark": ([.458, .490], "C3")}
for k, (lab, (v, c)) in enumerate(vals.items()):
    ax.bar(np.arange(2) + (k - .5) * .34, v, .34, color=c, label=lab)
    for xi, vi in zip(np.arange(2) + (k - .5) * .34, v): ax.text(xi, vi + .012, f"{vi:.2f}", ha="center", fontsize=8)
ax.axhline(.5, color="k", lw=1, ls="--"); ax.set_ylim(.4, .85); ax.set_xticks(range(2)); ax.set_xticklabels(groups)
ax.set_ylabel("mean AUROC over the 8 judges\n(dashed line = coin flip, axis starts at 0.4)"); ax.legend(fontsize=8, loc="upper left")
ax.set_title("Plot 3: the probe does not carry over to a different benchmark", fontsize=10)
fig.tight_layout(); fig.savefig(os.path.join(out, "plot3_transfer.png"), dpi=130); plt.close(fig)
print("saved", os.listdir(out))
