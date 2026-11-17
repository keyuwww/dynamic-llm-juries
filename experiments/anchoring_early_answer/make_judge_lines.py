"""One belief staircase per judge: share of WRONG candidates accepted at the verdict, by belief (how many of the
judge's 7 own answers reach the candidate's answer). Qwens (3 sizes), Llama-3.1-8B and Nemotron-3-Super on the same
benchmarks, clean RB2-Math labels. Llama is drawn only with --judges ...,llama3.1-8b. Error bars: 95% intervals, questions resampled.

Only rows with all 7 own answers matched are used (Nemotron's belief run may still be filling in).

  python3 experiments/anchoring_early_answer/make_judge_lines.py [--benches rb2math,judgebench,bff]
      -> out/figs_belief/fig6_belief_by_judge.png (+ table printed)
"""
import argparse
import collections
import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 11, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlecolor": INK,
                     "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
                     "axes.spines.top": False, "axes.spines.right": False})
# Qwens: one hue, light -> dark with size; other families get their own hues
JUDGES = [("qwen3.5-4b", "Qwen3.5-4B", "#9cc3f0", "out/belief_rows_clean.json"),
          ("qwen3.5-9b", "Qwen3.5-9B", "#2a78d6", "out/belief_rows_clean.json"),
          ("qwen3.6-35b-a3b", "Qwen3.6-35B-A3B", "#0d3d7a", "out/belief_rows_clean.json"),
          ("llama3.1-8b", "Llama-3.1-8B", "#eb6834", "out/belief_rows_llama3.1-8b_clean.json"),
          ("nemotron3-super-120b", "Nemotron-3-Super-120B", "#1baf7a", "out_nemotron/belief_rows_clean.json"),
          ("deepseek-v4.1-flash", "DeepSeek-V4.1-Flash", "#c23b8a", "out_deepseek/belief_rows_clean.json"),
          ("kimi-k2.6", "Kimi-K2.6", "#e8832f", "out_kimi/belief_rows_clean.json")]
BINS = ["0/7", "1–3", "4–6", "7/7"]


def binof(b):
    k = round(b * 7)
    return 0 if k == 0 else 1 if k <= 3 else 2 if k <= 6 else 3


def qid(r):
    return r["item"].rsplit("-", 1)[0] if r["bench"] == "rb2math" else (r.get("q") or r["item"])


def boot(rows, nb=2000, seed=0):
    """Accept rate with a 95% interval, resampling questions."""
    by = collections.defaultdict(list)
    for r in rows:
        by[qid(r)].append(r["acc_C"])
    keys = list(by)
    rng = np.random.default_rng(seed)
    est = np.mean([x for k in keys for x in by[k]])
    bs = []
    for _ in range(nb):
        pick = rng.integers(0, len(keys), len(keys))
        xs = [x for i in pick for x in by[keys[i]]]
        bs.append(np.mean(xs))
    return est, np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benches", default="rb2math,judgebench,bff")
    ap.add_argument("--audited", action="store_true", help="drop BFF / JudgeBench wrong answers the GLM-5.3 label audit "
                    "does not call clearly wrong (validation/, Experiment 11) -> fig7_belief_by_judge_clean.png")
    ap.add_argument("--judges", default="qwen3.5-4b,qwen3.5-9b,qwen3.6-35b-a3b,nemotron3-super-120b,deepseek-v4.1-flash,kimi-k2.6",
                    help="judges to draw; Llama-3.1-8B (llama3.1-8b) is left out by default: only 5 of its wrong "
                    "answers reach 7/7, too few to place the top of its curve")
    ap.add_argument("--min-n", type=int, default=10, help="bins with fewer rows are drawn hollow and not joined")
    a = ap.parse_args()
    benches = set(a.benches.split(","))
    ok_label = None
    if a.audited:
        import re
        ok_label = {}
        for line in open(HERE / "out" / "ask_glm5.3_labelaudit.jsonl"):
            r = json.loads(line)
            m = re.findall(r"AUDIT:\s*(LABEL_OK|LABEL_WRONG|CONTESTED)", r["text"])
            ok_label[r["cache_key"].split("|", 2)[2]] = bool(m) and m[-1] == "LABEL_OK"
    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    print(f"| judge | {' | '.join(BINS)} | 7/7 minus 0/7 |\n|---|---|---|---|---|---|")
    for key, name, col, path in JUDGES:
        p = HERE / path
        if key not in a.judges.split(",") or not p.exists():
            continue
        R = [r for r in json.load(open(p)) if r["judge"] == key and r["bench"] in benches and r["target_ok"] == 0
             and r.get("acc_C") is not None and r.get("belief") is not None and r.get("n_votes") == 7
             and (ok_label is None or r["bench"] == "rb2math" or ok_label.get(r["item"], True))]
        if not R:
            continue
        cells, xs, ys, lo, hi, ns = [], [], [], [], [], []
        for i in range(4):
            g = [r for r in R if binof(r["belief"]) == i]
            if not g:
                cells.append("–")
                continue
            e, l, h = boot(g)
            xs.append(i), ys.append(100 * e), lo.append(100 * (e - l)), hi.append(100 * (h - e)), ns.append(len(g))
            cells.append(f"{100 * e:.0f}% (n={len(g)})")
        full = [n >= a.min_n for n in ns]
        X = [x for x, f in zip(xs, full) if f]
        Y = [y for y, f in zip(ys, full) if f]
        ax.plot(X, Y, "-", color=col, lw=2.4, label=name, zorder=3)
        for x, y, l_, h_, n, f in zip(xs, ys, lo, hi, ns, full):
            ax.errorbar(x, y, yerr=[[l_], [h_]], fmt="o", ms=7, color=col, mfc=col if f else SURF, mec=col, mew=2,
                        elinewidth=1.4, capsize=3, zorder=4)
            if not f:
                ax.annotate(f"n={n}", (x, y), textcoords="offset points", xytext=(8, -4), fontsize=9, color=col)
        d = f"{ys[-1] - ys[0]:+.0f}" if xs and xs[0] == 0 and xs[-1] == 3 else "–"
        print(f"| {name} | {' | '.join(cells)} | {d} |")
    ax.set_xticks(range(4), BINS)
    ax.set_xlim(-0.3, 3.3)
    ax.set_ylim(0, 100)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.set_xlabel("Belief: how many of the judge's 7 own answers reach this (wrong) answer")
    ax.set_ylabel("Wrong answers approved at the verdict (%)")
    names = {"rb2math": "RB2 Math", "judgebench": "JudgeBench", "bff": "BFF"}
    ax.set_title("Judges from four families approve the wrong answers they believe")
    ax.legend(frameon=False, loc="upper left", fontsize=10)
    fig.text(0.01, 0.01, f"Benchmarks: {' + '.join(names[b] for b in ['rb2math', 'judgebench', 'bff'] if b in benches)}. "
             f"Thinking off. {'Audited labels. ' if a.audited else ''}"
             f"Hollow: fewer than {a.min_n} answers. Whiskers: 95% CI.",
             fontsize=8.5, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    out = HERE / "out" / "figs_belief" / ("fig7_belief_by_judge_clean.png" if a.audited else "fig6_belief_by_judge.png")
    fig.savefig(out, dpi=150)
    print("wrote", out)


if __name__ == "__main__":
    main()
