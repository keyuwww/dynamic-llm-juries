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
ax.set_title("Plot 4: cascade (k,m) on four different splits of the same questions"); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(out, "cascade_seeds.png"), dpi=130); plt.close(fig)

# ---- 4. calibration: how often judges say "correct" vs how often the label is correct
labels = ["BFF\nno reference", "BFF\nreference given", "RewardBench-2\nSafety"]
gold, said = [0.558, 0.559, 0.250], [0.548, 0.496, 0.460]
fig, ax = plt.subplots(figsize=(7, 4.5)); x = range(3)
ax.bar([i - 0.2 for i in x], gold, 0.4, label="gold labels that are 'correct'")
ax.bar([i + 0.2 for i in x], said, 0.4, label="judge verdicts that say 'correct' (mean of 8 judges)")
ax.set_xticks(list(x)); ax.set_xticklabels(labels); ax.set_ylabel("share"); ax.set_ylim(0, 0.7)
ax.set_title("Plot 3: how often judges say 'correct' vs how often the label is correct", fontsize=10); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(out, "calibration.png"), dpi=130); plt.close(fig)
print("saved", sorted(os.listdir(out)))
