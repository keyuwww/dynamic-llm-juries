#!/usr/bin/env python3
"""
Build results/report.html: the judge-confidence and error-injection pilot as one page with inline SVG charts.
Every number is computed here from results/raw/ and the summary JSON files, so rerunning this after new data
refreshes the page.

  python experiments/judge_confidence/build_report.py
"""
import collections, html, json

from jc_common import HERE, RAW

RES = HERE / "results"
JUDGES = ["gpt-oss-120b", "qwen3.6-35b-a3b", "deepseek-v3.1"]
JNAME = {"gpt-oss-120b": "gpt-oss-120b", "qwen3.6-35b-a3b": "Qwen3.6-35B", "deepseek-v3.1": "DeepSeek-V3.1"}
JCLS = {"gpt-oss-120b": "j1", "qwen3.6-35b-a3b": "j2", "deepseek-v3.1": "j3"}
VORDER = ["ORIG", "C2", "C1", "V1", "V2-x10", "V2-10", "V2-lead", "V2-1"]
VNAME = {"ORIG": "Unchanged answer", "C2": "Paraphrased sentence", "C1": "Harmless rounding",
         "V1": "Final result contradicts working", "V2-x10": "Consistent error, ×10",
         "V2-10": "Consistent error, ~10%", "V2-lead": "Consistent error, leading digit",
         "V2-1": "Consistent error, ~1%"}
E = html.escape


def load(name):
    return [json.loads(l) for l in open(RAW / name)]


def pct(x, d=0):
    return f"{100 * x:.{d}f}%"


# ----------------------------------------------------------------------------- numbers
def numbers():
    N = {}
    pilot = json.load(open(RES / "pilot_summary.json"))
    N["pilot"] = {(r["judge"], r["condition"], r["vtype"]): r for r in pilot}
    N["n_texts"] = {r["vtype"]: r["n_texts"] for r in pilot if r["judge"] == JUDGES[0] and r["condition"] == "none"}
    inj = load("judgments.jsonl")
    real = load("judgments_real.jsonl")
    N["cost"] = dict(gen=sum(r["cost"] for r in load("generator_calls.jsonl")), inj=sum(r["cost"] for r in inj),
                     real=sum(r["cost"] for r in real),
                     unsure=sum(r["cost"] for r in load("judgments_unsure.jsonl")),
                     code=sum(r["cost"] for r in load("overstrict_codes.jsonl")) +
                     sum(r["cost"] for r in load("overstrict_blind.jsonl")) +
                     sum(r["cost"] for r in load("reasoning_codes.jsonl")))
    cm = {}
    for j in JUDGES:
        ie = [r for r in inj if r["judge"] == j and r["condition"] == "none" and r["gold"] == 0 and r["vote_share"] is not None]
        row = dict(inj=sum(r["vote_share"] == 1 for r in ie) / len(ie), n_inj=len(ie))
        for c in ("none", "human"):
            e = [r for r in real if r["judge"] == j and r["condition"] == c and r["gold_unanimous"] == 0 and r["vote_share"] is not None]
            k = [r for r in real if r["judge"] == j and r["condition"] == c and r["gold_unanimous"] == 1 and r["vote_share"] is not None]
            row[f"real_{c}"] = sum(r["vote_share"] == 1 for r in e) / len(e)
            row[f"fa_{c}"] = sum(r["vote_share"] == 0 for r in k) / len(k)
            row[f"n_real_{c}"] = len(e)
        lab = [r for r in real if r["judge"] == j and r["condition"] == "none" and r["gold_unanimous"] in (0, 1) and r["vote_share"] is not None]
        for name, f in (("agree", lambda r: r["vote_share"] in (0, 1)), ("mixed", lambda r: r["vote_share"] not in (0, 1))):
            rs = [r for r in lab if f(r)]
            row[f"acc_{name}"] = sum((r["vote_share"] >= 0.5) == (r["gold_unanimous"] == 1) for r in rs) / len(rs)
            row[f"n_{name}"] = len(rs)
        cm[j] = row
    N["conf"] = cm
    by = collections.defaultdict(dict)
    for r in real:
        if r["gold_unanimous"] == 0 and r["vote_share"] is not None:
            by[(r["item_id"], r["condition"])][r["judge"]] = r["vote_share"] == 1
    N["shared"] = {c: collections.Counter(sum(v.values()) for (i, cc), v in by.items() if cc == c and len(v) == 3)
                   for c in ("none", "human")}
    N["n_real"] = collections.Counter(r["gold_unanimous"] for r in real if r["judge"] == JUDGES[0] and r["condition"] == "none")
    N["probes"] = json.load(open(RES / "probes_modal.json"))
    N["unsure"] = json.load(open(RES / "unsure.json"))
    rc = load("reasoning_codes.jsonl")
    N["reason"] = []
    for verdict, said in ((1, "CORRECT"), (0, "INCORRECT")):
        for grp, label in (("confident_error", "missed a real error" if verdict else "rejected an approved answer"),
                           ("confident_correct", "rightly accepted" if verdict else "rightly rejected")):
            rs = [r for r in rc if r["group"] == grp and r["verdict"] == verdict]
            f = lambda k: sum(r.get(k) == "yes" for r in rs) / len(rs)
            N["reason"].append(dict(said=said, label=label, n=len(rs), recomputed=f("recomputed"), named=f("named_issue"),
                                    hedged=f("hedged"), definitions=sum(r.get("focus") == "definitions" for r in rs),
                                    tokens=sorted(r["n_out"] for r in rs)[len(rs) // 2]))
    bl = load("overstrict_blind.jsonl")
    cs = [r for r in real if r["condition"] == "human" and r["gold_unanimous"] == 1 and r["vote_share"] == 0]
    nby = collections.Counter(r["item_id"] for r in cs)
    n3 = {i for i, n in nby.items() if n == 3}
    groups = [("Rejected by all 3 judges", [b for b in bl if b["item_id"] in n3]),
              ("Rejected by at least 1 judge", [b for b in bl if b["group"] == "rejected"]),
              ("Accepted by all 3 (control)", [b for b in bl if b["group"] == "accepted"])]
    N["blind"] = [(n, len(g), sum(b["substantive_error"] == "yes" for b in g),
                   sum(b["conclusion_matches"] == "yes" for b in g)) for n, g in groups]
    N["strict"] = dict(cases=len(cs), answers=len(nby), by_k=dict(collections.Counter(nby.values())),
                       by_judge=dict(collections.Counter(r["judge"] for r in cs)),
                       gemma=sum(r["examinee"] == "gemma-2-2b" for r in cs))
    return N


# ----------------------------------------------------------------------------- charts
def dot_plot(N):
    """Rows = text types; two panels (no reference / reference); x = share of samples saying INCORRECT."""
    rowh, top, left, pw, gap = 30, 46, 238, 300, 40
    W = left + 2 * pw + gap + 20
    H = top + rowh * len(VORDER) + 30
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="c1t"><title id="c1t">Share of samples saying '
         f'INCORRECT for each kind of edited answer, per judge, without and with the reference</title>']
    for p, (cond, label) in enumerate((("none", "No reference"), ("human", "With expert reference"))):
        x0 = left + p * (pw + gap)
        s.append(f'<text class="lbl strong" x="{x0}" y="16">{label}</text>')
        for t in (0, 0.25, 0.5, 0.75, 1):
            x = x0 + t * pw
            s.append(f'<line class="grid" x1="{x}" x2="{x}" y1="{top - 10}" y2="{H - 26}"/>')
            s.append(f'<text class="tick" x="{x}" y="{H - 10}" text-anchor="middle">{int(t * 100)}%</text>')
        s.append(f'<rect class="band-ok" x="{x0}" y="{top - 10}" width="{pw}" height="{rowh * 3}"/>')
        s.append(f'<rect class="band-err" x="{x0}" y="{top - 10 + rowh * 3}" width="{pw}" height="{rowh * 5}"/>')
        # band tags sit where the dots are not: right side for still-correct rows, left side for error rows
        s.append(f'<text class="tag ok" x="{x0 + pw - 6}" y="{top + 3}" text-anchor="end">still correct</text>')
        s.append(f'<text class="tag err" x="{x0 + 6}" y="{top + 3 + rowh * 3}">contains an error</text>')
        for i, v in enumerate(VORDER):
            y = top + i * rowh + 5
            vals = [N["pilot"][(j, cond, v)]["detect"] for j in JUDGES]
            s.append(f'<line class="rng" x1="{x0 + min(vals) * pw}" x2="{x0 + max(vals) * pw}" y1="{y}" y2="{y}"/>')
            for j, d in zip(JUDGES, vals):
                s.append(f'<circle class="{JCLS[j]}" cx="{x0 + d * pw:.1f}" cy="{y}" r="5.5"><title>{JNAME[j]}: '
                         f'{pct(d)} of samples say INCORRECT</title></circle>')
    for i, v in enumerate(VORDER):
        y = top + i * rowh + 9
        s.append(f'<text class="lbl" x="{left - 12}" y="{y}" text-anchor="end">{VNAME[v]} '
                 f'<tspan class="muted">n={N["n_texts"][v]}</tspan></text>')
    s.append("</svg>")
    return "".join(s)


def conf_miss_chart(N):
    """Per judge: confident-miss rate on injected errors, real errors, real errors with reference."""
    bars = [("inj", "Injected errors, no reference", "b-inj"), ("real_none", "Real errors, no reference", "b-real"),
            ("real_human", "Real errors, with reference", "b-ref")]
    left, top, bh, gh, pw = 130, 14, 15, 18, 380
    W = left + pw + 70
    H = top + len(JUDGES) * (len(bars) * bh + gh) + 24
    mx = 0.25
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="c2t"><title id="c2t">Share of wrong answers '
         f'accepted with all 5 samples, per judge</title>']
    for t in (0, 0.05, 0.10, 0.15, 0.20, 0.25):
        x = left + t / mx * pw
        s.append(f'<line class="grid" x1="{x}" x2="{x}" y1="{top - 4}" y2="{H - 22}"/>')
        s.append(f'<text class="tick" x="{x}" y="{H - 6}" text-anchor="middle">{int(round(t * 100))}%</text>')
    y = top
    for j in JUDGES:
        s.append(f'<text class="lbl strong" x="{left - 10}" y="{y + bh * 1.5 + 4}" text-anchor="end">{JNAME[j]}</text>')
        for k, name, cls in bars:
            v = N["conf"][j][k]
            s.append(f'<rect class="{cls}" x="{left}" y="{y}" width="{max(1.5, v / mx * pw):.1f}" height="{bh - 3}" rx="1">'
                     f'<title>{name}: {pct(v, 1)}</title></rect>')
            s.append(f'<text class="val" x="{left + v / mx * pw + 6:.1f}" y="{y + bh - 5}">{pct(v)}</text>')
            y += bh
        y += gh
    s.append("</svg>")
    return "".join(s)


def agree_chart(N):
    """Per judge: accuracy when all 5 samples agree vs when they are mixed."""
    left, top, bh, gh, pw = 130, 10, 16, 16, 380
    W, H = left + pw + 90, top + len(JUDGES) * (2 * bh + gh) + 22
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="c3t"><title id="c3t">Accuracy on real BFF answers '
         f'when the 5 samples agree vs when they are mixed</title>']
    for t in (0, 0.25, 0.5, 0.75, 1):
        x = left + t * pw
        s.append(f'<line class="grid" x1="{x}" x2="{x}" y1="{top - 4}" y2="{H - 20}"/>')
        s.append(f'<text class="tick" x="{x}" y="{H - 5}" text-anchor="middle">{int(t * 100)}%</text>')
    y = top
    for j in JUDGES:
        c = N["conf"][j]
        s.append(f'<text class="lbl strong" x="{left - 10}" y="{y + bh + 4}" text-anchor="end">{JNAME[j]}</text>')
        for k, cls, lab in (("agree", "b-agree", "all 5 agree"), ("mixed", "b-mixed", "samples mixed")):
            v = c[f"acc_{k}"]
            s.append(f'<rect class="{cls}" x="{left}" y="{y}" width="{v * pw:.1f}" height="{bh - 3}" rx="1"><title>{lab}: '
                     f'{pct(v)} accurate (n={c[f"n_{k}"]})</title></rect>')
            s.append(f'<text class="val" x="{left + v * pw + 6:.1f}" y="{y + bh - 5}">{pct(v)} <tspan class="muted">'
                     f'n={c[f"n_{k}"]}</tspan></text>')
            y += bh
        y += gh
    s.append("</svg>")
    return "".join(s)


def probe_chart(N):
    """AUROC by layer for the three probe positions, one panel per condition, with the verdict's own AUROC."""
    pw, ph, left, top, gap = 300, 190, 44, 28, 46
    W, H = left + 2 * pw + gap + 16, top + ph + 40
    lo, hi = 0.4, 1.0
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="c4t"><title id="c4t">Probe AUROC by layer at three '
         f'positions, compared with the judge verdict</title>']
    pos = [("target", "p-target", "At the edited number"), ("verdict", "p-verdict", "At the verdict"),
           ("end", "p-end", "At the end of the answer")]
    for p, (cond, label) in enumerate((("none", "No reference"), ("human", "With expert reference"))):
        x0 = left + p * (pw + gap)
        d = N["probe"][cond]
        nL = len(d["positions"]["target"]["auroc_by_layer"])
        X = lambda L: x0 + L / (nL - 1) * pw
        Y = lambda a: top + (hi - a) / (hi - lo) * ph
        s.append(f'<text class="lbl strong" x="{x0}" y="14">{label}</text>')
        for a in (0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
            s.append(f'<line class="grid" x1="{x0}" x2="{x0 + pw}" y1="{Y(a):.1f}" y2="{Y(a):.1f}"/>')
            if p == 0:
                s.append(f'<text class="tick" x="{x0 - 6}" y="{Y(a) + 4:.1f}" text-anchor="end">{a:.1f}</text>')
        for L in (0, 8, 16, 24, 32):
            s.append(f'<text class="tick" x="{X(L):.1f}" y="{top + ph + 16}" text-anchor="middle">{L}</text>')
        s.append(f'<text class="tick" x="{x0 + pw / 2}" y="{top + ph + 32}" text-anchor="middle">layer</text>')
        va = d["verdict_auroc"]
        s.append(f'<line class="verdict-line" x1="{x0}" x2="{x0 + pw}" y1="{Y(va):.1f}" y2="{Y(va):.1f}"/>')
        s.append(f'<text class="val" x="{x0 + 4}" y="{Y(va) - 6:.1f}">verdict alone {va:.2f}</text>')
        for k, cls, _ in pos:
            pts = " ".join(f"{X(L):.1f},{Y(max(lo, a)):.1f}" for L, a in enumerate(d["positions"][k]["auroc_by_layer"]))
            s.append(f'<polyline class="{cls}" points="{pts}"/>')
            b = d["positions"][k]
            s.append(f'<circle class="{cls}-dot" cx="{X(b["best_layer"]):.1f}" cy="{Y(b["best_auroc"]):.1f}" r="3.5">'
                     f'<title>best layer {b["best_layer"]}: AUROC {b["best_auroc"]:.3f}</title></circle>')
    s.append("</svg>")
    return "".join(s)


def blind_chart(N):
    left, top, bh, pw = 210, 8, 30, 330
    W, H = left + pw + 80, top + len(N["blind"]) * bh + 22
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="c5t"><title id="c5t">Share of expert-approved '
         f'answers in which a blind coder found a substantive error</title>']
    for t in (0, 0.25, 0.5, 0.75, 1):
        x = left + t * pw
        s.append(f'<line class="grid" x1="{x}" x2="{x}" y1="{top - 4}" y2="{H - 20}"/>')
        s.append(f'<text class="tick" x="{x}" y="{H - 5}" text-anchor="middle">{int(t * 100)}%</text>')
    for i, (name, n, err, _) in enumerate(N["blind"]):
        y = top + i * bh
        v = err / n
        cls = "b-ctrl" if "control" in name else "b-real"
        s.append(f'<text class="lbl" x="{left - 10}" y="{y + 15}" text-anchor="end">{E(name)}</text>')
        s.append(f'<rect class="{cls}" x="{left}" y="{y + 2}" width="{max(1.5, v * pw):.1f}" height="{bh - 10}" rx="1">'
                 f'<title>{err} of {n}</title></rect>')
        s.append(f'<text class="val" x="{left + v * pw + 6:.1f}" y="{y + 15}">{pct(v)} <tspan class="muted">{err}/{n}'
                 f'</tspan></text>')
    s.append("</svg>")
    return "".join(s)


MODELS = [("qwen3.5-0.8b", "Qwen3.5-0.8B"), ("jeff", "Jeff (0.8B, decision-trained)"), ("qwen3.5-4b", "Qwen3.5-4B"),
          ("qwen3.5-9b", "Qwen3.5-9B")]


def probe_dumbbell(N):
    """Per small model: its own verdict's AUROC (hollow) vs the best hidden-state probe (filled), two panels."""
    panels = [("Planted errors, at the verdict", lambda r: (r["planted_none"]["planted@verdict"]["verdict_auroc"],
                                                              r["planted_none"]["planted@verdict"]["best_auroc"])),
              ("Real errors, within answer model", lambda r: (r["real_none"]["error@verdict"]["within_model_verdict"],
                                                               r["real_none"]["error@verdict"]["within_model_probe"]))]
    left, top, rowh, pw, gap = 210, 34, 34, 250, 40
    W, H = left + 2 * pw + gap + 20, top + rowh * len(MODELS) + 28
    lo, hi = 0.5, 1.0
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="c6t"><title id="c6t">AUROC of each small model\'s '
         f'own verdict vs a probe on its hidden state</title>']
    for p, (name, get) in enumerate(panels):
        x0 = left + p * (pw + gap)
        X = lambda a: x0 + (a - lo) / (hi - lo) * pw
        s.append(f'<text class="lbl strong" x="{x0}" y="14">{name}</text>')
        for t in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
            s.append(f'<line class="grid" x1="{X(t):.1f}" x2="{X(t):.1f}" y1="{top - 10}" y2="{H - 24}"/>')
            s.append(f'<text class="tick" x="{X(t):.1f}" y="{H - 8}" text-anchor="middle">{t:.1f}</text>')
        for i, (m, _) in enumerate(MODELS):
            v, pr = get(N["probes"][m])
            y = top + i * rowh + 6
            s.append(f'<line class="rng" x1="{X(v):.1f}" x2="{X(pr):.1f}" y1="{y}" y2="{y}" style="opacity:.9"/>')
            s.append(f'<circle class="dot-verdict" cx="{X(v):.1f}" cy="{y}" r="5.5"><title>verdict {v:.2f}</title></circle>')
            s.append(f'<circle class="dot-probe" cx="{X(pr):.1f}" cy="{y}" r="5.5"><title>probe {pr:.2f}</title></circle>')
            s.append(f'<text class="val" x="{X(pr) + 9:.1f}" y="{y + 4}">+{pr - v:.2f}</text>')
    for i, (_, nm) in enumerate(MODELS):
        s.append(f'<text class="lbl" x="{left - 12}" y="{top + i * rowh + 10}" text-anchor="end">{E(nm)}</text>')
    s.append("</svg>")
    return "".join(s)


def unsure_chart(N):
    """Per judge and condition: share of the judge's errors caught by UNSURE vs by a split vote."""
    rows = [(k, v) for k, v in N["unsure"].items()]
    left, top, bh, gh, pw = 250, 10, 15, 14, 330
    W, H = left + pw + 110, top + len(rows) * (2 * bh + gh) + 22
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="c7t"><title id="c7t">Share of each judge\'s errors '
         f'flagged by an UNSURE option vs by a split vote</title>']
    for t in (0, 0.25, 0.5):
        x = left + t / 0.5 * pw
        s.append(f'<line class="grid" x1="{x}" x2="{x}" y1="{top - 4}" y2="{H - 20}"/>')
        s.append(f'<text class="tick" x="{x}" y="{H - 5}" text-anchor="middle">{int(t * 100)}%</text>')
    y = top
    for k, v in rows:
        j, c = k.split("|")
        s.append(f'<text class="lbl" x="{left - 10}" y="{y + bh + 3}" text-anchor="end">{JNAME[j]} · '
                 f'{"no reference" if c == "none" else "reference"}</text>')
        for key, esc, cls, lab in (("caught_split", "esc_split", "b-agree", "split vote"),
                                   ("caught_unsure", "esc_unsure", "b-real", "UNSURE")):
            val = v[key]
            s.append(f'<rect class="{cls}" x="{left}" y="{y}" width="{max(1.5, val / 0.5 * pw):.1f}" height="{bh - 3}" rx="1">'
                     f'<title>{lab}: catches {pct(val)} of {v["n_errors"]} errors, escalates {pct(v[esc])}</title></rect>')
            s.append(f'<text class="val" x="{left + max(1.5, val / 0.5 * pw) + 6:.1f}" y="{y + bh - 4}">{pct(val)} '
                     f'<tspan class="muted">at {pct(v[esc])} escalated</tspan></text>')
            y += bh
        y += gh
    s.append("</svg>")
    return "".join(s)


def blindspot_table(N):
    rows = []
    for m, nm in MODELS:
        r = N["probes"][m]["real_none"]
        cells = "".join(f'<td class="n">{r[f"flags_missed_by_{j}"]["probe_auroc"]:.2f} / '
                        f'{r[f"flags_missed_by_{j}"]["verdict_auroc"]:.2f}</td>' for j in JUDGES)
        rows.append(f"<tr><td>{E(nm)}</td>{cells}</tr>")
    head = "".join(f"<th>{JNAME[j]}'s misses (n={N['probes']['qwen3.5-4b']['real_none'][f'flags_missed_by_{j}']['n_missed']})</th>"
                   for j in JUDGES)
    return (f'<div class="tablewrap"><table><thead><tr><th>Small model (probe / verdict)</th>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def reasoning_table(N):
    rows = "".join(f'<tr><td>{r["said"]}</td><td>{E(r["label"])}</td><td class="n">{r["n"]}</td>'
                   f'<td class="n">{pct(r["recomputed"])}</td><td class="n">{pct(r["named"])}</td>'
                   f'<td class="n">{pct(r["hedged"])}</td><td class="n">{r["definitions"]}</td><td class="n">{r["tokens"]}</td></tr>'
                   for r in N["reason"])
    return ('<div class="tablewrap"><table><thead><tr><th>Judge said</th><th>Group</th><th>n</th><th>Recomputed</th>'
            '<th>Named an issue</th><th>Hedged</th><th>Argued definitions</th><th>Median tokens</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')


def legend(items):
    return '<div class="legend">' + "".join(f'<span><i class="sw {c}"></i>{E(t)}</span>' for c, t in items) + "</div>"


# ----------------------------------------------------------------------------- page
CSS = """
/* Layout: one reading column (~70ch) with wide figure blocks; findings first, method and caveats after. */
:root{
  --paper:#fbfcfd; --ink:#16212c; --muted:#5d6b78; --rule:#d9e0e6; --panel:#f1f4f7;
  --accent:#1f5f8b;
  --j1:#1f5f8b; --j2:#c07a12; --j3:#7a4fa3;
  --ok:#2e7d5b; --err:#b4472f; --okband:rgba(46,125,91,.07); --errband:rgba(180,71,47,.06);
  --font-display:"Newsreader", Georgia, "Times New Roman", serif;
  --font-body:"IBM Plex Sans", "Helvetica Neue", Arial, sans-serif;
  --font-data:"IBM Plex Mono", ui-monospace, Menlo, monospace;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --paper:#0f151b; --ink:#e3e9ee; --muted:#93a1ad; --rule:#26313b; --panel:#17202835;
  --accent:#6fb0dc; --j1:#6fb0dc; --j2:#e2a443; --j3:#b994dd;
  --ok:#5cc297; --err:#ec8a6f; --okband:rgba(92,194,151,.08); --errband:rgba(236,138,111,.07); color-scheme:dark }}
:root[data-theme="dark"]{
  --paper:#0f151b; --ink:#e3e9ee; --muted:#93a1ad; --rule:#26313b; --panel:#17202835;
  --accent:#6fb0dc; --j1:#6fb0dc; --j2:#e2a443; --j3:#b994dd;
  --ok:#5cc297; --err:#ec8a6f; --okband:rgba(92,194,151,.08); --errband:rgba(236,138,111,.07); color-scheme:dark }
body{background:var(--paper);color:var(--ink);font:16px/1.6 var(--font-body)}
.wrap{max-width:960px;margin:0 auto;padding-block:40px 64px;
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));
  display:grid;gap:40px}
.col{max-width:70ch}
h1,h2{font-family:var(--font-display);font-weight:500;text-wrap:balance;letter-spacing:-.01em;margin:0}
h1{font-size:clamp(2rem,5vw,3rem);line-height:1.1}
h2{font-size:1.6rem;line-height:1.2}
h3{font-size:1rem;margin:0 0 4px}
p{margin:0}
.stack{display:grid;gap:14px}
.eyebrow{font:500 .75rem/1 var(--font-data);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.lede{font-size:1.15rem;color:var(--ink)}
.muted{color:var(--muted);fill:var(--muted)}
.meta{font:.8rem/1.5 var(--font-data);color:var(--muted)}
.keys{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
.key{border-top:2px solid var(--ink);padding-top:10px;display:grid;gap:4px;min-width:0}
.key b{font:500 1.9rem/1 var(--font-display);font-variant-numeric:tabular-nums}
.key span{font-size:.9rem;color:var(--muted)}
figure{margin:0;display:grid;gap:10px}
.chart{overflow-x:auto}
.chart svg{width:100%;min-width:560px;height:auto;display:block}
figcaption{font-size:.9rem;color:var(--muted);max-width:75ch}
.legend{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:.85rem;color:var(--muted)}
.legend span{display:inline-flex;align-items:center;gap:6px}
.sw{width:12px;height:12px;border-radius:2px;display:inline-block}
.sw.j1{background:var(--j1)} .sw.j2{background:var(--j2)} .sw.j3{background:var(--j3)}
.sw.b-inj{background:var(--muted)} .sw.b-real{background:var(--err)} .sw.b-ref{background:var(--ok)}
.sw.b-agree{background:var(--accent)} .sw.b-mixed{background:var(--rule);outline:1px solid var(--muted)}
.sw.p-target{background:var(--muted)} .sw.p-verdict{background:var(--accent)} .sw.p-end{background:var(--j2)}
.sw.vl{background:none;border-top:2px dashed var(--ink);height:0;border-radius:0}
svg text{font-family:var(--font-body);fill:var(--ink)}
svg .lbl{font-size:12.5px} svg .strong{font-weight:600}
svg .tick{font:11px var(--font-data);fill:var(--muted)}
svg .val{font:11.5px var(--font-data);fill:var(--ink)}
svg .tag{font:600 10.5px var(--font-data);letter-spacing:.06em;text-transform:uppercase}
svg .tag.ok{fill:var(--ok)} svg .tag.err{fill:var(--err)}
svg .grid{stroke:var(--rule);stroke-width:1}
svg .band-ok{fill:var(--okband)} svg .band-err{fill:var(--errband)}
svg .rng{stroke:var(--muted);stroke-width:1.5;opacity:.5}
svg .j1{fill:var(--j1)} svg .j2{fill:var(--j2)} svg .j3{fill:var(--j3)}
svg .b-inj{fill:var(--muted)} svg .b-real{fill:var(--err)} svg .b-ref{fill:var(--ok)} svg .b-ctrl{fill:var(--ok)}
svg .b-agree{fill:var(--accent)} svg .b-mixed{fill:var(--rule);stroke:var(--muted);stroke-width:1}
svg .p-target,svg .p-verdict,svg .p-end{fill:none;stroke-width:2}
svg .p-target{stroke:var(--muted);stroke-dasharray:4 3} svg .p-verdict{stroke:var(--accent)} svg .p-end{stroke:var(--j2)}
svg .p-target-dot{fill:var(--muted)} svg .p-verdict-dot{fill:var(--accent)} svg .p-end-dot{fill:var(--j2)}
svg .dot-verdict{fill:var(--paper);stroke:var(--muted);stroke-width:2} svg .dot-probe{fill:var(--accent)}
.sw.dot-verdict{background:var(--paper);border:2px solid var(--muted);border-radius:50%} .sw.dot-probe{background:var(--accent);border-radius:50%}
svg .verdict-line{stroke:var(--ink);stroke-width:1.5;stroke-dasharray:6 4}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}
.card{background:var(--panel);border:1px solid var(--rule);border-radius:6px;padding:14px 16px;display:grid;gap:6px;min-width:0}
.card .meta{font-size:.75rem}
.card q{font-style:italic}
table{border-collapse:collapse;font-size:.9rem;font-variant-numeric:tabular-nums;width:100%}
th,td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--rule);vertical-align:top}
th{font-weight:600;color:var(--muted);font-size:.8rem;text-transform:uppercase;letter-spacing:.05em}
td.n{text-align:right;font-family:var(--font-data)}
.tablewrap{overflow-x:auto}
ul,ol{margin:0;padding-left:1.2em;display:grid;gap:6px}
code{font:.85em var(--font-data);background:var(--panel);padding:1px 4px;border-radius:3px}
section{display:grid;gap:18px}
hr{border:0;border-top:1px solid var(--rule);margin:0}
"""


def page(N):
    c, cost = N["conf"], N["cost"]
    total = sum(cost.values())
    g, q, d = c["gpt-oss-120b"], c["qwen3.6-35b-a3b"], c["deepseek-v3.1"]
    st = N["strict"]
    bl = {n: (k, e, m) for n, k, e, m in N["blind"]}
    P = N["probes"]
    ratios = [x["real_none"] / x["inj"] for x in c.values() if x["inj"] > 0]
    v2 = [N["pilot"][(j, cc, t)]["detect"] for j in JUDGES[:2] for cc in ("none", "human") for t in ("V2-10", "V2-x10", "V2-lead", "V2-1")]
    gap_small = [P[m]["planted_none"]["planted@verdict"]["best_auroc"] - P[m]["planted_none"]["planted@verdict"]["verdict_auroc"] for m in ("qwen3.5-0.8b", "jeff")]
    gap_big = [P[m]["planted_none"]["planted@verdict"]["best_auroc"] - P[m]["planted_none"]["planted@verdict"]["verdict_auroc"] for m in ("qwen3.5-4b", "qwen3.5-9b")]
    unsure_use = max(v["use_any"] for v in N["unsure"].values())
    inj_lo, inj_hi = min(x["inj"] for x in c.values()), max(x["inj"] for x in c.values())
    real_lo, real_hi = min(x["real_none"] for x in c.values()), max(x["real_none"] for x in c.values())
    ref_lo, ref_hi = min(x["real_human"] for x in c.values()), max(x["real_human"] for x in c.values())
    return f"""<title>When Judges Are Confidently Wrong</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;600&family=Newsreader:opsz,wght@6..72,500&display=swap">
<style>{CSS}</style>
<main class="wrap">

<header class="stack col">
  <p class="eyebrow">AC 297r · Dynamic LLM Juries · BFF-Bench · 10/23</p>
  <h1>When judges are confidently wrong</h1>
  <p class="lede">We planted one numeric error at a time into finance answers that experts had approved, and compared
  how three strong LLM judges handled those errors with how they handled the real mistakes in BFF-Bench. The judges
  catch planted numbers. They confidently miss real method errors, which the expert reference mostly fixes. And when
  they confidently reject an answer the experts approved, the answer usually does contain an error. Offered an
  UNSURE option, they never use it. Small open judges hold more in their hidden states than their verdicts say, but
  they share the big judges' blind spots.</p>
  <p class="meta">Judges: gpt-oss-120b, Qwen3.6-35B-A3B, DeepSeek-V3.1 (Tinker) · 5 samples per verdict at T = 0.7 ·
  "confident" = all 5 samples agree · hidden-state probes: Qwen3.5-0.8B, Jeff, Qwen3.5-4B, Qwen3.5-9B (Modal) ·
  Tinker cost ${total:.2f}</p>
</header>

<div class="keys">
  <div class="key"><b>{pct(inj_lo)}–{pct(inj_hi)}</b><span>of planted numeric errors accepted with all 5 samples</span></div>
  <div class="key"><b>{pct(real_lo)}–{pct(real_hi)}</b><span>of real BFF errors accepted with all 5 samples, no reference</span></div>
  <div class="key"><b>{pct(ref_lo)}–{pct(ref_hi)}</b><span>of real errors accepted with all 5 samples once the judge has the expert reference</span></div>
  <div class="key"><b>{pct(unsure_use, 1)}</b><span>most often any judge chose UNSURE when offered it</span></div>
</div>

<section>
  <div class="stack col">
    <p class="eyebrow">1 · Planted errors</p>
    <h2>Strong judges catch a single wrong number, even when it is carried through</h2>
    <p>DeepSeek-V3.1 edited each approved answer in one controlled way, and a script checked that only the intended
    numbers changed ({sum(v for k, v in N['n_texts'].items() if k.startswith('V'))} error texts and
    {N['n_texts']['C1'] + N['n_texts']['C2']} harmless edits passed). A "consistent" error changes one
    intermediate number and recomputes everything after it, so the answer agrees with itself and the judge has to
    redo the arithmetic to notice. The Validation Gap paper found small models catch only 3–45% of those. Our
    reasoning judges catch {pct(min(v2))}–{pct(max(v2))} (gpt-oss-120b and Qwen3.6).</p>
  </div>
  <figure>
    <div class="chart">{dot_plot(N)}</div>
    {legend([('j1', 'gpt-oss-120b'), ('j2', 'Qwen3.6-35B'), ('j3', 'DeepSeek-V3.1')])}
    <figcaption>Share of the 5 samples that say INCORRECT. In the top three rows the answer is still correct, so any
    INCORRECT is a false alarm. Only the smallest change (about 1%) is noticeably harder. The reference mostly cuts
    false alarms, not misses. DeepSeek-V3.1 covers only the pilot subset (58 answers): Tinker stopped serving it during
    the run.</figcaption>
  </figure>
</section>

<section>
  <div class="stack col">
    <p class="eyebrow">2 · Real errors</p>
    <h2>Real mistakes are confidently missed {min(ratios):.0f}–{max(ratios):.0f} times more often, until the reference arrives</h2>
    <p>We judged all 960 real BFF answers the same way. Against the {N['n_real'][0]} answers all experts marked
    wrong, the judges accept many more with full confidence than they did for planted errors. In {N['shared']['none'][3]}
    of them all three judges were fully confident and wrong. Each of those answers has correct arithmetic built on the
    wrong method or premise. One example is the IFRS impairment question, where three different answer models gave
    the same $116,550 and every judge agreed. With the expert reference, none of the {N['n_real'][0]} fool all three
    judges.</p>
  </div>
  <figure>
    <div class="chart">{conf_miss_chart(N)}</div>
    {legend([('b-inj', 'Planted errors, no reference'), ('b-real', 'Real errors, no reference'), ('b-ref', 'Real errors, with reference')])}
    <figcaption>Share of wrong answers that a judge accepted with all 5 samples. Planted: {c['gpt-oss-120b']['n_inj']}
    error texts per judge. Real: {c['gpt-oss-120b']['n_real_none']} answers all experts marked incorrect.</figcaption>
  </figure>
</section>

<section>
  <div class="stack col">
    <p class="eyebrow">3 · Confidence as a signal</p>
    <h2>Five samples are a usable confidence signal; the verdict-word probability is not</h2>
    <p>When all five samples agree, the verdict is right {pct(min(x['acc_agree'] for x in c.values()))}–{pct(max(x['acc_agree'] for x in c.values()))}
    of the time. When they split, it is right only {pct(min(x['acc_mixed'] for x in c.values()))}–{pct(max(x['acc_mixed'] for x in c.values()))}. The probability on the verdict word adds nothing on top. After the judge has reasoned, that probability is
    almost always near 0 or 1. Confidence also does not track human doubt: judges give a unanimous verdict on about
    78% of the answers the experts split on, about as often as on clear ones.</p>
  </div>
  <figure>
    <div class="chart">{agree_chart(N)}</div>
    {legend([('b-agree', 'All 5 samples agree'), ('b-mixed', 'Samples mixed')])}
    <figcaption>Accuracy against the unanimous expert label on real BFF answers, no reference.</figcaption>
  </figure>
</section>

<section>
  <div class="stack col">
    <p class="eyebrow">4 · Asking the judge to say when it is unsure</p>
    <h2>Offered an UNSURE option, the judges do not use it</h2>
    <p>We repeated the real-answer runs with one change to the prompt: the judge could answer
    <code>VERDICT: UNSURE</code> when it could not tell and the answer should go to a human expert. The judges chose
    it on at most {pct(unsure_use, 1)} of answers, including the ones they then got wrong. The five-sample vote does
    the job instead: sending split votes to a human catches a third or more of each judge's errors.</p>
  </div>
  <figure>
    <div class="chart">{unsure_chart(N)}</div>
    {legend([('b-agree', 'Split vote among 5 samples'), ('b-real', 'Judge chose UNSURE')])}
    <figcaption>Share of each judge's errors (binary prompt, majority verdict vs unanimous expert label) that each rule
    would send to a human, and the share of all answers it sends. DeepSeek-V3.1 has no reference run and covers 511
    of 960 answers.</figcaption>
  </figure>
</section>

<section>
  <div class="stack col">
    <p class="eyebrow">5 · What the reasoning looks like</p>
    <h2>A confident miss reads exactly like a confident correct verdict</h2>
    <p>A blind coder described the reasoning behind confident errors and an equal number of confident correct
    verdicts. When the judge wrongly accepts an answer, its reasoning recomputes just as often and hedges just as
    rarely as when it is right. Its wrong rejections recompute less and argue about definitions.</p>
  </div>
  {reasoning_table(N)}
</section>

<section>
  <div class="stack col">
    <p class="eyebrow">6 · Inside small judges</p>
    <h2>Small judges know more than they say, and the gap shrinks as they grow</h2>
    <p>Four open models saw the same grading prompt with the verdict forced right away, and a linear probe read
    their hidden state at the verdict position. In the 0.8B models the probe beats the model's own verdict by
    {min(gap_small):+.2f} to {max(gap_small):+.2f} AUROC on planted errors; at 4B–9B by only {min(gap_big):+.2f} to
    {max(gap_big):+.2f}. Jeff, the decision-trained 0.8B model, says no more than its base but holds a slightly cleaner
    signal. A probe for "the experts disagreed on this answer" stays near 0.6 in every model.</p>
  </div>
  <figure>
    <div class="chart">{probe_dumbbell(N)}</div>
    {legend([('dot-verdict', "The model's own verdict"), ('dot-probe', 'Probe on its hidden state')])}
    <figcaption>AUROC, 5-fold cross-validated with folds grouped by question; best layer picked on the same folds, so
    probe values are slightly optimistic. Real errors are scored within each answer model, because the answer model
    and length alone already reach 0.80. Planted errors compare each edited answer with the same answer unedited, and
    harmless paraphrases stay at 0.48.</figcaption>
  </figure>
  <div class="stack col">
    <h3>Do small models see what the big judges miss?</h3>
    <p>No. Among answers all experts marked wrong, the ones a strong judge confidently accepted are also the ones
    small models find most convincing. Values above 0.5 mean the small model shares the blind spot.</p>
  </div>
  {blindspot_table(N)}
</section>

<section>
  <div class="stack col">
    <p class="eyebrow">7 · Over-strict judges?</p>
    <h2>Most confident rejections of approved answers point at real flaws</h2>
    <p>With the reference, the judges' remaining confident disagreement goes the other way. In {st['cases']} cases a
    judge rejected, with all five samples, one of {st['answers']} answers that every expert had marked correct.
    {st['by_k'].get(3, 0)} of those answers were rejected by all three judges, and {st['gemma']} of the {st['cases']} cases
    are gemma-2-2b answers. A coder that saw the judge's reasoning agreed with the judge every time, so we ran it
    blind. It saw only the question, the reference and the answer, and we compared against answers all judges had
    accepted.</p>
  </div>
  <figure>
    <div class="chart">{blind_chart(N)}</div>
    <figcaption>Share of expert-approved answers in which a blind coder (Nemotron-3 Super 120B, not one of the three
    judges) found a substantive error: a wrong number, formula, definition, fact or reasoning step, ignoring style and
    minor rounding.</figcaption>
  </figure>
  <div class="cards">
    <div class="card"><p class="meta">5749d391-t2 · qwen2.5-7b · options</p><p>Says the $100-strike put is worth
    <q>$20 ($120 − $100)</q> with the stock at $120. A put above its strike is worth $0.</p></div>
    <div class="card"><p class="meta">3449e3bf-t1 · qwen2.5-7b · capital structure</p><p>Credits the Pecking Order
    Theory to <q>Myron S. Miller and Ferris J.文明 (Fama) in 1987</q>. It is Myers and Majluf.</p></div>
    <div class="card"><p class="meta">00098cc2-t1 · gemma-2-2b · tax</p><p>Right conclusion, but states that
    <q>a negative tax liability means he owes the government money</q>.</p></div>
    <div class="card"><p class="meta">02c3d722-t1 · llama-3.3-70b · margin</p><p>Fixes the maintenance margin at
    30% of the purchase price, not of the current market value.</p></div>
  </div>
  <p class="col">The expert "correct" label often accepts an answer whose conclusion is roughly right while a step,
  definition or fact is wrong; the judges grade the whole answer. A second judge or a split vote would rarely
  overturn these rejections, and should not. The one exception is Qwen3.6, where another judge accepts 43% of its
  rejections at a 9% escalation rate. The four cards were checked by hand; the other answers still need a human
  check before we quote a label-error rate.</p>
</section>

<hr>

<section class="col">
  <h2>What this means</h2>
  <ol>
    <li>Planted numeric slips are not where strong reasoning judges fail. Their confident failures without a
    reference are method and premise errors they share with the answer models.</li>
    <li>A reference fixes most of those. With a reference, the remaining confident disagreements are mostly cases
    where the expert label is too lenient, so judge accuracy against BFF's unanimous labels is understated.</li>
    <li>For a router: escalate when the five samples split, and always supply a reference when one exists. A
    self-reported UNSURE, the verdict-word probability, hedging language and item features add almost nothing.</li>
    <li>Hidden-state probes help mainly for very small judges, whose verdicts lag what they hold. They do not see
    the big judges' blind spots, because small models share them.</li>
  </ol>
</section>

<section class="col">
  <h2>Limits</h2>
  <ul>
    <li>One answer set (BFF-Bench). Planted errors: 50–125 per type. DeepSeek-V3.1 was withdrawn by Tinker mid-run,
    so its planted and UNSURE results are partial.</li>
    <li>The coder is an LLM. The 33 disputed answers need a human check (about 1 hour).</li>
    <li>Probed models answer without reasoning and are at most 9B, so they show the mechanism and do not describe
    gpt-oss-120b. Best-layer probe numbers are slightly optimistic.</li>
    <li>Planted errors were written by DeepSeek-V3.1, which is also one of the judges; its detection rates are not
    higher than the others'.</li>
  </ul>
</section>

<section class="col">
  <h2>Data and code</h2>
  <div class="tablewrap"><table>
    <thead><tr><th>Step</th><th>Script</th><th>Cost</th></tr></thead>
    <tbody>
      <tr><td>Planted-error variants and checks</td><td><code>inject.py</code></td><td class="n">${cost['gen']:.2f}</td></tr>
      <tr><td>Judging original and edited answers</td><td><code>judge.py</code></td><td class="n">${cost['inj']:.2f}</td></tr>
      <tr><td>Judging all 960 real answers (+ reference for 459)</td><td><code>judge_real.py</code></td><td class="n">${cost['real']:.2f}</td></tr>
      <tr><td>UNSURE-option runs</td><td><code>judge_real.py --unsure</code>, <code>unsure_analysis.py</code></td><td class="n">${cost['unsure']:.2f}</td></tr>
      <tr><td>Coding over-strict cases and judge reasoning</td><td><code>overstrict.py</code>, <code>reasoning_codes.py</code></td><td class="n">${cost['code']:.2f}</td></tr>
      <tr><td>Item features vs confidence</td><td><code>features.py</code></td><td class="n">$0.00</td></tr>
      <tr><td>Hidden-state probes, 4 models (Modal GPUs)</td><td><code>probe_modal.py</code>, <code>analyze_probes.py</code></td><td class="n">Modal</td></tr>
    </tbody>
  </table></div>
  <p class="meta">All in <code>experiments/judge_confidence/</code> on branch <code>wip/cross-benchmark-analysis</code>.
  Raw outputs (every sample, prompt, verdict-token log-probs and activation) are in <code>results/raw/</code> on
  the laptop and are not in git. This page is rebuilt by <code>build_report.py</code>.</p>
</section>

</main>"""


def main():
    out = RES / "report.html"
    out.write_text(page(numbers()))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
