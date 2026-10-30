"""The four charts of Self-Agreement, drawn only from the CSV files in results/, never from the run rows.

    from lib import figures
    figures.draw_all()     # reads results/*.csv, writes results/figures/*.png, returns the four paths

The look is shared by the other experiments in this series. Navy is the series the chart is about (the agreement jury, or a
juror's self-agreement), silver the comparisons and slate the secondary text. Connectors are light grey, reference lines dark
grey and 95% intervals thin lines. Labels are direct, with two decimals. There are no legends and no footnotes, as the
write-up holds the definitions. Titles name the measure, then the scope. Each PNG is the same bytes on every rerun on the
same machine: no date or software stamp is written into the file, and nothing random is drawn.
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib as mpl
from matplotlib.figure import Figure

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

NAVY, SILVER, SLATE, LINK, REF = "#1f4e79", "#adb5bd", "#6c757d", "#cfd4da", "#555555"
WIDTH, DPI = 8.2, 160
STYLE = {"font.family": "sans-serif", "font.sans-serif": ["Inter", "Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
         "font.size": 10.5, "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.titlepad": 14,
         "axes.edgecolor": "#cccccc", "axes.labelcolor": "#333333", "xtick.color": "#333333", "ytick.color": "#333333",
         "axes.grid": True, "axes.grid.axis": "x", "grid.color": "#eeeeee", "axes.axisbelow": True, "axes.spines.top": False,
         "axes.spines.right": False, "axes.spines.left": False, "ytick.left": False, "axes.unicode_minus": False,
         "figure.dpi": 110, "savefig.dpi": DPI}
JURORS = ["gpt-oss-20b", "gpt-oss-120b", "qwen3.6-35b", "nemotron-3-super"]   # the four kept jurors, in the order of every table
NAMES = {"agreement_by_jury_rule": "agreement_by_jury_rule.png", "routing_at_matched_coverage": "routing_at_matched_coverage.png",
         "agreement_by_jurors_that_agree": "agreement_by_jurors_that_agree.png", "uncovered_answers_fallbacks": "uncovered_answers_fallbacks.png"}
ALT = {   # alternative text for each chart, for the notebook and the write-up
    "agreement_by_jury_rule": "Dot chart of Cohen's kappa against the expert labels, with 95% intervals, for the agreement jury, the self-solve "
                              "jury, the majority of four, the best single judge and the gut majority, on all answers, the finance answers and "
                              "the MT-Bench answers.",
    "routing_at_matched_coverage": "Dumbbell chart with one row per juror: Cohen's kappa of its reasoned read on the answers kept by self-solve "
                                   "routing and by self-agreement routing, with the same number of answers kept under each.",
    "agreement_by_jurors_that_agree": "Bar chart of the agreement jury's Cohen's kappa on the answers where 0, 1, 2, 3 or 4 jurors agree with "
                                      "themselves, with the number of answers under each bar and a dashed line at its kappa on all answers.",
    "uncovered_answers_fallbacks": "Dot chart of Cohen's kappa, with 95% intervals, of four fallback rules on the answers where no juror agrees "
                                   "with itself, with lines at chance level and at the agreement jury's kappa on the other answers.",
}


def _rows(results, name: str) -> list[dict]:
    with open(Path(results) / f"{name}.csv", newline="") as fh:
        return list(csv.DictReader(fh))


def _f(v: str) -> float:
    return float(v)


def _text_color(color: str) -> str:
    return SLATE if color == SILVER else color   # value labels take their mark's colour, slate on the light grey marks


def _interval(ax, y, v, lo, hi, color, room, pad, fmt="{:.2f}"):
    """One dot and its 95% line, the value labelled right of the line, or left of it when it would run past the right edge."""
    ax.hlines(y, lo, hi, color=color, lw=1.4, zorder=2)
    ax.scatter([v], [y], s=40, color=color, zorder=3)
    if hi + pad + room <= ax.get_xlim()[1]:
        ax.text(hi + pad, y, fmt.format(v), ha="left", va="center", fontsize=9.5, color=_text_color(color), zorder=4)
    else:
        ax.text(min(lo, v) - pad, y, fmt.format(v), ha="right", va="center", fontsize=9.5, color=_text_color(color), zorder=4)


def _title(fig, text):
    fig.suptitle(text, x=0.01, ha="left", fontsize=13, fontweight="bold")


def _save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white", metadata={"Software": None})
    return path


def _figures(results, out) -> Path:
    return Path(out) if out is not None else Path(results) / "figures"


def agreement_by_jury_rule(results=RESULTS, out=None) -> Path:
    """Cohen's kappa against the expert label for the agreement jury and its comparisons, four jurors, on all answers and on each
    answer set, with the 95% interval (results_by_rule.csv, jurors = 4)."""
    R = [r for r in _rows(results, "results_by_rule") if r["jurors"] == "4"]
    get = lambda rule, juror, s: next(r for r in R if r["rule"] == rule and r["juror"] == juror and r["answer_set"] == s)  # noqa: E731
    rows = [("agreement jury", "", "agreement jury", NAVY), ("self-solve jury", "", "self-solve jury", SILVER),
            ("majority vote", "", "majority of four", SILVER), ("reasoned read", "gpt-oss-120b", "best single judge", SILVER),
            ("gut majority vote", "", "gut majority", SILVER)]
    sets = [("all", "All answers"), ("finance", "Finance answers"), ("mt_bench", "MT-Bench answers")]
    with mpl.rc_context(STYLE):
        fig = Figure(figsize=(WIDTH, 3.3))
        axes = fig.subplots(1, 3, sharey=True)
        Y = list(range(len(rows)))[::-1]
        for ax, (s, name) in zip(axes, sets):
            ax.set_xlim(0.35, 1.02)
            for y, (rule, juror, _, col) in zip(Y, rows):
                r = get(rule, juror, s)
                _interval(ax, y, _f(r["kappa"]), _f(r["kappa_lo"]), _f(r["kappa_hi"]), col, room=0.1, pad=0.015)
            ax.set_title(f"{name} ({int(get('agreement jury', '', s)['answers']):,})", fontsize=10.5, fontweight="bold", pad=8)
            ax.set_xticks([0.4, 0.6, 0.8, 1.0]); ax.set_xticklabels(["0.4", "0.6", "0.8", "1.0"])
        axes[0].set_yticks(Y); axes[0].set_yticklabels([r[2] for r in rows]); axes[0].set_ylim(-0.6, len(rows) - 0.4)
        _title(fig, "Agreement with the experts (Cohen's κ, 95% interval), by jury rule and answer set")
        fig.tight_layout(rect=(0, 0, 1, 0.96))
        best = get("reasoned read", "gpt-oss-120b", "all")   # the best single judge is the highest κ of the single reads on all answers
        assert max((r for r in R if r["rule"] in ("reasoned read", "gut read") and r["answer_set"] == "all"), key=lambda r: _f(r["kappa"])) is best
        return _save(fig, _figures(results, out) / NAMES["agreement_by_jury_rule"])


def routing_at_matched_coverage(results=RESULTS, out=None) -> Path:
    """For each juror, the kappa of its reasoned read on the answers it keeps when it keeps as many answers as fall on question
    turns it solved: kept by self-solve and by self-agreement (matched_coverage.csv). The random 95th percentile is in the table."""
    M = {r["juror"]: r for r in _rows(results, "matched_coverage")}
    with mpl.rc_context(STYLE):
        fig = Figure(figsize=(WIDTH, 3.3))
        ax = fig.subplots()
        ax.set_xlim(0.53, 0.79)
        Y = list(range(len(JURORS)))[::-1]; pad = 0.006
        for y, j in zip(Y, JURORS):
            ss, sa = _f(M[j]["kappa_self_solve"]), _f(M[j]["kappa_self_agreement"])
            ax.hlines(y, ss, sa, color=LINK, lw=5, zorder=1)
            ax.scatter([ss], [y], s=55, color=SILVER, zorder=3); ax.scatter([sa], [y], s=55, color=NAVY, zorder=3)
            ax.text(ss - pad, y, f"{ss:.2f}", ha="right", va="center", fontsize=9.5, color=SLATE)
            ax.text(sa + pad, y, f"{sa:.2f}", ha="left", va="center", fontsize=9.5, color=NAVY)
        first = M[JURORS[0]]
        ax.text(_f(first["kappa_self_solve"]), Y[0] + 0.5, "self-solve routing", ha="center", fontsize=9, color=SLATE)
        ax.text(_f(first["kappa_self_agreement"]), Y[0] + 0.5, "self-agreement routing", ha="center", fontsize=9, color=NAVY)
        ax.set_yticks(Y); ax.set_yticklabels(JURORS)
        ax.set_ylim(-0.6, Y[0] + 0.9)
        ax.set_xticks([0.55, 0.60, 0.65, 0.70, 0.75]); ax.set_xticklabels(["0.55", "0.60", "0.65", "0.70", "0.75"])
        _title(fig, "Agreement with the experts (Cohen's κ), answers each juror keeps")
        fig.tight_layout(rect=(0, 0, 1, 0.96))
        return _save(fig, _figures(results, out) / NAMES["routing_at_matched_coverage"])


def agreement_by_jurors_that_agree(results=RESULTS, out=None) -> Path:
    """The agreement jury's kappa on the answers grouped by how many of the four jurors agree with themselves, 0 to 4, with the
    number of answers in each group (kappa_by_juror_count.csv), against its kappa on all answers (results_by_rule.csv)."""
    K = sorted((r for r in _rows(results, "kappa_by_juror_count") if r["jurors"] == "4" and r["count_of"] == "agree with themselves"),
               key=lambda r: int(r["count"]))
    alls = next(r for r in _rows(results, "results_by_rule")
                if r["jurors"] == "4" and r["rule"] == "agreement jury" and r["juror"] == "" and r["answer_set"] == "all")
    with mpl.rc_context(STYLE):
        fig = Figure(figsize=(WIDTH, 3.3))
        ax = fig.subplots()
        x = [int(r["count"]) for r in K]; k = [_f(r["kappa_jury"]) for r in K]
        ax.bar(x, k, width=0.62, color=NAVY, zorder=2)
        for xi, ki in zip(x, k):
            ax.text(xi, ki - 0.025, f"{ki:.2f}", ha="center", va="top", fontsize=9.5, color="white", zorder=3)
        ka = _f(alls["kappa"])
        ax.axhline(ka, color=REF, lw=1, ls=(0, (4, 3)), zorder=1)
        ax.text(x[0] - 0.31, ka + 0.02, f"agreement jury on all {int(alls['answers']):,} answers: {ka:.2f}", ha="left", va="bottom",
                fontsize=9, color=REF)
        ax.set_xticks(x); ax.set_xticklabels([f"{c}\n{int(r['answers']):,} answers" for c, r in zip(x, K)])
        ax.set_xlabel("how many of the four jurors agree with themselves", labelpad=8)
        ax.set_yticks([]); ax.grid(False); ax.set_ylim(0, 0.9); ax.set_xlim(x[0] - 0.5, x[-1] + 0.5)
        ax.tick_params(axis="x", length=0, pad=6)
        _title(fig, f"Agreement with the experts (Cohen's κ), agreement jury on {int(alls['answers']):,} answers")
        fig.tight_layout(rect=(0, 0, 1, 0.96))
        return _save(fig, _figures(results, out) / NAMES["agreement_by_jurors_that_agree"])


def uncovered_answers_fallbacks(results=RESULTS, out=None) -> Path:
    """Each fallback's kappa on the answers where no juror agrees with itself, with the 95% interval (uncovered_fallbacks.csv),
    against the agreement jury's kappa on the other answers (coverage.csv)."""
    F = {r["fallback"]: r for r in _rows(results, "uncovered_fallbacks")}
    own, own_only = ("own-answer reference (gpt-oss-120b gut read), majority vote where it has no own answer",
                     "own-answer reference, answers where gpt-oss-120b has its own answer")
    assert {k: v for k, v in F[own].items() if k != "fallback"} == {k: v for k, v in F[own_only].items() if k != "fallback"}
    rows = [("majority vote", "majority of four\n(the agreement jury here)", NAVY), ("gut majority vote", "gut majority", SILVER),
            ("best single judge, chosen without the question", "best single judge,\nchosen without the question", SILVER),
            (own, "own-answer reference", SILVER)]   # the last row of the file equals the own-answer row, so it is left out
    C = {r["measure"]: r for r in _rows(results, "coverage") if r["jurors"] == "4"}
    n_out = int(_f(C["answers where no juror agrees with itself"]["value"]))
    n_all = int(next(r for r in _rows(results, "results_by_rule") if r["jurors"] == "4" and r["answer_set"] == "all")["answers"])
    k_in = _f(C["kappa of the agreement jury where some juror agrees with itself"]["value"])
    assert all(int(F[r[0]]["answers"]) == n_out for r in rows)
    uncovered = [r for r in _rows(Path(results) / "per_answer", "answers") if r["jurors_agreeing"] == "0"]
    assert len(uncovered) == n_out
    with mpl.rc_context(STYLE):
        fig = Figure(figsize=(WIDTH, 3.3))
        ax = fig.subplots()
        ax.set_xlim(-0.6, 1.0)
        Y = list(range(len(rows)))[::-1]
        ax.axvline(0, color=REF, lw=1, ls=(0, (4, 3)), zorder=1)
        ax.axvline(k_in, color=REF, lw=1, ls=(0, (1.5, 2.5)), zorder=1)
        for y, (name, _, col) in zip(Y, rows):
            r = F[name]
            _interval(ax, y, _f(r["kappa"]), _f(r["kappa_lo"]), _f(r["kappa_hi"]), col, room=0.14, pad=0.025)
        ax.text(-0.015, Y[-1] - 0.55, "chance level", ha="right", va="top", fontsize=9, color=REF)
        ax.text(k_in - 0.015, Y[0] + 0.55, f"agreement jury, other {n_all - n_out} answers: {k_in:.2f}", ha="right", fontsize=9, color=REF)
        ax.set_yticks(Y); ax.set_yticklabels([r[1] for r in rows]); ax.set_ylim(-0.95, Y[0] + 0.9)
        ax.set_xticks([-0.4, 0, 0.4, 0.8]); ax.set_xticklabels(["-0.4", "0", "0.4", "0.8"])
        _title(fig, f"Agreement with the experts (Cohen's κ, 95% interval), {n_out} answers no juror vouches for")
        fig.tight_layout(rect=(0, 0, 1, 0.96))
        return _save(fig, _figures(results, out) / NAMES["uncovered_answers_fallbacks"])


def draw_all(results=RESULTS, out=None) -> list[Path]:
    """Draw the four charts from results/ into results/figures/ (or out). Returns the paths, in the order of the notebook."""
    return [agreement_by_jury_rule(results, out), routing_at_matched_coverage(results, out),
            agreement_by_jurors_that_agree(results, out), uncovered_answers_fallbacks(results, out)]
