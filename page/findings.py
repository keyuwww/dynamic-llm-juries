import marimo

__generated_with = "0.24.2"
app = marimo.App(
    width="medium",
    app_title="Grading Like the Experts",
)


@app.cell
def _():
    # Setup: imports, paths, house helpers. Export: marimo export html page/findings.py -o page/index.html --no-include-code -f
    # Data: every number comes from runs/ through lib/juries.py annotator() (cached in .cache/, rebuilt when a run file changes).
    # The notebook never calls a model.
    import sys
    import warnings
    from pathlib import Path

    import marimo as mo
    import pandas as pd

    warnings.filterwarnings("ignore")
    HERE = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
    ROOT = HERE.parent if HERE.name == "page" else HERE  # the grading_like_experts folder
    sys.path.insert(0, str(ROOT))
    from lib import charts as C
    from lib import juries as J
    from lib import nbkit as kit

    kit.enable_theme()

    esc = kit.esc
    card = kit.card
    NAVY, SILVER = kit.NAVY, kit.SILVER
    ORDER = J.ANNO_JUDGES  # most lenient first (false accepts on the standard prompt), the one order for every chart
    return C, J, NAVY, ORDER, SILVER, card, esc, kit, mo, pd


@app.cell
def _():
    # The only typed values in the notebook. Each entry carries its source on the line above.
    FACTS = {
        # source: prompts/standard.md, the baseline system prompt every judge got (quoted, last sentence cut)
        "judge_prompt": "You are an expert finance and accounting grader. Read the conversation and decide whether the assistant's FINAL response "
                        "correctly answers the user's final question. Key facts, calculations, numbers and conclusions must be correct; wording and formatting do not matter.",
        # source: prompts/experts_rules.md, No Free Labels appendix A.4, the annotator guidelines (shortened, same order)
        "rules": ["Final answer disagrees with the reference: incorrect",
                  "Final answer agrees but the steps disagree: incorrect",
                  "Extra information that is not obviously wrong: correct",
                  "Slightly off from rounding: correct",
                  "Missing information: decide if crucial; if unsure, correct"],
        # source: OpenRouter list price on Oct 15, 2026, in $ per million tokens (in, out), for the two judges we self-hosted
        "price": {"gpt-oss-120b": (0.15, 0.60), "gpt-oss-20b": (0.018, 0.09)},
        # source: prompts/, system message length in characters per prompt (for the token estimate)
        "system_chars": {"STD": 367, "GUIDE": 1116, "GUIDE_NO2": 933},
        # illustrative examples of each rejection reason (written for readability, not quoted from the runs)
        "examples": {"One point differs from the reference": "Recommends the right bond, but cites a different risk than the reference",
                     "A number or step differs": "Picks the same three bonds, but prices one at $1,038 instead of $1,028",
                     "The conclusion is hedged": "Recommends FRS 102, but notes when FRS 105 could also work",
                     "Missing information judged crucial": "Explains beta correctly, but leaves out the formula"},
    }
    return (FACTS,)


@app.cell
def _(FACTS, J):
    # Data: 5 judges x 2 or 3 prompts x 799 BFF-Bench answers with the expert reference (lib/juries.py annotator()).
    A = J.annotator()

    def cost(judge, arm):
        """$ per graded answer: what the API charged (gpt-4.1-mini estimated from tokens), or, for the self-hosted gpt-oss judges, their
        tokens at OpenRouter's list price (about 4 characters per input token, recorded output tokens)."""
        c = A["cells"][f"{judge}|{arm}"]
        if judge in FACTS["price"]:
            pin, pout = FACTS["price"][judge]
            return ((A["prompt_chars"] + FACTS["system_chars"][arm]) / 4 * pin + c["n_out"] * pout) / 1e6
        return c["cost"]

    return A, cost


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Grading Like the Experts
    """)
    return


@app.cell
def _(A, C, FACTS, ORDER, card, esc, kit, mo):
    _n = A["noise"]
    card([
        mo.md("## The experiment."),
        mo.Html(C.side_by_side("What the LLM judges were told", FACTS["judge_prompt"], "What the experts who made the labels were told", FACTS["rules"])),
        kit.kpi_strip([
            ("Answers graded", kit.num(A["n_items"]), f"where at least 2 of 3 experts agree on the label, from {A['n_question_turns']} of BFF-Bench's 160 finance questions"),
            ("Judges", str(len(ORDER)), ", ".join(ORDER)),
            ("Agreement", "Cohen's κ", "How closely a judge's verdicts match the experts', after removing matches expected by chance"),
            ("Rerun noise", f"{abs(_n['k1'] - _n['k0']):.2f}", "κ change from grading the same answers twice with the same prompt"),
        ]),
        mo.md(esc(f"**Kensho's judges were never shown the rules its experts graded by.** Each judge graded the same {kit.num(A['n_items'])} answers twice: with the standard prompt and with the experts' rules.")),
    ])
    return


@app.cell
def _(A, C, ORDER, pd):
    _d = pd.DataFrame([dict(judge=j, a=A["cells"][f"{j}|STD"]["kappa"][0], b=A["cells"][f"{j}|GUIDE"]["kappa"][0]) for j in ORDER])
    kappa_chart = C.dumbbell(_d, y="judge", a="a", b="b", order=ORDER, a_name="standard", b_name="expert rules",
                             title="Agreement with the experts (Cohen's κ)", x_title="κ", x_domain=(0.62, 0.82))
    return (kappa_chart,)


@app.cell
def _(A, FACTS, ORDER, card, esc, kappa_chart, kit, mo):
    _d = {j: A["deltas"][f"{j}|GUIDE-STD"] for j in ORDER}
    _g = [_d[j]["orig"][0] for j in ("qwen3.7-flash", "gpt-4.1-mini", "deepseek-v3.1")]
    card([
        mo.md("## Do the rules raise agreement?\n\nGrey is each judge with the standard prompt, navy with a prompt that gives the experts' rules instead. Judges run from most to least lenient, as the next section shows."),
        kappa_chart,
        mo.md(esc(f"**The rules lift lenient judges by {min(_g):.2f} to {max(_g):.2f}, and lower the two gpt-oss judges.** The three gains are bigger than chance, with 95% confidence intervals above 0.")),
    ])
    return


@app.cell
def _(A, ORDER, kit, pd):
    GROUPS = {"unanimous": f"All 3 experts agree ({A['groups']['unanimous']})", "two_plus_unsure": f"2 agree, 1 not sure ({A['groups']['two_plus_unsure']})",
              "split": f"2 to 1 split ({A['groups']['split']})"}
    _d = pd.DataFrame([dict(judge=j, group=GROUPS[g], v=v[0], lo=v[1], hi=v[2]) for j in ORDER for g, v in A["deltas_by_group"][f"{j}|GUIDE-STD"].items()])
    _short = {"qwen3.7-flash": "qwen", "gpt-4.1-mini": "4.1-mini", "deepseek-v3.1": "deepseek", "gpt-oss-20b": "oss-20b", "gpt-oss-120b": "oss-120b"}
    groups_chart = kit.dot_grid(_d, x="judge", y="v", lo="lo", hi="hi", column="group", order=ORDER, labels=_short, column_order=list(GROUPS.values()), hline=0,
                                hline_label="no change", fmt="+.2f", height=200).properties(title="Change in agreement from the rules (Cohen's κ)")
    return GROUPS, groups_chart


@app.cell
def _(A, card, esc, groups_chart, mo):
    _n = A["groups"]["two_plus_unsure"] + A["groups"]["split"]
    card([
        mo.md("## Does it hold when the experts disagreed?\n\nKensho counts an answer when at least 2 of its 3 experts agree, so we did the same for this experiment."),
        groups_chart,
        mo.md(esc(f"**The gain is clearest where all three experts agreed.** On the {_n} answers where one expert was unsure or dissented, every judge agrees less with the label, "
                  f"and no gain there is clearly above zero.")),
    ])
    return


@app.cell
def _(A, C, ORDER, pd):
    import altair as alt
    _d = pd.DataFrame([dict(judge=j, fa0=100 * A["cells"][f"{j}|STD"]["fpr"], fa1=100 * A["cells"][f"{j}|GUIDE"]["fpr"],
                            fr0=100 * A["cells"][f"{j}|STD"]["fnr"], fr1=100 * A["cells"][f"{j}|GUIDE"]["fnr"]) for j in ORDER])
    errors_chart = alt.hconcat(
        C.dumbbell(_d, y="judge", a="fa0", b="fa1", order=ORDER, a_name="standard", b_name="rules", title="False accepts: wrong answers called correct (%)",
                   fmt=".0f", x_domain=(-2.5, 20), width=300, tick_values=range(0, 21, 4)),
        C.dumbbell(_d, y="judge", a="fr0", b="fr1", order=ORDER, a_name="standard", b_name="rules", title="False rejects: correct answers called wrong (%)",
                   fmt=".0f", x_domain=(10, 32), width=300, show_y=False, tick_values=range(10, 33, 4)),
        spacing=24)
    return (errors_chart,)


@app.cell
def _(A, card, errors_chart, esc, kit, mo):
    _fa = [A["cells"][f"{j}|GUIDE"]["fpr"] for j in ("qwen3.7-flash", "gpt-4.1-mini", "deepseek-v3.1", "gpt-oss-20b", "gpt-oss-120b")]
    _r0 = [A["cells"][f"{j}|STD"]["fnr"] for j in ("gpt-oss-20b", "gpt-oss-120b")]
    _l0 = [A["cells"][f"{j}|STD"]["fpr"] for j in ("qwen3.7-flash", "gpt-4.1-mini", "deepseek-v3.1")]  # the lenient judges, standard prompt
    _r1 = [A["cells"][f"{j}|GUIDE"]["fnr"] for j in ("gpt-oss-20b", "gpt-oss-120b")]
    card([
        mo.md("## What changes in the verdicts?"),
        errors_chart,
        mo.md(esc(f"**False accepts fall to {kit.pct(min(_fa), 0)} to {kit.pct(max(_fa), 0)} for every judge**, down from {kit.pct(min(_l0), 0)} to {kit.pct(max(_l0), 0)} "
                  f"for the lenient judges (qwen3.7-flash, gpt-4.1-mini and deepseek), "
                  f"while false rejects rise mostly for gpt-oss, from about {kit.pct(sum(_r0) / 2, 0)} to {kit.pct(sum(_r1) / 2, 0)}.")),
    ])
    return


@app.cell
def _(A, C, NAVY, ORDER, SILVER, cost, pd):
    _d = pd.DataFrame([dict(judge=j, cost_a=1000 * cost(j, "STD"), k_a=A["cells"][f"{j}|STD"]["kappa"][0], cost_b=1000 * cost(j, "GUIDE"),
                            k_b=A["cells"][f"{j}|GUIDE"]["kappa"][0], col=NAVY) for j in ORDER])
    cost_chart = C.cost_moves(_d, title="Agreement against cost", log=False, x_ticks=(0, 0.2, 0.4, 0.6, 0.8, 1.0), y_domain=(0.62, 0.80))
    COSTS = _d.set_index("judge")
    return COSTS, cost_chart


@app.cell
def _(A, COSTS, ORDER, card, cost_chart, esc, kit, mo):
    _b = max(ORDER, key=lambda j: A["cells"][f"{j}|STD"]["kappa"][0])  # the best judge on the standard prompt
    _q, _o = A["cells"]["qwen3.7-flash|GUIDE"]["kappa"], A["cells"][f"{_b}|STD"]["kappa"]
    card([
        mo.md("## Can a cheap judge match the best one?\n\nEach line runs from a judge on the standard prompt in grey to the same judge with the rules in navy, where up is better and left is cheaper."),
        cost_chart,
        mo.md(esc(f"**Rules let a cheap judge match the best:** qwen3.7-flash reaches {_q[0]:.2f} against {_o[0]:.2f} for {_b}, the best judge on the standard prompt, "
                  f"at {kit.usd(COSTS.loc['qwen3.7-flash', 'cost_b'], 2)} against {kit.usd(COSTS.loc[_b, 'cost_a'], 2)} per 1,000 answers.")),
    ])
    return


@app.cell
def _(A, C, NAVY, kit, pd):
    _rows = ["gpt-oss-120b", "gpt-oss-20b"]
    _arms = [("STD", "standard prompt", kit.SILVER), ("GUIDE", "all 5 rules", kit.ORANGE), ("GUIDE_NO2", "rules without rule 2", NAVY)]
    _d = pd.DataFrame([dict(row=f"{j}, {name}", v=A["cells"][f"{j}|{a}"]["kappa"][0], lo=A["cells"][f"{j}|{a}"]["kappa"][1], hi=A["cells"][f"{j}|{a}"]["kappa"][2],
                            col=col, txt=f"{A['cells'][f'{j}|{a}']['kappa'][0]:.2f}") for j in _rows for a, name, col in _arms])
    strict_chart = C.row_dots(_d, y="row", x="v", lo="lo", hi="hi", color="col", label="txt", order=list(_d.row),
                              title="Agreement with the experts (Cohen's κ) for the two gpt-oss judges", x_title="κ", x_domain=(0.55, 0.85), width=420, row_height=34, tick_values=(0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85))
    return (strict_chart,)


@app.cell
def _(A, FACTS, J, card, esc, kit, mo, pd, strict_chart):
    _f = A["flips"]["gpt-oss-120b"]
    _read = J.rejections_read()
    assert set(_read.item_id) == set(_f["ids"]), "the hand reading no longer matches the run files: reread the new rejections"
    _t = (_read.reason.value_counts().rename_axis("Why it rejected the answer").reset_index(name="Answers")
          .assign(Example=lambda d: d["Why it rejected the answer"].map(FACTS["examples"])))
    card([
        mo.md(f"## Why does gpt-oss lose?\n\nOn the {A['groups']['unanimous']} answers all three experts agreed on, gpt-oss-120b rejected {_f['n']} correct answers with the rules "
              f"that it had accepted on the standard prompt, and we read its reasoning for each."),
        kit.html_table(_t, right=("Answers",)),
        mo.md("Rule 2 is the one rule that tells a judge to reject an answer with the right conclusion because a step differs. We reran both gpt-oss judges without it, to see whether that one rule causes the drop or gpt-oss is too strict with any rules."),
        strict_chart,
        mo.md(esc(f"**Dropping rule 2 reverts the damage:** both gpt-oss judges return to their standard prompt agreement of "
                  f"{A['cells']['gpt-oss-120b|GUIDE_NO2']['kappa'][0]:.2f} and {A['cells']['gpt-oss-20b|GUIDE_NO2']['kappa'][0]:.2f}, so no version of the rules we tested helps gpt-oss.")),
    ])
    return


@app.cell
def _(A, card, cost, kit, mo, pd):
    _k = lambda j, a: A["cells"][f"{j}|{a}"]["kappa"][0]  # noqa: E731
    _gain = [A["deltas"][f"{j}|GUIDE-STD"]["orig"][0] for j in ("qwen3.7-flash", "gpt-4.1-mini", "deepseek-v3.1")]
    _loss = [A["deltas"][f"{j}|GUIDE-STD"]["orig"][0] for j in ("gpt-oss-120b", "gpt-oss-20b")]
    _b = max(A["cells"], key=lambda k: A["cells"][k]["kappa"][0] if k.endswith("|STD") else -1).split("|")[0]  # best judge on the standard prompt
    _ratio = cost("qwen3.7-flash", "GUIDE") / cost(_b, "STD")
    _lo, _hi = f"{abs(max(_loss)):.2f}", f"{abs(min(_loss)):.2f}"
    _drop = _lo if _lo == _hi else f"{_lo} to {_hi}"  # both round to the same value on this run
    _t = pd.DataFrame([
        {"Finding": "The rules help 3 of 5 judges",
         "What it means": f"qwen3.7-flash, gpt-4.1-mini and deepseek gain {min(_gain):.2f} to {max(_gain):.2f} mostly by accepting fewer wrong answers",
         "What to do": "Give judges the experts' guidelines before adding more judges"},
        {"Finding": "A cheap judge can match the best",
         "What it means": f"qwen3.7-flash with the rules scores {_k('qwen3.7-flash', 'GUIDE'):.2f} against {_k(_b, 'STD'):.2f} for {_b}, the best on the standard prompt, at {_ratio:.0%} of the cost",
         "What to do": f"Default to qwen3.7-flash with the rules, or deepseek with the rules at {_k('deepseek-v3.1', 'GUIDE'):.2f} when agreement matters more"},
        {"Finding": "The rules hurt gpt-oss",
         "What it means": f"It rejects correct answers over one detail that differs from the reference, losing {_drop}",
         "What to do": "Keep gpt-oss on the standard prompt and test new judges on both prompts"},
    ])
    card([
        mo.md("## Key takeaways"),
        kit.html_table(_t),
        kit.note("Still open: does any careful rubric work as well, and does this hold outside finance?"),
    ])
    return


if __name__ == "__main__":
    app.run()
