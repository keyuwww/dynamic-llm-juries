"""nbkit: the house presentation layer for marimo briefs (cards, tables, KPI strips, Altair charts), self-contained.

Imports marimo, pandas and altair only. In this folder it is imported as `from lib import nbkit as kit`, then `kit.enable_theme()`.

Every HTML helper returns `mo.Html`, and every chart helper an Altair chart. Category order is always explicit (`order=`),
display names come from a `labels=` mapping and colours from one `palette=` list (default PALETTE). The helpers enforce
chart text of at least 11 px, dark text on light fills, a reference line labelled once at its right end in its own colour,
facets sized to fit the 820 px card budget, "(95% interval)" in the title of interval charts and no Vega actions menu.
"""
from __future__ import annotations

import html as _html
import math
from typing import Callable, Iterable, Sequence

import altair as alt
import marimo as mo
import pandas as pd

# ── tokens ──────────────────────────────────────────────────────────────────────────────────────────────────────────
FONT = "Inter, Helvetica Neue, Helvetica, Arial, sans-serif"  # charts and HTML blocks; prose stays marimo's PT Sans
NAVY = "#1f4e79"  # the one accent: numbers that matter, first table column, the main series
BLUE = "#2e86ab"
TEAL = "#69b3a2"
GOLD = "#c9a227"
ORANGE = "#e07a5f"  # alert: missed / bad / promo windows
PLUM = "#8e5572"
SLATE = "#6c757d"  # muted labels, baseline series
SILVER = "#adb5bd"  # comparison bars, de-emphasised dots
LIGHT_BLUE = "#8fb3d9"  # secondary series next to navy
ORANGE_TEXT = "#b85c43"  # text on or next to orange
REF = "#555555"  # reference lines (dashed) and their labels
PALETTE = [NAVY, BLUE, TEAL, GOLD, ORANGE, PLUM, SLATE, SILVER]  # ordered categorical; a meaning keeps its colour
BORDER = "#e3e6ea"  # every 1 px border
PANEL = "#fafbfc"  # card background
ROW_RULE = "#e9ecef"
HEAD_BG = "#f8f9fa"
TINT = "#f1f4f8"  # highlighted rows, shade bands
TEXT, TEXT_2, TEXT_3, TEXT_4 = "#222", "#333", "#555", "#666"
WIDTH = 820  # the content budget inside a card (px) for tables, strips and charts


def theme() -> dict:
    """The Altair config: 14 px bold left title, 11 px axes, faint grid, no plot frame, top legend without title."""
    return {
        "config": {
            "font": FONT,
            "view": {"stroke": None, "continuousWidth": 320, "continuousHeight": 200},
            "axis": {"labelFontSize": 11, "titleFontSize": 11, "gridColor": "#eeeeee", "domainColor": "#cccccc", "tickColor": "#cccccc",
                     "titleFontWeight": "normal", "labelColor": TEXT_2, "titleColor": TEXT_2},
            "header": {"labelFontSize": 12, "titleFontSize": 12, "labelFontWeight": "bold", "labelColor": TEXT},
            "legend": {"labelFontSize": 11, "titleFontSize": 11, "titleFontWeight": "normal", "orient": "top", "title": None},
            "title": {"fontSize": 14, "fontWeight": "bold", "anchor": "start", "color": TEXT, "subtitleFontSize": 11.5, "subtitleColor": TEXT_3},
            "text": {"fontSize": 11, "color": TEXT_2},
            "range": {"category": PALETTE},
        }
    }


def enable_theme() -> None:
    """Register + enable the 'nbkit' theme, hide the Vega actions menu, lift the row cap. Call once in the setup cell."""
    if hasattr(alt, "theme") and hasattr(alt.theme, "register"):
        alt.theme.register("nbkit", enable=True)(theme)
    else:  # altair < 5.5
        alt.themes.register("nbkit", theme)
        alt.themes.enable("nbkit")
    alt.renderers.set_embed_options(actions=False)  # marimo reads this (altair_formatters._apply_embed_options)
    alt.data_transformers.disable_max_rows()


# ── text and numbers ────────────────────────────────────────────────────────────────────────────────────────────────
def esc(text: str) -> str:
    """Escape `$` so marimo markdown does not read '$5 … $10' as LaTeX: mo.md(esc(f"... {usd(x)} ..."))."""
    return str(text).replace("$", r"\$")


def _nan(x) -> bool:
    try:
        return x is None or math.isnan(float(x))
    except (TypeError, ValueError):
        return False


DASH = "–"


def pct(x: float, d: int = 1, sign: bool = False) -> str:
    """Proportion to percent: pct(0.342, 0) -> '34%'; sign=True gives '+3.4%'."""
    return DASH if _nan(x) else f"{100 * x:{'+' if sign else ''}.{d}f}%"


def pp(x: float, d: int = 1, sign: bool = True) -> str:
    """Difference of proportions to percentage points: pp(0.012) -> '+1.2 pp'."""
    return DASH if _nan(x) else f"{100 * x:{'+' if sign else ''}.{d}f} pp"


def k(x: float, d: int = 0) -> str:
    """Thousands: k(63_400) -> '63k'."""
    return DASH if _nan(x) else f"{x / 1e3:,.{d}f}k"


def m(x: float, d: int = 1) -> str:
    """Millions: m(79_200_000) -> '79.2M'."""
    return DASH if _nan(x) else f"{x / 1e6:,.{d}f}M"


def num(x: float, d: int = 0) -> str:
    """Plain number with separators: num(12345) -> '12,345'."""
    return DASH if _nan(x) else f"{x:,.{d}f}"


def usd(x: float, d: int = 2, compact: bool = False) -> str:
    """Dollars: usd(4.5) -> '$4.50'; usd(5.6e6, 1, compact=True) -> '$5.6M'. Wrap prose in esc()."""
    if _nan(x):
        return DASH
    s = "-" if x < 0 else ""
    a = abs(x)
    if compact and a >= 1e6:
        return f"{s}${a / 1e6:,.{d}f}M"
    if compact and a >= 1e3:
        return f"{s}${a / 1e3:,.{d}f}k"
    return f"{s}${a:,.{d}f}"


def ci(lo: float, hi: float, f: Callable[[float], str] | None = None, label: bool = False) -> str:
    """An interval as words: ci(0.01, 0.03, lambda v: pct(v, 0)) -> '1% to 3%'; label=True prefixes '95% interval '."""
    f = f or (lambda v: f"{v:.2f}")
    return ("95% interval " if label else "") + f"{f(lo)} to {f(hi)}"


# ── layout ──────────────────────────────────────────────────────────────────────────────────────────────────────────
CARD = {"border": f"1px solid {BORDER}", "border-radius": "10px", "padding": "18px 22px 14px", "background": PANEL, "margin": "6px 0 18px"}


def card(items: list):
    """One grey box per question: card([mo.md(esc("## Question?\\n\\nHow to read.")), chart, mo.md(esc(f"Answer {x}."))])."""
    return mo.vstack(items, gap=0.75).style(CARD)


def takeaways(items: Sequence[tuple]):
    """The hook boxes at the top: takeaways([("01", "Bold finding.", "What to do."), ...]); num may be int or omitted."""
    box = {"flex": "1 1 0", "border": f"1px solid {BORDER}", "border-radius": "10px", "padding": "18px 20px", "background": PANEL,
           "height": "100%", "box-sizing": "border-box"}
    num_style = f"font-size:26px;font-weight:700;color:{NAVY};line-height:1;font-variant-numeric:tabular-nums"
    cells = []
    for i, it in enumerate(items, start=1):
        n, head, body = it if len(it) == 3 else (i, *it)
        n = f"{n:02d}" if isinstance(n, int) else str(n)
        cells.append(mo.vstack([mo.md(f"<div style='{num_style}'>{_html.escape(n)}</div>"), mo.md(esc(f"**{head}**")), mo.md(esc(body))], gap=0.4).style(box))
    return mo.hstack(cells, gap=0.9, align="stretch", widths="equal")


def byline(text: str):
    """A muted one-line byline under the page title: owner, date, data window. byline("Isaac Chang · May 2026 · data to May 10")."""
    return mo.Html(f"<div style='font-size:14px;color:{SLATE};margin:-6px 0 10px'>{_html.escape(text)}</div>")


def note(text: str, label: str = ""):
    """An italic inline caveat line, quiet and small: note("Attributed, not incremental: there was no holdout.", label="Caveat")."""
    e = _html.escape
    lab = f"<span style='font-style:normal;font-weight:600;color:{TEXT_4}'>{e(label)}:</span> " if label else ""
    return mo.Html(f"<div style='font-style:italic;font-size:13.5px;line-height:1.55;color:{TEXT_3};max-width:{WIDTH}px;margin:2px 0 6px'>{lab}{e(text)}</div>")


# ── HTML blocks ─────────────────────────────────────────────────────────────────────────────────────────────────────
def kpi_strip(items: Sequence[tuple[str, str, str]], width: int = WIDTH):
    """Headline tiles: kpi_strip([("Spend", "$5.6M", "of a $14.4M budget (39%)."), ...]). The detail carries the caveat."""
    e = _html.escape
    tiles = "".join(
        f"<div style='flex:1 1 0;min-width:150px;padding:12px 14px;border:1px solid {BORDER};border-radius:8px;background:#fff'>"
        f"<div style='font-size:11.5px;color:{TEXT_4};text-transform:uppercase;letter-spacing:.04em'>{e(label)}</div>"
        f"<div style='font-size:22px;font-weight:700;color:{NAVY};margin:2px 0;font-variant-numeric:tabular-nums'>{e(value)}</div>"
        f"<div style='font-size:12.5px;color:#444;line-height:1.4'>{e(detail)}</div></div>"
        for label, value, detail in items
    )
    return mo.Html(f"<div style='display:flex;gap:10px;flex-wrap:wrap;max-width:{width}px;margin:4px 0 12px;font-family:{FONT}'>{tiles}</div>")


def _caption(caption: str, sub: str = "") -> str:
    e = _html.escape
    cap = f"<div style='font-weight:700;font-size:15px;color:{TEXT}'>{e(caption)}</div>" if caption else ""
    if sub:
        cap += f"<div style='color:{TEXT_4};font-size:12.5px;margin:2px 0 0'>{e(sub)}</div>"
    return f"<div style='margin-bottom:8px'>{cap}</div>" if cap else ""


def _foot(note_text: str) -> str:
    return f"<div style='color:{TEXT_3};font-size:12.5px;margin-top:8px;line-height:1.5'>{_html.escape(note_text)}</div>" if note_text else ""


def html_table(df: pd.DataFrame, caption: str = "", note: str = "", right: Iterable[str] = (), bold_first: bool = True, width: int = WIDTH, subcaption: str = ""):
    """Read-only table (never a dataframe widget). Format numbers to strings first: html_table(t, right=("Claims", "Rate"))."""
    e = _html.escape
    right = set(right)
    cell = f"padding:8px 12px;border-bottom:1px solid {ROW_RULE};vertical-align:top;font-size:13.5px;line-height:1.4"
    head = "".join(
        f"<th style='padding:8px 12px;text-align:{'right' if c in right else 'left'};font-size:11.5px;font-weight:600;color:{TEXT_4};"
        f"text-transform:uppercase;letter-spacing:.04em;border-bottom:2px solid {NAVY};background:{HEAD_BG}'>{e(str(c))}</th>"
        for c in df.columns
    )
    rows = []
    for _, r in df.iterrows():
        tds = []
        for i, c in enumerate(df.columns):
            st = cell + (";text-align:right;font-variant-numeric:tabular-nums" if c in right else "")
            st += f";font-weight:600;color:{NAVY};white-space:nowrap" if bold_first and i == 0 else f";color:{TEXT_2}"
            v = r[c]
            tds.append(f"<td style='{st}'>{e(DASH if _nan(v) else str(v))}</td>")
        rows.append(f"<tr>{''.join(tds)}</tr>")
    return mo.Html(
        f"<div style='max-width:{width}px;margin:4px 0 12px;font-family:{FONT}'>{_caption(caption, subcaption)}"
        f"<div style='border:1px solid {BORDER};border-radius:8px;overflow:hidden'><table style='width:100%;border-collapse:collapse;background:#fff'>"
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>{_foot(note)}</div>"
    )


def rules_table(rows: Sequence[tuple[str, str]], total_label: str = "", total_value: str = "", caption: str = "", subcaption: str = "", note: str = "",
                highlight: set[int] | None = None, highlight_label: str = "", width: int = 760):
    """Definitions: bold navy term, plain-words rule; optional bold total row and tinted row group.
    rules_table([("Eligible", "No order in 12 months."), ...], total_label="Audience", total_value="79.2M", highlight={2, 3}, highlight_label="Low intent")."""
    e = _html.escape
    cell = f"padding:9px 14px;border-bottom:1px solid {ROW_RULE};vertical-align:top;font-size:14px;line-height:1.45"
    hl = set(highlight or ())
    body, label_done = [], False
    for i, (term, rule) in enumerate(rows):
        if i in hl and highlight_label and not label_done:
            body.append(f"<tr><td colspan='2' style='padding:6px 14px 2px;font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;"
                        f"color:{SLATE};background:{TINT};border-left:3px solid {NAVY}'>{e(highlight_label)}</td></tr>")
            label_done = True
        body.append(
            f"<tr style='{'background:' + TINT if i in hl else ''}'><td style='{cell};width:34%;font-weight:600;color:{NAVY};white-space:nowrap;"
            f"border-left:3px solid {NAVY if i in hl else 'transparent'}'>{e(term)}</td><td style='{cell};color:{TEXT_2}'>{e(rule)}</td></tr>"
        )
    if total_label:
        body.append(f"<tr><td style='padding:11px 14px;border-top:2px solid {NAVY};font-weight:700;color:{TEXT};font-size:14px'>{e(total_label)}</td>"
                    f"<td style='padding:11px 14px;border-top:2px solid {NAVY};font-weight:700;color:{NAVY};font-size:20px;text-align:right;"
                    f"font-variant-numeric:tabular-nums'>{e(total_value)}</td></tr>")
    return mo.Html(
        f"<div style='max-width:{width}px;margin:4px 0 8px;font-family:{FONT}'>{_caption(caption, subcaption)}"
        f"<div style='border:1px solid {BORDER};border-radius:8px;overflow:hidden'><table style='width:100%;border-collapse:collapse;background:#fff'>"
        f"<tbody>{''.join(body)}</tbody></table></div>{_foot(note)}</div>"
    )


def sankey(nodes: list[dict], links: list[tuple[str, str, float]], title: str = "", subtitle: str = "", note: str = "", denominator_label: str = "of total",
           width: int = WIDTH, height: int = 400, node_width: int = 14, gap: int = 18, label_fmt: Callable[[float], str] | None = None):
    """Left-to-right Sankey as inline SVG (no JS). Ribbons take the target's colour so an outcome reads as one colour root to leaf.
    nodes=[{"id", "label", "col", "color", "left_label"?}], links=[(src, tgt, value)]; sankey(nodes, links, title="Where the audience went")."""
    e = _html.escape
    label_fmt = label_fmt or (lambda v: m(v))
    by_id = {n["id"]: dict(n) for n in nodes}
    ids = [n["id"] for n in nodes]
    inflow, outflow = {i: 0.0 for i in by_id}, {i: 0.0 for i in by_id}
    for s, t, v in links:
        outflow[s] += v
        inflow[t] += v
    for i, n in by_id.items():
        n["value"] = max(inflow[i], outflow[i])
    total = max(n["value"] for n in by_id.values()) or 1.0
    ncols = max(n["col"] for n in by_id.values()) + 1
    pad_top = ((58 if subtitle else 40) if title else 12)
    pad_bot, label_w = 16, 250
    plot_h = height - pad_top - pad_bot
    scale = min((plot_h - gap * (sum(1 for n in by_id.values() if n["col"] == c) - 1)) / max(sum(n["value"] for n in by_id.values() if n["col"] == c), 1e-9)
                for c in range(ncols))
    col_x = [20 + c * (width - 20 - label_w - node_width) / max(ncols - 1, 1) for c in range(ncols)]
    for c in range(ncols):
        col_nodes = [by_id[i] for i in ids if by_id[i]["col"] == c]
        if c == 0:
            y = pad_top
            for n in col_nodes:
                n["x"], n["y"], n["h"] = col_x[c], y, max(n["value"] * scale, 1.5)
                y += n["value"] * scale + gap
            continue
        for n in col_nodes:
            n["x"], n["h"] = col_x[c], max(n["value"] * scale, 1.5)
            ys, ws = [], []
            for s_, t_, v_ in links:
                if t_ == n["id"]:
                    off = sum(v2 * scale for s2, t2, v2 in links if s2 == s_ and ids.index(t2) < ids.index(t_))
                    ys.append(by_id[s_]["y"] + off)
                    ws.append(v_)
            n["y"] = sum(a * b for a, b in zip(ys, ws)) / sum(ws) if ws else pad_top
        for i in range(1, len(col_nodes)):
            col_nodes[i]["y"] = max(col_nodes[i]["y"], col_nodes[i - 1]["y"] + col_nodes[i - 1]["h"] + gap)
        over = col_nodes[-1]["y"] + col_nodes[-1]["h"] - (height - pad_bot) if col_nodes else 0
        if over > 0:
            for i in range(len(col_nodes) - 1, -1, -1):
                col_nodes[i]["y"] -= over
                if i:
                    over = max(0.0, col_nodes[i - 1]["y"] + col_nodes[i - 1]["h"] + gap - col_nodes[i]["y"])
    out_y, in_y = {i: by_id[i]["y"] for i in by_id}, {i: by_id[i]["y"] for i in by_id}
    ribbons = []
    for s, t, v in links:
        a, b, h = by_id[s], by_id[t], v * scale
        x0, x1, y0, y1 = a["x"] + node_width, b["x"], out_y[s], in_y[t]
        out_y[s] += h
        in_y[t] += h
        cx = (x0 + x1) / 2
        d = f"M{x0},{y0} C{cx},{y0} {cx},{y1} {x1},{y1} L{x1},{y1 + h} C{cx},{y1 + h} {cx},{y0 + h} {x0},{y0 + h} Z"
        ribbons.append(f"<path d='{d}' fill='{b['color']}' fill-opacity='0.42'><title>{e(a['label'])} → {e(b['label'])}: {e(label_fmt(v))} ({v / total:.0%} {e(denominator_label)})</title></path>")
    rects, texts = [], []
    for n in by_id.values():
        rects.append(f"<rect x='{n['x']:.1f}' y='{n['y']:.1f}' width='{node_width}' height='{n['h']:.1f}' rx='2' fill='{n['color']}'>"
                     f"<title>{e(n['label'])}: {e(label_fmt(n['value']))} ({n['value'] / total:.0%} {e(denominator_label)})</title></rect>")
        share = n["value"] / total
        val = (f"{label_fmt(n['value'])} · {share:.1%}" if share < 0.02 else f"{label_fmt(n['value'])} · {share:.0%}") if n["col"] else label_fmt(n["value"])
        tx, anchor = (n["x"] - 8, "end") if n.get("left_label") else (n["x"] + node_width + 8, "start")
        texts.append(f"<text x='{tx:.1f}' y='{n['y'] + n['h'] / 2:.1f}' text-anchor='{anchor}' dominant-baseline='central' font-size='12.5' fill='{TEXT}' stroke='#fff' "
                     f"stroke-width='3.5' stroke-linejoin='round' paint-order='stroke'><tspan font-weight='600'>{e(n['label'])}</tspan>"
                     f"<tspan dx='6' fill='{TEXT_3}' font-variant-numeric='tabular-nums'>{e(val)}</tspan></text>")
    head = f"<text x='0' y='18' font-size='14' font-weight='700' fill='{TEXT}'>{e(title)}</text>" if title else ""
    if subtitle:
        head += f"<text x='0' y='36' font-size='11.5' fill='{TEXT_3}'>{e(subtitle)}</text>"
    svg = (f"<svg viewBox='0 0 {width} {height}' width='100%' style='max-width:{width}px;display:block;font-family:{FONT}' role='img' aria-label='{e(title or 'Sankey diagram')}'>"
           f"{head}{''.join(ribbons)}{''.join(rects)}{''.join(texts)}</svg>")
    foot = f"<div style='color:{TEXT_3};font-size:12.5px;margin-top:8px;line-height:1.5;max-width:{width}px'>{e(note)}</div>" if note else ""
    return mo.Html(f"<div style='margin:4px 0 12px'>{svg}{foot}</div>")


# ── chart internals ─────────────────────────────────────────────────────────────────────────────────────────────────
def _relabel(df: pd.DataFrame, col: str, labels: dict | None, order: Sequence | None) -> tuple[pd.DataFrame, list[str]]:
    """Map `col` to display labels (as str) and return the frame plus the display order (explicit order first, then the rest)."""
    d = df.copy()
    raw = [str(v) for v in (order if order is not None else pd.unique(d[col]))]
    extra = [str(v) for v in pd.unique(d[col]) if str(v) not in raw]
    lab = {str(k_): str(v) for k_, v in (labels or {}).items()}
    d[col] = d[col].astype(str).map(lambda v: lab.get(v, v))
    return d, list(dict.fromkeys(lab.get(v, v) for v in raw + extra))


def _is_dark(hex_color: str) -> bool:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return True
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    lum = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4  # noqa: E731
    return 0.2126 * lum(r) + 0.7152 * lum(g) + 0.0722 * lum(b) < 0.30


def _title(title: str, subtitle: str = "", interval: bool = False):
    t = title
    if interval and t and "95%" not in t:
        t = f"{t} (95% interval)"
    if subtitle:
        return alt.TitleParams(text=t, subtitle=subtitle)
    return t


def _datum(v, x_type: str):
    if x_type == "T":
        t = pd.to_datetime(v)
        return alt.datum(alt.DateTime(year=t.year, month=t.month, date=t.day))
    return alt.datum(v)


def _wrap_axis(**kw) -> alt.Axis:
    return alt.Axis(labelExpr="split(datum.label, '\\n')", labelAngle=0, **kw)


# ── charts ──────────────────────────────────────────────────────────────────────────────────────────────────────────
def bars(df: pd.DataFrame, x: str, y: str, order: Sequence | None = None, labels: dict | None = None, color: str | None = None, color_order: Sequence | None = None,
         color_labels: dict | None = None, stack: bool = True, lo: str | None = None, hi: str | None = None, total: bool = False, palette: Sequence[str] | None = None,
         title: str = "", subtitle: str = "", y_title: str = "", x_title: str = "", fmt: str = ".0%", label: bool = True, label_min: float = 0.0,
         width: int = 70, height: int = 240, legend: bool = True) -> alt.Chart:
    """Labelled bars. Plain: bars(d, x="group", y="rate", order=ORDER). Stacked: color="channel" (total=True adds the bold stack total).
    Grouped: color=..., stack=False. lo/hi draw 95% rules on plain or grouped bars. A newline in an x label wraps it."""
    d, x_sort = _relabel(df, x, labels, order)
    enc_x = alt.X(f"{x}:N", sort=x_sort, title=x_title or None, axis=_wrap_axis(labelLimit=int(width * 1.3)))
    enc_y = alt.Y(f"{y}:Q", title=y_title or None, axis=alt.Axis(format=fmt, grid=True))
    tips = [alt.Tooltip(f"{x}:N"), alt.Tooltip(f"{y}:Q", format=fmt)]
    if color:
        d, c_sort = _relabel(d, color, color_labels, color_order)
        pal = list(palette or PALETTE)[: len(c_sort)]
        enc_c = alt.Color(f"{color}:N", sort=c_sort, scale=alt.Scale(domain=c_sort, range=pal), legend=alt.Legend(title=None) if legend else None)
        text_c = alt.Color(f"{color}:N", sort=c_sort, scale=alt.Scale(domain=c_sort, range=["#ffffff" if _is_dark(p) else TEXT for p in pal]), legend=None)
        d["_ord"] = d[color].map({c: i for i, c in enumerate(c_sort)})
        d = d.sort_values([x, "_ord"])
        tips.insert(1, alt.Tooltip(f"{color}:N"))
        if stack:
            d["_top"] = d.groupby(x)[y].cumsum()
            d["_mid"] = d["_top"] - d[y] / 2
            base = alt.Chart(d)
            layers = [base.mark_bar(size=width * 0.8).encode(x=enc_x, y=alt.Y(f"{y}:Q", title=y_title or None, axis=alt.Axis(format=fmt), stack=True), color=enc_c,
                                                             order=alt.Order("_ord:Q"), tooltip=tips)]
            if label:
                layers.append(base.transform_filter(alt.datum[y] >= label_min).mark_text(fontSize=11, baseline="middle").encode(
                    x=enc_x, y="_mid:Q", text=alt.Text(f"{y}:Q", format=fmt), color=text_c))
            if total:
                tot = d.groupby(x, as_index=False)[y].sum()
                layers.append(alt.Chart(tot).mark_text(dy=-7, fontSize=12, fontWeight="bold", color=TEXT).encode(x=enc_x, y=f"{y}:Q", text=alt.Text(f"{y}:Q", format=fmt)))
        else:
            off = alt.XOffset(f"{color}:N", sort=c_sort)
            base = alt.Chart(d)
            layers = [base.mark_bar().encode(x=enc_x, xOffset=off, y=enc_y, color=enc_c, tooltip=tips)]
            if lo and hi:
                layers.append(base.mark_rule(color=TEXT_2, strokeWidth=1.5).encode(x=enc_x, xOffset=off, y=f"{lo}:Q", y2=f"{hi}:Q"))
            if label:
                layers.append(base.mark_text(dy=-6, fontSize=11, color=TEXT_2).encode(x=enc_x, xOffset=off, y=f"{hi or y}:Q", text=alt.Text(f"{y}:Q", format=fmt)))
    else:
        base = alt.Chart(d)
        layers = [base.mark_bar(size=width * 0.8, color=(palette or [NAVY])[0]).encode(x=enc_x, y=enc_y, tooltip=tips)]
        if lo and hi:
            layers.append(base.mark_rule(color=TEXT_2, strokeWidth=1.5).encode(x=enc_x, y=f"{lo}:Q", y2=f"{hi}:Q"))
        if label:
            layers.append(base.mark_text(dy=-6, fontSize=11, color=TEXT_2).encode(x=enc_x, y=f"{hi or y}:Q", text=alt.Text(f"{y}:Q", format=fmt)))
    ch = alt.layer(*layers).properties(width=max(width * len(x_sort), 160), height=height, title=_title(title, subtitle, bool(lo and hi)))
    return ch.resolve_scale(color="independent") if color and stack and label else ch  # band text keeps its own dark/white scale


def dot_rows(df: pd.DataFrame, y: str, x: str, lo: str, hi: str, order: Sequence | None = None, labels: dict | None = None, group: str | None = None,
             group_order: Sequence | None = None, palette: Sequence[str] | None = None, emphasis: str | None = None, shade: Sequence | None = None, shade_label: str = "",
             vline: float | None = None, vline_label: str = "", direct_labels: bool | None = None, title: str = "", subtitle: str = "", x_title: str = "",
             fmt: str = ".1f", width: int = 520, row_height: int = 56, x_domain: tuple[float, float] | None = None) -> alt.Chart:
    """Effect rows: one row per `y`, one dot + 95% line per `group` inside it. dot_rows(d, y="segment", x="lift", lo="lo", hi="hi", group="tier",
    shade=["dormant"], shade_label="Low intent", vline=0, vline_label="no effect"). Groups are named once: legend, or direct labels if <= 4 groups and no legend."""
    d, y_sort = _relabel(df, y, labels, order)
    shade_lab = [str((labels or {}).get(s, s)) for s in (shade or [])]
    if group:
        d, g_sort = _relabel(d, group, None, group_order)
    else:
        d["_g"], group, g_sort = "all", "_g", ["all"]
    multi = len(g_sort) > 1
    direct = (multi and len(g_sort) <= 4) if direct_labels is None else direct_labels
    if emphasis is not None:
        color = alt.condition(alt.datum[group] == str(emphasis), alt.value(NAVY), alt.value(SILVER))
    else:
        pal = list(palette or PALETTE)[: len(g_sort)]
        color = alt.Color(f"{group}:N", sort=g_sort, scale=alt.Scale(domain=g_sort, range=pal),
                          legend=alt.Legend(title=None, orient="top", direction="horizontal") if multi and not direct else None)
    xs = alt.Scale(domain=list(x_domain)) if x_domain else alt.Scale(zero=False, nice=True)
    xt = x_title or None  # same title on every layer so Vega-Lite does not join field names
    # direct group labels sit left of the plot, so pad the row labels by the longest group name (about 6.5 px per character at 11 px)
    pad = 8 if not direct else int(16 + 6.5 * max(len(str(g)) for g in g_sort))
    enc_y = alt.Y(f"{y}:N", sort=y_sort, title=None, axis=alt.Axis(labelFontSize=12, labelFontWeight="bold", labelColor=TEXT, labelLimit=220, ticks=False, domain=False,
                                                              grid=False, labelPadding=pad))
    off = alt.YOffset(f"{group}:N", sort=g_sort)
    tips = [alt.Tooltip(f"{y}:N"), alt.Tooltip(f"{x}:Q", format=fmt), alt.Tooltip(f"{lo}:Q", format=fmt), alt.Tooltip(f"{hi}:Q", format=fmt)] + ([alt.Tooltip(f"{group}:N")] if multi else [])
    layers = []
    if shade_lab:
        sh = pd.DataFrame({y: shade_lab})
        layers.append(alt.Chart(sh).mark_rect(color=TINT).encode(y=alt.Y(f"{y}:N", sort=y_sort), x=alt.value(0), x2=alt.value(width)))
        if shade_label:
            layers.append(alt.Chart(sh.head(1)).mark_text(align="right", baseline="top", dx=-6, dy=-row_height / 2 + 4, fontSize=11, fontWeight="bold", color=SLATE,
                                                          text=shade_label.upper()).encode(y=alt.Y(f"{y}:N", sort=y_sort), x=alt.value(width)))
    if vline is not None:
        v = pd.DataFrame({"_v": [vline]})
        layers.append(alt.Chart(v).mark_rule(color=REF, strokeDash=[4, 3], strokeWidth=1.2).encode(x=alt.X("_v:Q", scale=xs, title=xt)))
        if vline_label:
            layers.append(alt.Chart(v).mark_text(align="left", baseline="bottom", dx=4, dy=-3, fontSize=11, color=REF, text=vline_label).encode(x=alt.X("_v:Q", scale=xs, title=xt), y=alt.value(0)))
    base = alt.Chart(d)
    layers.append(base.mark_rule(strokeWidth=1.8).encode(y=enc_y, yOffset=off, x=alt.X(f"{lo}:Q", scale=xs, title=xt, axis=alt.Axis(format=fmt)), x2=f"{hi}:Q", color=color))
    layers.append(base.mark_point(filled=True, size=60, opacity=1).encode(y=enc_y, yOffset=off, x=alt.X(f"{x}:Q", scale=xs, title=xt), color=color, tooltip=tips))
    if direct:
        tc = alt.Color(f"{group}:N", sort=g_sort, scale=alt.Scale(domain=g_sort, range=list(palette or PALETTE)[: len(g_sort)]), legend=None) if emphasis is None else alt.value(TEXT_2)
        # name the groups once, on the first row only (the study's fix for 28 repeated tier labels)
        layers.append(alt.Chart(d[d[y] == y_sort[0]]).mark_text(align="right", baseline="middle", dx=-6, fontSize=11).encode(y=enc_y, yOffset=off, x=alt.value(0), text=f"{group}:N", color=tc))
    return alt.layer(*layers).properties(width=width, height=row_height * len(y_sort), title=_title(title, subtitle, True))


def dot_grid(df: pd.DataFrame, x: str, y: str, lo: str, hi: str, column: str, order: Sequence | None = None, labels: dict | None = None,
             column_order: Sequence | None = None, column_labels: dict | None = None, color: str | None = None, color_order: Sequence | None = None,
             palette: Sequence[str] | None = None, hline: float | None = None, hline_label: str = "", y_max: float | None = None, log_y: bool = False,
             log_ticks: Sequence[float] | None = None, title: str = "", subtitle: str = "", y_title: str = "", fmt: str = ".0%", total_width: int = WIDTH,
             facet_width: int | None = None, height: int = 180) -> alt.Chart:
    """Small multiples of point + 95% line: one facet per `column`, categories on x. dot_grid(d, x="period", y="rel", lo="lo", hi="hi",
    column="segment", column_order=ORDER, labels=LABELS, hline=0, hline_label="no lift"). Facet width defaults to fit `total_width`;
    `color` dodges with xOffset; the reference line is labelled once (first facet, right end); values above `y_max` are capped with a ▲."""
    d, x_sort = _relabel(df, x, labels, order)
    d, f_sort = _relabel(d, column, column_labels if column_labels is not None else labels, column_order)
    n_f = len(f_sort)
    fw = facet_width or max(60, int((total_width - 70 - 12 * (n_f - 1)) / n_f))
    d["_clip"] = False
    if y_max is not None:
        d["_clip"] = d[hi] > y_max
        d[hi] = d[hi].clip(upper=y_max)
        d[y] = d[y].clip(upper=y_max)
    ys = alt.Scale(type="log") if log_y else alt.Scale(zero=False, nice=True)
    axis = alt.Axis(format=fmt, values=list(log_ticks)) if log_ticks else alt.Axis(format=fmt)
    enc_x = alt.X(f"{x}:N", sort=x_sort, title=None, axis=_wrap_axis(labelLimit=fw, labelFontSize=11))
    if color:
        d, c_sort = _relabel(d, color, None, color_order)
        pal = list(palette or PALETTE)[: len(c_sort)]
        enc_c = alt.Color(f"{color}:N", sort=c_sort, scale=alt.Scale(domain=c_sort, range=pal), legend=alt.Legend(title=None))
        off = {"xOffset": alt.XOffset(f"{color}:N", sort=c_sort)}
    else:
        enc_c, off = alt.value(NAVY), {}
    tips = [alt.Tooltip(f"{column}:N"), alt.Tooltip(f"{x}:N"), alt.Tooltip(f"{y}:Q", format=fmt), alt.Tooltip(f"{lo}:Q", format=fmt), alt.Tooltip(f"{hi}:Q", format=fmt)]
    base = alt.Chart()
    layers = []
    if hline is not None:
        layers.append(base.mark_rule(color=REF, strokeDash=[4, 3], strokeWidth=1.2).encode(y=alt.datum(hline)))
        if hline_label:
            layers.append(base.transform_filter(alt.datum[column] == f_sort[0]).transform_aggregate(_n="count()").mark_text(
                align="right", baseline="bottom", dx=-2, dy=-3, fontSize=11, color=REF, text=hline_label).encode(y=alt.datum(hline), x=alt.value(fw)))
    layers.append(base.mark_rule(strokeWidth=1.6, opacity=0.8).encode(x=enc_x, y=alt.Y(f"{lo}:Q", title=y_title or None, scale=ys, axis=axis), y2=f"{hi}:Q", color=enc_c, **off))
    layers.append(base.mark_point(filled=True, size=55, opacity=1).encode(x=enc_x, y=alt.Y(f"{y}:Q", scale=ys), color=enc_c, tooltip=tips, **off))
    if y_max is not None and d["_clip"].any():
        layers.append(base.transform_filter(alt.datum._clip).mark_text(text="▲", fontSize=11, dy=-2, baseline="bottom").encode(x=enc_x, y=f"{hi}:Q", color=enc_c, **off))
    ch = alt.layer(*layers, data=d).properties(width=fw, height=height)
    return ch.facet(column=alt.Column(f"{column}:N", sort=f_sort, title=None, header=alt.Header(labelFontSize=12, labelLimit=fw + 10)), spacing=12).resolve_scale(
        y="shared").properties(title=_title(title, subtitle, True))


def diff_dots(df: pd.DataFrame, x: str, offset: str, y: str, lo: str, hi: str, order: Sequence | None = None, labels: dict | None = None,
              offset_order: Sequence | None = None, offset_labels: dict | None = None, palette: Sequence[str] | None = None, zero_label: str = "no change",
              title: str = "", subtitle: str = "", y_title: str = "change against control", x_title: str = "", fmt: str = "+.1f", width: int = 640, height: int = 280) -> alt.Chart:
    """Arm-minus-control effects: per `x` (arm), dots dodged by `offset` (component) with 95% lines and a labelled zero.
    diff_dots(d, x="tier", offset="component", y="diff", lo="lo", hi="hi", subtitle="Control: 41 buyers per 10,000")."""
    d, x_sort = _relabel(df, x, labels, order)
    d, o_sort = _relabel(d, offset, offset_labels, offset_order)
    lo_v, hi_v = float(min(d[lo].min(), 0)), float(max(d[hi].max(), 0))
    pad = 0.08 * ((hi_v - lo_v) or 1)
    ys = alt.Scale(domain=[lo_v - pad, hi_v + pad], nice=True, zero=True)
    pal = list(palette or PALETTE)[: len(o_sort)]
    color = alt.Color(f"{offset}:N", sort=o_sort, scale=alt.Scale(domain=o_sort, range=pal),
                      legend=alt.Legend(title=None, orient="top", direction="horizontal", symbolType="circle", symbolSize=80))
    enc_x = alt.X(f"{x}:N", sort=x_sort, title=x_title or None, scale=alt.Scale(paddingInner=0.45, paddingOuter=0.3), axis=_wrap_axis(labelFontSize=12, ticks=False, domain=False))
    xo = alt.XOffset(f"{offset}:N", sort=o_sort, scale=alt.Scale(paddingInner=0.2, paddingOuter=0.1))
    tips = [alt.Tooltip(f"{x}:N"), alt.Tooltip(f"{offset}:N"), alt.Tooltip(f"{y}:Q", format=fmt), alt.Tooltip(f"{lo}:Q", format=fmt), alt.Tooltip(f"{hi}:Q", format=fmt)]
    z = pd.DataFrame({"_y": [0.0], "_t": [zero_label]})
    layers = [alt.Chart(z).mark_rule(color=REF, strokeDash=[4, 3], strokeWidth=1).encode(y=alt.Y("_y:Q", scale=ys))]
    if zero_label:
        layers.append(alt.Chart(z).mark_text(align="right", baseline="bottom", dx=-2, dy=-3, color=REF, fontSize=11).encode(y=alt.Y("_y:Q", scale=ys), x=alt.value(width), text="_t:N"))
    base = alt.Chart(d)
    layers.append(base.mark_rule(strokeWidth=2.2, opacity=0.85).encode(x=enc_x, xOffset=xo, y=alt.Y(f"{lo}:Q", title=y_title or None, scale=ys, axis=alt.Axis(format=fmt.lstrip("+"),
                                                                       labelExpr="datum.value > 0 ? '+' + datum.label : datum.label")), y2=f"{hi}:Q", color=color, tooltip=tips))
    layers.append(base.mark_point(filled=True, size=90, opacity=1, stroke="white", strokeWidth=0.8).encode(x=enc_x, xOffset=xo, y=alt.Y(f"{y}:Q", scale=ys), color=color, tooltip=tips))
    return alt.layer(*layers).properties(width=width, height=height, title=_title(title, subtitle, True))


def lines(df: pd.DataFrame, x: str, y: str, color: str | None = None, color_order: Sequence | None = None, color_labels: dict | None = None, palette: Sequence[str] | None = None,
          lo: str | None = None, hi: str | None = None, shade: Sequence[tuple] | None = None, vlines: Sequence[tuple] | None = None, hline: float | None = None,
          hline_label: str = "", x_type: str = "T", x_format: str = "%b %d", title: str = "", subtitle: str = "", y_title: str = "", x_title: str = "", fmt: str = ".2f",
          zero: bool = False, width: int = 760, height: int = 260, points: bool = False, legend: bool = True) -> alt.Chart:
    """Time series. shade=[(x0, x1, label)] tints windows with labels in a strip above the plot; vlines=[(x, label)] labelled
    dashed lines; hline + hline_label at the right end; lo/hi band. lines(d, x="date", y="buyers", color="arm", shade=[("2025-11-19", "2025-11-24", "$5")])."""
    d = df.copy()
    if color:
        d, c_sort = _relabel(d, color, color_labels, color_order)
        pal = list(palette or PALETTE)[: len(c_sort)]
        enc_c = alt.Color(f"{color}:N", sort=c_sort, scale=alt.Scale(domain=c_sort, range=pal),
                          legend=alt.Legend(title=None, symbolType="stroke", symbolStrokeWidth=3, symbolOpacity=1) if legend else None)
    else:
        enc_c = alt.value((palette or [NAVY])[0])
    ax = alt.Axis(format=x_format, labelAngle=0, grid=False, tickCount="week") if x_type == "T" else alt.Axis(labelAngle=0, grid=False)
    enc_x = alt.X(f"{x}:{x_type}", title=x_title or None, axis=ax)
    ys = alt.Scale(zero=zero, nice=True)
    enc_y = alt.Y(f"{y}:Q", title=y_title or None, axis=alt.Axis(format=fmt), scale=ys)
    one = alt.Chart(pd.DataFrame({"_n": [1]}))
    layers = []
    has_shade_labels = any(len(s) > 2 and s[2] for s in (shade or []))
    for i, s in enumerate(shade or []):
        x0, x1 = s[0], s[1]
        layers.append(one.mark_rect(color=ORANGE, opacity=0.10 if i % 2 == 0 else 0.18).encode(x=_datum(x0, x_type), x2=_datum(x1, x_type)))
        if len(s) > 2 and s[2]:
            mid = pd.Timestamp(x0) + (pd.Timestamp(x1) - pd.Timestamp(x0)) / 2 if x_type == "T" else (x0 + x1) / 2
            layers.append(one.mark_text(align="center", baseline="bottom", dy=-5, fontSize=11, color=ORANGE_TEXT, text=s[2]).encode(x=_datum(mid, x_type), y=alt.value(0)))
    for xv, lab in (vlines or []):
        layers.append(one.mark_rule(color=REF, strokeDash=[4, 3]).encode(x=_datum(xv, x_type)))
        if lab:
            layers.append(one.mark_text(align="left", baseline="top", dx=4, dy=4, fontSize=11, color=REF, text=lab).encode(x=_datum(xv, x_type), y=alt.value(0)))
    if hline is not None:
        layers.append(one.mark_rule(color=REF, strokeDash=[4, 3]).encode(y=alt.datum(hline)))
        if hline_label:
            layers.append(one.mark_text(align="right", baseline="bottom", dx=-2, dy=-3, fontSize=11, color=REF, text=hline_label).encode(y=alt.datum(hline), x=alt.value(width)))
    base = alt.Chart(d)
    if lo and hi:
        layers.append(base.mark_area(opacity=0.15).encode(x=enc_x, y=alt.Y(f"{lo}:Q", scale=ys), y2=f"{hi}:Q", color=enc_c))
    tips = [alt.Tooltip(f"{x}:{x_type}"), alt.Tooltip(f"{y}:Q", format=fmt)] + ([alt.Tooltip(f"{color}:N")] if color else [])
    layers.append(base.mark_line(strokeWidth=2, point=points).encode(x=enc_x, y=enc_y, color=enc_c, tooltip=tips))
    ch = alt.layer(*layers).properties(width=width, height=height, title=_title(title, subtitle, bool(lo and hi)))
    return ch.properties(padding={"top": 18 if has_shade_labels else 5, "left": 5, "right": 5, "bottom": 5})


def profile_bars(df: pd.DataFrame, y: str, panels: Sequence[tuple], order: Sequence | None = None, labels: dict | None = None, color: str = NAVY,
                 title: str = "", subtitle: str = "", panel_width: int | None = None, row_height: int = 26, total_width: int = WIDTH) -> alt.Chart:
    """One category profiled on 2-3 measures, shared y, one colour (same category, same colour), values at bar ends.
    profile_bars(d, y="segment", panels=[("share", "share of users", ".0%"), ("cr", "conversion", ".1%")], order=ORDER)."""
    d, y_sort = _relabel(df, y, labels, order)
    pw = panel_width or max(140, int((total_width - 200) / len(panels)) - 20)
    out = []
    for i, p in enumerate(panels):
        col, ptitle, f = p[0], p[1], (p[2] if len(p) > 2 else ".0%")
        enc_y = alt.Y(f"{y}:N", sort=y_sort, title=None, axis=alt.Axis(labelFontSize=12, labelColor=TEXT, ticks=False, domain=False, labelLimit=200) if i == 0 else None)
        b = alt.Chart(d)
        xs = alt.Scale(domain=[0, float(d[col].max()) * 1.22])
        layer = alt.layer(
            b.mark_bar(color=color, height=row_height * 0.7).encode(y=enc_y, x=alt.X(f"{col}:Q", title=None, axis=None, scale=xs), tooltip=[alt.Tooltip(f"{y}:N"), alt.Tooltip(f"{col}:Q", format=f)]),
            b.mark_text(align="left", dx=4, fontSize=11, color=TEXT_2).encode(y=alt.Y(f"{y}:N", sort=y_sort), x=alt.X(f"{col}:Q", scale=xs), text=alt.Text(f"{col}:Q", format=f)),
        ).properties(width=pw, height=row_height * len(y_sort), title=alt.TitleParams(ptitle, fontSize=12, fontWeight="normal", color=TEXT_2, anchor="start"))
        out.append(layer)
    return alt.hconcat(*out, spacing=16).properties(title=_title(title, subtitle))
