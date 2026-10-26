"""Plots for the EmbedLLM README. Numbers are copied from the table in the README (from embedllm.py, prompt-only text)."""
import os
import matplotlib.pyplot as plt

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(out, exist_ok=True)

settings = ["BFF\nno reference", "BFF\nreference given", "RewardBench-2\nSafety"]

# ---- Plot 1: predicting whether a judge is right (accuracy), prompt-only text, 20 splits
acc = {"constant": [.7653, .8846, .7642], "kNN": [.7569, .8774, .7621], "EmbedLLM (MF)": [.7607, .8792, .7636]}
fig, ax = plt.subplots(figsize=(8, 4.5))
for j, (name, v) in enumerate(acc.items()):
    ax.bar([i + (j - 1) * 0.27 for i in range(3)], v, 0.27, label=name)
ax.set_ylim(0.7, 0.92); ax.set_ylabel("accuracy predicting judge correctness"); ax.legend(fontsize=8)
ax.set_xticks(range(3)); ax.set_xticklabels(settings)
ax.set_title("Plot 1: EmbedLLM predicting whether a judge is right on unseen questions (bars start at 0.7)", fontsize=10)
fig.tight_layout(); fig.savefig(os.path.join(out, "embedllm_correctness.png"), dpi=130); plt.close(fig)

# ---- Plot 2: routing accuracy vs baselines
route = {"EmbedLLM router": [.8310, .9160, .8211], "best single judge": [.8559, .9049, .8486], "static top-3": [.8694, .9288, .8386],
         "weighted random (paper's baseline)": [.8043, .9066, .7956]}
fig, ax = plt.subplots(figsize=(9, 4.8))
for j, (name, v) in enumerate(route.items()):
    ax.bar([i + (j - 1.5) * 0.2 for i in range(3)], v, 0.2, label=name)
ax.set_xticks(range(3)); ax.set_xticklabels(settings); ax.set_ylim(0.75, 0.96); ax.set_ylabel("share of questions where the routed judge is right")
ax.set_title("Plot 2: EmbedLLM routing vs baselines (bars start at 0.75)"); ax.legend(fontsize=8, loc="upper left")
fig.tight_layout(); fig.savefig(os.path.join(out, "embedllm_routing.png"), dpi=130); plt.close(fig)
print("saved", sorted(os.listdir(out)))
