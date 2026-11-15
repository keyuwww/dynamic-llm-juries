#!/usr/bin/env python3
"""Builds results/trust_read_think.html from the saved result JSONs (Steps 0-9). Light mode only, inline SVG charts.

  .venv/bin/python experiments/trust_read_think/build_report.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE / "results"
JR = R / "qwen3.5-4b"                       # the judge this report covers
J = lambda n: json.loads(((R if n == "pilot.json" else JR) / n).read_text())
S2, S5, S7, S8, CI = J("step2.json"), J("step5.json"), J("step7.json"), J("step8.json"), J("step9_ci.json")["results"]
PILOT = J("pilot.json")
JUDGES3 = ["qwen3.5-4b", "gpt-oss-20b", "nvidia-nemotron-nano-9b-v2"]
CI3 = {j: json.loads((R / j / "step9_ci.json").read_text())["results"] for j in JUDGES3}
S2J = {j: json.loads((R / j / "step2.json").read_text()) for j in JUDGES3}
JURY = json.loads((R / "jury" / "step10_jury.json").read_text())
BUD = {j: json.loads((R / j / "step12_budget.json").read_text())["benches"] for j in JUDGES3}
FMT = {j: json.loads((R / j / "step11_format.json").read_text()) for j in JUDGES3}

INK, MUTED, FAINT, GRID = "#14243A", "#5B6B82", "#8A97AA", "#E3E9F1"
NAVY, BLUE, SKY, PALE, GRAY = "#0B2545", "#1F5FAD", "#5B9BE0", "#B9D3F2", "#9AA5B4"
NAMES = dict(safety="Safety", focus="Focus", math="Math", bff="BFF", factuality="Factuality")
KIND = dict(safety="recognize", focus="recognize", math="solve", bff="solve", factuality="recognize · held out")


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def t(x, y, s, size=12, color=MUTED, anchor="start", weight=400):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{color}" text-anchor="{anchor}" '
            f'font-weight="{weight}">{esc(s)}</text>')


def legend(items, x, y):
    out, cx = [], x
    for name, col in items:
        out.append(f'<rect x="{cx}" y="{y - 9}" width="12" height="12" rx="2" fill="{col}"/>')
        out.append(t(cx + 18, y + 1, name, 12, INK))
        cx += 26 + 7.2 * len(name)
    return "".join(out)


def grouped_bars(cats, series, lo, hi, ticks, fmt, title_y="", h=300, w=680, value_labels=True):
    """Vertical grouped bars from a baseline lo (axis does not start at 0: labelled)."""
    L, Rr, T, B = 52, 12, 36, 48
    pw, ph = w - L - Rr, h - T - B
    y = lambda v: T + ph * (1 - (v - lo) / (hi - lo))
    out = [legend([(n, c) for n, c, _ in series], L, 16)]
    for tk in ticks:
        out.append(f'<line x1="{L}" x2="{w - Rr}" y1="{y(tk):.1f}" y2="{y(tk):.1f}" stroke="{GRID}" stroke-width="1"/>')
        out.append(t(L - 8, y(tk) + 4, fmt(tk), 11, FAINT, "end"))
    gw = pw / len(cats)
    bw = min(26, (gw - 18) / len(series) - 2)
    for i, c in enumerate(cats):
        gx = L + gw * i + (gw - (bw + 2) * len(series)) / 2
        for j, (n, col, vals) in enumerate(series):
            v = vals[i]
            x0 = gx + j * (bw + 2)
            top = y(max(min(v, hi), lo))
            out.append(f'<rect x="{x0:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{y(lo) - top:.1f}" rx="3" fill="{col}">'
                       f'<title>{esc(n)} · {esc(NAMES.get(c, c))}: {fmt(v)}</title></rect>')
            if value_labels:
                out.append(t(x0 + bw / 2, top - 4, fmt(v), 10, INK, "middle"))
        out.append(t(L + gw * i + gw / 2, h - B + 18, NAMES.get(c, c), 12, INK, "middle", 500))
        out.append(t(L + gw * i + gw / 2, h - B + 33, KIND.get(c, ""), 11, FAINT, "middle"))
    out.append(f'<line x1="{L}" x2="{w - Rr}" y1="{y(lo):.1f}" y2="{y(lo):.1f}" stroke="{FAINT}" stroke-width="1"/>')
    return f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title_y)}">{"".join(out)}</svg>'


def label_panel(b, w=330, h=190):
    """Probe AUROC vs number of gold labels (logistic probe), gut as a dashed line."""
    L, Rr, T, B = 40, 14, 26, 30
    pw, ph = w - L - Rr, h - T - B
    lo, hi = 0.70, 1.0
    ks = ["25", "50", "100", "200", "all"]
    vals = [S5[b]["probes"]["good"]["logreg"][k][0] for k in ks]
    gut = S5[b]["trust"]["good"]
    x = lambda i: L + pw * i / (len(ks) - 1)
    y = lambda v: T + ph * (1 - (v - lo) / (hi - lo))
    out = [t(L, 14, f"{NAMES[b]} · {KIND[b]}", 12, INK, "start", 500)]
    for tk in (0.7, 0.8, 0.9, 1.0):
        out.append(f'<line x1="{L}" x2="{w - Rr}" y1="{y(tk):.1f}" y2="{y(tk):.1f}" stroke="{GRID}"/>')
        out.append(t(L - 6, y(tk) + 4, f"{tk:.1f}", 10, FAINT, "end"))
    for i, k in enumerate(ks):
        out.append(t(x(i), h - 10, k, 10, FAINT, "middle"))
    out.append(f'<line x1="{L}" x2="{w - Rr}" y1="{y(gut):.1f}" y2="{y(gut):.1f}" stroke="{GRAY}" stroke-width="2" '
               f'stroke-dasharray="5 4"/>')
    gy = y(gut) + 14 if vals[0] > gut else y(gut) - 6     # put the label on the side away from the first point
    out.append(t(L + 4, gy, f"gut {gut:.2f}", 10, MUTED, "start"))
    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vals))
    out.append(f'<polyline points="{pts}" fill="none" stroke="{BLUE}" stroke-width="2.5" stroke-linejoin="round"/>')
    for i, v in enumerate(vals):
        out.append(f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="4" fill="{BLUE}" stroke="#fff" stroke-width="1.5">'
                   f'<title>{ks[i]} labels: {v:.3f}</title></circle>')
    out.append(t(x(4), y(vals[-1]) - 9, f"{vals[-1]:.2f}", 10, INK, "middle"))
    return f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{NAMES[b]} label efficiency">{"".join(out)}</svg>'


def token_chart(w=680, h=290):
    costs = S8["costs"]
    avg = S8["results"]["average"]
    lines = [("Cascade v2 (1,024 tokens)", BLUE, avg["v2@1024"], ""),
             ("Cascade v2 + staged thinking", SKY, avg["v2+staged"], "6 4"),
             ("Gut → think (standard)", GRAY, avg["gut->think@1024"], ""),
             ("Gut → think, 2,048 tokens", GRAY, avg["gut->think@2048"], "3 3")]
    L, Rr, T, B = 52, 20, 56, 40
    pw, ph = w - L - Rr, h - T - B
    lo, hi = 0.74, 0.81
    x = lambda c: L + pw * (c - costs[0]) / (costs[-1] - costs[0])
    y = lambda v: T + ph * (1 - (v - lo) / (hi - lo))
    out = []
    for i, (n, col, _, dash) in enumerate(lines):      # 2 x 2 legend
        lx, ly = L + (i % 2) * 300, 14 + (i // 2) * 18
        out.append(f'<line x1="{lx}" x2="{lx + 22}" y1="{ly}" y2="{ly}" stroke="{col}" stroke-width="2.5" '
                   f'stroke-dasharray="{dash}"/>')
        out.append(t(lx + 28, ly + 4, n, 11, INK))
    for tk in (0.74, 0.76, 0.78, 0.80):
        out.append(f'<line x1="{L}" x2="{w - Rr}" y1="{y(tk):.1f}" y2="{y(tk):.1f}" stroke="{GRID}"/>')
        out.append(t(L - 8, y(tk) + 4, f"{tk:.2f}", 11, FAINT, "end"))
    for c in costs:
        out.append(t(x(c), h - B + 18, f"{c}", 11, FAINT, "middle"))
    out.append(t(L + pw / 2, h - 6, "Average thinking tokens per item", 11, MUTED, "middle"))
    for n, col, vals, dash in lines:
        pts = " ".join(f"{x(c):.1f},{y(v):.1f}" for c, v in zip(costs, vals))
        out.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.5" stroke-dasharray="{dash}"/>')
        for c, v in zip(costs, vals):
            out.append(f'<circle cx="{x(c):.1f}" cy="{y(v):.1f}" r="3.5" fill="{col}"><title>{esc(n)}, {c} tokens: '
                       f'{v:.3f}</title></circle>')
    return f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Accuracy versus thinking tokens">{"".join(out)}</svg>'


def stack_bars(w=680, h=200):
    """Where items end in the cascade (20% thinking)."""
    L, T = 110, 30
    rows = list(NAMES)
    bh, gap = 22, 10
    pw = w - L - 20
    cols = [("Trust (gut)", GRAY), ("Read (probe)", BLUE), ("Think", NAVY)]
    out = [legend(cols, L, 14)]
    for i, b in enumerate(rows):
        s = S7[b]["0.2"]["cascade_maxconf"]["steps"]
        yy = T + i * (bh + gap)
        out.append(t(L - 10, yy + 15, NAMES[b], 12, INK, "end", 500))
        x0 = L
        for (n, col), v in zip(cols, (s["gut"], s["read"], s["think"])):
            wv = pw * v
            out.append(f'<rect x="{x0:.1f}" y="{yy}" width="{max(wv - 2, 0):.1f}" height="{bh}" rx="3" fill="{col}">'
                       f'<title>{NAMES[b]} · {n}: {v:.0%}</title></rect>')
            if wv > 34:
                out.append(t(x0 + wv / 2 - 1, yy + 15, f"{v:.0%}", 11, "#fff" if col != GRAY else INK, "middle", 500))
            x0 += wv
    return f'<svg viewBox="0 0 {w} {T + len(rows) * (bh + gap) + 6}" role="img" aria-label="Where items end">' \
           f'{"".join(out)}</svg>'


def policy_svg():
    box = lambda x, y, w, h, fill, stroke, title, sub, tc=INK, sc=MUTED: (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}"/>'
        + t(x + w / 2, y + (h / 2 - 3 if sub else h / 2 + 5), title, 14, tc, "middle", 500)
        + (t(x + w / 2, y + h / 2 + 14, sub, 12, sc, "middle") if sub else ""))
    arr = lambda x1, y1, x2, y2: (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{FAINT}" stroke-width="1.5" '
                                  f'marker-end="url(#ah)"/>')
    o = ['<defs><marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" '
         f'orient="auto-start-reverse"><path d="M2 1L8 5L2 9" fill="none" stroke="{FAINT}" stroke-width="1.5"/>'
         '</marker></defs>']
    o.append(box(250, 10, 180, 40, "#F4F7FB", "#C9D5E4", "New item", ""))
    o.append(arr(340, 50, 340, 74))
    o.append(f'<rect x="150" y="76" width="380" height="118" rx="12" fill="#EEF4FC" stroke="{PALE}"/>')
    o.append(t(340, 98, "One forward pass, thinking off (free)", 13, NAVY, "middle", 500))
    o.append(box(170, 112, 160, 64, "#fff", PALE, "Probe", "calibrated verdict"))
    o.append(box(350, 112, 160, 64, "#fff", "#C9D5E4", "Gut", "optional fallback"))
    o.append(arr(340, 194, 340, 218))
    o.append(box(190, 220, 300, 56, "#fff", "#C9D5E4", "Rank all items by confidence", "Among the surest 80%?"))
    o.append(arr(490, 248, 548, 248))
    o.append(t(519, 240, "yes", 11, MUTED, "middle"))
    o.append(box(550, 220, 120, 56, BLUE, BLUE, "Done", "Read (or Trust)", "#fff", "#DCE9FA"))
    o.append(arr(340, 276, 340, 300))
    o.append(t(350, 292, "no", 11, MUTED))
    o.append(box(190, 302, 300, 56, NAVY, NAVY, "Think (1,024 tokens)", "least confident 20%, all tasks pooled", "#fff",
                 "#C9D7EA"))
    o.append(t(10, 30, "Setup, once per benchmark:", 11, MUTED))
    o.append(t(10, 46, "train the probe on", 11, MUTED))
    o.append(t(10, 62, "~100 labelled items,", 11, MUTED))
    o.append(t(10, 78, "and calibrate the gut", 11, MUTED))
    return f'<svg viewBox="0 0 680 370" role="img" aria-label="Cascade policy">{"".join(o)}</svg>'


def pct(x):
    return f"{x * 100:+.1f}"


# ---------------------------------------------------------------- data for charts
B4 = ["safety", "focus", "math", "bff"]
best_think = [max(S2[b]["auc"][f"think_{k}"] for k in (512, 1024, 2048, 4096)) for b in B4]
chart_reads = grouped_bars(B4, [("Trust · gut", GRAY, [S2[b]["auc"]["trust"] for b in B4]),
                                ("Read · probe", BLUE, [S2[b]["auc"]["read"] for b in B4]),
                                ("Think · best budget", NAVY, best_think)],
                           0.70, 1.0, (0.7, 0.8, 0.9, 1.0), lambda v: f"{v:.2f}", "Which read wins where")
B5 = ["safety", "focus", "math", "bff", "factuality"]
chart_policy = grouped_bars(B5, [("Cascade", BLUE, [CI[b]["acc"]["cascade_cal"] for b in B5]),
                                 ("Gut → think", GRAY, [CI[b]["acc"]["gut_think"] for b in B5]),
                                 ("Router → think (Think When Needed)", PALE, [CI[b]["acc"]["router_think"] for b in B5])],
                            0.65, 0.90, (0.65, 0.70, 0.75, 0.80, 0.85, 0.90), lambda v: f"{v:.2f}",
                            "Cascade accuracy", h=310)
panels = "".join(f'<div class="panel">{label_panel(b)}</div>' for b in B4)

ci_rows = []
for b in B5 + ["all"]:
    c = CI[b]
    cell = lambda p: (f'<td class="num">{pct(c["cascade_cal_minus"][p]["d"])}<span class="ci"> '
                      f'[{pct(c["cascade_cal_minus"][p]["ci"][0])}, {pct(c["cascade_cal_minus"][p]["ci"][1])}]</span></td>')
    name = "All five (mean)" if b == "all" else NAMES[b]
    ci_rows.append(f'<tr{" class=\"total\"" if b == "all" else ""}><th>{name}</th>'
                   f'<td class="num">{c["acc"]["cascade_cal"]:.3f}</td>{cell("gut_think")}{cell("router_think")}'
                   f'{cell("probe_think")}{cell("think")}</tr>')

JN = {"qwen3.5-4b": ("Qwen3.5-4B", "Alibaba · 4B"), "gpt-oss-20b": ("gpt-oss-20b", "OpenAI · 21B MoE"),
      "nvidia-nemotron-nano-9b-v2": ("Nemotron Nano 9B", "NVIDIA · Mamba hybrid")}
NAMES.update({j: v[0] for j, v in JN.items()})
KIND.update({j: v[1] for j, v in JN.items()})
chart_judges = grouped_bars(JUDGES3, [("Cascade 20%", BLUE, [CI3[j]["all"]["acc"]["cascade_cal"] for j in JUDGES3]),
                                      ("Gut → think 20%", GRAY, [CI3[j]["all"]["acc"]["gut_think"] for j in JUDGES3]),
                                      ("Probe → think 20%", SKY, [CI3[j]["all"]["acc"]["probe_think"] for j in JUDGES3]),
                                      ("Think on all · 100%", NAVY, [CI3[j]["all"]["acc"]["think"] for j in JUDGES3])],
                            0.65, 0.85, (0.65, 0.70, 0.75, 0.80, 0.85), lambda v: f"{v:.2f}", "Cascade across judges",
                            h=300)
judge_bench = "".join(
    f'<figure><h3>{JN[j][0]} <span class="meta">· {JN[j][1]}</span></h3>'
    + grouped_bars(B5, [("Cascade", BLUE, [CI3[j][b]["acc"]["cascade_cal"] for b in B5]),
                        ("Probe → think", SKY, [CI3[j][b]["acc"]["probe_think"] for b in B5]),
                        ("Gut → think", GRAY, [CI3[j][b]["acc"]["gut_think"] for b in B5]),
                        ("Think on all · 100%", NAVY, [CI3[j][b]["acc"]["think"] for b in B5])],
                   0.55, 0.95, (0.55, 0.65, 0.75, 0.85, 0.95), lambda v: f"{v:.2f}", f"{JN[j][0]} by benchmark", h=300)
    + "</figure>" for j in JUDGES3)
chart_budget = grouped_bars(JUDGES3, [
    ("Uniform 20%", GRAY, [BUD[j]["all"]["acc"]["uniform"] for j in JUDGES3]),
    ("Pooled 20%", BLUE, [BUD[j]["all"]["acc"]["pooled_conf"] for j in JUDGES3]),
    ("Known format 20%", SKY, [BUD[j]["all"]["acc"]["format_known"] for j in JUDGES3]),
    ("Think on all · 100%", NAVY, [CI3[j]["all"]["acc"]["think"] for j in JUDGES3])],
    0.70, 0.86, (0.70, 0.74, 0.78, 0.82, 0.86), lambda v: f"{v:.2f}", "Budget allocation", h=300)
bud_rows = []
for j in JUDGES3:
    m = BUD[j]["all"]["minus_uniform"]["pooled_conf"]
    bm = BUD[j]["math"]
    bud_rows.append(f'<tr><th>{JN[j][0]}</th><td class="num">{BUD[j]["all"]["acc"]["pooled_conf"]:.3f}</td>'
                    f'<td class="num">{pct(m["d"])}<span class="ci"> [{pct(m["ci"][0])}, {pct(m["ci"][1])}]</span></td>'
                    f'<td class="num">{bm["acc"]["uniform"]:.3f} → {bm["acc"]["pooled_conf"]:.3f} '
                    f'<span class="ci">({pct(bm["minus_uniform"]["pooled_conf"]["d"])} '
                    f'[{pct(bm["minus_uniform"]["pooled_conf"]["ci"][0])}, {pct(bm["minus_uniform"]["pooled_conf"]["ci"][1])}])</span></td>'
                    f'<td class="num">{CI3[j]["math"]["acc"]["think"]:.3f}</td>'
                    f'<td class="num">{bm["think_share"]["pooled_conf"]:.0%}</td></tr>')
judge_rows = []
for j in JUDGES3:
    m = CI3[j]["all"]["cascade_cal_minus"]
    c = lambda p: (f'<td class="num">{pct(m[p]["d"])}<span class="ci"> [{pct(m[p]["ci"][0])}, '
                   f'{pct(m[p]["ci"][1])}]</span></td>')
    judge_rows.append(f'<tr><th>{JN[j][0]}</th><td class="num">{CI3[j]["all"]["acc"]["cascade_cal"]:.3f}</td>'
                      f'{c("gut_think")}{c("router_think")}{c("probe_think")}{c("think")}</tr>')
win_rows = []
for j in JUDGES3:
    cells = []
    for b in ["safety", "focus", "math", "bff"]:
        a = S2J[j][b]["auc"]
        bt = max(a[f"think_{k}"] for k in (512, 1024, 2048, 4096))
        opts = {"Gut": a["trust"], "Read": a["read"], "Think": bt}
        w = max(opts, key=opts.get)
        cells.append(f'<td><span class="pill {w.lower()}">{w}</span> <span class="num">{opts[w]:.2f}</span></td>')
    win_rows.append(f'<tr><th>{JN[j][0]}</th>{"".join(cells)}</tr>')


def jury_chart(w=680):
    rows = [("Dynamic jury", "dynamic jury", 0.2, True), ("Cascade jury", "cascade jury", 0.2, True),
            ("Free majority (gut or probe)", "free majority", 0.0, False),
            ("Think majority", "think majority", 1.0, False),
            ("Best single judge (cascade)", "best single judge (cascade)", 0.2, False),
            ("Agreement jury (Isaac)", "agreement jury (Isaac)", 1.0, False),
            ("Gut → think jury", "gut->think jury", 0.2, False), ("Gut majority", "gut majority", 0.0, False)]
    acc = JURY["benches"]["all"]["acc"]
    L, Rr, T, bh, gap = 220, 70, 8, 24, 10
    lo, hi = 0.70, 0.86
    pw = w - L - Rr
    x = lambda v: L + pw * (v - lo) / (hi - lo)
    out = []
    for tk in (0.70, 0.75, 0.80, 0.85):
        out.append(f'<line x1="{x(tk):.1f}" x2="{x(tk):.1f}" y1="{T}" y2="{T + len(rows) * (bh + gap)}" stroke="{GRID}"/>')
        out.append(t(x(tk), T + len(rows) * (bh + gap) + 14, f"{tk:.2f}", 11, FAINT, "middle"))
    for i, (lab, key, cost, hl) in enumerate(rows):
        yy = T + i * (bh + gap)
        v = acc[key]
        out.append(t(L - 10, yy + 16, lab, 12, INK, "end", 500 if hl else 400))
        out.append(f'<rect x="{L}" y="{yy}" width="{x(v) - L:.1f}" height="{bh}" rx="3" fill="{BLUE if hl else GRAY}">'
                   f'<title>{esc(lab)}: {v:.3f}, thinks on {cost:.0%} of judge calls</title></rect>')
        out.append(t(x(v) + 6, yy + 16, f"{v:.3f}", 11, INK))
        out.append(t(w - 4, yy + 16, f"think {cost:.0%}", 11, MUTED, "end"))
    h = T + len(rows) * (bh + gap) + 24
    return f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Jury accuracy">{"".join(out)}</svg>'


jm = JURY["benches"]["all"]["dynamic_minus"]
jury_rows = []
for key, lab in (("think majority", "Think majority (5× cost)"), ("agreement jury (Isaac)", "Agreement jury (Isaac, 5× cost)"),
                 ("gut->think jury", "Gut → think jury"), ("best single judge (cascade)", "Best single judge"),
                 ("free majority", "Free majority (no thinking)")):
    jury_rows.append(f'<tr><th>{lab}</th><td class="num">{pct(jm[key]["d"])}<span class="ci"> '
                     f'[{pct(jm[key]["ci"][0])}, {pct(jm[key]["ci"][1])}]</span></td></tr>')
jb = JURY["benches"]
jury_bench_rows = "".join(
    f'<tr><th>{NAMES[b]}</th>' + "".join(f'<td class="num">{jb[b]["acc"][k]:.3f}</td>'
                                          for k in ("dynamic jury", "think majority", "agreement jury (Isaac)",
                                                    "gut->think jury", "gut majority")) + "</tr>" for b in B5)

STEPS = [
    ("0", "Pilot", "Can a small judge think without looping?",
     f"Qwen3.5-0.8B loops on 78–98% of items. Switched to Qwen3.5-4B with a thinking budget (forced verdict at 512 / "
     f"1,024 / 2,048 / 4,096 tokens)."),
    ("1", "Three reads", "Record the gut verdict, hidden state and thinking verdict for every item.",
     "1,359 items on Safety, Focus, Math and BFF. Saved once, so every later step runs on a laptop."),
    ("2", "Which read wins", "Compare Trust, Read and Think on each benchmark.",
     "Read wins on recognize tasks (Safety 0.95, Focus 0.97). Think wins on solve tasks (Math 0.93). A probe trained "
     "on other benchmarks does not transfer."),
    ("3", "Free routing signals", "Does anything free predict where thinking changes the answer?",
     "Gut uncertainty does (AUROC 0.70–0.86). The probe adds nothing to it."),
    ("4", "Read without labels", "Train the probe on the model's own confident or agreed answers.",
     "Fails: self-made labels copy the gut's mistakes."),
    ("–", "Literature", "Read 10 probing papers and their code.",
     "All train probes on gold labels; none measures how few labels a judge probe needs."),
    ("5", "Literature probes", "Six published probes × 25 to all labels, with a length control.",
     "25–50 labels already beat the gut on recognize tasks, and the gain survives the length control. "
     "No probe helps on Math."),
    ("6", "Held-out benchmark", "Run everything on RewardBench 2 Factuality, unseen until now.",
     "Read with 50 labels beats the gut and thinking (AUROC 0.90 vs 0.86). A per-benchmark read-or-think test is too noisy."),
    ("7", "Cascade", "Route each item: gut, probe, or think.",
     "Sequential gut → probe failed on Math. Cascade v2 (more confident of gut/probe, think on the rest) wins overall."),
    ("8", "Staged / longer thinking", "Peek 512 tokens before a full think; give thinkers 2,048 tokens.",
     "No gain at equal token cost. Kept the simple cascade."),
    ("9", "Confidence intervals", "Paired bootstrap over questions for every comparison.",
     "The cascade's gain over gut → think holds on average (CI above 0)."),
    ("10", "Two more judges", "Repeat everything with gpt-oss-20b (OpenAI) and Nemotron Nano 9B (NVIDIA).",
     "Same split: Read wins on recognize tasks for all three. Their gut verdicts are overconfident, which broke cascade v2."),
    ("11", "Calibrated cascade", "Calibrate the gut on the same labelled items before comparing confidences.",
     "Fixes it: the cascade now beats gut → think for every judge (+3 to +11 points)."),
    ("12", "The jury", "Three judges, each with three reads, voting.",
     "A dynamic jury that thinks only on the 20% of items where the jury is least sure beats thinking on everything."),
    ("13", "Task-format probe", "Predict recognize vs solve from the hidden state, on a benchmark it never saw.",
     "Spots recognize tasks almost perfectly but misses Math. Routing on format adds at most ~1 point."),
    ("14", "Pool the thinking budget", "Think on the least confident 20% of all items, not 20% per benchmark.",
     "Thinking moves to Math by itself (~40% of Math items). +0.8 to +1.7 points for every judge; Math gap about half closed."),
]
steps_html = "".join(f'<li><span class="sn">{n}</span><div><b>{esc(a)}</b><p class="q">{esc(q)}</p>'
                     f'<p>{esc(r)}</p></div></li>' for n, a, q, r in STEPS)

allc = CI["all"]["cascade_cal_minus"]
html = f"""<title>Trust, Read, Think</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: one reading column; charts sit full column width, small multiples in a 2-up grid */
:root {{
  --bg: #FFFFFF; --ink: {INK}; --muted: {MUTED}; --rule: {GRID}; --wash: #F3F7FC;
  --blue: {BLUE}; --navy: {NAVY}; --pale: {PALE};
  --sans: "IBM Plex Sans", "Helvetica Neue", Arial, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
  color-scheme: light;
}}
body {{ background: var(--bg); color: var(--ink); font-family: var(--sans); font-size: 15.5px; line-height: 1.6; }}
.wrap {{ max-width: 860px; margin: 0 auto; padding-block: 40px 64px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }}
header {{ border-bottom: 2px solid var(--navy); padding-bottom: 20px; margin-bottom: 28px; }}
.eyebrow {{ font: 500 12px/1 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--blue); }}
h1 {{ font-size: 34px; line-height: 1.15; margin: 10px 0 10px; color: var(--navy); font-weight: 600; text-wrap: balance; }}
h2 {{ font-size: 21px; margin: 44px 0 6px; color: var(--navy); font-weight: 600; text-wrap: balance; }}
h3 {{ font-size: 15px; margin: 22px 0 4px; font-weight: 600; }}
p {{ margin: 8px 0; max-width: 68ch; }}
.lede {{ font-size: 17px; color: var(--ink); }}
.meta {{ color: var(--muted); font-size: 13px; }}
.bottom {{ background: var(--wash); border: 1px solid var(--pale); border-radius: 10px; padding: 18px 20px; margin: 22px 0; }}
.bottom p {{ margin: 6px 0; }}
.tiles {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 18px 0 4px; }}
.tile {{ border: 1px solid var(--rule); border-radius: 10px; padding: 14px 16px; }}
.tile .v {{ font: 600 26px/1.1 var(--sans); color: var(--navy); font-variant-numeric: tabular-nums; }}
.tile .l {{ font-size: 13px; color: var(--muted); margin-top: 4px; }}
.reads {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 14px 0; }}
.read {{ border-top: 3px solid var(--c); padding: 10px 2px 0; }}
.read b {{ display: block; font-size: 15px; }}
.pill {{ display: inline-block; font: 500 11px/1 var(--mono); padding: 4px 7px; border-radius: 999px; }}
.pill.read {{ background: var(--blue); color: #fff; }} .pill.think {{ background: var(--navy); color: #fff; }}
.pill.gut {{ background: #E3E7EE; color: var(--ink); }}
.read span {{ font-size: 13.5px; color: var(--muted); }}
figure {{ margin: 18px 0 8px; }}
figure svg {{ width: 100%; height: auto; display: block; font-family: var(--sans); }}
figcaption {{ font-size: 13px; color: var(--muted); margin-top: 6px; max-width: 70ch; }}
.grid2 {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 18px; }}
ol.steps {{ list-style: none; padding: 0; margin: 14px 0; display: grid; gap: 2px; }}
ol.steps li {{ display: grid; grid-template-columns: 34px minmax(0, 1fr); gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--rule); }}
ol.steps .sn {{ font: 500 13px/24px var(--mono); color: #fff; background: var(--blue); border-radius: 6px; text-align: center; height: 24px; }}
ol.steps p {{ margin: 2px 0; font-size: 14.5px; }}
ol.steps p.q {{ color: var(--muted); }}
.tablewrap {{ overflow-x: auto; margin: 14px 0; }}
table {{ border-collapse: collapse; width: 100%; font-size: 14px; min-width: 620px; }}
th, td {{ padding: 8px 10px; border-bottom: 1px solid var(--rule); text-align: left; }}
thead th {{ font-size: 12px; color: var(--muted); font-weight: 500; text-transform: uppercase; letter-spacing: .05em; }}
td.num {{ font-variant-numeric: tabular-nums; font-family: var(--mono); font-size: 13px; white-space: nowrap; }}
.ci {{ color: var(--muted); }}
tr.total th, tr.total td {{ border-top: 2px solid var(--navy); font-weight: 600; }}
ul.plain {{ padding-left: 18px; margin: 8px 0; }} ul.plain li {{ margin: 4px 0; max-width: 68ch; }}
code {{ font-family: var(--mono); font-size: 13px; }}
@media (max-width: 640px) {{ .tiles, .reads, .grid2 {{ grid-template-columns: minmax(0, 1fr); }} h1 {{ font-size: 27px; }} }}
</style>
<div class="wrap">
<header>
  <div class="eyebrow">Dynamic LLM juries · weight-space follow-up</div>
  <h1>Trust, Read, Think: when should an AI judge stop and think?</h1>
  <p class="lede">A judge can answer on gut, we can read its hidden state with a probe, or it can reason first.
  We tested which works where, and built a cascade that picks per item.</p>
  <p class="meta">Judges: Qwen3.5-4B, gpt-oss-20b, Nemotron Nano 9B · 5 benchmarks, 1,659 graded responses · Nov 2026</p>
</header>

<div class="bottom">
  <p><b>Bottom line.</b> The best read depends on the task. On <b>recognize</b> tasks (is this response safe, on topic,
  factual?) a probe on the hidden state beats both the gut and thinking, with no thinking cost, after only ~50–100 labels.
  On <b>solve</b> tasks (is this math or finance answer right?) only thinking helps.</p>
  <p><b>The method:</b> train a probe on ~100 labelled items, use its verdict, and think only on the 20% of items
  where it is least sure, ranked across all tasks together. For all three judges this beats thinking on every item
  at a fifth of the cost (gpt-oss: <b>{BUD["gpt-oss-20b"]["all"]["acc"]["pooled_conf"]:.3f}</b> vs
  {CI3["gpt-oss-20b"]["all"]["acc"]["think"]:.3f}), and it sends thinking to math by itself.</p>
  <p>Earlier version: a cascade that calibrates gut and probe and thinks on 20% of each benchmark beats the standard
  gut → think escalation for all three judges
  (<b>+{CI3["qwen3.5-4b"]["all"]["cascade_cal_minus"]["gut_think"]["d"] * 100:.1f}</b>,
  <b>+{CI3["gpt-oss-20b"]["all"]["cascade_cal_minus"]["gut_think"]["d"] * 100:.1f}</b> and
  <b>+{CI3["nvidia-nemotron-nano-9b-v2"]["all"]["cascade_cal_minus"]["gut_think"]["d"] * 100:.1f} points</b>), at the same cost.
  A jury of the three, thinking on 20% of items, reaches <b>{JURY["benches"]["all"]["acc"]["dynamic jury"]:.3f}</b>:
  at least as good as the best single judge and above a jury that thinks on everything ({JURY["benches"]["all"]["acc"]["think majority"]:.3f}).</p>
</div>

<div class="tiles">
  <div class="tile"><div class="v">{BUD["gpt-oss-20b"]["all"]["acc"]["pooled_conf"]:.3f}</div><div class="l">gpt-oss-20b: probe, thinking on the least confident 20% (mean of 5 benchmarks)</div></div>
  <div class="tile"><div class="v">{CI3["gpt-oss-20b"]["all"]["acc"]["think"]:.3f}</div><div class="l">gpt-oss-20b thinking on every item (5× the cost)</div></div>
  <div class="tile"><div class="v">{CI3["gpt-oss-20b"]["all"]["acc"]["gut_think"]:.3f}</div><div class="l">gpt-oss-20b standard gut → think, same cost</div></div>
</div>

<h2>The three reads</h2>
<p>All three come from the same judge. The first two come from one forward pass, so they cost the same; only Think costs tokens.</p>
<div class="reads">
  <div class="read" style="--c:{GRAY}"><b>Trust</b><span>The gut verdict: thinking off, the next word after “VERDICT:”.</span></div>
  <div class="read" style="--c:{BLUE}"><b>Read</b><span>A linear probe on the hidden state at that same word. Needs labels to train.</span></div>
  <div class="read" style="--c:{NAVY}"><b>Think</b><span>Reason first (up to 1,024 tokens), then give the verdict.</span></div>
</div>
<p class="meta">Why Read: in the earlier weight-space study the 0.8B judge “knew” the right answer inside (probe 0.95) but
said it at chance (0.51), and editing the weights to fix that was blunt. Here we read the knowledge instead of editing it.</p>

<h2>What we did, step by step</h2>
<ol class="steps">{steps_html}</ol>

<h2>1 · The best read depends on the task</h2>
<figure>{chart_reads}
<figcaption>Same-source AUROC (0.5 = chance; axis starts at 0.70). Read: probe trained on gold labels, cross-fitted.
Think: best of 4 budgets. Recognize tasks: the probe wins. Solve tasks: only thinking helps.</figcaption></figure>

<h2>2 · A few labels are enough on recognize tasks</h2>
<div class="grid2">{panels}</div>
<figcaption>Probe AUROC by number of gold labels (logistic probe, mean of 3 draws); dashed line = gut.
On Safety and Focus, 25–50 labels already beat the gut. On Math no amount of labels does.
With length and formatting cues removed, the probe keeps most of its gain (Safety 0.92, Focus 0.94).
Probes trained without labels (on the model's own answers) fail: they copy the gut's mistakes.</figcaption>

<h2>3 · The cascade</h2>
<figure>{policy_svg()}
<figcaption>The probe comes from the same free pass as the gut and is calibrated on ~100 labelled items per
benchmark, so its confidence means the same thing on every task. All items are ranked together and the least confident
20% go to Think. The probe is unsure on math, so math gets most of the thinking (section 7). Adding the calibrated gut
(use whichever is more confident) changes little on average: it helps on math and costs 1–2 points on recognize tasks
(sections 4–5).</figcaption></figure>

<h2>4 · Results at equal cost</h2>
<figure>{chart_policy}
<figcaption>Qwen3.5-4B. Accuracy on held-out items, thinking on 20% of items for every policy (axis starts at 0.65).
Router → think follows Think When Needed (arXiv 2601.18146): a learned regressor of when thinking helps.</figcaption></figure>
<div class="tablewrap"><table>
<thead><tr><th>Benchmark</th><th>Cascade acc.</th><th>vs gut → think</th><th>vs router → think</th><th>vs probe → think</th><th>vs think on all</th></tr></thead>
<tbody>{"".join(ci_rows)}</tbody></table></div>
<p class="meta">Points of accuracy, cascade minus each policy, with 95% CIs from 2,000 paired bootstrap resamples of
questions (10 label draws). Think on all uses 5× the thinking tokens.</p>
<ul class="plain">
  <li>The cascade beats gut → think and the learned router on average, and thinking on everything at a fifth of the cost.</li>
  <li>It ties probe → think on average: the probe carries most of the gain; the gut and thinking cover solve tasks.</li>
</ul>

<h3>More or staged thinking does not help</h3>
<figure>{token_chart()}
<figcaption>Qwen3.5-4B, cascade v2. Mean accuracy over the 5 benchmarks by thinking tokens spent per item. Staged thinking (a 512-token peek,
then 2,048 only if needed) and longer budgets add at most half a point. On recognize tasks, more thinking lowers accuracy.</figcaption></figure>

<h2>5 · It holds for other judges</h2>
<p>We repeated every step with two judges from other families: gpt-oss-20b (OpenAI, mixture of experts) and
Nemotron Nano 9B (NVIDIA, Mamba–Transformer hybrid).</p>
<div class="tablewrap"><table>
<thead><tr><th>Best read (AUROC)</th><th>Safety · recognize</th><th>Focus · recognize</th><th>Math · solve</th><th>BFF · solve</th></tr></thead>
<tbody>{"".join(win_rows)}</tbody></table></div>
<p class="meta">Read wins on recognize tasks for every judge. On solve tasks thinking wins, except for Nemotron, which
thinks only briefly (median 160–300 tokens) and gains little from it.</p>
<figure>{chart_judges}
<figcaption>Mean accuracy over the 5 benchmarks (axis starts at 0.65). Cascade, gut → think and probe → think think on 20%
of items; think on all thinks on every item.</figcaption></figure>
<div class="tablewrap"><table>
<thead><tr><th>Judge</th><th>Cascade acc.</th><th>vs gut → think</th><th>vs router → think</th><th>vs probe → think</th><th>vs think on all</th></tr></thead>
<tbody>{"".join(judge_rows)}</tbody></table></div>
<p class="meta">Points of accuracy, cascade minus each policy, 95% paired bootstrap CIs, mean of 5 benchmarks.
The cascade ties probe → think on average: the probe carries the gain; the gut helps on Math and costs 1–2 points on
Focus and Factuality.</p>
<h3>By benchmark</h3>
<p class="meta">Accuracy on held-out items (axis starts at 0.55). Cascade, probe → think and gut → think think on 20% of
items; think on all thinks on every item.</p>
{judge_bench}

<h2>6 · The jury</h2>
<p>Each of the three judges gives a calibrated free verdict (gut or probe, whichever is more confident). The
<b>dynamic jury</b> sums the judges' confidence and sends only the 20% of items where the jury is least sure to
thinking, for every judge. Other juries are shown for comparison.</p>
<figure>{jury_chart()}
<figcaption>Mean accuracy over the 5 benchmarks; right column = share of judge calls that think. Cascade jury: each judge
runs its own cascade, then a majority vote.</figcaption></figure>
<div class="grid2">
<div class="tablewrap"><table style="min-width:0">
<thead><tr><th>Dynamic jury vs</th><th>Points [95% CI]</th></tr></thead>
<tbody>{"".join(jury_rows)}</tbody></table></div>
<div class="tablewrap"><table style="min-width:0">
<thead><tr><th>Benchmark</th><th>Dynamic</th><th>Think maj.</th><th>Agree.</th><th>Gut→think</th><th>Gut maj.</th></tr></thead>
<tbody>{jury_bench_rows}</tbody></table></div>
</div>
<ul class="plain">
  <li>The dynamic jury beats thinking on everything on average while thinking on a fifth of the items.</li>
  <li>On recognize tasks it wins clearly (Focus 0.85 vs 0.76); on Math, thinking on everything is still best (0.87 vs 0.80).</li>
  <li>Even with no thinking at all, the free majority (0.82) matches the jury that thinks on everything.</li>
</ul>

<h2>7 · Spend thinking where it helps</h2>
<div class="bottom">
  <p><b>What the pooled version does.</b> Put every item from every task in one pile, rank them by how unsure the
  probe is, and think only on the 20% it is least sure about. The probe is often unsure on math, so math gets most of
  the thinking; safety and focus barely get any, and do not need it. No one tells it which tasks are hard.</p>
</div>
<p>Before this, every benchmark got the same 20% of thinking, even though thinking hurts on recognize tasks and helps on
solve tasks.</p>
<figure>{chart_budget}
<figcaption>Probe → think, mean accuracy over the 5 benchmarks (axis starts at 0.70). Uniform, pooled and known format all
think on 20% of all items. Known format puts all thinking on Math and BFF (an upper bound: it needs the true task type).</figcaption></figure>
<div class="tablewrap"><table>
<thead><tr><th>Judge</th><th>Pooled acc.</th><th>vs uniform [95% CI]</th><th>Math: uniform → pooled [95% CI]</th><th>Math: think on all</th><th>Math items that think</th></tr></thead>
<tbody>{"".join(bud_rows)}</tbody></table></div>
<ul class="plain">
  <li>Pooling needs no task labels: the probe is unsure on math, so math gets ~40% of the thinking and recognize tasks 5–12%.</li>
  <li>Math improves significantly for every judge (+2.4 to +5.3 points) and no benchmark gets significantly worse.
  About half of the math gap closes (gpt-oss 0.75 → 0.80, against 0.88 thinking on everything), at no extra cost.</li>
  <li>A task-format probe (step 13) would route budget the same way but misses Math on held-out tests; knowing the true
  format adds only ~1 more point.</li>
</ul>

<h2>What did not work</h2>
<ul class="plain">
  <li><b>Read without labels.</b> Probes trained on the model's own confident or agreed answers learn its mistakes.</li>
  <li><b>One probe for all benchmarks.</b> Trained on three benchmarks, it scores below the gut on the fourth.</li>
  <li><b>Picking which Math items to think on.</b> Perfect routing would reach 0.86 at 16% thinking (Qwen); every
  per-item signal we tried (gut confidence, probes, a learned router, a short peek) stays near 0.76. Giving math more of
  the budget (section 7) helps more than picking items better.</li>
</ul>

<h2>What this adds</h2>
<ul class="plain">
  <li>A per-item gut / probe / think cascade for LLM judges, compared with escalation and a learned router at equal cost.
  Each piece exists in the literature; we found no paper combining them for judges.</li>
  <li>The task-format split: hidden states replace thinking on recognize tasks, not on solve tasks.</li>
  <li>The first label-efficiency curve for judge probes: ~50–100 labels per benchmark, and none is not enough.</li>
  <li>A dynamic jury that spends thinking only where the whole jury is unsure, across three model families.</li>
  <li>Pooling the thinking budget across tasks by probe confidence: it allocates thinking to solve-type tasks by itself.</li>
</ul>
<p class="meta">Closest prior work: probes on hidden states as judges (Representation-as-a-Judge, ICLR 2026; Calibrating
LLM Judges, 2512.22245), probe-based compute allocation across queries (Learning How Hard to Think, 2410.04707; DiffAdapt),
and confidence-based escalation (FrugalGPT; Think When Needed, 2601.18146; JEV-as-a-Judge, 2609.26550). The techniques are
known; what is new here is the evidence on judges: when reading beats thinking, how few labels it needs, and that
Read → Think with a pooled budget beats standard escalation for three model families.</p>
<p class="meta">Limits: 300–459 items per benchmark; three judges. The cascade rule was revised twice after seeing results
(v2 after Math, gut calibration after the new judges), so Factuality and the two new judges are the cleanest tests of
the first and second revisions respectively. Code and numbers: <code>experiments/trust_read_think/</code>
(steps 1–12; results per judge in results/&lt;judge&gt;/, the jury in results/jury/). Pooling assumes a judge sees a
mix of tasks to rank together.</p>
</div>
"""
(R / "trust_read_think.html").write_text(html)
print("wrote", R / "trust_read_think.html", len(html) // 1024, "KB")
