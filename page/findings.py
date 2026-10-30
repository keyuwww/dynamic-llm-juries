import marimo

__generated_with = "0.24.2"
app = marimo.App(
    width="medium",
    app_title="Self-Agreement",
)


@app.cell
def _():
    # Setup: imports, paths, house helpers. Export: marimo export html page/findings.py -o page/index.html --no-include-code -f
    # Data: every number comes from the CSVs the notebook writes to results/ (notebook/self_agreement.ipynb, lib/self_agreement.py write_results()).
    # The page reads those tables only. It never recomputes them and never calls a model.
    import sys
    import warnings
    from pathlib import Path

    import marimo as mo
    import pandas as pd

    warnings.filterwarnings("ignore")
    HERE = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
    ROOT = HERE.parent if HERE.name == "page" else HERE  # the self_agreement folder
    sys.path.insert(0, str(ROOT))
    from lib import charts as C
    from lib import nbkit as kit

    kit.enable_theme()

    esc = kit.esc
    card = kit.card
    NAVY, SILVER = kit.NAVY, kit.SILVER
    JURORS = ["gpt-oss-20b", "gpt-oss-120b", "qwen3.6-35b", "nemotron-3-super"]  # the four kept jurors: the one juror order for every chart and table
    BEST = "best single judge (gpt-oss-120b reasoned read)"  # the best single judge's name in contrasts.csv
    N = len(JURORS)
    WORD = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}  # small counts written as words in prose
    return BEST, C, JURORS, N, NAVY, ROOT, SILVER, WORD, card, esc, kit, mo, pd


@app.cell
def _():
    # The only typed values on the page. Each entry carries its source on the line above.
    FACTS = {
        # source: runs/ (every model output is from the run on Oct 24, 2026) and data/README.md (the answers, labels and questions)
        "byline": "Isaac Chang · Oct 24, 2026 · 544 finance and MT-Bench answers graded by four open-weight LLM jurors on Tinker, "
                  "none shown an answer key · source: notebook/self_agreement.ipynb",
        # source: results/decisions.csv `needs`, the rules set before the run (rule 1, rule 2 and the self-solve gap test)
        "rule1": 0.04,
        "rule2": 0.03,
        "holds": (0.65, 0.55),
        "vanishes": (0.60, 0.10),
        # source: the plan written before the run (not in this folder): pooled κ differences below 0.03 are not interpreted, and a
        # tie on rule 1 prefers self-agreement because it needs no reference
        "noise": 0.03,
        # source: lib/self_agreement.py screening(), the juror screening rule on the first 100 finance answers, and the grader bar
        "juror_bar": {"auroc": 0.60, "verdict_rate": 0.90, "missing": 0.05},
        "grader_bar": 0.80,
    }
    return (FACTS,)


@app.cell
def _(FACTS, ROOT, pd):
    # Data: the tables in results/ (main tables) and results/checks/ (supporting checks), as the notebook wrote them.
    R = ROOT / "results"

    def _csv(name):
        return pd.read_csv(R / name)

    RULES = _csv("results_by_rule.csv").fillna({"juror": ""})
    CON, DEC, MC = _csv("contrasts.csv"), _csv("decisions.csv"), _csv("matched_coverage.csv")
    COV, UNC, CNT = _csv("coverage.csv"), _csv("uncovered_fallbacks.csv"), _csv("kappa_by_juror_count.csv")
    ERR, LAT = _csv("error_rankers.csv").fillna({"compared_with": ""}), _csv("latent_solver.csv")
    SETS, GRADE, JCHECK = _csv("checks/answer_sets.csv").set_index("answer_set"), _csv("checks/grader_check.csv"), _csv("checks/juror_check.csv")
    DUP = _csv("checks/duplicates.csv").set_index("reader")

    def rule(name, juror="", answer_set="all", jurors=4):
        """The results_by_rule row of one rule (and juror, for a single read)."""
        return RULES[(RULES.rule == name) & (RULES.juror == juror) & (RULES.answer_set == answer_set) & (RULES.jurors == jurors)].iloc[0]

    def contrast(name, minus, answer_set="all", jurors=4):
        """The contrasts row of `name` minus `minus`."""
        return CON[(CON.rule == name) & (CON.minus == minus) & (CON.answer_set == answer_set) & (CON.jurors == jurors)].iloc[0]

    def decision(prefix, jurors=4):
        """The decisions row whose decision starts with `prefix`."""
        return DEC[DEC.decision.str.startswith(prefix) & (DEC.jurors == jurors)].iloc[0]

    def cov(measure, jurors=4):
        """The coverage row of one measure."""
        return COV[(COV.measure == measure) & (COV.jurors == jurors)].iloc[0]

    # the rules as the page states them must be the rules the analysis applied
    assert f"{FACTS['rule1']:+.2f}" in decision("rule 1").needs and f"{FACTS['rule2']:+.2f}" in decision("rule 2").needs
    assert all(f"{v:.2f}" in decision("self-solve gap").needs for v in (*FACTS["holds"], FACTS["vanishes"][0]))
    assert f"{FACTS['vanishes'][1]:+.2f}" in decision("self-solve gap").needs
    assert (GRADE.passes == (GRADE.kappa >= FACTS["grader_bar"])).all()
    return CNT, DUP, ERR, GRADE, JCHECK, LAT, MC, RULES, SETS, UNC, contrast, cov, decision, rule


@app.cell
def _(kit):
    # Number formats used in every sentence and table: κ and AUROC with 3 decimals, differences signed, intervals as "point (lo to hi)".
    def f3(v):
        return f"{v:.3f}"

    def iv(v, lo, hi):
        return f"{v:.3f} ({lo:.3f} to {hi:.3f})"

    def dv(v, lo, hi):
        return f"{v:+.3f} ({lo:+.3f} to {hi:+.3f})"

    def pct(v, d=0):
        return kit.pct(v, d)

    def of(n, total):
        """'all 4' when every one qualifies, else '3 of 4'."""
        return f"all {total}" if n == total else f"{n} of {total}"
    return dv, f3, iv, of, pct


@app.cell(hide_code=True)
def _(FACTS, kit, mo):
    mo.vstack([
        mo.md("# Self-Agreement"),
        mo.Html(f"<div style='font-size:19px;line-height:1.4;color:{kit.TEXT_3};margin:-4px 0 10px'>"
                "Can an LLM judge tell when to trust itself without an answer key?</div>"),
        kit.byline(FACTS["byline"]),
    ], gap=0)
    return


@app.cell
def _(BEST, FACTS, MC, contrast, dv, kit, mo, of):
    # 01 is the opening claim of "Which signal should route a judge's answers?"
    # 02 is the opening claim of "Does self-agreement beat self-solve inside a jury?"
    # 03 is the opening claim of "Does the agreement jury beat the best single judge?"
    _d = MC.self_agreement_minus_self_solve
    _r1 = contrast("agreement jury", "self-solve jury")
    _r2 = contrast("agreement jury", BEST)
    mo.vstack([
        mo.md("# Key takeaways"),
        kit.takeaways([
            ("Self-agreement routes a juror's answers better than self-solve.",
             f"It agrees better with the experts for {of(int((_d > 0).sum()), len(MC))} jurors, by {_d.min():+.3f} to {_d.max():+.3f} in Cohen's κ, "
             f"with an interval above 0 for {of(int((MC.self_agreement_minus_self_solve_lo > 0).sum()), len(MC))}. "
             f"Self-solve's grader missed its {FACTS['grader_bar']:.2f} bar."),
            ("Inside a jury, the two signals tie.",
             f"The agreement jury leads the self-solve jury by {dv(_r1.difference, _r1.lo, _r1.hi)}, short of the {FACTS['rule1']:+.2f} "
             "set before the run."),
            ("The agreement jury does not beat the best single judge.",
             f"Its edge over gpt-oss-120b's reasoned read is {dv(_r2.difference, _r2.lo, _r2.hi)}, an interval that includes 0. "
             "That judge was chosen in hindsight with the expert labels."),
        ]),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # What we tested
    """)
    return


@app.cell
def _(DUP, JCHECK, JURORS, SETS, card, esc, kit, mo):
    _a, _f, _m = SETS.loc["all"], SETS.loc["finance"], SETS.loc["mt_bench"]
    card([
        mo.md("## The experiment."),
        kit.kpi_strip([
            ("Answers", kit.num(_a.answers), f"{_f.answers} finance answers and {_m.answers} MT-Bench answers to {_a.questions} questions, each labelled by three experts"),
            ("Jurors", str(len(JURORS)), f"of {len(JCHECK)} screened: {', '.join(JURORS[:-1])} and {JURORS[-1]}"),
            ("Answer key", "None", "No juror saw a reference answer. Agreement is Cohen's κ with the experts' majority label"),
            ("Rerun noise", f"{int(DUP.loc['agreement jury', 'verdict_flips'])} of {int(DUP.loc['agreement jury', 'answers'])}",
             "agreement jury verdicts changed when the first answers were read a second time"),
        ]),
        kit.rules_table([
            ("Gut read", "One token and no reasoning: whether INCORRECT or CORRECT is more likely right after \"VERDICT:\""),
            ("Reasoned read", "The juror reasons first, then writes CORRECT or INCORRECT"),
            ("Agrees with itself", "Its gut read and its reasoned read give the same verdict. This needs no answer key"),
            ("Conflict", "How strongly its gut read leans against its reasoned verdict. A low conflict means the gut read firmly backs that verdict"),
            ("Solved the question", "The juror answered the question itself, and a grader that saw the expert reference called its answer correct. "
                                    "Kensho's paper No Free Labels trusts a judge only on the questions it can solve"),
        ], highlight={2}, highlight_label="The trust signal we test"),
        mo.md(esc("**Each juror graded every answer twice, and we asked which jurors to trust on each one.** Without an answer key, "
                  "a juror can check itself only against itself. So we compared trusting jurors whose two reads agree with "
                  "trusting jurors that could solve the question.")),
    ])
    return


@app.cell
def _(FACTS, RULES, card, decision, kit, mo, pd):
    _o = {k: decision(k).outcome for k in ("rule 1", "rule 2", "self-solve gap")}
    _singles = RULES[(RULES.jurors == 4) & (RULES.answer_set == "all") & RULES.rule.isin(["gut read", "reasoned read"])]
    _same = all(decision(k, n).outcome == decision(k, 4).outcome for k in ("rule 1", "rule 2") for n in (3, 5))
    _t = pd.DataFrame([
        {"Rule": "Rule 1: agreement against self-solve",
         "What it needs": f"The agreement jury wins at {FACTS['rule1']:+.2f} or more over the self-solve jury, with its interval above 0. "
                          f"The self-solve jury wins at {-FACTS['rule1']:+.2f} or less, with its interval below 0. Anything else is a tie",
         "Result": _o["rule 1"]},
        {"Rule": "Rule 2: the jury wins",
         "What it needs": f"The agreement jury beats the best single judge by {FACTS['rule2']:+.2f} or more, with its interval above 0, "
                          "and is at least the majority of four",
         "Result": _o["rule 2"]},
        {"Rule": "Self-solve gap test",
         "What it needs": f"Holds if self-agreement ranks a juror's errors on questions it could not solve at an AUROC of {FACTS['holds'][0]:.2f} "
                          f"or more, lower bound {FACTS['holds'][1]:.2f}. Vanishes at {FACTS['vanishes'][0]:.2f} or less with solved minus unsolved at "
                          f"{FACTS['vanishes'][1]:+.2f} or more",
         "Result": _o["self-solve gap"]},
    ])
    card([
        mo.md("## The juries, and the rules we set before the run."),
        kit.rules_table([
            ("Agreement jury", "Only jurors that agree with themselves vote, with their reasoned verdicts"),
            ("Self-solve jury", "Only jurors that solved the question vote, with their reasoned verdicts"),
            ("Majority of four", "Every juror's reasoned verdict votes, and a tie counts as a reject. The gut majority is the same vote over the gut reads"),
            ("Best single judge", f"gpt-oss-120b's reasoned read, the best of the {len(_singles)} single reads, chosen in hindsight with the expert labels"),
        ], highlight={0}, highlight_label="The jury we test"),
        kit.note("When no juror qualifies, a jury falls back on the majority of four. A tie goes to the voter whose gut read is most "
                 "confident, and a missing verdict counts as a reject. A juror with no reasoned verdict never counts as agreeing with itself."),
        kit.html_table(_t, right=("Result",)),
        kit.note(f"AUROC is the chance that a score ranks an error above a correct verdict, where 0.5 is chance. Differences in κ below "
                 f"{FACTS['noise']:.2f} are not read as real. The three-juror jury, closest to the planned design, and a five-juror jury with "
                 f"gpt-oss-safeguard-20b {'reach the same outcomes on both rules' if _same else 'reach different outcomes'}. "
                 "The plan is not in this folder, but results/decisions.csv quotes each rule."),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Which answers to trust
    """)
    return


@app.cell
def _(C, JURORS, MC):
    _d = MC.set_index("juror").loc[JURORS].reset_index()
    _d["row"] = [f"{j}, keeps {n}" for j, n in zip(_d.juror, _d.answers_kept)]
    routing_chart = C.routing_rows(_d, y="row", a="kappa_self_solve", b="kappa_self_agreement", tick="kappa_random_95th", order=list(_d.row),
                                   a_name="self-solve", b_name="self-agreement", tick_name="random, 95th percentile",
                                   title="Agreement of each juror's reasoned read with the experts on the answers it keeps, Cohen's κ",
                                   fmt=".3f", x_domain=(0.50, 0.80), tick_values=(0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80), width=440)
    return (routing_chart,)


@app.cell
def _(FACTS, MC, card, esc, kit, mo, of, routing_chart):
    _d = MC.self_agreement_minus_self_solve
    _sig = int((MC.self_agreement_minus_self_solve_lo > 0).sum())
    _below = int((MC.kappa_self_solve < MC.kappa_random_95th).sum())
    card([
        mo.md("## Which signal should route a judge's answers?\n\nRouting means choosing which of a juror's answers to trust. Each juror keeps "
              "as many answers as it solved, chosen two ways. Grey keeps the answers on questions it solved, navy the ones with the least "
              "conflict between its two reads. The dark tick is the 95th percentile of random draws of the same size."),
        routing_chart,
        mo.md(esc(f"**Self-agreement routes a juror's answers better than self-solve.** It scores higher for {of(int((_d > 0).sum()), len(MC))} jurors, "
                  f"by {_d.min():+.3f} to {_d.max():+.3f}, with an interval above 0 for {of(_sig, len(MC))}. In κ, self-solve routing falls below "
                  f"the random 95th percentile for {of(_below, len(MC))}, and it rests on a grader that missed its {FACTS['grader_bar']:.2f} bar.")),
        mo.md(esc(f"**Solving still matters.** On the answers it did not solve, each juror's reasoned read scores κ {MC.kappa_unsolved.min():.2f} to "
                  f"{MC.kappa_unsolved.max():.2f}, against {MC.kappa_self_solve.min():.2f} to {MC.kappa_self_solve.max():.2f} on those it solved.")),
        kit.note(("Self-agreement also beats the gut read on the answers where that read is most confident, with an interval above 0 for every juror. "
                  if (MC.self_agreement_minus_gut_confidence_lo > 0).all() else "Against the gut read on its most confident answers the result is mixed. ")
                 + "Against the reasoned read on those same answers it is mixed. This comparison was planned, but no decision rule was set for it before the run. "
                 "A pilot on Oct 23, 2026, with gpt-oss-20b alone, set it as a test before its run and found the same."),
    ])
    return


@app.cell
def _(FACTS, N, WORD, card, contrast, decision, dv, esc, kit, mo, pd, rule):
    _names = {4: "Four jurors", 3: "Three jurors, closest to the planned design", 5: "Five, with gpt-oss-safeguard-20b"}
    _t = pd.DataFrame([{"Jury": _names[n], "Agreement jury": f"{rule('agreement jury', jurors=n).kappa:.3f}",
                        "Self-solve jury": f"{rule('self-solve jury', jurors=n).kappa:.3f}",
                        "Difference": dv(*contrast("agreement jury", "self-solve jury", jurors=n)[["difference", "lo", "hi"]]),
                        "Rule 1": decision("rule 1", n).outcome} for n in (4, 3, 5)])
    _r1 = contrast("agreement jury", "self-solve jury")
    card([
        mo.md("## Does self-agreement beat self-solve inside a jury?\n\nEach row is one jury, scored on all 544 answers. "
              "The difference is the agreement jury minus the self-solve jury, in κ, with its 95% interval."),
        kit.html_table(_t, right=("Agreement jury", "Self-solve jury", "Difference", "Rule 1")),
        mo.md(esc(f"**Inside a jury, the two signals tie.** With {WORD[N]} jurors the agreement jury leads by {dv(_r1.difference, _r1.lo, _r1.hi)}, "
                  f"short of the {FACTS['rule1']:+.2f} rule 1 needed. The plan preferred self-agreement in a tie, because it needs no answer key, "
                  "while self-solve needs a grader that sees the reference.")),
    ])
    return


@app.cell
def _(C, NAVY, SILVER, pd, rule):
    _rows = [("Agreement jury", rule("agreement jury"), NAVY),
             ("Best single judge, gpt-oss-120b", rule("reasoned read", "gpt-oss-120b"), SILVER),
             ("Majority of four", rule("majority vote"), SILVER),
             ("Self-solve jury", rule("self-solve jury"), SILVER),
             ("Gut majority", rule("gut majority vote"), SILVER)]
    _d = pd.DataFrame([dict(row=n, v=r.kappa, lo=r.kappa_lo, hi=r.kappa_hi, col=c, txt=f"{r.kappa:.3f}") for n, r, c in _rows])
    rules_chart = C.row_dots(_d, y="row", x="v", lo="lo", hi="hi", color="col", label="txt", order=list(_d.row),
                             title=f"Agreement with the experts on all {int(rule('agreement jury').answers)} answers, Cohen's κ", x_domain=(0.40, 0.80),
                             tick_values=(0.40, 0.50, 0.60, 0.70, 0.80), width=460, row_height=38, label_limit=240)
    return (rules_chart,)


@app.cell
def _(BEST, FACTS, N, RULES, WORD, card, contrast, dv, esc, kit, mo, pd, rule, rules_chart):
    _j, _b, _r2 = rule("agreement jury"), rule("reasoned read", "gpt-oss-120b"), contrast("agreement jury", BEST)
    _t = pd.DataFrame([{"Agreement jury minus": n, **{lab: dv(*contrast("agreement jury", m, s)[["difference", "lo", "hi"]])
                                                      for s, lab in (("all", "All answers"), ("finance", "Finance"), ("mt_bench", "MT-Bench"))}}
                       for n, m in (("Best single judge", BEST), ("Majority of four", "majority vote"), ("Self-solve jury", "self-solve jury"))])
    _mt = RULES[(RULES.jurors == 4) & (RULES.rule == "reasoned read") & (RULES.answer_set == "mt_bench")].kappa
    card([
        mo.md("## Does the agreement jury beat the best single judge?\n\nEach dot is one rule's agreement with the experts, with its 95% interval. "
              "Navy is the agreement jury and grey the comparisons. Further right is better."),
        rules_chart,
        mo.md(esc(f"**The agreement jury does not beat the best single judge.** It reaches {_j.kappa:.3f}, against {_b.kappa:.3f} for "
                  f"gpt-oss-120b's reasoned read, a gain of {dv(_r2.difference, _r2.lo, _r2.hi)}. Rule 2 needed {FACTS['rule2']:+.2f} with an "
                  f"interval above 0, so this run does not show that {WORD[N]} jurors beat one.")),
        kit.html_table(_t, right=("All answers", "Finance", "MT-Bench"), caption="Agreement jury minus each comparison, in κ, with its 95% interval",
                       note=f"The jury gains most on finance answers. On MT-Bench every juror's reasoned read already reaches "
                            f"{_mt.min():.2f} to {_mt.max():.2f}, which leaves little room."),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Where a person should look
    """)
    return


@app.cell
def _(C, NAVY, SILVER, UNC, cov, pd):
    _names = {"majority vote": "Majority of four, what the agreement jury uses here",
              "gut majority vote": "Gut majority",
              "best single judge, chosen without the question": "Best single judge, chosen without the question",
              "own-answer reference (gpt-oss-120b gut read), majority vote where it has no own answer": "Own-answer reference, gpt-oss-120b's gut read"}
    _d = pd.DataFrame([dict(row=_names[r.fallback], v=r.kappa, lo=r.kappa_lo, hi=r.kappa_hi, col=NAVY if r.fallback == "majority vote" else SILVER,
                            txt=f"{r.kappa:.3f}") for r in UNC.itertuples() if r.fallback in _names])
    _k = cov("kappa of the agreement jury where some juror agrees with itself")
    fallback_chart = C.row_dots(_d, y="row", x="v", lo="lo", hi="hi", color="col", label="txt", order=list(_names.values()),
                                title=f"Agreement with the experts on the {int(UNC.answers.iloc[0])} answers where no juror agrees with itself, Cohen's κ",
                                x_domain=(-0.5, 1.0), tick_values=(-0.5, -0.25, 0, 0.25, 0.5, 0.75, 1.0), vline=0, vline_label="chance", vline_left=True,
                                bar=_k.value, bar_label="agreement jury on the rest", width=420, row_height=38, label_limit=320)
    return (fallback_chart,)


@app.cell
def _(UNC, card, cov, esc, fallback_chart, iv, kit, mo, pct):
    _n = int(cov("answers where no juror agrees with itself").value)
    _own = UNC[UNC.fallback.str.startswith("own-answer reference (")].iloc[0]
    _rest = cov("kappa of the agreement jury where some juror agrees with itself")
    _auto = cov("share of answers where some juror agrees with itself (the rest go to a person)").value
    _dis = (cov("share with expert dissent, no juror agrees").value, cov("share with expert dissent, some juror agrees").value)
    card([
        mo.md("## How often does no juror vouch for an answer?\n\nEach dot is one fallback's agreement with the experts on the answers where no "
              "juror agrees with itself, with its 95% interval. Navy is what the agreement jury falls back on, and the dotted line is the agreement jury on every other answer."),
        fallback_chart,
        mo.md(esc(f"**No juror vouches for {_n} answers, {pct(cov('share of answers where no juror agrees with itself').value, 1)} of the total, "
                  f"and every fallback is weak there.** The best, gpt-oss-120b's gut read with its own answer as the reference, reaches "
                  f"{_own.kappa:.3f}, against {iv(_rest.value, _rest.lo, _rest.hi)} for the agreement jury on the rest. A person's review is the safe "
                  f"default for them, untested here, and would keep {pct(_auto)} of answers automatic.")),
        kit.note(f"Experts split more often on these answers, {pct(_dis[0], 1)} with an expert who dissented or was unsure against "
                 f"{pct(_dis[1], 1)} of the rest, but the gap could be chance."),
    ])
    return


@app.cell
def _(C, CNT, NAVY, SILVER, pd):
    _panels = {"agree with themselves": "Jurors that agree with themselves: agreement jury", "solved the question": "Jurors that solved the question: self-solve jury"}
    _d = pd.DataFrame([dict(panel=_panels[r.count_of], x=f"{r.count}\n{r.answers}", y=r.kappa_jury, label=f"{r.kappa_jury:.2f}")
                       for r in CNT[CNT.jurors == 4].sort_values(["count_of", "count"]).itertuples()])
    count_chart = C.count_panels(_d, panel="panel", panels=list(_panels.values()), x="x", y="y", label="label", colors=[NAVY, SILVER],
                                 title="Agreement with the experts by how many of the four jurors qualify, Cohen's κ", y_domain=(0, 0.9), width=330)
    return (count_chart,)


@app.cell
def _(CNT, ERR, N, SETS, WORD, card, count_chart, esc, iv, kit, mo, pd):
    _c = CNT[(CNT.jurors == 4) & (CNT.count_of == "agree with themselves")].set_index("count")
    _a = ERR[ERR.measure == "auroc"].set_index("score")
    _d = ERR[ERR.measure == "auroc difference"].set_index("compared_with")
    _t = pd.DataFrame([{"Score, higher is less trusted": s[0].upper() + s[1:], "AUROC": iv(r.estimate, r.lo, r.hi)} for s, r in _a.iterrows()])
    card([
        mo.md("## Does the count of jurors that agree track agreement with the experts?\n\nEach bar is a jury's agreement with the experts on the answers where that "
              "many jurors qualify: agree with themselves on the left, solved the question on the right. Under each count is its number of answers."),
        count_chart,
        mo.md(esc(f"**The more jurors agree with themselves, the closer the jury is to the experts.** κ climbs with each juror that agrees with itself, "
                  f"from {_c.loc[0].kappa_jury:.2f} with none to {_c.loc[N].kappa_jury:.2f} with all {WORD[N]}. All {WORD[N]} agree on {_c.loc[N].answers} of "
                  f"{SETS.loc['all'].answers} answers. The count that solved the question does not climb the same way.")),
        kit.note("No interval was computed for these groups, and the grouping was not a test set before the run."),
        kit.html_table(_t, right=("AUROC",), caption="Post hoc: how well each score ranks the majority of four's errors, with its 95% interval",
                       note=f"Added after the analysis first ran, so it is a lead, not a test. The count that agrees beats the count that solved by "
                            f"{_d.loc['fewer jurors solved the question'].estimate:+.3f}, with an interval above 0. The summed gut margins rank the errors "
                            f"about as well, {_a.loc['weak summed gut margin'].estimate:.3f} against {_a.loc['fewer jurors agree with themselves'].estimate:.3f}."),
    ])
    return


@app.cell
def _(C, LAT, NAVY, SILVER, FACTS, pd):
    _names = {"solved": "Solved", "contested": "Contested: grader and answer key disagree", "unsolved": "Unsolved",
              "unsolved, own answer present": "Unsolved, with its own answer"}
    _a = LAT[LAT.juror == "all"].set_index("self_solve_status")
    _d = pd.DataFrame([dict(row=f"{n}, {_a.loc[s].units:,} units", v=_a.loc[s].auroc, lo=_a.loc[s].auroc_lo, hi=_a.loc[s].auroc_hi,
                            col=NAVY if s.startswith("unsolved") else SILVER, txt=f"{_a.loc[s].auroc:.3f}") for s, n in _names.items()])
    gap_chart = C.row_dots(_d, y="row", x="v", lo="lo", hi="hi", color="col", label="txt", order=list(_d.row),
                           title="How well the conflict between a juror's two reads ranks its errors, AUROC", x_domain=(0.5, 1.0),
                           tick_values=(0.5, 0.6, 0.7, 0.8, 0.9, 1.0), vline=FACTS["vanishes"][0], vline_label=f"vanishes at {FACTS['vanishes'][0]:.2f}",
                           vline_left=True, bar=FACTS["holds"][0], bar_label=f"holds at {FACTS['holds'][0]:.2f}", width=400, row_height=38, label_limit=320)
    return (gap_chart,)


@app.cell
def _(FACTS, LAT, card, decision, dv, esc, gap_chart, iv, mo):
    _a = LAT[LAT.juror == "all"].set_index("self_solve_status")
    _s, _u, _g = _a.loc["solved"], _a.loc["unsolved"], _a.loc["solved minus unsolved"]
    card([
        mo.md("## Does self-agreement still flag errors where the juror could not solve the question?\n\nOne unit is one juror on one answer. Each "
              "dot is an AUROC with its 95% interval, where 0.5 is chance. Navy is the test, the dotted line the bar for holds and the dashed line the bar for vanishes."),
        gap_chart,
        mo.md(esc(f"**The signal is lower on unsolved questions but does not vanish.** On unsolved units its AUROC is "
                  f"{iv(_u.auroc, _u.auroc_lo, _u.auroc_hi)}, above chance but short of the {FACTS['holds'][0]:.2f} bar for holds. On solved units it is "
                  f"{_s.auroc:.3f}, and the drop of {dv(_g.auroc, _g.auroc_lo, _g.auroc_hi)} could be chance. So the test lands "
                  f"{decision('self-solve gap').outcome} the two outcomes we set.")),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # How far to trust the run
    """)
    return


@app.cell
def _(DUP, JURORS, card, esc, kit, mo, pd):
    _i = lambda r, c: int(DUP.loc[r, c])  # noqa: E731  (the jury rows have no gut columns, so the frame holds floats)
    _t = pd.DataFrame([{"Reader": r, "Reasoned verdicts changed": f"{_i(r, 'verdict_flips')} of {_i(r, 'answers')}",
                        "Gut reads that changed sign": f"{_i(r, 'gut_flips')} of {_i(r, 'answers')}",
                        "Median change in gut margin": f"{DUP.loc[r].median_abs_margin_change:.3f}"} for r in JURORS]
                      + [{"Reader": n, "Reasoned verdicts changed": f"{_i(r, 'verdict_flips')} of {_i(r, 'answers')}",
                          "Gut reads that changed sign": "", "Median change in gut margin": ""}
                         for r, n in (("agreement jury", "Agreement jury"), ("majority vote", "Majority of four"))])
    _f = DUP.loc[JURORS].verdict_flips.astype(int)
    card([
        mo.md(f"## Are the reads stable?\n\nEach juror read the first {_i(JURORS[0], 'answers')} answers a second time, in the same session and at temperature 0."),
        kit.html_table(_t, right=("Reasoned verdicts changed", "Gut reads that changed sign", "Median change in gut margin")),
        mo.md(esc(f"**Reads barely move on a second pass.** {_f.min()} to {_f.max()} reasoned verdicts changed per juror and no gut read changed sign. "
                  f"The agreement jury changed {_i('agreement jury', 'verdict_flips')} verdict, so rerun noise is small next to the sampling intervals above.")),
    ])
    return


@app.cell
def _(FACTS, GRADE, JCHECK, JURORS, WORD, card, esc, kit, mo, pct, pd):
    _t = pd.DataFrame([{"Juror": r.juror, "Gut AUROC": f"{r.gut_auroc:.3f}", "Reasoned verdicts": pct(r.verdict_rate),
                        "Hit the token limit": pct(r.token_limit_rate), "Token limit": kit.num(r.token_limit), "Result": "kept" if r.kept else "dropped"}
                       for r in pd.concat([JCHECK[JCHECK.kept].set_index("juror").loc[JURORS].reset_index(), JCHECK[~JCHECK.kept]]).itertuples()])
    _drop = JCHECK[~JCHECK.kept]
    _g = GRADE.set_index("grader")
    _c = _g[_g.chosen].iloc[0]
    card([
        mo.md(f"## Which jurors and grader passed screening?\n\nEach juror gave a gut read and a reasoned read of the first {JCHECK.answers.iloc[0]} finance answers. "
              "Gut AUROC is how well the gut margin ranks correct answers above wrong ones. Reasoned verdicts is the share of reasoned reads that ended in a verdict."),
        kit.html_table(_t, right=("Gut AUROC", "Reasoned verdicts", "Hit the token limit", "Token limit", "Result"),
                       note=f"A juror was kept with a gut AUROC of {FACTS['juror_bar']['auroc']:.2f} or more, a verdict on {pct(FACTS['juror_bar']['verdict_rate'])} "
                            f"or more of its reasoned reads and {pct(FACTS['juror_bar']['missing'])} or fewer missing gut margins."),
        mo.md(esc(f"**{WORD[int(JCHECK.kept.sum())].capitalize()} of {WORD[len(JCHECK)]} jurors passed, and "
                  + ("neither grader did.** " if not GRADE.passes.any() else f"{int(GRADE.passes.sum())} of {len(GRADE)} graders did.** ")
                  + f"{' and '.join(_drop.juror)} looped and ran out of tokens on "
                  f"{pct(_drop.token_limit_rate.iloc[0])} and {pct(_drop.token_limit_rate.iloc[1])} of their reasoned reads. The grader {_g[_g.chosen].index[0]} reached "
                  f"κ {_c.kappa:.3f} against the {FACTS['grader_bar']:.2f} bar, so self-solve rests on an imperfect grader.")),
        kit.note(f"Both graders read {_c.answers} finance answers with the expert reference. {_g[~_g.chosen].index[0]} reached {_g[~_g.chosen].kappa.iloc[0]:.3f}. "
                 f"{_g[_g.chosen].index[0]} rejected {_c.label_correct_rejected} of the {_c.label_correct} correct ones."),
    ])
    return


@app.cell
def _(BEST, CNT, MC, N, WORD, card, contrast, cov, kit, mo, of, pd, pct):
    _c = CNT[(CNT.jurors == 4) & (CNT.count_of == "agree with themselves")].set_index("count")
    _r2 = contrast("agreement jury", BEST)
    _d = MC.self_agreement_minus_self_solve
    _t = pd.DataFrame([
        {"Finding": "Self-agreement routes better than self-solve",
         "What it means": f"It scores higher for {of(int((_d > 0).sum()), len(MC))} jurors, by {_d.min():+.3f} to {_d.max():+.3f} in κ, "
                          "and needs no answer key, but no decision rule was set for it before the run",
         "What to do": "Test it with a rule set in advance and a grader that meets its bar"},
        {"Finding": "The agreement jury does not beat the best single judge",
         "What it means": f"It adds {_r2.difference:+.3f} over gpt-oss-120b's reasoned read, chosen with the expert labels, and the interval includes 0",
         "What to do": "Test a larger or more varied jury before relying on four judges over one"},
        {"Finding": "No juror vouches for some answers",
         "What it means": f"On {pct(cov('share of answers where no juror agrees with itself').value, 1)} of answers every fallback is weak",
         "What to do": f"Send those answers to a person, untested here, which keeps {pct(cov('share of answers where some juror agrees with itself (the rest go to a person)').value)} automatic"},
        {"Finding": "More jurors agree, closer to the experts",
         "What it means": f"κ runs from {_c.loc[0].kappa_jury:.2f} with no juror agreeing with itself to {_c.loc[N].kappa_jury:.2f} with all {WORD[N]}. "
                          "The grouping has no interval and was not a test set before the run",
         "What to do": "Test the count as an order for a person's review, against the summed gut margin, which ranked errors as well post hoc"},
    ])
    card([
        mo.md("## What follows."),
        kit.html_table(_t),
        kit.note("Still open: does it hold with a grader that meets the bar, with jurors from more model families, and on questions beyond finance and math?"),
    ])
    return


if __name__ == "__main__":
    app.run()
