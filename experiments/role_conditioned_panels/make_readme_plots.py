"""Plots for the README. Numbers are copied from the README tables (which come from run.py / cascade.py /
cascade_sweep.py / cheapest_first.py / calibration.py), so this script needs no data and runs instantly."""
import os
import matplotlib.pyplot as plt

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(out, exist_ok=True)

# ---- 1. cascade: accuracy vs cost per item  (name, accuracy, $/item)
pts = {
    "BFF, reference given": [("best single", .9104, .0021), ("static top-3", .9254, .0043), ("full jury (8)", .9254, .0084),
                              ("cascade 2,2", .9099, .0012), ("cascade 3,3", .9212, .0020), ("cascade 4,4", .9202, .0028),
                              ("cascade 4,3", .9263, .0023), ("cascade 5,5", .9174, .0039), ("cascade 5,4", .9259, .0034)],
    "BFF, no reference": [("best single", .8473, .0007), ("static top-3", .8664, .0038), ("full jury (8)", .8292, .0084),
                           ("cascade 2,2", .8350, .0010), ("cascade 3,3", .8531, .0018), ("cascade 4,4", .8553, .0028),
                           ("cascade 4,3", .8168, .0025), ("cascade 5,5", .8575, .0041), ("cascade 5,4", .8416, .0039)],
}
fig, axs = plt.subplots(1, 2, figsize=(12, 4.5))
for ax, (title, rows) in zip(axs, pts.items()):
    for name, acc, cost in rows:
        base = not name.startswith("cascade")
        ax.scatter(cost, acc, marker="s" if base else "o", color="C3" if base else "C0", s=60 if base else 35)
        ax.annotate(name, (cost, acc), fontsize=8, xytext=(4, 4), textcoords="offset points")
    ax.set_title(title); ax.set_xlabel("cost per item ($)"); ax.set_ylabel("accuracy")
fig.suptitle("Plot 2: cheap-first cascade, accuracy vs cost (cascade k,m = k cheap judges, accept if m agree; squares = baselines)")
fig.tight_layout(); fig.savefig(os.path.join(out, "cascade_cost_accuracy.png"), dpi=130); plt.close(fig)

# ---- 2. accuracy difference vs static top-3, with 95% CI  (label, diff, lo, hi) in points
rows = {
    "BFF, no reference": [("greedy, majority", -1.9, -3.1, -0.8), ("greedy, eta-hat", -2.7, -4.3, -1.1),
                           ("cheapest first, majority", -4.0, -5.9, -2.0), ("cheapest first, eta-hat", -2.4, -3.9, -0.8),
                           ("cascade, 2 cheap judges", -3.1, -5.4, -1.0), ("cascade, 3 cheap judges", -1.3, -3.2, 0.4)],
    "BFF, reference given": [("greedy, majority", -1.6, -2.7, -0.8), ("greedy, eta-hat", -0.4, -2.4, 1.2),
                              ("cheapest first, majority", -0.8, -1.9, 0.3), ("cheapest first, eta-hat", -0.8, -2.7, 0.8),
                              ("cascade, 2 cheap judges", -1.6, -3.2, -0.1), ("cascade, 3 cheap judges", -0.4, -1.3, 0.5)],
}
fig, axs = plt.subplots(1, 2, figsize=(12, 4), sharex=True)
for ax, (title, rs) in zip(axs, rows.items()):
    for i, (lab, d, lo, hi) in enumerate(rs):
        ax.errorbar(d, i, xerr=[[d - lo], [hi - d]], fmt="o", color="C0" if hi >= 0 else "C3", capsize=3)
    ax.axvline(0, color="k", lw=0.8); ax.set_yticks(range(len(rs))); ax.set_yticklabels([r[0] for r in rs]); ax.invert_yaxis()
    ax.set_title(title); ax.set_xlabel("accuracy minus static top-3 (points), 95% CI")
fig.suptitle("Plot 1: accuracy vs static top-3 (red = CI entirely below 0, blue = CI includes 0)")
fig.tight_layout(); fig.savefig(os.path.join(out, "difference_vs_top3.png"), dpi=130); plt.close(fig)

# ---- 3. cascade across 4 split seeds (accuracy difference vs top-3, points)
seeds = [0, 1, 2, 3]
series = {"3,3 reference given": [-0.4, -0.6, -0.4, -0.4], "3,3 no reference": [-1.3, -2.2, -1.7, -2.3],
          "4,3 reference given": [0.1, 0.0, -0.2, 0.1], "4,3 no reference": [-5.0, -5.2, -5.4, -5.8]}
fig, ax = plt.subplots(figsize=(7, 4.5))
for name, ys in series.items():
    ax.plot(seeds, ys, marker="o", label=name, ls="-" if name.startswith("3,3") else "--")
ax.axhline(0, color="k", lw=0.8); ax.set_xticks(seeds); ax.set_xlabel("split seed"); ax.set_ylabel("accuracy minus static top-3 (points)")
ax.set_title("Plot 3: cascade (k,m) on four different splits of the same questions"); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(out, "cascade_seeds.png"), dpi=130); plt.close(fig)

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
fig.suptitle("Plot 4: EmbedLLM predicting whether a judge is right on unseen questions (bars start at 0.7 and 0.4)")
fig.tight_layout(); fig.savefig(os.path.join(out, "embedllm_correctness.png"), dpi=130); plt.close(fig)

# ---- 5. EmbedLLM routing accuracy vs baselines
route = {"EmbedLLM router": [.8310, .9160, .8211], "best single judge": [.8559, .9049, .8486], "static top-3": [.8694, .9288, .8386],
         "weighted random (paper's baseline)": [.8043, .9066, .7956]}
fig, ax = plt.subplots(figsize=(9, 4.8))
for j, (name, v) in enumerate(route.items()):
    ax.bar([i + (j - 1.5) * 0.2 for i in range(3)], v, 0.2, label=name)
ax.set_xticks(range(3)); ax.set_xticklabels(settings); ax.set_ylim(0.75, 0.96); ax.set_ylabel("share of questions where the routed judge is right")
ax.set_title("Plot 5: EmbedLLM routing vs baselines (bars start at 0.75)"); ax.legend(fontsize=8, loc="upper left")
fig.tight_layout(); fig.savefig(os.path.join(out, "embedllm_routing.png"), dpi=130); plt.close(fig)
print("saved", sorted(os.listdir(out)))
