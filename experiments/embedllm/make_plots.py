"""Plots for the EmbedLLM README. Numbers are copied from the table in the README (from embedllm.py, prompt-only text)."""
import os
import matplotlib.pyplot as plt

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(out, exist_ok=True)

# ---- 4. EmbedLLM: predicting whether a judge is right (accuracy and AUROC), prompt-only text, 20 splits
settings = ["BFF\nno reference", "BFF\nreference given", "RewardBench-2\nSafety"]
acc = {"constant": [.7653, .8846, .7642], "kNN": [.7569, .8774, .7621], "EmbedLLM (MF)": [.7607, .8792, .7636]}
auc = {"kNN": [.590, .625, .696], "EmbedLLM (MF)": [.582, .587, .693]}
fig, axs = plt.subplots(1, 2, figsize=(12, 4.5))
for j, (name, v) in enumerate(acc.items()):
    axs[0].bar([i + (j - 1) * 0.27 for i in range(3)], v, 0.27, label=name)
axs[0].set_ylim(0.7, 0.92); axs[0].set_ylabel("accuracy predicting judge correctness"); axs[0].legend(fontsize=8)
for j, (name, v) in enumerate(auc.items()):
    axs[1].bar([i + (j - 0.5) * 0.35 for i in range(3)], v, 0.35, color=f"C{j + 1}", label=name)
axs[1].axhline(0.5, color="k", lw=0.8); axs[1].set_ylim(0.4, 0.8); axs[1].set_ylabel("AUROC (0.5 = chance)"); axs[1].legend(fontsize=8)
for ax in axs:
    ax.set_xticks(range(3)); ax.set_xticklabels(settings)
fig.suptitle("Plot 1: EmbedLLM predicting whether a judge is right on unseen questions (bars start at 0.7 and 0.4)")
fig.tight_layout(); fig.savefig(os.path.join(out, "embedllm_correctness.png"), dpi=130); plt.close(fig)

# ---- 5. EmbedLLM routing accuracy vs baselines
route = {"EmbedLLM router": [.8310, .9160, .8211], "best single judge": [.8559, .9049, .8486], "static top-3": [.8694, .9288, .8386],
         "weighted random (paper's baseline)": [.8043, .9066, .7956]}
fig, ax = plt.subplots(figsize=(9, 4.8))
for j, (name, v) in enumerate(route.items()):
    ax.bar([i + (j - 1.5) * 0.2 for i in range(3)], v, 0.2, label=name)
ax.set_xticks(range(3)); ax.set_xticklabels(settings); ax.set_ylim(0.75, 0.96); ax.set_ylabel("share of questions where the routed judge is right")
ax.set_title("Plot 2: EmbedLLM routing vs baselines (bars start at 0.75)"); ax.legend(fontsize=8, loc="upper left")
fig.tight_layout(); fig.savefig(os.path.join(out, "embedllm_routing.png"), dpi=130); plt.close(fig)
print("saved", sorted(os.listdir(out)))
