#!/usr/bin/env python3
"""
Build the tabbed cross-benchmark report: one tab per benchmark plus an overview, in the visual style of
judge_decisions/results/judge_report.html. Self-contained HTML, no network, no libraries.

  uv run python experiments/cross_benchmark/build_report.py --work <work folder> --out results/report.html
Reads results/<bench>/analysis.json, error_codes.jsonl, contamination.jsonl and results/takeaways.json.
"""
import argparse, html, json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ORDER = ["bff", "mtb", "bffpair", "safety", "bbeh", "judgebench", "rb2", "alpacafarm", "mtbhuman", "dpo5k", "triviaqa"]
TITLE = {"bff": "BFF-Bench", "mtb": "(C)MT-Bench", "bffpair": "BFF pairwise", "safety": "RB2 Safety",
         "bbeh": "BBEH Mini", "judgebench": "JudgeBench", "rb2": "RB2 other", "alpacafarm": "AlpacaFarm",
         "mtbhuman": "MT-Bench human", "dpo5k": "dpo-5k", "triviaqa": "TriviaQA"}
LONG = {
    "bff": "80 two-turn finance conversations × 6 answer models; 3 expert votes per answer (kensho/VERDICTS). Single grading: is the final answer correct?",
    "mtb": "(C)MT-Bench half of VERDICTS: 20 math / reasoning conversations × 6 answer models, 3 votes per answer. Single grading.",
    "bffpair": "kensho/VERDICTSPairwise: 442 pairs of answers to the same BFF turn (one correct, one incorrect), each shown in both orders.",
    "safety": "RewardBench 2 Safety: 450 CoCoNot prompts × 4 responses (1 chosen, 3 rejected), human-annotated. Single grading: is the response appropriate?",
    "bbeh": "BIG-Bench Extra Hard Mini: 460 reasoning questions (23 tasks). Our 8 pool models answer; the answer key grades them; judges grade 2 answers per question.",
    "judgebench": "JudgeBench (GPT-4o split): 350 pairs of GPT-4o answers to hard knowledge, reasoning, math and coding questions; the better one is fixed by ground truth. Both orders.",
    "rb2": "RewardBench 2 Factuality, Precise IF, Math and Focus: 60 prompts each × 4 responses (1 chosen, 3 rejected). Single grading.",
    "alpacafarm": "AlpacaFarm human cross-annotations: 648 instruction pairs with 4 crowd votes each; majority label, 2–2 ties dropped. Both orders.",
    "mtbhuman": "lmsys MT-Bench expert pairwise judgments: 400 sampled (question, model pair, turn) groups, 1–6 expert votes each; majority label, ties dropped. Both orders.",
    "dpo5k": "stindardlogic/llm-judge-dpo-5k: 5,000 rows but only 15 distinct items. Used as a 15-item bias checklist: which of two critiques is better calibrated.",
    "triviaqa": "“Judging the Judges” TriviaQA set (400 questions × 9 exam-takers).",
}
JUDGE = {"gpt-oss-120b": "gpt-oss-120b", "gpt-oss-20b": "gpt-oss-20b", "deepseek-v3.1": "DeepSeek-V3.1",
         "qwen3.6-35b-a3b": "Qwen3.6-35B-A3B", "qwen3.5-4b": "Qwen3.5-4B", "qwen3.5-9b": "Qwen3.5-9B",
         "nemotron3-super-120b": "Nemotron-3-Super-120B", "nemotron3-nano-30b": "Nemotron-3-Nano-30B",
         "jev": "Jev", "jeff": "Jeff", "laya": "Laya", "clm": "CLM-8B"}
ASPECT = {"knowledge": "Specialist knowledge", "reasoning": "Multi-step reasoning", "constraints": "Explicit constraints",
          "open_endedness": "Open-endedness", "context_load": "Context to track", "risk": "Harm if complied"}
RULE = {"best_single": "Best single judge (CV)", "majority_all": "Majority of 8", "top1": "Top-1 by predicted p",
        "top3": "Top-3 (weighted)", "top5": "Top-5 (weighted)"}
ERRCAT = {"too_strict": "Too strict on a minor deviation", "missed_error": "Missed a real error",
          "solved_wrong": "Solved it itself, wrongly", "misread_task": "Misread the task",
          "constraint_missed": "Missed a violated constraint", "safety_overrefusal": "Rewarded over-refusal",
          "safety_missed_harm": "Missed harmful compliance", "style_preference": "Preferred style over substance",
          "gold_questionable": "Gold label looks debatable", "no_verdict": "No verdict (ran out of tokens)", "other": "Other"}


def rule_name(r):
    if r in RULE:
        return RULE[r]
    if r.startswith("thr"):
        tau = r[3:].replace("_cap3", "")
        return f"All judges with p ≥ {tau}" + (" (max 3)" if r.endswith("_cap3") else "")
    return r


def e(s):
    return html.escape(str(s))


def pct(x, d=1):
    return "–" if x is None else f"{100 * x:.{d}f}%"


def num(x, d=3):
    return "–" if x is None else f"{x:.{d}f}"


def jl(j):
    return JUDGE.get(j, j)


CSS = """
:root { color-scheme: light;
  --surface:#fcfcfb; --surface-2:#f3f5f8; --border:#dfe4ea; --ink:#172b45; --ink-2:#52606f; --ink-3:#6b7785;
  --c-sel:#2a78d6; --c-fixed:#eb6834; --c-weight:#1baf7a; --judge:#8f8e88; --oracle-bar:#4a4946; --track:#e8edf3;
  --h0:#eef4fc; --h1:#cde2fb; --h2:#9ec5f4; --h3:#6da7ec; --h4:#3987e5; --h5:#256abf; --h6:#184f95; --h7:#0d366b;
  --d0:#fbe9e1; --d1:#f6c9b5; --d2:#ee9b78; --cell-dark-ink:#ffffff; --cell-light-ink:#172b45; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { color-scheme: dark;
  --surface:#1a1a19; --surface-2:#232322; --border:#3a3a38; --ink:#f2f2f0; --ink-2:#c3c2b7; --ink-3:#a3a29a;
  --c-sel:#3987e5; --c-fixed:#d95926; --c-weight:#199e70; --judge:#74736d; --oracle-bar:#c9c8c0; --track:#2e2e2c;
  --h0:#1f2733; --h1:#1b3352; --h2:#1c4677; --h3:#20599a; --h4:#2a6fc0; --h5:#4a8ddf; --h6:#79aceb; --h7:#b3d1f6;
  --d0:#3a2620; --d1:#6b3522; --d2:#a4492a; --cell-dark-ink:#10161f; --cell-light-ink:#f2f2f0; } }
:root[data-theme="dark"] { color-scheme: dark;
  --surface:#1a1a19; --surface-2:#232322; --border:#3a3a38; --ink:#f2f2f0; --ink-2:#c3c2b7; --ink-3:#a3a29a;
  --c-sel:#3987e5; --c-fixed:#d95926; --c-weight:#199e70; --judge:#74736d; --oracle-bar:#c9c8c0; --track:#2e2e2c;
  --h0:#1f2733; --h1:#1b3352; --h2:#1c4677; --h3:#20599a; --h4:#2a6fc0; --h5:#4a8ddf; --h6:#79aceb; --h7:#b3d1f6;
  --d0:#3a2620; --d1:#6b3522; --d2:#a4492a; --cell-dark-ink:#10161f; --cell-light-ink:#f2f2f0; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--surface); color: var(--ink); font: 15px/1.45 Arial, Helvetica, sans-serif; }
main { max-width: 1180px; margin: 0 auto; padding: 32px 16px 64px; }
.kicker { font-size: 12px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: var(--ink-3); margin: 0 0 6px; }
h1 { font-size: 30px; margin: 0; line-height: 1.15; }
h2 { font-size: 22px; margin: 0 0 4px; }
h3 { font-size: 16px; margin: 0 0 8px; }
.sub { color: var(--ink-2); margin: 6px 0 0; max-width: 900px; }
.note { color: var(--ink-3); font-size: 13px; margin: 8px 0 0; max-width: 900px; }
section { margin-top: 30px; }
section > h2 { border-top: 2px solid var(--ink); padding-top: 12px; }
.tabs { display: flex; flex-wrap: nowrap; overflow-x: auto; gap: 6px; margin-top: 22px; border-bottom: 1px solid var(--border); padding-bottom: 10px;
  position: sticky; top: 0; background: var(--surface); z-index: 5; padding-top: 10px; }
.tabs button { flex: none; white-space: nowrap; font: inherit; font-size: 13px; padding: 7px 12px; border: 1px solid var(--border); border-radius: 8px; background: transparent; color: var(--ink-2); cursor: pointer; }
.tabs button[aria-selected="true"] { background: var(--ink); color: var(--surface); border-color: var(--ink); }
.tabs button.na { border-style: dashed; }
.panel { display: none; } .panel.on { display: block; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin-top: 14px; }
.tile { background: var(--surface-2); border-radius: 10px; padding: 12px 14px; }
.tile .v { font-size: 26px; font-weight: 700; font-variant-numeric: tabular-nums; }
.tile .l { color: var(--ink-2); font-size: 13px; }
.scroll { overflow-x: auto; }
table.t { border-collapse: collapse; font-size: 13px; width: 100%; margin-top: 10px; }
table.t th { text-align: left; color: var(--ink-2); font-weight: 600; padding: 6px 8px; border-bottom: 1px solid var(--border); vertical-align: bottom; }
table.t td { padding: 6px 8px; border-bottom: 1px solid var(--border); font-variant-numeric: tabular-nums; vertical-align: top; }
table.t td.n, table.t th.n { text-align: right; }
table.t tr.hl td { font-weight: 700; }
table.t tr.muted td { color: var(--ink-3); }
table.hm { border-collapse: separate; border-spacing: 2px; font-size: 12px; margin-top: 10px; }
table.hm th { font-weight: 600; color: var(--ink-2); text-align: center; padding: 3px 5px; }
table.hm th.rowh { text-align: left; white-space: nowrap; color: var(--ink); font-weight: 400; }
table.hm td { text-align: center; padding: 6px 4px; border-radius: 4px; min-width: 52px; font-variant-numeric: tabular-nums; }
.barcell { display: flex; align-items: center; gap: 8px; min-width: 180px; }
.barcell .tr { flex: 1; height: 12px; background: var(--track); border-radius: 0 4px 4px 0; position: relative; }
.barcell .tr i { position: absolute; left: 0; top: 0; bottom: 0; background: var(--judge); border-radius: 0 4px 4px 0; }
.barcell .tr i.best { background: var(--c-sel); }
.barcell .tr i.combo { background: var(--c-fixed); }
.barcell .tr i.thr { background: var(--c-weight); }
.callout { border-left: 3px solid var(--ink-3); padding: 8px 12px; background: var(--surface-2); border-radius: 0 6px 6px 0; margin-top: 12px; font-size: 14px; color: var(--ink); max-width: 940px; }
.callout.good { border-left-color: var(--c-weight); } .callout.warn { border-left-color: var(--c-fixed); }
.concl { font-size: 17px; line-height: 1.4; font-weight: 700; margin: 8px 0 4px; max-width: 940px; }
ul.take { max-width: 940px; padding-left: 20px; } ul.take li { margin: 6px 0; }
.ex { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 340px), 1fr)); gap: 12px; margin-top: 12px; }
.excard { background: var(--surface-2); border-radius: 10px; padding: 12px 14px; font-size: 13px; }
.excard .meta { color: var(--ink-3); margin-bottom: 6px; }
.excard blockquote { margin: 0 0 6px; }
details.more { margin-top: 14px; border: 1px solid var(--border); border-radius: 8px; padding: 0 14px; }
details.more > summary { cursor: pointer; padding: 10px 0; font-weight: 700; font-size: 14px; }
details.more p, details.more li { font-size: 13px; color: var(--ink-2); }
.legend { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 12px; color: var(--ink-3); margin-top: 6px; }
.legend span::before { content: ""; display: inline-block; width: 11px; height: 11px; border-radius: 3px; margin-right: 5px; vertical-align: -1px; background: var(--c); }
svg text { fill: var(--ink-2); font-size: 11px; font-family: Arial, Helvetica, sans-serif; }
svg .ax { stroke: var(--border); } svg .gl { stroke: var(--border); stroke-dasharray: 2 3; }
.grid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 520px), 1fr)); gap: 22px; }
.smgrid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 400px), 1fr)); gap: 14px 22px; margin-top: 12px; }
.smcard { background: var(--surface-2); border-radius: 10px; padding: 10px 12px 2px; }
.tag { display: inline-block; font-size: 11px; padding: 1px 7px; border-radius: 9px; border: 1px solid var(--border); color: var(--ink-3); margin-left: 6px; }
"""

JS = """
const tabs=[...document.querySelectorAll('.tabs button')];
function show(id){tabs.forEach(b=>b.setAttribute('aria-selected',b.dataset.t===id));
 document.querySelectorAll('.panel').forEach(p=>p.classList.toggle('on',p.id===id));
 try{history.replaceState(null,'','#'+id)}catch(e){} window.scrollTo({top:0});}
tabs.forEach(b=>b.addEventListener('click',()=>show(b.dataset.t)));
const h=(location.hash||'').slice(1); show(tabs.some(b=>b.dataset.t===h)?h:'overview');
"""


def heat(v, lo, hi, scale="h"):
    """Background + ink for a value on a 0..7 ramp."""
    if v is None:
        return "background:var(--surface-2);color:var(--ink-3)"
    k = int(round(7 * max(0.0, min(1.0, (v - lo) / (hi - lo or 1)))))
    return f"background:var(--h{k});color:var({'--cell-dark-ink' if k >= 4 else '--cell-light-ink'})"


def barcell(v, lo=0.0, hi=1.0, cls="", label=None):
    w = 0 if v is None else max(0, min(100, 100 * (v - lo) / (hi - lo)))
    return f'<div class="barcell"><div class="tr"><i class="{cls}" style="width:{w:.1f}%"></i></div><span>{label or pct(v)}</span></div>'


# ----------------------------------------------------------------------------- sections
def sec_judges(a):
    rows = a["judges"]
    pair = a["fmt"] == "pair"
    tink = [r for r in rows if r["tinker"]]
    best = tink[0]["judge"] if tink else None
    lo = min(0.4, min(r["acc"] for r in rows) - 0.05)
    h = ['<section><h2>1 · How well each judge agrees with the gold label</h2>',
         f'<p class="sub">Agreement = share of {"presentations" if pair else "items"} where the judge’s verdict matches the gold label, without a reference answer. '
         f'κ corrects for chance. {"Each pair is shown in both orders, so always picking one position scores exactly 50%." if pair else ""}</p>',
         '<div class="scroll"><table class="t"><thead><tr><th>Judge</th><th>Agreement</th><th class="n">κ</th><th class="n">Parsed</th>',
         f'<th class="n">{"Picks first" if pair else "Says good"}</th>' + ('<th class="n">Same pick both orders</th>' if pair else '') +
         '<th class="n">$ / call</th></tr></thead><tbody>']
    for r in rows:
        cls = "best" if r["judge"] == best else ""
        tag = "" if r["tinker"] else (f'<span class="tag">only {r["partial"]} items graded · not in pool</span>' if r.get("partial") else '<span class="tag">not in routing pool</span>')
        h.append(f'<tr class="{"" if r["tinker"] else "muted"}"><td>{e(jl(r["judge"]))}{tag}</td><td>{barcell(r["acc"], lo, 1, cls)}</td>'
                 f'<td class="n">{num(r["kappa"])}</td><td class="n">{pct(r["parse"], 0)}</td>'
                 f'<td class="n">{pct(r.get("first_pick") if pair else r["positive"], 0)}</td>' +
                 (f'<td class="n">{pct(r.get("consistent"), 0)}</td>' if pair else '') +
                 f'<td class="n">{"–" if r["cost"] is None else f"${r[chr(99)+chr(111)+chr(115)+chr(116)]:.4f}"}</td></tr>')
    h.append('</tbody></table></div>')
    if a.get("human_condition"):
        hc = a["human_condition"]
        h.append(f'<p class="note">With the expert reference answer shown, the best judge is {e(jl(hc[0]["judge"]))} '
                 f'({pct(hc[0]["acc"])}, κ {num(hc[0]["kappa"])}); without it, {e(jl(best))} ({pct(tink[0]["acc"])}, κ {num(tink[0]["kappa"])}).</p>')
    base = a["base_rate"]
    h.append(f'<p class="note">Gold base rate: {pct(base)} {"first-shown better (50% by construction)" if pair else "good / correct"}. '
             'Unparseable verdicts count as the negative verdict (Incorrect, or the second response). Jev, Jeff, Laya and CLM are shown where we have them but are not part of any combination below.</p></section>')
    return "".join(h)


def sec_labels(a):
    L = a.get("labels")
    if not L:
        return ""
    h = ['<section><h2>2 · How much the human labels agree</h2>',
         f'<p class="sub">{L["n_units"]} labelled units; {L["unanimous_units"]} have unanimous votes and {L["no_majority"]} have no majority (dropped). '
         'Every κ below is on items with a majority label, split into the unanimous and the split-vote part.</p>',
         '<div class="grid2"><div><h3>Vote patterns</h3><table class="t"><thead><tr><th>Votes</th><th class="n">Units</th></tr></thead><tbody>']
    for p in L["patterns"]:
        h.append(f'<tr><td>{e(p["pattern"])}</td><td class="n">{p["n"]}</td></tr>')
    h.append('</tbody></table></div><div><h3>Judge κ by label agreement</h3><table class="t"><thead><tr><th>Judge</th><th class="n">All majority</th><th class="n">Unanimous only</th><th class="n">Split votes</th></tr></thead><tbody>')
    for r in L["judges"]:
        if r["judge"] not in JUDGE:
            continue
        h.append(f'<tr><td>{e(jl(r["judge"]))}</td><td class="n">{num(r["k_all"])} <small>({r["n_all"]})</small></td>'
                 f'<td class="n">{num(r["k_unan"])} <small>({r["n_unan"]})</small></td><td class="n">{num(r["k_split"])} <small>({r["n_split"]})</small></td></tr>')
    h.append('</tbody></table></div></div>')
    js = [r for r in L["judges"] if r["k_unan"] is not None and r["k_split"] is not None and r["judge"] in JUDGE]
    if js:
        drop = sum(r["k_unan"] - r["k_split"] for r in js) / len(js)
        h.append(f'<div class="callout">Judges agree far less with humans on items the humans themselves split on: κ is {drop:.2f} lower on '
                 'split-vote items than on unanimous ones, averaged over judges. Scoring only unanimous items inflates every judge.</div>')
    h.append('</section>')
    return "".join(h)


def phi_table(es):
    js = es["judges"]
    h = ['<div class="scroll"><table class="hm"><tr><th></th>' + "".join(f'<th>{e(jl(j))}</th>' for j in js) + '</tr>']
    for i, j in enumerate(js):
        h.append(f'<tr><th class="rowh">{e(jl(j))}</th>')
        for k in range(len(js)):
            v = es["phi"][i][k]
            h.append(f'<td style="{heat(v, 0, 0.8) if i != k else "background:var(--surface-2);color:var(--ink-3)"}">{"–" if i == k or v is None else f"{v:.2f}"}</td>')
        h.append('</tr>')
    h.append('</table></div>')
    return "".join(h)


def sec_errors(a, codes):
    es = a.get("errors")
    if not es:
        return ""
    best = jl(es["best"])
    h = ['<section><h2>3 · Do the judges fail on the same items?</h2>',
         '<div class="tiles">',
         f'<div class="tile"><div class="v">{es["phi_mean"]:.2f}</div><div class="l">mean pairwise error correlation (φ), range {es["phi_min"]:.2f}–{es["phi_max"]:.2f}</div></div>',
         f'<div class="tile"><div class="v">{pct(es["all_right_obs"], 0)}</div><div class="l">items every judge gets right ({pct(es["all_right_ind"], 0)} if errors were independent)</div></div>',
         f'<div class="tile"><div class="v">{pct(es["many_wrong_obs"], 1)}</div><div class="l">items 6+ of 8 judges get wrong ({pct(es["many_wrong_ind"], 1)} if independent)</div></div>',
         f'<div class="tile"><div class="v">{es["best_errors"]}</div><div class="l">errors of the best judge, {best} ({es["fp"]} accepted a bad answer, {es["fn"]} rejected a good one)</div></div>',
         '</div>']
    ow = es["others_wrong"]
    shared = sum(v for k, v in ow.items() if int(k) >= 5)
    h.append(f'<p class="note">On {shared} of {best}’s {es["best_errors"]} errors, at least 5 of the other 7 judges are wrong too; '
             f'{es["q_with_2plus"]} of {es["n_questions"]} questions hold {es["errors_in_2plus"]} of its errors.</p>')
    h.append('<div class="grid2"><div><h3>Error correlation between judges</h3>' + phi_table(es) +
             '<p class="note">φ = correlation of two judges’ 0/1 error indicators. 0 = independent mistakes; higher = they fail on the same items.</p></div>')
    h.append(f'<div><h3>{best}: error rate by category</h3><table class="t"><thead><tr><th>Category</th><th class="n">Items</th><th>Error rate</th></tr></thead><tbody>')
    hi = max([r["rate"] for r in es["by_category"]] + [0.2])
    for r in es["by_category"][:14]:
        h.append(f'<tr><td>{e(r["category"])}</td><td class="n">{r["n"]}</td><td>{barcell(r["rate"], 0, hi, "combo")}</td></tr>')
    h.append('</tbody></table>')
    if es.get("by_examinee") and len(es["by_examinee"]) > 1:
        h.append(f'<p class="note">By answer model: ' + ", ".join(f'{e(r["examinee"])} {pct(r["rate"], 0)}' for r in es["by_examinee"]) + '.</p>')
    h.append('</div></div>')
    if codes:
        cnt = pd.Series([c["category"] for c in codes]).value_counts()
        h.append(f'<h3 style="margin-top:20px">Why {best} got it wrong (sample of {len(codes)} errors, LLM-coded)</h3><table class="t"><tbody>')
        for k, v in cnt.items():
            h.append(f'<tr><td>{e(ERRCAT.get(k, k))}</td><td>{barcell(v / len(codes), 0, 1, "", f"{v}")}</td></tr>')
        h.append('</tbody></table><div class="ex">')
        for c in [c for c in codes if c.get("why")][:4]:
            h.append(f'<div class="excard"><div class="meta">{e(ERRCAT.get(c["category"], c["category"]))} · {e(c["item_category"])}</div>{e(c["why"])}</div>')
        h.append('</div><p class="note">Coded by DeepSeek-V3.1 from the question, response(s), gold label and the judge’s reasoning, into a fixed taxonomy. Read as a guide to where to look, not a measurement.</p>')
    h.append('</section>')
    return "".join(h)


def sec_aspects(a):
    A = a.get("aspects")
    if not A or not A["tests"]:
        return ""
    h = ['<section><h2>4 · Which questions are hard to judge</h2>',
         '<p class="sub">Every question was coded on six 0–3 demand aspects from its text alone (gpt-oss-120b, shared rubric across benchmarks). '
         'Cells: judge agreement at each level. The test asks whether some judges are relatively better at some levels than others '
         '(judge × level interaction, permuting levels across conversations / prompts; Benjamini–Hochberg q).</p><div class="grid2">']
    for t in sorted(A["tests"], key=lambda t: t["q"]):
        lv = t["levels"]
        sig = t["q"] < 0.1
        h.append(f'<div><h3>{e(ASPECT[t["aspect"]])} <span class="tag">q = {t["q"]:.3f}{" · interaction" if sig else ""}</span></h3>'
                 '<table class="hm"><tr><th></th>' + "".join(f'<th>{l}<br><small>{t["items_per_level"].get(str(l), t["items_per_level"].get(l, ""))} q</small></th>' for l in lv) + '</tr>')
        for j, cells in t["cells"].items():
            h.append(f'<tr><th class="rowh">{e(jl(j))}</th>')
            for l in lv:
                c = cells.get(str(l)) or cells.get(l)
                v = c["acc"] if c and c["n"] else None
                h.append(f'<td style="{heat(v, 0.4, 1.0)}">{"–" if v is None else f"{100 * v:.0f}"}</td>')
            h.append('</tr>')
        h.append('</table></div>')
    h.append('</div><p class="note">Levels with few questions are noisy; the item count is under each level. Aspect codes are AI-authored annotations, not expert labels.</p></section>')
    return "".join(h)


def sec_candidates(a):
    C = a.get("candidates")
    if not C:
        return ""
    h = ['<section><h2>5 · The answer models themselves</h2>',
         f'<p class="sub">Here the gold label is each answer model’s own correctness, so we can ask how much a perfect per-question pick of answer model would gain. {C["n_questions"]} questions answered by every model.</p>',
         '<div class="tiles">',
         f'<div class="tile"><div class="v">{pct(C["acc"][C["best"]])}</div><div class="l">best single answer model ({e(C["best"])})</div></div>',
         f'<div class="tile"><div class="v">{pct(C["oracle"])}</div><div class="l">oracle: any model correct</div></div>',
         f'<div class="tile"><div class="v">{C["phi_mean"]:.2f}</div><div class="l">mean error correlation between answer models</div></div></div>',
         '<table class="t"><thead><tr><th>Answer model</th><th>Accuracy</th><th class="n">Rescues best model’s misses</th></tr></thead><tbody>']
    resc = {r["model"]: f'{r["rescues"]} / {r["of"]}' for r in C["rescue"]}
    for m, v in C["acc"].items():
        h.append(f'<tr><td>{e(m)}</td><td>{barcell(v, 0, 1, "best" if m == C["best"] else "")}</td><td class="n">{resc.get(m, "–")}</td></tr>')
    h.append('</tbody></table></section>')
    return "".join(h)


def sec_length(a):
    L = a.get("length")
    if not L:
        return ""
    h = ['<section><h2>6 · Length and position</h2>']
    if L["kind"] == "pair":
        h.append('<p class="sub">Pairs whose lengths differ by more than 20%. “Picks longer” should match “Humans prefer longer” if length has no pull of its own; '
                 'the last two columns show agreement when the longer or the shorter answer is the better one.</p><table class="t"><thead><tr><th>Judge</th><th class="n">Picks longer</th><th class="n">Humans prefer longer</th>'
                 '<th class="n">Agreement, longer is better</th><th class="n">Agreement, shorter is better</th></tr></thead><tbody>')
        for r in L["rows"]:
            if r["judge"] not in JUDGE:
                continue
            h.append(f'<tr><td>{e(jl(r["judge"]))}</td><td class="n">{pct(r["pick_longer"], 0)}</td><td class="n">{pct(r["human_longer"], 0)}</td>'
                     f'<td class="n">{pct(r["acc_when_longer_better"], 0)}</td><td class="n">{pct(r["acc_when_shorter_better"], 0)}</td></tr>')
        h.append('</tbody></table>')
        firsts = [r.get("first_pick") for r in a["judges"] if r["tinker"] and r.get("first_pick") is not None]
        if firsts:
            h.append(f'<p class="note">Position: judges pick the first-shown response {pct(min(firsts), 0)}–{pct(max(firsts), 0)} of the time (50% = no position bias, since each pair appears in both orders). '
                     'See “Same pick both orders” in section 1.</p>')
    else:
        h.append('<p class="sub">Share of responses each judge calls good, by response-length tercile, separately for good and bad responses. '
                 'A judge without length bias would show flat rows.</p><table class="t"><thead><tr><th>Judge</th><th class="n">Good: short</th><th class="n">medium</th><th class="n">long</th>'
                 '<th class="n">Bad: short</th><th class="n">medium</th><th class="n">long</th></tr></thead><tbody>')
        for r in L["rows"]:
            if r["judge"] not in JUDGE:
                continue
            g, b = r["good"], r["bad"]
            h.append(f'<tr><td>{e(jl(r["judge"]))}</td>' + "".join(f'<td class="n">{pct(g.get(t), 0)}</td>' for t in ["short", "medium", "long"]) +
                     "".join(f'<td class="n">{pct(b.get(t), 0)}</td>' for t in ["short", "medium", "long"]) + '</tr>')
        h.append('</tbody></table>')
        h.append('<p class="note">Base rate of good responses by tercile: ' + ", ".join(f'{k} {pct(v, 0)}' for k, v in L["base"].items()) + '.</p>')
    h.append('</section>')
    return "".join(h)


def sec_contam(rows):
    if not rows:
        return ""
    df = pd.DataFrame(rows)
    g = df.groupby("model").lcr
    h = ['<section><h2>7 · Has the judge seen this benchmark?</h2>',
         '<p class="sub">Question-completion probe: given the first half of a benchmark question, continue it word for word. '
         'Longest run of words shared with the real second half, for the strongest judge and a small control model.</p>',
         '<table class="t"><thead><tr><th>Model</th><th class="n">Questions</th><th class="n">Mean longest run</th><th class="n">Median</th><th class="n">Share ≥ 13 words</th></tr></thead><tbody>']
    for m, s in g:
        h.append(f'<tr><td>{e(jl(m))}</td><td class="n">{len(s)}</td><td class="n">{s.mean():.1f}</td><td class="n">{s.median():.0f}</td><td class="n">{pct((s >= 13).mean(), 0)}</td></tr>')
    h.append('</tbody></table>')
    m = {k: (v >= 13).mean() for k, v in g}
    if "gpt-oss-120b" in m and "qwen3.5-4b" in m:
        d = m["gpt-oss-120b"] - m["qwen3.5-4b"]
        msg = ("The judge reproduces long verbatim runs much more often than the control: possible exposure to this benchmark."
               if d > 0.15 else "No sign the judge memorised the questions beyond what the control model does.")
        h.append(f'<div class="callout {"warn" if d > 0.15 else ""}">{msg}</div>')
    h.append('<p class="note">Absence of verbatim recall does not prove the model never saw the data, and the control is also a recent model.</p></section>')
    return "".join(h)


def rule_rows(J):
    rows = {r["rule"]: r for r in J["rules"]}
    order = ["best_single", "majority_all", "top1", "top3", "top5"] + [f"thr{t}" for t in [0.6, 0.7, 0.8, 0.85, 0.9, 0.95]] + \
            [f"thr{t}_cap3" for t in [0.8, 0.9]]
    return [rows[k] for k in order if k in rows]


def jury_chart(J):
    """Accuracy vs mean jury size for every rule (SVG)."""
    rows = rule_rows(J)
    W, H, L, B = 520, 250, 46, 34
    xs = [r["size"] for r in rows]
    ys = [r["acc"] for r in rows]
    x0, x1 = 0.5, 8.5
    y0, y1 = min(ys) - 0.02, max(ys) + 0.02
    X = lambda v: L + (W - L - 12) * (v - x0) / (x1 - x0)
    Y = lambda v: H - B - (H - B - 14) * (v - y0) / (y1 - y0)
    s = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px" role="img" aria-label="Accuracy against jury size">']
    for k in range(5):
        v = y0 + (y1 - y0) * k / 4
        s.append(f'<line class="gl" x1="{L}" x2="{W - 12}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/><text x="{L - 6}" y="{Y(v) + 4:.1f}" text-anchor="end">{100 * v:.0f}%</text>')
    for v in range(1, 9):
        s.append(f'<text x="{X(v):.1f}" y="{H - B + 16}" text-anchor="middle">{v}</text>')
    s.append(f'<text x="{(L + W) / 2:.0f}" y="{H - 4}" text-anchor="middle">mean judges called per item</text>')
    thr = [r for r in rows if r["rule"].startswith("thr") and not r["rule"].endswith("cap3")]
    pts = " ".join(f"{X(r['size']):.1f},{Y(r['acc']):.1f}" for r in sorted(thr, key=lambda r: r["size"]))
    s.append(f'<polyline points="{pts}" fill="none" stroke="var(--c-weight)" stroke-width="2"/>')
    top = [r for r in rows if r["rule"] in ("top1", "top3", "top5")]
    pts = " ".join(f"{X(r['size']):.1f},{Y(r['acc']):.1f}" for r in top)
    s.append(f'<polyline points="{pts}" fill="none" stroke="var(--c-sel)" stroke-width="2" stroke-dasharray="5 3"/>')
    for r in rows:
        c = "var(--c-weight)" if r["rule"].startswith("thr") else "var(--c-sel)" if r["rule"].startswith("top") else "var(--c-fixed)"
        lab = r["rule"].replace("thr", "τ").replace("_cap3", "·3") if r["rule"].startswith("thr") else {"best_single": "best", "majority_all": "maj", "top1": "k1", "top3": "k3", "top5": "k5"}[r["rule"]]
        s.append(f'<circle cx="{X(r["size"]):.1f}" cy="{Y(r["acc"]):.1f}" r="4" fill="{c}"><title>{e(rule_name(r["rule"]))}: {100 * r["acc"]:.1f}%, {r["size"]:.2f} judges</title></circle>')
        s.append(f'<text x="{X(r["size"]) + 6:.1f}" y="{Y(r["acc"]) - 6:.1f}">{e(lab)}</text>')
    s.append('</svg>')
    return "".join(s)


def sec_juries(a):
    J = a.get("juries")
    if not J:
        return ""
    rows = rule_rows(J)
    h = ['<section><h2>8 · Top-k jury vs a probability threshold</h2>',
         '<p class="sub">A reliability predictor estimates, before any judge runs, P(judge agrees with the gold label) for each of the 8 judges on each item '
         f'(per-judge logistic regression on {J["features"]} pre-call features: aspect codes, category, response length, a TF-IDF summary of the question; '
         'out-of-fold, 5 × 5-fold grouped by conversation / prompt). <b>Top-k</b> always calls the k judges with the highest p. '
         '<b>Threshold</b> calls every judge with p ≥ τ, so slots are not filled with judges predicted to be unreliable; if none passes, the single top judge decides. '
         'Votes are weighted by logit(p).</p>',
         '<div class="grid2"><div class="scroll"><table class="t"><thead><tr><th>Rule</th><th>Accuracy</th><th class="n">Judges / item</th><th class="n">Δ vs best single</th><th class="n">95% CI</th></tr></thead><tbody>']
    for r in rows:
        cls = "thr" if r["rule"].startswith("thr") else "best" if r["rule"].startswith("top") else "combo"
        sig = r["ci"][0] > 0 or r["ci"][1] < 0
        h.append(f'<tr class="{"hl" if sig and r["rule"] != "best_single" else ""}"><td>{e(rule_name(r["rule"]))}</td><td>{barcell(r["acc"], 0.4, 1, cls)}</td>'
                 f'<td class="n">{r["size"]:.2f}{f" <small>({pct(r[chr(102)+chr(97)+chr(108)+chr(108)+chr(98)+chr(97)+chr(99)+chr(107)], 0)} fallback)</small>" if r["rule"].startswith("thr") else ""}</td>'
                 f'<td class="n">{"–" if r["rule"] == "best_single" else f"{100 * r[chr(100)+chr(105)+chr(102)+chr(102)]:+.1f}"}</td>'
                 f'<td class="n">{"–" if r["rule"] == "best_single" else f"[{100 * r[chr(99)+chr(105)][0]:+.1f}, {100 * r[chr(99)+chr(105)][1]:+.1f}]"}</td></tr>')
    h.append('</tbody></table><p class="note">Bold = 95% conversation/prompt-bootstrap interval excludes 0. “Best single judge (CV)” is the judge with the highest training-fold agreement.</p></div>')
    h.append('<div>' + jury_chart(J) + '<div class="legend"><span style="--c:var(--c-sel)">top-k</span><span style="--c:var(--c-weight)">threshold τ (·3 = at most 3)</span><span style="--c:var(--c-fixed)">best single, majority</span></div></div></div>')
    # verdict
    rr = {r["rule"]: r for r in J["rules"]}
    pairs = [("top3", "thr0.8_cap3"), ("top3", "thr0.9_cap3")]
    bt = max((r for r in J["rules"] if r["rule"].startswith("thr")), key=lambda r: r["acc"])
    bk = max((r for r in J["rules"] if r["rule"] in ("top1", "top3", "top5")), key=lambda r: r["acc"])
    msg = (f'Best threshold rule: {rule_name(bt["rule"])}, {pct(bt["acc"])} with {bt["size"]:.1f} judges per item. '
           f'Best top-k: {rule_name(bk["rule"])}, {pct(bk["acc"])} with {bk["size"]:.0f}. ')
    if "top3" in rr and "thr0.9_cap3" in rr:
        d = rr["thr0.9_cap3"]["acc"] - rr["top3"]["acc"]
        msg += (f'Dropping top-3 members with p < 0.9 changes accuracy by {100 * d:+.1f} points while calling '
                f'{rr["thr0.9_cap3"]["size"]:.2f} instead of 3 judges.')
    h.append(f'<div class="callout">{msg}</div>')
    h.append('<details class="more"><summary>How good is the reliability predictor?</summary><table class="t"><thead><tr><th>Judge</th><th class="n">Actual agreement</th><th class="n">Mean predicted p</th>'
             '<th class="n">AUROC</th><th class="n">ECE</th><th class="n">Share p ≥ 0.8</th><th class="n">Share p ≥ 0.9</th></tr></thead><tbody>')
    for p in J["predictor"]:
        h.append(f'<tr><td>{e(jl(p["judge"]))}</td><td class="n">{pct(p["acc"])}</td><td class="n">{pct(p["mean_p"])}</td><td class="n">{num(p["auroc"], 2)}</td>'
                 f'<td class="n">{num(p["ece"], 3)}</td><td class="n">{pct(p["share_above"]["0.8"], 0)}</td><td class="n">{pct(p["share_above"]["0.9"], 0)}</td></tr>')
    h.append('</tbody></table><p>AUROC near 0.5 means the predictor cannot tell, before the call, which items a judge will get wrong; then every rule mostly ranks judges by their overall accuracy, and the threshold mostly decides <i>how many</i> of the strong judges are called.</p></details></section>')
    return "".join(h)


def panel(b, a, codes, contam):
    if a is None:
        return (f'<div class="panel" id="{b}"><section><h2>{e(TITLE[b])}</h2><p class="sub">{e(LONG.get(b, ""))}</p>'
                + (NOT_RUN.get(b, '<div class="callout warn">Not run.</div>')) + '</section></div>')
    tink = [r for r in a["judges"] if r["tinker"]]
    J = a.get("juries") or {}
    maj = next((r for r in J.get("rules", []) if r["rule"] == "majority_all"), None)
    tiles = (f'<div class="tiles"><div class="tile"><div class="v">{a["n_items"]:,}</div><div class="l">{"presentations" if a["fmt"] == "pair" else "items"} judged ({a["n_groups"]} groups)</div></div>'
             f'<div class="tile"><div class="v">{pct(tink[0]["acc"])}</div><div class="l">best judge: {e(jl(tink[0]["judge"]))} (κ {num(tink[0]["kappa"], 2)})</div></div>'
             + (f'<div class="tile"><div class="v">{pct(maj["acc"])}</div><div class="l">majority of 8 judges</div></div>' if maj else '')
             + (f'<div class="tile"><div class="v">{pct(J["oracle"])}</div><div class="l">oracle: any judge right</div></div>' if J else '')
             + f'<div class="tile"><div class="v">${a["cost"]:.2f}</div><div class="l">judging cost (list prices)</div></div></div>')
    cats = ", ".join(f"{e(k)} {v}" for k, v in list(a["categories"].items())[:10])
    h = [f'<div class="panel" id="{b}"><section><h2>{e(TITLE[b])}</h2><p class="sub">{e(LONG.get(b, ""))}</p>{tiles}'
         f'<p class="note">Categories: {cats}{" …" if len(a["categories"]) > 10 else ""}.</p>'
         + (f'<div class="callout">{TAKE[b]}</div>' if b in TAKE else '') + '</section>',
         sec_judges(a), sec_labels(a), sec_errors(a, codes), sec_aspects(a), sec_candidates(a), sec_length(a),
         sec_contam(contam), sec_juries(a), '</div>']
    return "".join(h)


NOT_RUN = {
    "triviaqa": '<div class="callout warn">Not run: the human-labelled data was never publicly released. The paper (arXiv 2406.12624, GEM² 2025) links no code or data, '
                'and it used one human label per answer for its main experiments (three only on a 1,200-answer agreement subset). Ask the authors if we still want it.</div>',
}
TAKE = {}


SUMMARY_ROWS = [  # (key, label, family)
    ("hind", "Best single judge (hindsight)", "single"),
    ("best_single", "Best single judge (cross-validated)", "single"),
    ("majority_all", "Majority of all judges", "majority"),
    ("top1", "Top-1 by predicted p", "topk"),
    ("top3", "Top-3 (weighted)", "topk"),
    ("top5", "Top-5 (weighted)", "topk"),
    ("thr0.8", "All judges with p ≥ 0.8", "thr"),
    ("thr0.9", "All judges with p ≥ 0.9", "thr"),
    ("thr0.8_cap3", "Top-3, drop p < 0.8", "thr"),
    ("thr0.9_cap3", "Top-3, drop p < 0.9", "thr"),
    ("oracle", "Oracle (any judge right)", "oracle"),
]
FAM_COLOR = {"single": "var(--judge)", "majority": "var(--c-fixed)", "topk": "var(--c-sel)", "thr": "var(--c-weight)",
             "oracle": "var(--oracle-bar)"}


def summary_values(a):
    J = a.get("juries")
    if not J:
        return None
    R = {r["rule"]: r for r in J["rules"]}
    pool = a.get("pool") or [r["judge"] for r in a["judges"] if r["tinker"]]
    hind = max((r for r in a["judges"] if r["judge"] in pool), key=lambda r: r["acc"])
    vals = {"hind": (hind["acc"], f'{jl(hind["judge"])}, 1 judge'), "oracle": (J["oracle"], "any of the judges right")}
    for k, _, _ in SUMMARY_ROWS:
        if k in R:
            vals[k] = (R[k]["acc"], f'{R[k]["size"]:.1f} judges / item; Δ vs CV best {100 * R[k]["diff"]:+.1f} pts')
    return vals


def summary_plot(an):
    """Small multiples: one panel per dataset, one dot per method, shared 50-100% axis."""
    lo, hi = 0.5, 1.0
    W, rowh, top, left, right = 420, 19, 26, 214, 46
    panels, table = [], []
    for b in ORDER:
        a = an.get(b)
        vals = summary_values(a) if a else None
        if not vals:
            continue
        H = top + rowh * len(SUMMARY_ROWS) + 26
        X = lambda v: left + (W - left - right) * (max(lo, min(hi, v)) - lo) / (hi - lo)
        s = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="{e(TITLE[b])}: accuracy by method">',
             f'<text x="0" y="14" style="font-size:13px;font-weight:700;fill:var(--ink)">{e(TITLE[b])}</text>']
        for t in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
            s.append(f'<line class="gl" x1="{X(t):.1f}" x2="{X(t):.1f}" y1="{top - 4}" y2="{H - 22}"/>'
                     f'<text x="{X(t):.1f}" y="{H - 8}" text-anchor="middle">{100 * t:.0f}%</text>')
        hind = vals["hind"][0]
        s.append(f'<line x1="{X(hind):.1f}" x2="{X(hind):.1f}" y1="{top - 4}" y2="{H - 22}" stroke="var(--ink-3)" stroke-width="1" stroke-dasharray="3 3"/>')
        for i, (k, lab, fam) in enumerate(SUMMARY_ROWS):
            y = top + rowh * i + rowh / 2
            s.append(f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end">{e(lab)}</text>')
            if k not in vals:
                s.append(f'<text x="{left + 4}" y="{y + 4:.1f}" style="fill:var(--ink-3)">–</text>')
                continue
            v, tip = vals[k]
            s.append(f'<line x1="{left}" x2="{X(v):.1f}" y1="{y:.1f}" y2="{y:.1f}" stroke="var(--track)" stroke-width="2"/>')
            if fam == "oracle":
                s.append(f'<circle cx="{X(v):.1f}" cy="{y:.1f}" r="5" fill="var(--surface)" stroke="{FAM_COLOR[fam]}" stroke-width="2"/>')
            else:
                s.append(f'<circle cx="{X(v):.1f}" cy="{y:.1f}" r="5" fill="{FAM_COLOR[fam]}" stroke="var(--surface)" stroke-width="2"/>')
            s.append(f'<text x="{X(v) + 9:.1f}" y="{y + 4:.1f}" style="fill:var(--ink)">{100 * v:.1f}</text>')
            s.append(f'<rect x="0" y="{y - rowh / 2:.1f}" width="{W}" height="{rowh}" fill="transparent"><title>{e(TITLE[b])} · {e(lab)}: {100 * v:.1f}% ({e(tip)})</title></rect>')
        s.append('</svg>')
        panels.append(f'<div class="smcard">{"".join(s)}</div>')
        table.append(f'<tr><td>{e(TITLE[b])}</td>' + "".join(
            f'<td class="n">{"–" if k not in vals else f"{100 * vals[k][0]:.1f}"}</td>' for k, _, _ in SUMMARY_ROWS) + '</tr>')
    head = "".join(f'<th class="n">{e(lab)}</th>' for _, lab, _ in SUMMARY_ROWS)
    return ('<section><h2>Accuracy of every method, every dataset</h2>'
            '<p class="sub">Agreement with the gold label without a reference answer. Each panel is one dataset, on the same 50–100% axis; '
            'the dashed line marks the best single judge picked in hindsight. Every jury rule is cross-validated (its reliability predictor never sees the items it is scored on). '
            'Hover a row for judges per item and the gain over the cross-validated best single judge.</p>'
            '<div class="legend"><span style="--c:var(--judge)">single judge</span><span style="--c:var(--c-fixed)">majority vote</span>'
            '<span style="--c:var(--c-sel)">top-k</span><span style="--c:var(--c-weight)">threshold on predicted p</span>'
            '<span style="--c:var(--oracle-bar)">oracle (open dot)</span></div>'
            f'<div class="smgrid">{"".join(panels)}</div>'
            '<details class="more"><summary>Same numbers as a table (accuracy, %)</summary><div class="scroll"><table class="t"><thead><tr><th>Dataset</th>'
            f'{head}</tr></thead><tbody>{"".join(table)}</tbody></table></div></details></section>')


def overview(an, take):
    h = ['<div class="panel" id="overview"><section><h2>Do the BFF-Bench findings hold on other benchmarks?</h2>',
         '<p class="sub">The same 8 Tinker judges, the same verdict rules and the same analyses, run on every benchmark the team has used or been pointed to. '
         'Each tab has the full breakdown; this page compares them.</p>']
    if take.get("headline"):
        h.append(f'<p class="concl">{take["headline"]}</p>')
    if take.get("bullets"):
        h.append('<ul class="take">' + "".join(f"<li>{b}</li>" for b in take["bullets"]) + '</ul>')
    h.append('</section>' + summary_plot(an) + '<section><h2>Benchmark by benchmark</h2><div class="scroll"><table class="t"><thead><tr><th>Benchmark</th><th class="n">Items</th>'
             '<th>Best judge</th><th class="n">Best</th><th class="n">Majority of 8</th><th class="n">Best top-k</th><th class="n">Best threshold</th>'
             '<th class="n">Oracle</th><th class="n">Mean error φ</th><th class="n">All right: seen / indep.</th></tr></thead><tbody>')
    for b in ORDER:
        a = an.get(b)
        if a is None:
            h.append(f'<tr class="muted"><td>{e(TITLE[b])}</td><td colspan="9">not run — see tab</td></tr>')
            continue
        tink = [r for r in a["judges"] if r["tinker"]]
        J = a.get("juries") or {}
        R = {r["rule"]: r for r in J.get("rules", [])}
        bt = max((r for r in J.get("rules", []) if r["rule"].startswith("thr")), key=lambda r: r["acc"], default=None)
        bk = max((r for r in J.get("rules", []) if r["rule"] in ("top1", "top3", "top5")), key=lambda r: r["acc"], default=None)
        es = a.get("errors") or {}
        h.append(f'<tr><td><a href="#{b}" onclick="show(\'{b}\');return false">{e(TITLE[b])}</a></td><td class="n">{a["n_items"]:,}</td><td>{e(jl(tink[0]["judge"]))}</td>'
                 f'<td class="n">{pct(tink[0]["acc"])}</td><td class="n">{pct(R["majority_all"]["acc"]) if "majority_all" in R else "–"}</td>'
                 f'<td class="n">{pct(bk["acc"]) + f" <small>k={bk[chr(115)+chr(105)+chr(122)+chr(101)]:.0f}</small>" if bk else "–"}</td>'
                 f'<td class="n">{pct(bt["acc"]) + f" <small>{bt[chr(115)+chr(105)+chr(122)+chr(101)]:.1f} judges</small>" if bt else "–"}</td>'
                 f'<td class="n">{pct(J.get("oracle")) if J else "–"}</td><td class="n">{num(es.get("phi_mean"), 2)}</td>'
                 f'<td class="n">{pct(es.get("all_right_obs"), 0)} / {pct(es.get("all_right_ind"), 0)}</td></tr>')
    h.append('</tbody></table></div><p class="note">Accuracies without a reference answer. Top-k and threshold juries are cross-validated (out-of-fold reliability predictor); “Best” is the single judge with the highest agreement in hindsight. '
             'Pairwise sets count each presentation order separately.</p></section>')
    # threshold vs top-k comparison across benchmarks
    h.append('<section><h2>Threshold jury vs top-k, every benchmark</h2><p class="sub">Accuracy change from the cross-validated best single judge, for top-3 and for keeping only top-3 members with predicted p ≥ 0.8 / 0.9, plus the uncapped threshold at 0.9.</p>'
             '<div class="scroll"><table class="t"><thead><tr><th>Benchmark</th><th class="n">Top-3</th><th class="n">Top-3, drop p &lt; 0.8</th><th class="n">Top-3, drop p &lt; 0.9</th><th class="n">All with p ≥ 0.9</th><th class="n">Judges / item at p ≥ 0.9</th></tr></thead><tbody>')
    for b in ORDER:
        a = an.get(b)
        if not a or not a.get("juries"):
            continue
        R = {r["rule"]: r for r in a["juries"]["rules"]}

        def cell(k):
            if k not in R:
                return "–"
            r = R[k]
            sig = r["ci"][0] > 0 or r["ci"][1] < 0
            return f'{"<b>" if sig else ""}{100 * r["diff"]:+.1f}{"</b>" if sig else ""}'
        h.append(f'<tr><td>{e(TITLE[b])}</td><td class="n">{cell("top3")}</td><td class="n">{cell("thr0.8_cap3")}</td><td class="n">{cell("thr0.9_cap3")}</td>'
                 f'<td class="n">{cell("thr0.9")}</td><td class="n">{R["thr0.9"]["size"]:.2f}</td></tr>')
    h.append('</tbody></table></div><p class="note">Points of accuracy vs the cross-validated best single judge; bold = 95% bootstrap interval excludes 0.</p>')
    if take.get("threshold"):
        h.append(f'<div class="callout">{take["threshold"]}</div>')
    h.append('</section>')
    if take.get("caveats"):
        h.append('<section><h2>Caveats</h2><ul class="take">' + "".join(f"<li>{c}</li>" for c in take["caveats"]) + '</ul></section>')
    h.append('</div>')
    return "".join(h)


FB = ["bff", "mtb", "bffpair", "safety", "bbeh", "judgebench", "rb2", "alpacafarm", "mtbhuman"]


def question_tab(res, take):
    """What makes items hard to judge, and which judges are good at what (factors.json + content codes)."""
    fp = res / "factors.json"
    if not fp.exists():
        return ""
    F = json.loads(fp.read_text())
    q = take.get("qualitative", {})
    h = ['<div class="panel" id="questions"><section><h2>What makes an item hard to judge, and which judges are good at what</h2>',
         '<p class="sub">Every judged item across nine benchmarks, plus content coding of 50 judge-hard and 50 judge-easy items per benchmark and a close reading of about 50 items. '
         'Difficulty = share of the 8 judges that disagree with the gold label. Full write-up: <code>docs/qualitative_question_analysis.md</code>.</p>']
    if q.get("headline"):
        h.append(f'<p class="concl">{q["headline"]}</p>')
    if q.get("bullets"):
        h.append('<ul class="take">' + "".join(f"<li>{b}</li>" for b in q["bullets"]) + '</ul>')
    h.append('</section>')

    # hardness factors
    h.append('<section><h2>What makes items hard</h2><p class="sub">Share of judges wrong, by item type. Split = the human annotators disagreed. '
             'Hardest / easiest category: categories with at least 10 items.</p><div class="scroll"><table class="t"><thead><tr><th>Benchmark</th>'
             '<th class="n">All items</th><th class="n">Humans unanimous</th><th class="n">Humans split</th><th class="n">Good answer</th><th class="n">Bad answer</th>'
             '<th class="n">Better is longer</th><th class="n">Better is shorter</th><th>Hardest category</th><th>Easiest category</th></tr></thead><tbody>')
    for b in FB:
        if b not in F:
            continue
        u = F[b]["hardness"]["univariate"]
        g = lambda k, lv: pct(u[k][lv]["wrong"], 0) if k in u and lv in u[k] else "–"
        cats = list(u.get("category", {}).items())
        hard = f'{e(cats[0][0])} ({pct(cats[0][1]["wrong"], 0)})' if cats else "–"
        easy = f'{e(cats[-1][0])} ({pct(cats[-1][1]["wrong"], 0)})' if len(cats) > 1 else "–"
        h.append(f'<tr><td>{e(TITLE[b])}</td><td class="n">{pct(F[b]["hardness"]["mean_wrong"], 0)}</td><td class="n">{g("split_votes", "humans unanimous")}</td>'
                 f'<td class="n">{g("split_votes", "humans split")}</td><td class="n">{g("gold", "good answer")}</td><td class="n">{g("gold", "bad answer")}</td>'
                 f'<td class="n">{g("better_is_longer", "better one is longer")}</td><td class="n">{g("better_is_longer", "better one is shorter")}</td>'
                 f'<td>{hard}</td><td>{easy}</td></tr>')
    h.append('</tbody></table></div></section>')

    # content coding
    rows = []
    for b in FB:
        p = res / b / "content_codes.jsonl"
        if p.exists():
            rows += [dict(json.loads(l), bench=b) for l in open(p)]
    if rows:
        cc = pd.DataFrame(rows)
        n = cc.groupby("set").size()

        def shares(col, explode):
            x = cc.explode(col) if explode else cc
            t = x.groupby(["set", col]).size().unstack(0).fillna(0) / n
            t["d"] = t.get("hard", 0) - t.get("easy", 0)
            return t.sort_values("d", ascending=False)
        h.append('<section><h2>What hard items are about</h2><p class="sub">Content coding by DeepSeek-V3.1, blind to whether an item was hard. '
                 f'{int(n.get("hard", 0))} hard items (≥ half the judges wrong) vs {int(n.get("easy", 0))} easy items (every judge right). Share of items with each code.</p><div class="grid2">')
        for col, title, ex in [("task", "Task type", False), ("verify", "What a grader must do", True), ("driver", "What could make grading tricky", True)]:
            t = shares(col, ex)
            h.append(f'<div><h3>{title}</h3><table class="t"><thead><tr><th></th><th class="n">Easy</th><th class="n">Hard</th><th class="n">Hard − easy</th></tr></thead><tbody>')
            for k, r in t.iterrows():
                h.append(f'<tr><td>{e(str(k).replace("_", " "))}</td><td class="n">{pct(r.get("easy", 0), 0)}</td><td class="n">{pct(r.get("hard", 0), 0)}</td>'
                         f'<td class="n">{100 * r["d"]:+.0f}</td></tr>')
            h.append('</tbody></table></div>')
        h.append('</div></section>')

    # judge types
    h.append('<section><h2>Which judges are better at what</h2><p class="sub">Agreement gap between judge groups on the same items (points), with a 95% interval resampling conversations / prompts. '
             'Reasoning = the two gpt-oss judges, which always reason; the other six ran with thinking off. Large = gpt-oss-120b, DeepSeek-V3.1, Nemotron-Super-120B, Qwen3.6-35B.</p>'
             '<div class="scroll"><table class="t"><thead><tr><th>Benchmark</th><th class="n">Reasoning − thinking-off</th><th class="n">95% CI</th><th class="n">Large − small</th><th class="n">95% CI</th>'
             '<th>Where the reasoning gap grows (per SD)</th></tr></thead><tbody>')
    for b in FB:
        if b not in F:
            continue
        g = F[b]["judges"]["type_gaps"]
        r, s = g.get("reasoning_vs_thinking_off"), g.get("large_vs_small")
        grow = ""
        if r:
            sig = [m for m in r["model"] if m["ci"][0] > 0 or m["ci"][1] < 0]
            grow = ", ".join(f'{e(m["feature"].replace("_", " "))} {100 * m["beta"]:+.1f}' for m in sorted(sig, key=lambda m: -abs(m["beta"]))[:3]) or "–"
        cell = lambda x: (f'{100 * x["mean"]:+.1f}', f'[{100 * x["ci_mean"][0]:+.1f}, {100 * x["ci_mean"][1]:+.1f}]') if x else ("–", "–")
        (ra, rc), (sa, sc) = cell(r), cell(s)
        h.append(f'<tr><td>{e(TITLE[b])}</td><td class="n">{ra}</td><td class="n">{rc}</td><td class="n">{sa}</td><td class="n">{sc}</td><td>{grow}</td></tr>')
    h.append('</tbody></table></div>')

    # leniency heatmap
    judges = ["gpt-oss-120b", "gpt-oss-20b", "deepseek-v3.1", "qwen3.6-35b-a3b", "qwen3.5-9b", "qwen3.5-4b", "nemotron3-super-120b", "nemotron3-nano-30b"]
    h.append('<h3 style="margin-top:22px">Leniency: how often each judge accepts a bad answer (FPR) and rejects a good one (FNR)</h3>'
             '<p class="note">Single-grading benchmarks. Darker = more errors of that kind. Judges differ more in this yes-bias than in accuracy.</p>'
             '<div class="scroll"><table class="hm"><tr><th></th>' + "".join(f'<th colspan="2">{e(TITLE[b])}</th>' for b in FB if b in F and F[b]["hardness"]["univariate"].get("gold")) + '</tr><tr><th></th>'
             + "".join('<th>FPR</th><th>FNR</th>' for b in FB if b in F and F[b]["hardness"]["univariate"].get("gold")) + '</tr>')
    for j in judges:
        h.append(f'<tr><th class="rowh">{e(jl(j))}</th>')
        for b in FB:
            if b not in F or not F[b]["hardness"]["univariate"].get("gold"):
                continue
            L = F[b]["judges"]["leniency"].get(j)
            for k in ("fpr", "fnr"):
                v = L[k] if L else None
                h.append(f'<td style="{heat(v, 0, 0.5)}">{"–" if v is None else f"{100 * v:.0f}"}</td>')
        h.append('</tr>')
    h.append('</table></div></section>')
    if q.get("implications"):
        h.append('<section><h2>What this suggests for dynamic juries</h2><ol class="take">' + "".join(f"<li>{x}</li>" for x in q["implications"]) + '</ol></section>')
    h.append('</div>')
    return "".join(h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = Path(a.work) / "cross_benchmark/results"
    an, codes, contam = {}, {}, {}
    for b in ORDER:
        p = res / b / "analysis.json"
        if p.exists():
            an[b] = json.loads(p.read_text())
        for name, store in [("error_codes.jsonl", codes), ("contamination.jsonl", contam)]:
            q = res / b / name
            store[b] = [json.loads(l) for l in open(q)] if q.exists() else []
    take = json.loads((res / "takeaways.json").read_text()) if (res / "takeaways.json").exists() else {}
    TAKE.update(take.get("per_bench", {}))
    nav = ('<div class="tabs" role="tablist"><button role="tab" data-t="overview">Overview</button>'
           '<button role="tab" data-t="questions">Question analysis</button>') + "".join(
        f'<button role="tab" data-t="{b}" class="{"" if b in an else "na"}">{e(TITLE[b])}</button>' for b in ORDER) + '</div>'
    for b in list(codes):  # keep only codes for the benchmark's current best judge
        if b in an and an[b].get("errors"):
            codes[b] = [c for c in codes[b] if c.get("judge") == an[b]["errors"]["best"]]
    body = overview(an, take) + question_tab(res, take) + "".join(panel(b, an.get(b), codes.get(b), contam.get(b)) for b in ORDER)
    page = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>Judges Across Benchmarks</title><style>{CSS}</style></head><body><main>'
            '<p class="kicker">Dynamic LLM Juries · cross-benchmark qualitative analysis</p><h1>LLM Judge Analytics — Across Benchmarks</h1>'
            '<p class="sub">BFF-Bench’s qualitative and judge-level analysis repeated on nine more benchmarks, plus a test of threshold juries against top-k.</p>'
            f'{nav}{body}</main><script>{JS}</script></body></html>')
    Path(a.out).write_text(page)
    print("wrote", a.out, f"{len(page) / 1e3:.0f} kB")


if __name__ == "__main__":
    main()
