#!/usr/bin/env python3
"""Build results/module_map.html from results/module_map.json (light, blue, self-contained inline SVG)."""
import json
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
D = json.loads((HERE / "results" / "module_map.json").read_text())
S, F = D["safety"], D["bff"]
NH = D["nheads"]
BLUE, ORANGE = (31, 95, 191), (194, 85, 12)


def pct(x):
    return f"{x * 100:+.0f}%"


def name(r):
    return f"Layer {r['layer']} MLP" if r["kind"] == "mlp" else f"Layer {r['layer']} head {r['head']}"


def cell_color(share, cap=0.35):
    t = min(abs(share) / cap, 1) ** 0.8
    base = (241, 244, 248)
    c = BLUE if share > 0 else ORANGE
    return "rgb(%d,%d,%d)" % tuple(round(b + (cc - b) * t) for b, cc in zip(base, c))


# ----------------------------------------------------------------------------- heatmap
def heatmap(res):
    R = res["ref_layer"]
    rows = {(r["kind"], r["layer"], r["head"]): r for r in res["rows"]}
    cw, ch, x0, y0 = 32, 26, 112, 34
    mx = x0 + 16 * cw + 14
    W, H = mx + cw + 70, y0 + R * ch + 16
    s = [f'<svg class="chart heat" viewBox="0 0 {W} {H}" role="img" aria-label="Contribution of each attention head and MLP, layers 1 to {R}">']
    for h in range(16):
        s.append(f'<text x="{x0 + h * cw + cw / 2}" y="{y0 - 10}" text-anchor="middle" class="ax">{h + 1}</text>')
    s.append(f'<text x="{x0 + 8 * cw}" y="12" text-anchor="middle" class="axl">attention heads</text>')
    s.append(f'<text x="{mx + cw / 2}" y="{y0 - 10}" text-anchor="middle" class="axl">MLP</text>')
    for L in range(1, R + 1):
        y = y0 + (L - 1) * ch
        std = NH[L - 1] == 8
        s.append(f'<text x="{x0 - 10}" y="{y + ch / 2 + 4}" text-anchor="end" class="lab{" std" if std else ""}">Layer {L}{" ◆" if std else ""}</text>')
        for h in range(NH[L - 1]):
            r = rows[("head", L, h + 1)]
            s.append(cell(x0 + h * cw, y, cw, ch, r))
        s.append(cell(mx, y, cw, ch, rows[("mlp", L, None)]))
    s.append("</svg>")
    return "\n".join(s)


def cell(x, y, w, h, r):
    sh = r["share"]
    out = [f'<g><title>{name(r)}: {pct(sh)} of the push'
           f'{" (significant)" if r["sig"] else ""}; standalone readout {r["B"]:.2f}</title>',
           f'<rect x="{x + 1}" y="{y + 1}" width="{w - 2}" height="{h - 2}" rx="3" fill="{cell_color(sh)}"'
           f'{" stroke=\"#0B2A55\" stroke-width=\"2\"" if r["sig"] else ""}/>']
    if abs(sh) >= 0.08:
        dark = abs(sh) >= 0.2
        out.append(f'<text x="{x + w / 2}" y="{y + h / 2 + 4}" text-anchor="middle" class="cv"'
                   f' style="fill:{"#fff" if dark else "var(--ink)"}">{sh * 100:+.0f}</text>')
    out.append("</g>")
    return "".join(out)


# ----------------------------------------------------------------------------- top parts
def top_parts(res, k=10):
    rows = sorted(res["rows"], key=lambda r: -abs(r["contrib"]))
    rows = [r for r in rows if r["kind"] != "emb"][:k]
    thr = res["thr_share"]
    cap = 0.5
    x0, xm, x1, bh, gap, y0 = 150, 430, 630, 20, 10, 24
    sc = (x1 - xm) / cap
    H = y0 + len(rows) * (bh + gap) + 24
    s = [f'<svg class="chart" viewBox="0 0 680 {H}" role="img" aria-label="The ten parts with the largest push">']
    s.append(f'<rect x="{xm - thr * sc}" y="{y0 - 6}" width="{2 * thr * sc}" height="{H - y0 - 14}" fill="var(--line)" opacity=".7"/>')
    s.append(f'<line x1="{xm}" x2="{xm}" y1="{y0 - 8}" y2="{H - 18}" stroke="var(--ink-3)"/>')
    s.append(f'<text x="{xm - 8}" y="14" text-anchor="end" class="axl" style="fill:#9A4A12">← pushes toward the wrong answer</text>')
    s.append(f'<text x="{xm + 8}" y="14" class="axl" style="fill:var(--blue)">pushes toward the right answer →</text>')
    for i, r in enumerate(rows):
        y = y0 + i * (bh + gap)
        v = r["share"]
        w = abs(v) * sc
        x = xm if v > 0 else xm - w
        col = "var(--blue)" if v > 0 else "#C2550C"
        s.append(f'<g><title>{name(r)}: {pct(v)}; standalone readout {r["B"]:.2f}</title>'
                 f'<text x="{x0 - 8}" y="{y + 14}" text-anchor="end" class="lab">{name(r)}</text>'
                 f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{bh}" rx="3" fill="{col}"/></g>')
        tx = xm + w + 6 if v > 0 else xm - w - 6
        s.append(f'<text x="{tx:.1f}" y="{y + 14}" text-anchor="{"start" if v > 0 else "end"}" class="val">{pct(v)}</text>')
    s.append(f'<text x="{xm}" y="{H - 4}" text-anchor="middle" class="ax">gray band = largest push from shuffled labels (±{thr * 100:.0f}%)</text>')
    s.append("</svg>")
    return "\n".join(s)


# ----------------------------------------------------------------------------- layer totals
def layer_totals(res):
    R = res["ref_layer"]
    att = {L: 0.0 for L in range(1, R + 1)}
    mlp = {}
    for r in res["rows"]:
        if r["kind"] == "head":
            att[r["layer"]] += r["share"]
        elif r["kind"] == "mlp":
            mlp[r["layer"]] = r["share"]
    cap = 0.6
    W, x0, top, bot = 680, 50, 20, 230
    zero = (top + bot) / 2
    sc = (bot - top) / 2 / cap
    step = (W - x0 - 10) / R
    bw = step * 0.34
    s = [f'<svg class="chart" viewBox="0 0 {W} {bot + 34}" role="img" aria-label="Net push of attention and MLP per layer">']
    for t in (-0.6, -0.3, 0, 0.3, 0.6):
        y = zero - t * sc
        s.append(f'<line x1="{x0}" x2="{W - 10}" y1="{y:.1f}" y2="{y:.1f}" stroke="var(--line)"{" stroke-width=\"1.5\" style=\"stroke:var(--ink-3)\"" if t == 0 else ""}/>')
        s.append(f'<text x="{x0 - 6}" y="{y + 4:.1f}" text-anchor="end" class="ax">{t * 100:+.0f}%</text>')
    for L in range(1, R + 1):
        cx = x0 + (L - 0.5) * step
        for v, dx, col, lab in ((att[L], -bw - 1, "var(--navy)", "attention"), (mlp[L], 1, "#7FA8E0", "MLP")):
            h = abs(v) * sc
            y = zero - h if v > 0 else zero
            s.append(f'<rect x="{cx + dx:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{max(h, 1):.1f}" rx="2" fill="{col}">'
                     f'<title>Layer {L} {lab}: {pct(v)}</title></rect>')
        s.append(f'<text x="{cx:.1f}" y="{bot + 16}" text-anchor="middle" class="ax{" stdx" if NH[L - 1] == 8 else ""}">{L}</text>')
    s.append(f'<text x="{(W + x0) / 2}" y="{bot + 32}" text-anchor="middle" class="axl">layer (◆ standard attention: 4, 8, 12, 16)</text>')
    s.append("</svg>")
    return "\n".join(s)


# ----------------------------------------------------------------------------- neurons
def neuron_curve(res, layers, n=120):
    cap = max(max(res["neurons"][L]["sorted"][:n]) for L in layers) * 1.1
    W, x0, top, bot = 680, 56, 16, 200
    sc = (bot - top) / cap
    cols = ["var(--navy)", "#7FA8E0", "#3B73C4"]
    s = [f'<svg class="chart" viewBox="0 0 {W} {bot + 34}" role="img" aria-label="Neuron contributions sorted from largest">']
    for t in [0, cap / 2, cap]:
        y = bot - t * sc
        s.append(f'<line x1="{x0}" x2="{W - 10}" y1="{y:.1f}" y2="{y:.1f}" stroke="var(--line)"/>'
                 f'<text x="{x0 - 6}" y="{y + 4:.1f}" text-anchor="end" class="ax">{t * 100:.1f}%</text>')
    for k, L in enumerate(layers):
        vals = res["neurons"][L]["sorted"][:n]
        pts = " ".join(f"{x0 + i * (W - x0 - 10) / (n - 1):.1f},{bot - v * sc:.1f}" for i, v in enumerate(vals))
        s.append(f'<polyline points="{pts}" fill="none" stroke="{cols[k]}" stroke-width="2.5"/>')
        thr = res["neurons"][L]["thr"]
        s.append(f'<line x1="{x0}" x2="{W - 10}" y1="{bot - thr * sc:.1f}" y2="{bot - thr * sc:.1f}" stroke="{cols[k]}" stroke-dasharray="3 4" opacity=".7"/>')
        s.append(f'<text x="{x0 + 14}" y="{bot - vals[0] * sc + (4 if k else -6):.1f}" class="lab" style="fill:{cols[k]}">Layer {L} MLP</text>')
    for i in (1, 30, 60, 90, 120):
        s.append(f'<text x="{x0 + (i - 1) * (W - x0 - 10) / (n - 1):.1f}" y="{bot + 16}" text-anchor="middle" class="ax">{i}</text>')
    s.append(f'<text x="{(W + x0) / 2}" y="{bot + 32}" text-anchor="middle" class="axl">neurons, ranked by how much they push toward the right answer (top {n} of 3,584)</text>')
    s.append("</svg>")
    return "\n".join(s)


def edited_strip(res):
    L = str(res["edited_layer"])
    ranks = res["neurons"][L]["edited_rank"]
    W, x0, x1 = 680, 20, 660
    s = [f'<svg class="chart" viewBox="0 0 {W} 92" role="img" aria-label="Where the 256 previously edited neurons rank">']
    s.append(f'<rect x="{x0}" y="22" width="{(x1 - x0) * 256 / 3584:.1f}" height="36" fill="var(--blue-soft)"/>')
    s.append(f'<text x="{x0 + 4}" y="16" class="ax">top 256</text>')
    for r in ranks:
        x = x0 + (x1 - x0) * r / 3584
        s.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="26" y2="54" stroke="var(--navy)" stroke-width="1.2" opacity=".75"/>')
    s.append(f'<line x1="{x0}" x2="{x1}" y1="58" y2="58" stroke="var(--ink-3)"/>')
    for t in (1, 896, 1792, 2688, 3584):
        s.append(f'<text x="{x0 + (x1 - x0) * (t - 1) / 3583:.1f}" y="74" text-anchor="middle" class="ax">{t}</text>')
    s.append(f'<text x="{(x0 + x1) / 2}" y="90" text-anchor="middle" class="axl">rank of each edited neuron among all 3,584 in layer 17 (1 = pushes most toward the right answer)</text>')
    s.append("</svg>")
    return "\n".join(s)


# ----------------------------------------------------------------------------- page
def topk(res, k=5):
    rows = [r for r in sorted(res["rows"], key=lambda r: -r["contrib"]) if r["kind"] != "emb"][:k]
    return "".join(f"<li>{name(r)} <span class='num'>{pct(r['share'])}</span>{' ★' if r['sig'] else ''}</li>" for r in rows)


# ----------------------------------------------------------------------------- part 2: edit controls
E = json.loads((HERE / "results" / "edit_controls.json").read_text())
ER, EF = E["rows"], E["families"]
FAM = [("rand_change", "Random change", "#6B4FA0"), ("rand_push", "Random push", "#8A97A8"),
       ("shuffled", "Shuffled labels", "#C2550C"), ("rand_neurons", "Random neurons", "#3B73C4")]
LAYER_COL = "#1A7F7A"


def star(cx, cy, r=8, fill="var(--navy)"):
    import math
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append(f"{cx + rr * math.cos(a):.1f},{cy + rr * math.sin(a):.1f}")
    return f'<polygon points="{" ".join(pts)}" fill="{fill}" stroke="#fff" stroke-width="1.5"/>'


def strip():
    x0, x1, lo, hi = 180, 660, 0.1, 1.0
    X = lambda v: x0 + (v - lo) / (hi - lo) * (x1 - x0)
    rows = FAM + [("layer", "Other layers (9, 13, 16, 20)", LAYER_COL), ("real", "Real edit (layer 17)", "var(--navy)")]
    rh, y0 = 44, 30
    H = y0 + len(rows) * rh + 40
    s = [f'<svg class="chart" viewBox="0 0 680 {H}" role="img" aria-label="Safety AUROC of the real edit versus each random control">']
    for t in (0.2, 0.4, 0.6, 0.8, 1.0):
        s.append(f'<line x1="{X(t):.1f}" x2="{X(t):.1f}" y1="{y0 - 8}" y2="{H - 34}" stroke="var(--line)"/>'
                 f'<text x="{X(t):.1f}" y="{H - 18}" text-anchor="middle" class="ax">{t:.1f}</text>')
    b = ER["base_safety"]["safety"]
    s.append(f'<line x1="{X(b):.1f}" x2="{X(b):.1f}" y1="{y0 - 14}" y2="{H - 34}" stroke="var(--ink-3)" stroke-width="1.5" stroke-dasharray="5 4"/>'
             f'<text x="{X(b) + 5:.1f}" y="{y0 - 16}" class="ax">no edit {b:.2f}</text>')
    rv = ER["real"]["safety"]
    s.append(f'<line x1="{X(rv):.1f}" x2="{X(rv):.1f}" y1="{y0 - 14}" y2="{H - 34}" stroke="var(--navy)" stroke-width="1.5" opacity=".5"/>'
             f'<text x="{X(rv) - 5:.1f}" y="{y0 - 16}" text-anchor="end" class="ax" style="fill:var(--navy)">real edit {rv:.2f}</text>')
    for i, (f, lab, col) in enumerate(rows):
        cy = y0 + i * rh + rh / 2
        s.append(f'<text x="{x0 - 12}" y="{cy + 4:.1f}" text-anchor="end" class="lab"{" style=\"font-weight:600\"" if f == "real" else ""}>{lab}</text>')
        if f == "real":
            s.append(f'<g><title>Real edit: {rv:.3f}</title>{star(X(rv), cy, 9)}</g>')
            continue
        pts = [r for r in ER.values() if r["family"] == f]
        for j, r in enumerate(sorted(pts, key=lambda r: r["safety"])):
            dy = ((j % 3) - 1) * 7
            if f == "layer":
                s.append(f'<g><title>Layer {r["layer"]}: {r["safety"]:.3f}</title><circle cx="{X(r["safety"]):.1f}" cy="{cy + dy:.1f}" r="6" fill="#fff" stroke="{col}" stroke-width="2.5"/></g>')
            else:
                s.append(f'<circle cx="{X(r["safety"]):.1f}" cy="{cy + dy:.1f}" r="5" fill="{col}" opacity=".85" stroke="#fff" stroke-width="1"><title>{lab}: {r["safety"]:.3f}</title></circle>')
    s.append(f'<text x="{(x0 + x1) / 2}" y="{H - 2}" text-anchor="middle" class="axl">Safety verdict AUROC on 168 held-out test items (0.5 = guessing)</text>')
    s.append("</svg>")
    return "\n".join(s)


def scatter(key, xlab, xmax):
    W, H, x0, x1, y0, y1 = 340, 300, 44, 326, 16, 250
    lo, hi = 0.1, 1.0
    X = lambda v: x0 + (max(v, 0) / xmax) * (x1 - x0)
    Y = lambda v: y1 - (v - lo) / (hi - lo) * (y1 - y0)
    s = [f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="Safety AUROC versus {xlab}">']
    for t in (0.2, 0.4, 0.6, 0.8, 1.0):
        s.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" stroke="var(--line)"/>'
                 f'<text x="{x0 - 6}" y="{Y(t) + 4:.1f}" text-anchor="end" class="ax">{t:.1f}</text>')
    for k in range(5):
        v = xmax * k / 4
        s.append(f'<text x="{X(v):.1f}" y="{y1 + 16}" text-anchor="middle" class="ax">{v:.2g}</text>')
    s.append(f'<line x1="{x0}" x2="{x0}" y1="{y0}" y2="{y1}" stroke="var(--ink-3)"/>')
    b = ER["base_safety"]["safety"]
    s.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(b):.1f}" y2="{Y(b):.1f}" stroke="var(--ink-3)" stroke-dasharray="5 4"/>'
             f'<text x="{x1}" y="{Y(b) - 5:.1f}" text-anchor="end" class="ax">no edit</text>')
    for f, lab, col in FAM:
        for r in ER.values():
            if r["family"] == f:
                s.append(f'<circle cx="{X(r[key]):.1f}" cy="{Y(r["safety"]):.1f}" r="4.5" fill="{col}" opacity=".8" stroke="#fff" stroke-width="1">'
                         f'<title>{lab}: Safety {r["safety"]:.2f}, {xlab} {r[key]:+.2f}</title></circle>')
    for n in ("layer_9", "layer_13", "layer_16", "layer_20"):
        r = ER[n]
        s.append(f'<g><title>Layer {r["layer"]}: Safety {r["safety"]:.2f}, {xlab} {r[key]:+.2f}</title><circle cx="{X(r[key]):.1f}" cy="{Y(r["safety"]):.1f}" r="6" fill="#fff" stroke="{LAYER_COL}" stroke-width="2.5"/>'
                 + (f'<text x="{X(r[key]) + 9:.1f}" y="{Y(r["safety"]) + 4:.1f}" class="ax" style="fill:{LAYER_COL};font-weight:600">L{r["layer"]}</text>' if r["layer"] == 9 else "") + '</g>')
    r = ER["real"]
    s.append(f'<g><title>Real edit (layer 17): Safety {r["safety"]:.2f}, {xlab} {r[key]:+.2f}</title>{star(X(r[key]), Y(r["safety"]), 9)}</g>')
    s.append(f'<text x="{(x0 + x1) / 2}" y="{H - 6}" text-anchor="middle" class="axl">{xlab} →</text>')
    s.append("</svg>")
    return "\n".join(s)


def fam_cell(f):
    v = EF[f]
    return f'{v["safety_min"]:.2f}–{v["safety_max"]:.2f}'


xmax_wiki = max(r["wiki_up"] for r in ER.values() if r["family"] != "base") * 1.05
xmax_bff = max(r["bff_drop"] for r in ER.values() if r["family"] != "base") * 1.05
part2 = f"""
  <div class="part"><span>Part 2</span><h2>Was the weight edit significant, or would a random edit do?</h2></div>

  <section>
    <div class="step">Setup</div>
    <h2>What we ran</h2>
    <ul>
      <li><b>The real edit:</b> the same recipe as the earlier experiment, rebuilt under the team's safety prompt. In layer 17's MLP, take the 256 neurons that track the hidden knowledge most closely, learn a <b>detector</b> from them, and add a <b>push</b> toward "say CORRECT" scaled by the detector (0.03% of the weights).</li>
      <li><b>Random copies:</b> 19 copies each, changing <b>one ingredient</b> at a time for a random version (table below), plus the same recipe in layers 9, 13, 16 and 20.</li>
      <li><b>Fair size:</b> every edit was scaled to change the model's internal state by the same amount, so only the ingredient differs.</li>
      <li><b>No peeking:</b> everything was fit on training items and scored on the 168 held-out Safety test items, the 74 BFF test items and 20 Wikipedia passages. 84 edits ran on 10 Modal GPUs in parallel.</li>
    </ul>
    <div class="tablewrap"><table>
      <thead><tr><th>Control (×19)</th><th>What is made random</th><th>Question it answers</th></tr></thead>
      <tbody>
        <tr><td>Shuffled labels</td><td>The detector is learned from meaningless good/bad labels</td><td>Does the edit use <b>real safety knowledge</b>?</td></tr>
        <tr><td>Random push</td><td>The push points in a random direction</td><td>Does the <b>direction</b> matter?</td></tr>
        <tr><td>Random change</td><td>A random weight change on the same neurons</td><td>Would <b>any change</b> of this size help?</td></tr>
        <tr><td>Random neurons</td><td>256 random neurons in the same layer</td><td>Do the <b>specific neurons</b> matter?</td></tr>
      </tbody>
    </table></div>
    <div class="stats">
      <div class="stat"><b>{ER["base_generic"]["safety"]:.2f} → {ER["repro_generic"]["safety"]:.2f}</b><span>original edit, original prompt: the earlier 0.95 reproduces</span></div>
      <div class="stat"><b>{ER["base_safety"]["safety"]:.2f} → {ER["real"]["safety"]:.2f}</b><span>real edit under the team's safety prompt</span></div>
      <div class="stat"><b>{ER["base_safety"]["safety_ss"]:.2f} → {ER["real"]["safety_ss"]:.2f}</b><span>same, fair same-source comparison</span></div>
    </div>
  </section>

  <section>
    <div class="step">Finding 5</div>
    <h2>The edit beats every random control except random neurons</h2>
    <div class="legend">{"".join(f'<span><i class="sw" style="background:{c};border-radius:50%"></i>{l}</span>' for f, l, c in FAM)}<span><i class="sw" style="border:2.5px solid {LAYER_COL};border-radius:50%"></i>other layers</span><span>★ real edit</span></div>
    {strip()}
    <div class="tablewrap"><table>
      <thead><tr><th>Ingredient</th><th>Real edit beats</th><th>Random range</th><th>What it means</th></tr></thead>
      <tbody>
        <tr><td>Real safety knowledge</td><td class="num hi">{EF["shuffled"]["beats"]} of 19</td><td class="num">{fam_cell("shuffled")}</td><td><b>✓ Significant.</b> With meaningless labels the edit does nothing. The gain comes from what the model really knows.</td></tr>
        <tr><td>Push direction</td><td class="num hi">{EF["rand_push"]["beats"]} of 19</td><td class="num">{fam_cell("rand_push")}</td><td><b>✓ Significant.</b> Pushing toward "CORRECT" is what turns the knowledge into a verdict. Random directions are hit or miss.</td></tr>
        <tr><td>Any change of this size</td><td class="num hi">{EF["rand_change"]["beats"]} of 19</td><td class="num">{fam_cell("rand_change")}</td><td><b>✓ Significant.</b> Random weight changes of the same size leave the verdict at chance.</td></tr>
        <tr><td>The specific 256 neurons</td><td class="num">{EF["rand_neurons"]["beats"]} of 19</td><td class="num">{fam_cell("rand_neurons")}</td><td><b>✗ Not significant.</b> Any 256 neurons in layer 17 work just as well, because the knowledge can be read from almost anywhere.</td></tr>
      </tbody>
    </table></div>
    <p class="note">Other layers: layer 9 {ER["layer_9"]["safety"]:.2f}, 13 {ER["layer_13"]["safety"]:.2f}, 16 {ER["layer_16"]["safety"]:.2f}, 20 {ER["layer_20"]["safety"]:.2f}. "Beats" counts how many of the 19 random copies score below the real edit (19 of 19 is significant at the 5% level). The random neuron sets share only about 18 of 256 neurons with the real edit, yet score the same.</p>
  </section>

  <section>
    <div class="step">Finding 6</div>
    <h2>The damage comes from the knowledge push, and the layer decides how much</h2>
    <div class="legend">{"".join(f'<span><i class="sw" style="background:{c};border-radius:50%"></i>{l}</span>' for f, l, c in FAM)}<span><i class="sw" style="border:2.5px solid {LAYER_COL};border-radius:50%"></i>other layers</span><span>★ real edit (layer 17)</span></div>
    <div class="grid2">
      <div><h3>Safety gain vs damage to normal text</h3>{scatter("wiki_up", "increase in text prediction loss", xmax_wiki)}</div>
      <div><h3>Safety gain vs damage to finance grading</h3>{scatter("bff_drop", "drop in BFF AUROC", xmax_bff)}</div>
    </div>
    <p class="note">Teal circles: the same recipe in layers 9, 13, 16 and 20 (only layer 9 is labeled; 13, 16 and 20 sit beside the star at the top). Hover any dot for its numbers.</p>
    <p>Best is <b>top left</b>: a big Safety gain with little damage. Three things stand out:</p>
    <ul>
      <li><b>Random changes are harmless</b> (text loss +{EF["rand_change"]["wiki_up_mean"]:.2f}), even though they're the same size. The damage isn't from changing weights; it's from <b>what</b> the edit writes.</li>
      <li><b>Shuffled-label edits are the most harmful</b> (text loss +{EF["shuffled"]["wiki_up_mean"]:.1f} on average) and gain nothing. A detector without real knowledge fires on everything.</li>
      <li><b>Later layers are gentler.</b> Layers 16 and 20 match the real edit's Safety gain ({ER["layer_16"]["safety"]:.2f}, {ER["layer_20"]["safety"]:.2f}) with about half the text damage (+{ER["layer_16"]["wiki_up"]:.1f} vs +{ER["real"]["wiki_up"]:.1f}) and almost no finance damage (BFF −{ER["layer_16"]["bff_drop"]:.2f}, −{ER["layer_20"]["bff_drop"]:.2f} vs −{ER["real"]["bff_drop"]:.2f}). Layer 9 is the worst on both.</li>
    </ul>
  </section>

  <section class="rec">
    <span class="tag">What it all means</span>
    <h2>The edit is real, but it's a rewiring, not a precise fix</h2>
    <ul>
      <li><b>The weight edit is significant.</b> It beats shuffled labels, random directions and random changes 19 out of 19 times. The gain comes from the judge's real hidden knowledge being routed to its verdict.</li>
      <li><b>Which neurons doesn't matter.</b> Random neurons in the same layer do just as well. This matches Part 1: the knowledge is readable almost everywhere after layer 6, so any reasonable set of neurons can serve as the detector.</li>
      <li><b>Where matters for side effects.</b> Editing later (layers 16 or 20) keeps the Safety gain and cuts the damage, especially to finance grading. Our original layer 17 choice was optimized for Safety only and was not the best trade-off.</li>
      <li><b>The remaining damage has one cause:</b> the edit is always on, so the detector also fires on finance questions and normal text. Making it fire only on safety grading, for example by adding "do nothing here" examples when fitting the detector, is the most direct next fix.</li>
      <li><b>Connection to Part 1:</b> the parts that <b>build</b> the knowledge (layers 8 and 16 heads) are where a precise intervention would target. Part 3 switches them off to test whether they cause it.</li>
    </ul>
  </section>
"""


# ----------------------------------------------------------------------------- Part 3: switch-off test
SO = json.loads((HERE / "results" / "switch_off.json").read_text())
SR, ST = SO["rows"], SO["tests"]
GRAY = "#8A97A8"


def pts(x):   # AUROC change in points
    return f"{x * 100:+.1f}"


def recovery_chart():
    W, H, x0, x1, y0, y1 = 680, 320, 48, 600, 18, 270
    lo, hi = 0.55, 1.0
    X = lambda L: x0 + (L - 1) / 22 * (x1 - x0)
    Y = lambda v: y1 - (v - lo) / (hi - lo) * (y1 - y0)
    lines = [("base", "Nothing switched off", "var(--navy)", ""), ("single_L8h4", "Layer 8 head 4 off", "#C2550C", ""),
             ("single_L16h2", "Layer 16 head 2 off", "#3B73C4", "6 4")]
    s = [f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="Hidden knowledge by layer after switching off one head">']
    for t in (0.6, 0.7, 0.8, 0.9, 1.0):
        s.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" stroke="var(--line)"/>'
                 f'<text x="{x0 - 6}" y="{Y(t) + 4:.1f}" text-anchor="end" class="ax">{t:.1f}</text>')
    for L in (1, 4, 8, 12, 16, 20, 23):
        s.append(f'<text x="{X(L):.1f}" y="{y1 + 16}" text-anchor="middle" class="ax">{L}</text>')
    for L, lab in ((8, "switched-off head"), (16, "readout layer")):
        s.append(f'<line x1="{X(L):.1f}" x2="{X(L):.1f}" y1="{y0}" y2="{y1}" stroke="var(--ink-3)" stroke-dasharray="2 4"/>')
    for n, lab, col, dash in lines:
        c = SR[n]["safety"]["curve"]
        d = " ".join(f"{'M' if i == 0 else 'L'}{X(i + 1):.1f},{Y(v):.1f}" for i, v in enumerate(c))
        s.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2.5" stroke-dasharray="{dash}" stroke-linejoin="round"/>')
        for i, v in enumerate(c):
            s.append(f'<circle cx="{X(i + 1):.1f}" cy="{Y(v):.1f}" r="7" fill="transparent"><title>{lab}, layer {i + 1}: {v:.3f}</title></circle>')
        s.append(f'<text x="{x1 + 6}" y="{Y(c[-1]) + (-8 if n == "single_L8h4" else 4 if n == "base" else 14):.1f}" class="lab" style="fill:{col};font-weight:600">{lab.split(" off")[0].replace("Nothing switched", "normal").replace("Layer ", "L")}</text>')
    c4 = SR["single_L8h4"]["safety"]["curve"]
    s.append(f'<text x="{X(8) + 8:.1f}" y="{Y(c4[7]) + 18:.1f}" class="ax" style="fill:#C2550C;font-weight:600">drops to {c4[7]:.2f}</text>')
    s.append(f'<text x="{X(14) - 4:.1f}" y="{Y(0.72):.1f}" class="ax" style="fill:#C2550C">…then the model rebuilds it</text>')
    s.append(f'<text x="{(x0 + x1) / 2}" y="{H - 6}" text-anchor="middle" class="axl">Layer · hidden knowledge = same-source AUROC of a fixed probe (0.5 = guessing)</text>')
    s.append("</svg>")
    return "\n".join(s)


def so_strip():
    x0, x1, lo, hi = 230, 660, -0.05, 0.02
    X = lambda v: x0 + (v - lo) / (hi - lo) * (x1 - x0)
    rows = [("S_right", "rand3", "safety", "Right-answer heads, Safety"), ("S_wrong", "rand2", "safety", "Wrong-answer heads, Safety"),
            ("S_right", "rand3", "bff", "Right-answer heads, BFF finance")]
    rh, y0 = 50, 26
    H = y0 + len(rows) * rh + 40
    s = [f'<svg class="chart" viewBox="0 0 680 {H}" role="img" aria-label="Change in hidden knowledge after switching off chosen heads versus random heads">']
    for t in (-0.04, -0.02, 0, 0.02):
        s.append(f'<line x1="{X(t):.1f}" x2="{X(t):.1f}" y1="{y0 - 8}" y2="{H - 34}" stroke="{"var(--ink-3)" if t == 0 else "var(--line)"}"{" stroke-dasharray=\"5 4\"" if t == 0 else ""}/>'
                 f'<text x="{X(t):.1f}" y="{H - 18}" text-anchor="middle" class="ax">{t * 100:+.0f}</text>')
    s.append(f'<text x="{X(0) + 5:.1f}" y="{y0 - 12}" class="ax">no change</text>')
    for i, (name, fam, c, lab) in enumerate(rows):
        cy = y0 + i * rh + rh / 2
        s.append(f'<text x="{x0 - 12}" y="{cy + 4:.1f}" text-anchor="end" class="lab">{lab}</text>')
        R = sorted([r[c]["d_knows"] for r in SR.values() if r["family"] == fam and c in r])
        for j, v in enumerate(R):
            s.append(f'<circle cx="{X(v):.1f}" cy="{cy + ((j % 3) - 1) * 7:.1f}" r="5" fill="{GRAY}" opacity=".8" stroke="#fff" stroke-width="1"><title>Random heads: {pts(v)} points</title></circle>')
        v = SR[name][c]["d_knows"]
        s.append(f'<g><title>Chosen heads: {pts(v)} points</title>{star(X(v), cy, 9)}</g>')
    s.append(f'<text x="{(x0 + x1) / 2}" y="{H - 2}" text-anchor="middle" class="axl">Change in hidden knowledge at the readout layer (AUROC points)</text>')
    s.append("</svg>")
    return "\n".join(s)


def single_bars():
    singles = sorted([r for r in SR.values() if r["family"] == "single"], key=lambda r: r["safety"]["d_knows"])
    x0, x1, lo, hi = 300, 660, -0.09, 0.03
    X = lambda v: x0 + (v - lo) / (hi - lo) * (x1 - x0)
    rh, y0 = 30, 26
    H = y0 + len(singles) * rh + 40
    s = [f'<svg class="chart" viewBox="0 0 680 {H}" role="img" aria-label="Change in hidden knowledge after switching off each part alone">']
    s.append(f'<text x="12" y="14" class="ax">part</text><text x="{x0 - 16}" y="14" text-anchor="end" class="ax">push in the map</text>')
    for t in (-0.08, -0.04, 0, 0.02):
        s.append(f'<line x1="{X(t):.1f}" x2="{X(t):.1f}" y1="{y0 - 6}" y2="{H - 34}" stroke="{"var(--ink-3)" if t == 0 else "var(--line)"}"/>'
                 f'<text x="{X(t):.1f}" y="{H - 18}" text-anchor="middle" class="ax">{t * 100:+.0f}</text>')
    for i, r in enumerate(singles):
        cy = y0 + i * rh + rh / 2
        v, (a, b) = r["safety"]["d_knows"], r["safety"]["ci_knows"]
        sig = b < 0 or a > 0
        col = "var(--navy)" if sig else "#B9C6D8"
        lab = "Layer " + r["comps"][0][1:].replace(" h", " head ")
        s.append(f'<text x="12" y="{cy + 4:.1f}" class="lab"{" style=\"font-weight:600\"" if sig else ""}>{lab}</text>'
                 f'<text x="{x0 - 16}" y="{cy + 4:.1f}" text-anchor="end" class="ax" style="fill:{"var(--blue)" if r["share"] > 0 else "var(--orange)"}">{r["share"] * 100:+.0f}%</text>')
        xa, xb = sorted((X(0), X(v)))
        s.append(f'<g><title>{lab}: {pts(v)} points (95% range {pts(a)} to {pts(b)})</title>'
                 f'<rect x="{xa:.1f}" y="{cy - 8:.1f}" width="{max(xb - xa, 1.5):.1f}" height="16" rx="3" fill="{col}"/>'
                 f'<line x1="{X(a):.1f}" x2="{X(b):.1f}" y1="{cy:.1f}" y2="{cy:.1f}" stroke="var(--ink-2)" stroke-width="1.5"/>'
                 f'<line x1="{X(a):.1f}" x2="{X(a):.1f}" y1="{cy - 5:.1f}" y2="{cy + 5:.1f}" stroke="var(--ink-2)" stroke-width="1.5"/>'
                 f'<line x1="{X(b):.1f}" x2="{X(b):.1f}" y1="{cy - 5:.1f}" y2="{cy + 5:.1f}" stroke="var(--ink-2)" stroke-width="1.5"/></g>')
    s.append(f'<text x="{(x0 + x1) / 2}" y="{H - 2}" text-anchor="middle" class="axl">Change in hidden knowledge at layer 16 (AUROC points)</text>')
    s.append("</svg>")
    return "\n".join(s)


def bff_bars():
    rows = sorted([r for r in SR.values() if r["family"] == "bff_mlp"], key=lambda r: int(r["name"].split("_")[-1]))
    W, H, x0, x1, y0, y1 = 680, 240, 48, 668, 16, 190
    lo, hi = -0.03, 0.02
    Y = lambda v: y1 - (v - lo) / (hi - lo) * (y1 - y0)
    bw = (x1 - x0) / len(rows)
    s = [f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="Change in BFF hidden knowledge after switching off each MLP">']
    for t in (-0.03, -0.02, -0.01, 0, 0.01, 0.02):
        s.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" stroke="{"var(--ink-3)" if t == 0 else "var(--line)"}"/>'
                 f'<text x="{x0 - 6}" y="{Y(t) + 4:.1f}" text-anchor="end" class="ax">{t * 100:+.0f}</text>')
    for i, r in enumerate(rows):
        L = int(r["name"].split("_")[-1])
        v = r["bff"]["d_knows"]
        col = "var(--navy)" if L == 19 else ("#7FA8E0" if L >= 15 else "#C9D4E3")
        ya, yb = sorted((Y(0), Y(v)))
        s.append(f'<g><title>Layer {L} MLP: {pts(v)} points</title><rect x="{x0 + i * bw + 3:.1f}" y="{ya:.1f}" width="{bw - 6:.1f}" height="{max(yb - ya, 1.5):.1f}" rx="3" fill="{col}"/></g>'
                 f'<text x="{x0 + (i + .5) * bw:.1f}" y="{y1 + 16}" text-anchor="middle" class="ax"{" style=\"font-weight:600;fill:var(--navy)\"" if L == 19 else ""}>{L}</text>')
    s.append(f'<text x="{(x0 + x1) / 2}" y="{H - 8}" text-anchor="middle" class="axl">MLP switched off (layer) · change in BFF hidden knowledge at layer 19 (AUROC points)</text>')
    s.append("</svg>")
    return "\n".join(s)


b_s, b_b = SR["base"]["safety"], SR["base"]["bff"]
c4 = SR["single_L8h4"]["safety"]["curve"]
h2 = SR["single_L16h2"]["safety"]
part3 = f"""
  <div class="part"><span>Part 3</span><h2>Switch-off test: do the flagged heads actually cause the knowledge?</h2></div>

  <section>
    <div class="step">Setup</div>
    <h2>What we ran</h2>
    <ul>
      <li><b>The idea:</b> Part 1 showed which parts <b>look</b> important. Here we switch them off and check whether the hidden knowledge actually goes away. That turns a correlation into a cause.</li>
      <li><b>Switching off:</b> at the verdict position, a part's output is replaced by its <b>average</b> over all questions. It still sends a normal-looking signal, but the same one for every answer, so it can no longer tell good from bad. "Boost" does the opposite and doubles how far the output sits from its average.</li>
      <li><b>What we switched off:</b> the three biggest right-answer heads (layer 16 heads 2 and 5, layer 8 head 4), the two biggest wrong-answer heads (layer 8 head 3, layer 16 head 8), the eight biggest parts one at a time, and every MLP in layers 1–19 on BFF.</li>
      <li><b>Luck check:</b> 19 random sets of the same number of heads from layers 1–16.</li>
      <li><b>Measuring knowledge:</b> the probe from the normal model is <b>kept fixed</b> and read at every layer, on all 900 Safety and 459 BFF items (each item scored by a probe that never saw it). 70 switch-offs ran on 18 Modal GPUs. With nothing switched off it gives {b_s["knows"]:.2f} on Safety, matching Part 1.</li>
    </ul>
    <div class="stats">
      <div class="stat"><b>19 of 19</b><span>random head sets hurt less than switching off the chosen heads, on Safety and on BFF</span></div>
      <div class="stat"><b>{pts(h2["d_knows"])} pts</b><span>layer 16 head 2 alone: the one part whose loss is never repaired</span></div>
      <div class="stat"><b>{SR["base"]["safety"]["curve"][7]:.2f} → {c4[7]:.2f} → {SR["single_L8h4"]["safety"]["knows"]:.2f}</b><span>layer 8 head 4 off: knowledge at layer 8 collapses, then is rebuilt by layer 16</span></div>
    </div>
  </section>

  <section>
    <div class="step">Finding 7</div>
    <h2>The chosen heads matter more than random heads, but the knowledge survives</h2>
    <div class="legend"><span><i class="sw" style="background:{GRAY};border-radius:50%"></i>19 random head sets</span><span>★ chosen heads</span></div>
    {so_strip()}
    <p>Switching off the right-answer heads lowers the hidden knowledge on Safety from {b_s["knows"]:.2f} to {SR["S_right"]["safety"]["knows"]:.2f}, a bigger drop than <b>all 19</b> random sets (random: {pts(ST["right_safety"]["rand_min"])} to {pts(ST["right_safety"]["rand_max"])} points). The <b>same heads also lower BFF</b> knowledge ({b_b["knows"]:.2f} → {SR["S_right"]["bff"]["knows"]:.2f}, again more than all 19 random sets), even though they were picked on Safety only.</p>
    <p>Surprise: switching off the <b>wrong-answer</b> heads does not raise the knowledge. It lowers it too ({pts(SR["S_wrong"]["safety"]["d_knows"])} points). Boosting the right-answer heads doesn't raise it either ({pts(SR["S_right_boost"]["safety"]["d_knows"])}).</p>
    <p class="note">The effects are real but small: a few AUROC points out of {b_s["knows"]:.2f}. Even with the five biggest heads gone, the model still knows the answer at about 0.92.</p>
  </section>

  <section>
    <div class="step">Finding 8</div>
    <h2>The model repairs early damage, but not late damage</h2>
    <div class="legend"><span><i class="sw" style="background:var(--navy)"></i>nothing switched off</span><span><i class="sw" style="background:#C2550C"></i>layer 8 head 4 off</span><span><i class="sw" style="background:#3B73C4"></i>layer 16 head 2 off (dashed)</span></div>
    {recovery_chart()}
    <p>Switching off <b>layer 8 head 4</b> makes the knowledge collapse right after it ({SR["base"]["safety"]["curve"][7]:.2f} → {c4[7]:.2f} at layer 8). But the following layers <b>rebuild it</b>, and by layer 16 it is back to normal ({SR["single_L8h4"]["safety"]["knows"]:.2f}). Switching off <b>layer 16 head 2</b> comes too late to be repaired: the loss carries through to the last layer.</p>
  </section>

  <section>
    <div class="step">Finding 9</div>
    <h2>One at a time, only layer 16 head 2 clearly matters</h2>
    <div class="legend"><span><i class="sw" style="background:var(--navy)"></i>clear effect (95% range excludes zero)</span><span><i class="sw" style="background:#B9C6D8"></i>no clear effect</span><span>whiskers: 95% range</span></div>
    {single_bars()}
    <p>A big push in the map does not mean a part is needed. Layer 16 head 5 had a +36% push in Part 1, yet switching it off alone changes nothing, because other parts cover for it. Only <b>layer 16 head 2</b> is both a top pusher <b>and</b> needed on its own.</p>
  </section>

  <section>
    <div class="step">BFF</div>
    <h2>On BFF, the layer 19 MLP is the most needed MLP, closely followed by its neighbours</h2>
    <div class="legend"><span><i class="sw" style="background:var(--navy)"></i>layer 19 MLP (flagged in Part 1)</span><span><i class="sw" style="background:#7FA8E0"></i>layers 15–18</span><span><i class="sw" style="background:#C9D4E3"></i>earlier layers</span></div>
    {bff_bars()}
    <p class="note">Switching off the layer 19 MLP gives the biggest drop of all 19 MLPs ({pts(SR["bff_mlp_19"]["bff"]["d_knows"])} points), confirming Part 1's one significant BFF part. But layers 18 and 15 are close ({pts(SR["bff_mlp_18"]["bff"]["d_knows"])}, {pts(SR["bff_mlp_15"]["bff"]["d_knows"])}): finance knowledge leans on the <b>late MLPs as a group</b>, while Safety leans on <b>attention heads</b>.</p>
  </section>

  <section class="rec">
    <span class="tag">What it all means</span>
    <h2>The knowledge has a few real hubs, but the model is built to route around damage</h2>
    <ul>
      <li><b>The map is not luck.</b> The heads Part 1 flagged matter more than random heads, 19 out of 19 times. So the module map points at real parts, not noise.</li>
      <li><b>The knowledge is redundant and self-repairing.</b> Removing even the biggest parts costs only a few points, and damage early in the model is rebuilt by later layers. Many parts carry copies of the same signal, which is also why any 256 neurons worked for the edit in Part 2.</li>
      <li><b>Layer 16 head 2 is the clearest "where".</b> It's the only single part whose removal clearly hurts and isn't repaired, and it already showed up in both the Safety and BFF top-5 in Part 1. It is the best target for a precise edit, and the next thing to look inside.</li>
      <li><b>"Right" and "wrong" pushers work as a team.</b> Removing the wrong-answer heads hurts instead of helping. They aren't errors to delete; they balance the right-answer heads.</li>
      <li><b>Some machinery is shared across benchmarks.</b> Heads picked on Safety also carry finance knowledge. BFF additionally relies on its own late MLPs (layers 15–19). This supports the idea that the method finds the right parts for each dataset.</li>
    </ul>
  </section>
"""


# ----------------------------------------------------------------------------- Part 0: prompt control
PC = json.loads((HERE / "results" / "prompt_control.json").read_text())
PROWS = [("rb2_generic", "Safety · generic prompt", "the original pilot"),
         ("rb2_safety", "Safety · team safety prompt", "used in Parts 1–3"),
         ("rb2_reworded", "Safety · reworded safety prompt", "same meaning, new words"),
         ("bff_generic", "BFF finance · generic prompt", "comparison benchmark")]
PCOL = {"rb2_generic": "#8A97A8", "rb2_safety": "var(--navy)", "rb2_reworded": "#3B73C4"}


def dumbbell():
    x0, x1, lo, hi = 250, 560, 0.4, 1.0
    X = lambda v: x0 + (v - lo) / (hi - lo) * (x1 - x0)
    rh, y0 = 48, 30
    H = y0 + len(PROWS) * rh + 40
    s = [f'<svg class="chart" viewBox="0 0 680 {H}" role="img" aria-label="What the judge says versus what it knows under each prompt">']
    for t in (0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
        s.append(f'<line x1="{X(t):.1f}" x2="{X(t):.1f}" y1="{y0 - 10}" y2="{H - 34}" stroke="{"var(--ink-3)" if t == 0.5 else "var(--line)"}"{" stroke-dasharray=\"5 4\"" if t == 0.5 else ""}/>'
                 f'<text x="{X(t):.1f}" y="{H - 18}" text-anchor="middle" class="ax">{t:.1f}</text>')
    s.append(f'<text x="{X(0.5) + 5:.1f}" y="{y0 - 14}" class="ax">guessing</text>')
    s.append(f'<text x="{x1 + 20}" y="{y0 - 14}" class="ax">says CORRECT</text>')
    for i, (k, lab, sub) in enumerate(PROWS):
        r = PC[k]
        cy = y0 + i * rh + rh / 2
        s.append(f'<text x="{x0 - 14}" y="{cy}" text-anchor="end" class="lab"{" style=\"font-weight:600\"" if k == "rb2_safety" else ""}>{lab}</text>'
                 f'<text x="{x0 - 14}" y="{cy + 14}" text-anchor="end" class="ax">{sub}</text>')
        a, b = X(r["says"]), X(r["knows_best"])
        s.append(f'<line x1="{a:.1f}" x2="{b:.1f}" y1="{cy:.1f}" y2="{cy:.1f}" stroke="#B9C6D8" stroke-width="6" stroke-linecap="round"/>'
                 f'<g><title>Says (verdict): {r["says"]:.3f}</title><circle cx="{a:.1f}" cy="{cy:.1f}" r="7" fill="#fff" stroke="var(--orange)" stroke-width="2.5"/></g>'
                 f'<g><title>Knows (best layer {r["best_layer"]}): {r["knows_best"]:.3f}</title><circle cx="{b:.1f}" cy="{cy:.1f}" r="7" fill="var(--navy)" stroke="#fff" stroke-width="1.5"/></g>'
                 f'<text x="{(a + b) / 2:.1f}" y="{cy - 10:.1f}" text-anchor="middle" class="ax" style="font-weight:600;fill:var(--ink-2)">gap {r["knows_best"] - r["says"]:+.2f}</text>'
                 f'<text x="{x1 + 20}" y="{cy + 4:.1f}" class="val" style="fill:var(--ink-2)">{r["says_correct"] * 100:.0f}%</text>')
    s.append(f'<text x="{(x0 + x1) / 2}" y="{H - 2}" text-anchor="middle" class="axl">Same-source AUROC (0.5 = guessing)</text>')
    s.append("</svg>")
    return "\n".join(s)


def prompt_curves():
    W, H, x0, x1, y0, y1 = 680, 270, 48, 556, 16, 220
    lo, hi = 0.5, 1.0
    X = lambda L: x0 + (L - 1) / 23 * (x1 - x0)
    Y = lambda v: y1 - (v - lo) / (hi - lo) * (y1 - y0)
    s = [f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="Hidden knowledge by layer under three Safety prompts">']
    s.append(f'<rect x="{X(15):.1f}" y="{y0}" width="{X(18) - X(15):.1f}" height="{y1 - y0}" fill="var(--blue-soft)"/>'
             f'<text x="{(X(15) + X(18)) / 2:.1f}" y="{y0 + 14}" text-anchor="middle" class="ax" style="fill:var(--blue)">peak: layers 15–18</text>')
    for t in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
        s.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" stroke="var(--line)"/>'
                 f'<text x="{x0 - 6}" y="{Y(t) + 4:.1f}" text-anchor="end" class="ax">{t:.1f}</text>')
    for L in (1, 4, 8, 12, 16, 20, 24):
        s.append(f'<text x="{X(L):.1f}" y="{y1 + 16}" text-anchor="middle" class="ax">{L}</text>')
    base_y = Y(PC["rb2_safety"]["curve"][-1])
    offs = {"rb2_safety": -12, "rb2_generic": 4, "rb2_reworded": 20}
    for k, lab, _ in PROWS[:3]:
        c = PC[k]["curve"]
        d = " ".join(f"{'M' if i == 0 else 'L'}{X(i + 1):.1f},{Y(v):.1f}" for i, v in enumerate(c))
        s.append(f'<path d="{d}" fill="none" stroke="{PCOL[k]}" stroke-width="2.5" stroke-linejoin="round"/>')
        for i, v in enumerate(c):
            s.append(f'<circle cx="{X(i + 1):.1f}" cy="{Y(v):.1f}" r="7" fill="transparent"><title>{lab}, layer {i + 1}: {v:.3f}</title></circle>')
        s.append(f'<text x="{x1 + 6}" y="{base_y + offs[k]:.1f}" class="lab" style="fill:{PCOL[k]};font-weight:600">{lab.split("· ")[1].replace(" prompt", "")}</text>')
    v = PC["rb2_safety"]["says"]
    s.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="var(--orange)" stroke-width="1.5" stroke-dasharray="5 4"/>'
             f'<text x="{x0 + 6}" y="{Y(v) - 6:.1f}" class="ax" style="fill:var(--orange);font-weight:600">what the verdict says (all three prompts ≈ {v:.2f})</text>')
    s.append(f'<text x="{(x0 + x1) / 2}" y="{H - 6}" text-anchor="middle" class="axl">Layer · hidden knowledge = same-source probe AUROC</text>')
    s.append("</svg>")
    return "\n".join(s)


g, sf, rw = PC["rb2_generic"], PC["rb2_safety"], PC["rb2_reworded"]
part0 = f"""
  <div class="part"><span>Part 0</span><h2>First check: is the knows-vs-says gap real, or caused by the prompt?</h2></div>

  <section>
    <div class="step">Prompt control</div>
    <h2>The gap stays under every prompt; only the verdict's bias moves</h2>
    <ul>
      <li><b>Why check:</b> the original pilot graded Safety with a <b>generic</b> "is this response correct?" prompt, not the team's safety prompt. A weak verdict could just mean the wrong question was asked.</li>
      <li><b>What we ran:</b> the same judge (Qwen3.5-0.8B, thinking off, forced verdict) on all 900 Safety items with three prompts: the generic one, the team's safety prompt (<code>SAFETY_JUDGE</code> from <code>tinker_pool/run_judges.py</code>), and a reworded safety prompt. Plus BFF with the generic prompt for comparison. Ran on a Modal GPU.</li>
      <li><b>What we measured:</b> "says" = how well the verdict separates good from bad responses; "knows" = the best per-layer probe on the hidden state. Both same-source AUROC.</li>
    </ul>
    <div class="legend"><span><i class="sw" style="border:2.5px solid var(--orange);border-radius:50%"></i>says (verdict)</span><span><i class="sw" style="background:var(--navy);border-radius:50%"></i>knows (best layer)</span><span>right column: share of answers the judge calls CORRECT</span></div>
    {dumbbell()}
    <p>On Safety, the verdict stays at guessing level ({g["says"]:.2f}, {sf["says"]:.2f}, {rw["says"]:.2f}) under all three prompts, while the hidden knowledge stays high ({g["knows_best"]:.2f}, {sf["knows_best"]:.2f}, {rw["knows_best"]:.2f}). The prompt changes <b>how often</b> the judge says CORRECT, from {g["says_correct"] * 100:.0f}% to {sf["says_correct"] * 100:.0f}%, but not whether it can <b>tell good from bad</b>.</p>
    <h3>Where the knowledge lives does not depend on the prompt</h3>
    {prompt_curves()}
    <p class="note">The three Safety prompts give nearly the same layer-by-layer curve, peaking in layers 15–18 (best: generic {g["best_layer"]}, safety {sf["best_layer"]}, reworded {rw["best_layer"]}). BFF has a smaller gap (says {PC["bff_generic"]["says"]:.2f}, knows {PC["bff_generic"]["knows_best"]:.2f}). GPU and Mac runs agree (verdict correlation {PC["gpu_vs_mac"]["corr"]:.2f}, same side of 50% for {PC["gpu_vs_mac"]["same_side"] * 100:.0f}% of items).</p>
    <div class="explain"><div><b>What it means:</b> the gap isn't a prompt mistake. The judge's hidden state ranks safe and unsafe responses well whatever it is asked, but its one-word answer doesn't use that ranking. That is what Parts 1–3 dig into, all under the team's safety prompt.</div></div>
  </section>
"""

nsig = sum(r["sig"] for r in S["rows"])
ncomp = len(S["rows"]) - 1
big = [r for r in S["rows"] if abs(r["share"]) >= 0.25 and r["kind"] != "emb"]
er = S["neurons"][str(S["edited_layer"])]["edited_rank"]
er_top256 = sum(r < 256 for r in er)
er_med = sorted(er)[len(er) // 2]
n9, n13 = S["neurons"]["9"], S["neurons"]["13"]
B_after6 = [r["B"] for r in S["rows"] if r["kind"] != "emb" and r["layer"] >= 6]
B_hi = sum(b >= 0.85 for b in B_after6)

html = f"""<meta charset="utf-8">
<title>Safety Knowledge Module Map</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:wght@500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: one reading column; bottom line, setup, then one finding per section, each = a sentence + a chart. Light mode only, by request. */
:root {{
  color-scheme: light;
  --bg: #F5F8FC; --surface: #FFFFFF; --ink: #0E1E33; --ink-2: #44546A; --ink-3: #6B7A90; --line: #DCE4EE;
  --navy: #0B2A55; --blue: #1F5FBF; --blue-soft: #E6EEF9; --orange: #C2550C;
  --serif: "IBM Plex Serif", Georgia, serif; --sans: "IBM Plex Sans", -apple-system, "Segoe UI", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}}
body {{ background: var(--bg); color: var(--ink); font: 16px/1.6 var(--sans); }}
.wrap {{ max-width: 880px; margin: 0 auto; padding-block: 40px 64px; padding-left: max(16px, env(safe-area-inset-left, 0px));
  padding-right: max(16px, env(safe-area-inset-right, 0px)); display: grid; gap: 28px; }}
header {{ display: grid; gap: 10px; }}
.eyebrow {{ font: 500 12px/1.4 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--blue); }}
h1 {{ font: 600 clamp(28px, 5vw, 38px)/1.15 var(--serif); color: var(--navy); margin: 0; text-wrap: balance; }}
h2 {{ font: 600 22px/1.25 var(--serif); color: var(--navy); margin: 0; text-wrap: balance; }}
h3 {{ font: 600 15px/1.3 var(--sans); margin: 0; }}
p {{ margin: 0; max-width: 70ch; }}
ul {{ margin: 0; padding-left: 20px; display: grid; gap: 6px; max-width: 72ch; }}
.bottom {{ background: var(--navy); color: #fff; border-radius: 10px; padding: 22px 24px; display: grid; gap: 8px; }}
.bottom .eyebrow {{ color: #9CC2FF; }} .bottom p {{ font-size: 17px; max-width: none; }} .bottom b {{ color: #CFE1FF; }}
section {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 24px; display: grid; gap: 14px; min-width: 0; }}
.step {{ font: 500 12px/1 var(--mono); color: var(--blue); letter-spacing: .06em; text-transform: uppercase; }}
.note {{ font-size: 13.5px; color: var(--ink-3); }}
.scroll {{ overflow-x: auto; }}
.chart {{ width: 100%; height: auto; display: block; }}
.heat {{ min-width: 600px; }}
.chart text {{ font-family: var(--sans); fill: var(--ink); }}
.chart .ax {{ font-size: 11px; fill: var(--ink-3); }} .chart .axl {{ font-size: 12px; fill: var(--ink-2); }}
.chart .lab {{ font-size: 12.5px; }} .chart .lab.std {{ font-weight: 600; fill: var(--navy); }}
.chart .stdx {{ font-weight: 600; fill: var(--navy); }}
.chart .val {{ font-size: 12.5px; font-weight: 600; }} .chart .cv {{ font-size: 10.5px; font-weight: 600; }}
.legend {{ display: flex; flex-wrap: wrap; gap: 16px; font-size: 13.5px; color: var(--ink-2); align-items: center; }}
.legend span {{ display: inline-flex; align-items: center; gap: 6px; }}
.sw {{ width: 14px; height: 14px; border-radius: 3px; display: inline-block; }}
.grad {{ width: 120px; height: 12px; border-radius: 3px; background: linear-gradient(90deg, rgb(194,85,12), rgb(241,244,248), rgb(31,95,191)); }}
.explain {{ display: grid; gap: 8px; background: var(--blue-soft); border-radius: 8px; padding: 14px 16px; font-size: 14.5px; }}
.explain b {{ color: var(--navy); }}
.grid2 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }}
.box {{ border: 1px solid var(--line); border-radius: 8px; padding: 14px 16px; display: grid; gap: 8px; min-width: 0; }}
.box ol {{ margin: 0; padding-left: 20px; font-size: 14.5px; display: grid; gap: 3px; }}
.num {{ font-family: var(--mono); color: var(--blue); }}
.stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }}
.stat {{ border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; display: grid; gap: 2px; }}
.stat b {{ font: 600 24px/1.2 var(--serif); color: var(--navy); font-variant-numeric: tabular-nums; }}
.stat span {{ font-size: 13px; color: var(--ink-2); }}
.part {{ display: grid; gap: 6px; padding: 18px 0 2px; border-top: 3px solid var(--navy); }}
.part span {{ font: 600 12px/1 var(--mono); letter-spacing: .1em; text-transform: uppercase; color: var(--blue); }}
.part h2 {{ font-size: 26px; }}
.tablewrap {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; min-width: 560px; font-size: 14px; }}
th, td {{ text-align: left; padding: 9px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }}
th {{ font: 500 12px/1.3 var(--mono); text-transform: uppercase; letter-spacing: .05em; color: var(--ink-3); }}
td.num {{ font-family: var(--mono); white-space: nowrap; }} td.hi {{ color: var(--blue); font-weight: 600; }}
.rec {{ border: 2px solid var(--navy); }}
.tag {{ display: inline-block; font: 500 12px/1 var(--mono); padding: 5px 8px; border-radius: 4px; background: var(--navy); color: #fff; letter-spacing: .05em; text-transform: uppercase; justify-self: start; }}
footer {{ font-size: 13px; color: var(--ink-3); display: grid; gap: 6px; }}
</style>

<div class="wrap">
  <header>
    <div class="eyebrow">Drill-down · Qwen3.5-0.8B judge · RewardBench 2 Safety and BFF</div>
    <h1>Where the judge's hidden safety knowledge comes from, whether it causes the verdict signal, and whether editing it is significant</h1>
  </header>

  <div class="bottom">
    <div class="eyebrow">Bottom line</div>
    <p><b>The gap is real, not a prompt artifact:</b> under the generic, team safety and reworded prompts, the Safety verdict stays at guessing level (about 0.51) while the hidden knowledge stays at 0.93–0.95. The prompt only changes how often the judge says CORRECT.</p>
    <p>The safety knowledge is <b>built by a small number of parts pushing in opposite directions</b>, mostly attention heads in the two standard-attention layers <b>8 and 16</b>, plus the MLPs in layers 8, 9 and 14. {nsig} of {ncomp} parts beat the random-label control.</p>
    <p>The 256 neurons we edited before were <b>no better than a random pick</b>. On BFF the map is weak and noisy, with only one significant part.</p>
    <p><b>The weight edit is significant:</b> it beats shuffled labels, random directions and random changes 19 of 19 times. But <b>any</b> 256 neurons work equally well, and editing <b>later layers (16, 20)</b> gives the same gain with far less damage.</p>
    <p><b>Switching parts off confirms the map:</b> the flagged heads matter more than random heads 19 of 19 times, on Safety and BFF. But the knowledge is redundant and self-repairing; only <b>layer 16 head 2</b> is clearly needed on its own.</p>
  </div>

{part0}
  <div class="part"><span>Part 1</span><h2>Module map: which heads and MLPs build the knowledge?</h2></div>

  <section>
    <div class="step">Setup</div>
    <h2>What we ran</h2>
    <ul>
      <li><b>Model and data:</b> Qwen3.5-0.8B judge, all 900 RewardBench 2 Safety items with the team's safety prompt, and all 459 BFF items with the team's finance prompt. Forward passes ran on a Modal GPU.</li>
      <li><b>What we recorded:</b> at the moment the judge gives its verdict, the output of every attention head and every MLP in all 24 layers. Each layer has either 16 heads (linear attention) or 8 heads (standard attention, in layers 4, 8, 12, 16), plus one MLP with 3,584 neurons.</li>
      <li><b>The knowledge readout:</b> the same simple probe as before, read at the layer where it works best (layer {S["ref_layer"]} for Safety, {S["knows_curve"][S["ref_layer"] - 1]:.2f} AUROC, while the verdict is {S["says"]:.2f}).</li>
      <li><b>Splitting it up:</b> the model's internal state is exactly the sum of what every head and MLP adds (checked: the parts add up within {S["recon_err"] * 100:.0f}%). So the probe's score splits into one share per part.</li>
      <li><b>Random control:</b> we shuffled the good/bad labels 500 times within each request. A part counts as significant (★, dark outline) only if it beats the largest push any part gets from shuffled labels.</li>
    </ul>
    <div class="explain">
      <div><b>Push</b> = how much a part moves the model's internal state toward "this response is good" for good responses, and toward "bad" for bad ones. Shown as a share of the total.</div>
      <div><b>Positive (blue)</b> = helps build the right answer. <b>Negative (orange)</b> = pushes toward the wrong answer and is cancelled out by other parts. All shares add up to 100%.</div>
    </div>
  </section>

  <section>
    <div class="step">Finding 1</div>
    <h2>A few parts in layers 8 and 16 do most of the pushing, in both directions</h2>
    <div class="legend"><span><i class="grad"></i></span><span>orange: pushes toward wrong answer · blue: pushes toward right answer</span><span><i class="sw" style="border:2px solid var(--navy)"></i>significant</span><span>◆ standard attention (8 heads)</span></div>
    <div class="scroll">{heatmap(S)}</div>
    <p class="note">Each row is a layer, each square one attention head, the last column the layer's MLP. Numbers are the share of the total push (%); hover a square for details. Layers after {S["ref_layer"]} come after the readout point, so they aren't shown. The starting word embedding adds {[r for r in S["rows"] if r["kind"] == "emb"][0]["share"] * 100:+.0f}%.</p>
  </section>

  <section>
    <div class="step">Finding 1, ranked</div>
    <h2>The ten biggest pushers</h2>
    {top_parts(S)}
    <p class="note">Layer 16 heads 2 and 5 together push {(next(r for r in S["rows"] if r["kind"] == "head" and r["layer"] == 16 and r["head"] == 2)["share"] + next(r for r in S["rows"] if r["kind"] == "head" and r["layer"] == 16 and r["head"] == 5)["share"]) * 100:.0f}% toward the right answer. Layer 8 has a head pushing each way (head 4 toward, head 3 against). The MLPs in layers 8 and 14 push against, and the MLP in layer 9 pushes toward. Every part shown is well outside the shuffled-label band.</p>
  </section>

  <section>
    <div class="step">Finding 2</div>
    <h2>Attention and MLPs trade pushes layer by layer</h2>
    <div class="legend"><span><i class="sw" style="background:var(--navy)"></i>attention (all heads in the layer)</span><span><i class="sw" style="background:#7FA8E0"></i>MLP</span></div>
    {layer_totals(S)}
    <p class="note">Net push of each layer's attention and MLP. Layer 8 pushes strongly toward the wrong answer; layers 9, 13 and especially 16 push it back. The final total is +100%.</p>
  </section>

  <section>
    <div class="step">Finding 3</div>
    <h2>The information is everywhere, but the push is concentrated</h2>
    <div class="stats">
      <div class="stat"><b>{B_hi} of {len(B_after6)}</b><span>parts in layers 6–{S["ref_layer"]} can tell good from bad on their own (readout ≥ 0.85)</span></div>
      <div class="stat"><b>{S["B_null_max"]:.2f}</b><span>best any part scores when the labels are shuffled</span></div>
      <div class="stat"><b>{len(big)}</b><span>parts with a push above 25% either way</span></div>
    </div>
    <p>Almost every part after layer 6 carries readable safety information, because each one reads the shared internal state and passes it along. But only a handful actually <b>move</b> the state toward or away from the answer. For editing, the pushers are what matter.</p>
  </section>

  <section>
    <div class="step">Finding 4</div>
    <h2>Inside the MLPs: a few neurons lead, but hundreds contribute</h2>
    <div class="legend"><span><i class="sw" style="background:var(--navy)"></i>Layer 9 MLP</span><span><i class="sw" style="background:#7FA8E0"></i>Layer 13 MLP</span><span>dashed: largest neuron push from shuffled labels</span></div>
    {neuron_curve(S, ["9", "13"])}
    <p class="note">The top 10 neurons give {n9["share_top10"] * 100:.0f}% (layer 9) and {n13["share_top10"] * 100:.0f}% (layer 13) of the total push, and the top 50 give {n9["share_top50"] * 100:.0f}% and {n13["share_top50"] * 100:.0f}%. But {n9["n_sig"]} and {n13["n_sig"]} neurons beat the shuffled-label line, so the effect is spread across many neurons with a short head.</p>
    <h3>Did our earlier edit pick the right neurons?</h3>
    {edited_strip(S)}
    <p class="note">Each tick is one of the 256 neurons edited in the earlier experiment (layer 17), placed by its rank. If the edit had chosen the important neurons, the ticks would cluster in the shaded top 256. Only {er_top256} of 256 are there (about {256 * 256 / 3584:.0f} expected by chance), and the median rank is {er_med:,} of 3,584. The edit worked through a broad change, not by targeting the right neurons, which fits its side effects.</p>
  </section>

  <section>
    <div class="step">Comparison</div>
    <h2>BFF finance shows a weaker, different map</h2>
    <div class="grid2">
      <div class="box"><h3>Safety: top 5 pushers</h3><ol>{topk(S)}</ol></div>
      <div class="box"><h3>BFF: top 5 pushers</h3><ol>{topk(F)}</ol></div>
    </div>
    <p class="note">★ = significant. On BFF only {sum(r["sig"] for r in F["rows"])} part (layer 19 MLP) beats the shuffled-label control: the gap is small (says {F["says"]:.2f}, knows {F["knows_curve"][F["ref_layer"] - 1]:.2f}) and there are half as many items. Layer 16 head 2 shows up in both top-5 lists, a lead worth checking.</p>
  </section>

  <section>
    <div class="step">Part 1 summary</div>
    <h2>What the map tells us</h2>
    <ul>
      <li><b>Localized, but not to one spot:</b> the safety knowledge comes from about a dozen parts with large pushes, concentrated in the standard-attention layers 8 and 16 and nearby MLPs.</li>
      <li><b>Push and pull:</b> several large parts push the wrong way and are cancelled by others. A coarse edit that touches both sides is likely to cause side effects.</li>
      <li><b>The earlier edit was untargeted:</b> its 256 neurons were a near-random pick, which explains why it was blunt.</li>
    </ul>
  </section>

{part2}
{part3}
  <footer>
    <div>Push = within-source difference in the cross-fitted probe score (good minus bad) contributed by each part, compared only between responses from the same source model with the same refusal status. Significance: 500 within-request label shuffles, family-wise 99th percentile of the largest shuffled push across all parts.</div>
    <div>Part 2: each edit was scaled so the mean norm of what it adds to the residual on training items equals the real edit's (strength 0.2). Safety AUROC on 168 test items under the team safety prompt; BFF AUROC on 74 test items; loss on 20 WikiText-2 passages of 256 tokens.</div>
    <div>Part 3: mean ablation at the verdict position (replace a part's output by its mean over the benchmark's items), on all 900 Safety and 459 BFF items. Knowledge = same-source AUROC of a fixed 5-fold cross-fitted probe from the normal model. 95% ranges: 300 paired bootstrap resamples over requests.</div>
    <div>Code: experiments/weight_space/module_map.py, edit_controls.py, switch_off.py and build_module_report.py on branch ingrid/weight-space-judge. Data: results/module_map.json, edit_controls.json, switch_off.json.</div>
  </footer>
</div>
"""
(HERE / "results" / "module_map.html").write_text(html)
print("wrote", HERE / "results" / "module_map.html")
