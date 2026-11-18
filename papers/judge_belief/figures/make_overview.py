"""Figure 1: how belief is measured and what we compare it with (one real JudgeBench item, Qwen3.5-9B; both label
auditors call the believed answer clearly wrong).

  .venv/bin/python papers/judge_belief/figures/make_overview.py  -> papers/judge_belief/figures/overview.pdf
"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent / "overview.pdf"
INK, MUTED, LINE = "#1f2328", "#5b6470", "#c9ced6"
FILL, ACC, ACC_FILL, OK_FILL = "#f4f6f8", "#b4442c", "#f7e7e2", "#e6f0e8"
FS, FS_S = 6.3, 5.9
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": FS})

fig, ax = plt.subplots(figsize=(7.0, 2.15))
ax.set_xlim(0, 100)
ax.set_ylim(0, 32)
ax.axis("off")


def box(x, y, w, h, fc=FILL, ec=LINE, lw=0.8):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=0.8", fc=fc, ec=ec, lw=lw))


def arrow(x0, y0, x1, y1):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=7, color=MUTED, lw=0.8))


def label(x, y, s):
    ax.text(x, y, s, color=MUTED, fontsize=FS_S, va="top")


# question
box(0.8, 1, 26.5, 30)
label(2, 30.0, "QUESTION  (JudgeBench / MMLU-Pro)")
ax.text(2, 26.8, "Paley maintains that the key\ndifference between the\n“contrivance” of a watch and\nthat of nature is that the\nlatter is ___.", color=INK, va="top", linespacing=1.35)
ax.text(2, 13.5, "(F) greater and grander   [gold]\n(H) not created by human hands\n… ten options in all",
        color=INK, va="top", linespacing=1.4)

# step 1: belief
arrow(27.9, 23.5, 32.6, 23.5)
box(33.2, 16.8, 31.5, 14.2)
label(34.4, 30.0, "① BELIEF: the judge answers alone, 7 times")
for i in range(7):
    box(35.0 + i * 4.1, 21.0, 3.1, 4.3, fc=ACC_FILL, ec=ACC, lw=0.7)
    ax.text(36.55 + i * 4.1, 23.15, "H", color=ACC, ha="center", va="center", fontsize=7, fontweight="bold")
ax.text(34.4, 19.6, "belief in H = 7/7,  in F = 0/7", color=INK, va="top")

# step 2: judging
arrow(27.9, 8.0, 32.6, 8.0)
box(33.2, 1, 31.5, 14.2)
label(34.4, 14.2, "② JUDGING: two other models’ answers")
box(35.0, 2.8, 13.2, 7.2, fc=OK_FILL, ec=LINE, lw=0.7)
ax.text(41.6, 9.2, "Response A", color=MUTED, ha="center", va="top", fontsize=FS_S)
ax.text(41.6, 5.3, "… FFFFF", color=INK, ha="center", va="center")
box(50.0, 2.8, 13.2, 7.2, fc=ACC_FILL, ec=ACC, lw=0.7)
ax.text(56.6, 9.2, "Response B", color=MUTED, ha="center", va="top", fontsize=FS_S)
ax.text(56.6, 5.3, "… HHHHH", color=ACC, ha="center", va="center", fontweight="bold")

# verdict
arrow(65.3, 8.0, 69.6, 8.0)
box(70.2, 1, 29, 14.2, fc="white", ec=INK, lw=0.8)
label(71.4, 14.2, "VERDICT of the judge (Qwen3.5-9B)")
ax.text(71.4, 10.9, "“…Response B correctly identifies\nthat the contrast is about the\n"
        "agent of creation…  VERDICT: B”", color=INK, va="top", linespacing=1.35)

# the question we ask
arrow(65.3, 23.5, 69.6, 23.5)
box(70.2, 16.8, 29, 14.2, fc="white", ec=LINE)
label(71.4, 30.0, "WHAT WE MEASURE")
ax.text(71.4, 26.9, "Is a wrong answer approved more\noften the more of the judge’s own\n"
        "7 answers reach it? (No judge\nwrote the answers it grades.)", color=INK, va="top", linespacing=1.32)

fig.savefig(OUT, bbox_inches="tight", pad_inches=0.02)
fig.savefig(OUT.with_suffix(".png"), dpi=200, bbox_inches="tight", pad_inches=0.02)
print("wrote", OUT)
