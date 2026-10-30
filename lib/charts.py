"""The chart shapes the findings page needs that nbkit lacks, drawn with nbkit's tokens and theme.

row_dots:      one dot and 95% line per row, each row coloured by meaning (navy for the quantity that matters, grey for a
               comparison). Value labels sit right of the interval. A labelled dashed reference line and an optional
               labelled dotted benchmark line are both in REF grey.
routing_rows:  one row per juror: the comparison in grey and the result in navy, joined by a bar, with a short dark tick for a
               benchmark (the random 95th percentile). Each mark is named once, and both values are labelled outside the bar.
count_panels:  one small panel of labelled bars per way of counting jurors, the count on x with its number of answers under it.
"""
from __future__ import annotations

import altair as alt
import pandas as pd

from . import nbkit as kit

NAVY, SILVER, SLATE, REF, TEXT, TEXT_2, ORANGE, ORANGE_TEXT = (kit.NAVY, kit.SILVER, kit.SLATE, kit.REF, kit.TEXT, kit.TEXT_2, kit.ORANGE,
                                                               kit.ORANGE_TEXT)
LINK = "#cfd4da"   # the bar joining two values of the same juror


def _y(field: str, order, show: bool = True, label_limit: int = 260):
    ax = alt.Axis(labelFontSize=12, labelFontWeight="bold", labelColor=TEXT, labelLimit=label_limit, ticks=False, domain=False, grid=False,
                  labelPadding=8) if show else None
    return alt.Y(f"{field}:N", sort=list(order), title=None, axis=ax)


def _ref(xs, value: float, label: str, color: str = REF, dash=(4, 3), x_title=None, left: bool = False):
    """A vertical reference line, labelled once at its top, right of the line (or left of it, so two nearby labels do not touch)."""
    v = pd.DataFrame({"_v": [value]})
    out = [alt.Chart(v).mark_rule(color=color, strokeDash=list(dash), strokeWidth=1.2).encode(x=alt.X("_v:Q", scale=xs, title=x_title))]
    if label:
        out.append(alt.Chart(v).mark_text(align="right" if left else "left", baseline="bottom", dx=-4 if left else 4, dy=-3, fontSize=11,
                                          color=ORANGE_TEXT if color == ORANGE else color, text=label).encode(x=alt.X("_v:Q", scale=xs), y=alt.value(0)))
    return out


def _text_color(df: pd.DataFrame, color: str) -> pd.DataFrame:
    """Value labels take their mark's colour, except light grey marks, whose labels are slate so they stay readable."""
    d = df.copy()
    d["_tc"] = d[color].where(d[color] != SILVER, SLATE)
    return d


ASCII_MINUS = "replace(datum.label, '\\u2212', '-')"   # Vega writes negatives with a typographic minus: print the ASCII one


def _axis(fmt: str, tick_values=None, grid: bool = True):
    """A value axis with ASCII minus signs; a "+" format writes the sign on positive ticks too."""
    return alt.Axis(format=fmt.lstrip("+"), grid=grid, values=list(tick_values) if tick_values else alt.Undefined,
                    labelExpr=f"datum.value > 0 ? '+' + {ASCII_MINUS} : {ASCII_MINUS}" if fmt.startswith("+") else ASCII_MINUS)


def row_dots(df: pd.DataFrame, y: str, x: str, lo: str, hi: str, color: str, label: str, order, title: str, x_title: str = "",
             fmt: str = ".2f", vline: float | None = None, vline_label: str = "", bar: float | None = None, bar_label: str = "", x_domain=None,
             width: int = 520, row_height: int = 40, label_limit: int = 300, tick_values=None, vline_left: bool = False, bar_left: bool = False):
    """row_dots(d, y="row", x="v", lo="lo", hi="hi", color="col", label="text", order=[...], vline=0, vline_label="chance")."""
    xs = alt.Scale(domain=list(x_domain)) if x_domain else alt.Scale(zero=False, nice=True)
    enc_y = _y(y, order, True, label_limit)
    df = _text_color(df, color)
    base = alt.Chart(df)
    layers = []
    if vline is not None:
        layers += _ref(xs, vline, vline_label, x_title=x_title or None, left=vline_left)
    if bar is not None:
        layers += _ref(xs, bar, bar_label, color=REF, dash=(2, 2), left=bar_left)
    layers.append(base.mark_rule(strokeWidth=1.8).encode(y=enc_y, x=alt.X(f"{lo}:Q", scale=xs, title=x_title or None, axis=_axis(fmt, tick_values)),
                                                         x2=f"{hi}:Q", color=alt.Color(f"{color}:N", scale=None, legend=None)))
    layers.append(base.mark_point(filled=True, size=70, opacity=1).encode(
        y=enc_y, x=alt.X(f"{x}:Q", scale=xs), color=alt.Color(f"{color}:N", scale=None, legend=None),
        tooltip=[alt.Tooltip(f"{y}:N"), alt.Tooltip(f"{x}:Q", format=fmt), alt.Tooltip(f"{lo}:Q", format=fmt), alt.Tooltip(f"{hi}:Q", format=fmt)]))
    layers.append(base.mark_text(align="left", dx=7, fontSize=11.5, fontWeight="bold").encode(
        y=enc_y, x=alt.X(f"{hi}:Q", scale=xs), text=f"{label}:N", color=alt.Color("_tc:N", scale=None, legend=None)))
    return alt.layer(*layers).properties(width=width, height=row_height * len(order), title=kit._title(title, "", True))


def routing_rows(df: pd.DataFrame, y: str, a: str, b: str, tick: str, order, a_name: str, b_name: str, tick_name: str, title: str = "",
                 x_title: str = "", fmt: str = ".2f", x_domain=None, width: int = 460, row_height: int = 46, tick_values=None):
    """One row per item: a grey dot at `a` (the comparison), a navy dot at `b` (the result), joined by a bar, and a short dark tick at
    `tick` (a benchmark). `a` and `b` are named once above the first row, the tick once below the last row."""
    d = df.copy()
    xs = alt.Scale(domain=list(x_domain)) if x_domain else alt.Scale(zero=False, nice=True)
    enc_y = _y(y, order)
    X = lambda f: alt.X(f"{f}:Q", scale=xs, title=x_title or None, axis=_axis(fmt, tick_values))  # noqa: E731
    base = alt.Chart(d)
    tips = [alt.Tooltip(f"{y}:N"), alt.Tooltip(f"{a}:Q", format=fmt), alt.Tooltip(f"{b}:Q", format=fmt), alt.Tooltip(f"{tick}:Q", format=fmt)]
    layers = [base.mark_rule(color=LINK, strokeWidth=4).encode(y=enc_y, x=X(a), x2=f"{b}:Q"),
              base.mark_tick(color=REF, thickness=2, size=row_height * 0.5).encode(y=enc_y, x=X(tick), tooltip=tips),
              base.mark_point(filled=True, size=80, opacity=1, color=SILVER).encode(y=enc_y, x=X(a), tooltip=tips),
              base.mark_point(filled=True, size=80, opacity=1, color=NAVY).encode(y=enc_y, x=X(b), tooltip=tips),
              base.mark_text(align="left", dx=9, fontSize=11.5, fontWeight="bold", color=NAVY).encode(y=enc_y, x=X(b), text=alt.Text(f"{b}:Q", format=fmt)),
              base.mark_text(align="right", dx=-9, fontSize=11, color=SLATE).encode(y=enc_y, x=X(a), text=alt.Text(f"{a}:Q", format=fmt))]
    first, last = d[d[y] == order[0]], d[d[y] == order[-1]]
    layers.append(alt.Chart(first).mark_text(baseline="bottom", dy=-11, fontSize=10.5, color=SLATE).encode(y=enc_y, x=X(a), text=alt.value(a_name)))
    layers.append(alt.Chart(first).mark_text(baseline="bottom", dy=-11, fontSize=10.5, fontWeight="bold", color=NAVY).encode(y=enc_y, x=X(b), text=alt.value(b_name)))
    layers.append(alt.Chart(last).mark_text(baseline="top", dy=13, fontSize=10.5, color=REF).encode(y=enc_y, x=X(tick), text=alt.value(tick_name)))
    return alt.layer(*layers).properties(width=width, height=row_height * len(order), title=title)


def count_panels(df: pd.DataFrame, panel: str, panels, x: str, y: str, label: str, colors, title: str, y_domain=(0, 0.9),
                 width: int = 320, height: int = 210, fmt: str = ".1f"):
    """One panel of bars per `panel` value (in `panels` order, colour from `colors`), x in the frame's row order (a newline in an x
    label wraps it), the value `label` on top of each bar. df columns: panel, x, y, label."""
    ys = alt.Scale(domain=list(y_domain))
    out = []
    for i, p in enumerate(panels):
        d = df[df[panel] == p]
        enc_x = alt.X(f"{x}:N", sort=list(d[x]), title=None,
                      axis=alt.Axis(labelExpr="split(datum.label, '\\n')", labelAngle=0, labelFontSize=11, labelColor=TEXT_2, ticks=False, labelPadding=6))
        enc_y = alt.Y(f"{y}:Q", scale=ys, title=None, axis=alt.Axis(format=fmt, grid=True, labels=i == 0, tickCount=5))
        tc = SLATE if colors[i] == SILVER else colors[i]
        b = alt.Chart(d)
        out.append(alt.layer(
            b.mark_bar(size=36, color=colors[i]).encode(x=enc_x, y=enc_y, tooltip=[alt.Tooltip(f"{x}:N"), alt.Tooltip(f"{y}:Q", format=".3f")]),
            b.mark_text(baseline="bottom", dy=-4, fontSize=11.5, fontWeight="bold", color=tc).encode(x=enc_x, y=f"{y}:Q", text=f"{label}:N"),
        ).properties(width=width, height=height, title=alt.TitleParams(p, fontSize=12.5, fontWeight="bold", color=TEXT, anchor="start")))
    return alt.hconcat(*out, spacing=28).properties(title=title)
