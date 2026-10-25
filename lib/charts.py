"""The chart shapes the findings page needs that nbkit does not have, drawn with nbkit's tokens and theme.

row_dots:     one dot + 95% line per row, each row coloured by meaning (navy = the quantity that matters, grey = comparison),
              value labels right of the interval, an optional labelled reference line.
dumbbell:     two values per row joined by a line, the comparison in grey and the result in navy.
stages:       three values per row, for a prompt with and without one rule.
cost_moves:   one arrow per judge from the standard prompt to the rules, on cost against agreement.
side_by_side: two text tiles, for the two instructions.
"""
from __future__ import annotations

import altair as alt
import pandas as pd

from . import nbkit as kit

NAVY, SILVER, SLATE, REF, TEXT, TEXT_2 = kit.NAVY, kit.SILVER, kit.SLATE, kit.REF, kit.TEXT, kit.TEXT_2


def row_dots(df: pd.DataFrame, y: str, x: str, lo: str, hi: str, color: str, label: str, order, title: str, x_title: str = "",
             fmt: str = ".2f", vline: float | None = None, vline_label: str = "", x_domain=None, width: int = 520, row_height: int = 44,
             label_limit: int = 260, tick_values=None):
    """row_dots(d, y="row", x="v", lo="lo", hi="hi", color="col", label="text", order=[...], vline=0, vline_label="no change")."""
    xs = alt.Scale(domain=list(x_domain)) if x_domain else alt.Scale(zero=False, nice=True)
    enc_y = alt.Y(f"{y}:N", sort=list(order), title=None,
                  axis=alt.Axis(labelFontSize=12, labelFontWeight="bold", labelColor=TEXT, labelLimit=label_limit, ticks=False, domain=False, grid=False, labelPadding=8))
    base = alt.Chart(df)
    layers = []
    if vline is not None:
        v = pd.DataFrame({"_v": [vline]})
        layers.append(alt.Chart(v).mark_rule(color=REF, strokeDash=[4, 3], strokeWidth=1.2).encode(x=alt.X("_v:Q", scale=xs, title=x_title or None)))
        if vline_label:
            layers.append(alt.Chart(v).mark_text(align="left", baseline="bottom", dx=4, dy=-3, fontSize=11, color=REF, text=vline_label)
                          .encode(x=alt.X("_v:Q", scale=xs), y=alt.value(0)))
    layers.append(base.mark_rule(strokeWidth=1.8).encode(y=enc_y, x=alt.X(f"{lo}:Q", scale=xs, title=x_title or None, axis=alt.Axis(format=fmt, values=list(tick_values) if tick_values else alt.Undefined)),
                                                         x2=f"{hi}:Q", color=alt.Color(f"{color}:N", scale=None, legend=None)))
    layers.append(base.mark_point(filled=True, size=70, opacity=1).encode(y=enc_y, x=alt.X(f"{x}:Q", scale=xs), color=alt.Color(f"{color}:N", scale=None, legend=None),
                                                                           tooltip=[alt.Tooltip(f"{y}:N"), alt.Tooltip(f"{x}:Q", format=fmt), alt.Tooltip(f"{lo}:Q", format=fmt), alt.Tooltip(f"{hi}:Q", format=fmt)]))
    layers.append(base.mark_text(align="left", dx=7, fontSize=11.5, fontWeight="bold").encode(y=enc_y, x=alt.X(f"{hi}:Q", scale=xs), text=f"{label}:N",
                                                                                              color=alt.Color(f"{color}:N", scale=None, legend=None)))
    return alt.layer(*layers).properties(width=width, height=row_height * len(order), title=kit._title(title, "", True))


# ── shapes for the findings page ─────────────────────────────────────────────────────────────────────────
LINK = "#cfd4da"   # the bar joining two values of the same judge
ORANGE = kit.ORANGE


def dumbbell(df: pd.DataFrame, y: str, a: str, b: str, order, a_name: str, b_name: str, title: str = "", x_title: str = "", fmt: str = ".2f",
             x_domain=None, width: int = 420, row_height: int = 42, b_color: str = NAVY, show_y: bool = True, name_row: str | None = None, tick_values=None):
    """One row per item: grey dot at `a` (before), coloured dot at `b` (after), joined by a bar; both values labelled on the outside.
    The two dot names are written once, above the first row (or `name_row`)."""
    d = df.copy()
    d["_up"] = d[b] >= d[a]
    xs = alt.Scale(domain=list(x_domain)) if x_domain else alt.Scale(zero=False, nice=True)
    ax = alt.Axis(labelFontSize=12, labelFontWeight="bold", labelColor=TEXT, labelLimit=200, ticks=False, domain=False, grid=False, labelPadding=8) if show_y else None
    enc_y = alt.Y(f"{y}:N", sort=list(order), title=None, axis=ax)
    X = lambda f: alt.X(f"{f}:Q", scale=xs, title=x_title or None, axis=alt.Axis(format=fmt, grid=True, values=list(tick_values) if tick_values else alt.Undefined))  # noqa: E731
    base = alt.Chart(d)
    layers = [base.mark_rule(color=LINK, strokeWidth=4).encode(y=enc_y, x=X(a), x2=f"{b}:Q"),
              base.mark_point(filled=True, size=80, opacity=1, color=SILVER).encode(y=enc_y, x=X(a)),
              base.mark_point(filled=True, size=80, opacity=1, color=b_color).encode(y=enc_y, x=X(b))]
    for up in (True, False):  # value labels outside the bar: after-value beyond the move, before-value on the other side
        sub = base.transform_filter(alt.datum._up == up)
        layers.append(sub.mark_text(align="left" if up else "right", dx=9 if up else -9, fontSize=11.5, fontWeight="bold", color=b_color)
                      .encode(y=enc_y, x=X(b), text=alt.Text(f"{b}:Q", format=fmt)))
        layers.append(sub.mark_text(align="right" if up else "left", dx=-9 if up else 9, fontSize=11, color=SLATE)
                      .encode(y=enc_y, x=X(a), text=alt.Text(f"{a}:Q", format=fmt)))
    if name_row is None:
        name_row = d.loc[(d[b] - d[a]).abs().idxmax(), y]
    first = d[d[y] == name_row]
    layers.append(alt.Chart(first).mark_text(baseline="bottom", dy=-11, fontSize=10.5, color=SLATE).encode(y=enc_y, x=X(a), text=alt.value(a_name)))
    layers.append(alt.Chart(first).mark_text(baseline="bottom", dy=-11, fontSize=10.5, fontWeight="bold", color=b_color).encode(y=enc_y, x=X(b), text=alt.value(b_name)))
    return alt.layer(*layers).properties(width=width, height=row_height * len(order), title=title)


def stages(df: pd.DataFrame, y: str, cols, order, title: str = "", x_title: str = "", fmt: str = ".2f", x_domain=None, width: int = 460, row_height: int = 56):
    """Several values per row on one axis: cols = [(column, name, colour), ...]; a grey bar spans them; names written over the first row."""
    d = df.copy()
    d["_lo"] = d[[c for c, _, _ in cols]].min(axis=1); d["_hi"] = d[[c for c, _, _ in cols]].max(axis=1)
    xs = alt.Scale(domain=list(x_domain)) if x_domain else alt.Scale(zero=False, nice=True)
    enc_y = alt.Y(f"{y}:N", sort=list(order), title=None, axis=alt.Axis(labelFontSize=12, labelFontWeight="bold", labelColor=TEXT, ticks=False, domain=False, grid=False, labelPadding=8))
    X = lambda f: alt.X(f"{f}:Q", scale=xs, title=x_title or None, axis=alt.Axis(format=fmt, grid=True))  # noqa: E731
    base = alt.Chart(d)
    layers = [base.mark_rule(color=LINK, strokeWidth=4).encode(y=enc_y, x=X("_lo"), x2="_hi:Q")]
    first = d[d[y] == order[0]]
    for i, (c, name, col) in enumerate(cols):
        layers.append(base.mark_point(filled=True, size=85, opacity=1, color=col).encode(y=enc_y, x=X(c)))
        layers.append(base.mark_text(baseline="top", dy=10, fontSize=11, fontWeight="bold", color=col).encode(y=enc_y, x=X(c), text=alt.Text(f"{c}:Q", format=fmt)))
        layers.append(alt.Chart(first).mark_text(baseline="bottom", dy=-11 - 12 * (i % 2), fontSize=10.5, color=col).encode(y=enc_y, x=X(c), text=alt.value(name)))
    return alt.layer(*layers).properties(width=width, height=row_height * len(order), title=title)


def cost_moves(df: pd.DataFrame, title: str = "", width: int = 560, height: int = 300, x_ticks=(0.05, 0.1, 0.2, 0.5, 1.0), log: bool = True,
               x_domain=None, y_domain=(0.75, 0.93)):
    """Agreement against cost per 1,000 answers, one arrow per judge from the standard prompt (grey) to the experts' rules (navy).
    df columns: judge, cost_a, k_a, cost_b, k_b, col (navy if the judge gains, grey otherwise)."""
    d = df.copy()
    xs = (alt.Scale(type="log", domain=list(x_domain or (min(x_ticks) * 0.8, max(x_ticks) * 1.25))) if log
          else alt.Scale(type="linear", domain=list(x_domain or (0, max(x_ticks) * 1.05))))
    ys = alt.Scale(domain=list(y_domain))
    X = lambda f: alt.X(f"{f}:Q", scale=xs, title="cost per 1,000 graded answers" + (" ($, log scale)" if log else ""), axis=alt.Axis(values=list(x_ticks), format="$.2f", grid=True))  # noqa: E731
    Y = lambda f: alt.Y(f"{f}:Q", scale=ys, title="agreement with the experts (Cohen's κ)", axis=alt.Axis(format=".2f"))  # noqa: E731
    base = alt.Chart(d)
    return alt.layer(
        base.mark_rule(color=LINK, strokeWidth=3).encode(x=X("cost_a"), x2="cost_b:Q", y=Y("k_a"), y2="k_b:Q"),
        base.mark_point(filled=True, size=70, opacity=1, color=SILVER).encode(x=X("cost_a"), y=Y("k_a")),
        base.mark_point(filled=True, size=90, opacity=1).encode(x=X("cost_b"), y=Y("k_b"), color=alt.Color("col:N", scale=None),
                                                                tooltip=["judge:N", alt.Tooltip("k_a:Q", format=".2f"), alt.Tooltip("k_b:Q", format=".2f"),
                                                                         alt.Tooltip("cost_b:Q", format="$.2f")]),
        base.mark_text(align="left", dx=9, dy=-2, fontSize=11.5, fontWeight="bold").encode(x=X("cost_b"), y=Y("k_b"), text="judge:N", color=alt.Color("col:N", scale=None)),
    ).properties(width=width, height=height, title=title)


def side_by_side(left_label: str, left_body: str, right_label: str, right_items, width: int = 820):
    """Two white tiles: a quoted instruction on the left, a numbered list on the right (HTML, house tokens)."""
    import html as h
    tile = f"flex:1 1 0;padding:14px 16px;border:1px solid {kit.BORDER};border-radius:8px;background:#fff"
    lab = f"font-size:11.5px;color:{kit.TEXT_4};text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px"
    left = (f"<div style='{tile}'><div style='{lab}'>{h.escape(left_label)}</div>"
            f"<div style='font-size:13.5px;line-height:1.5;color:{kit.TEXT_2};font-style:italic'>“{h.escape(left_body)}”</div></div>")
    items = "".join(f"<div style='display:flex;gap:8px;margin:0 0 5px'><span style='color:{NAVY};font-weight:700;min-width:14px'>{i}</span>"
                    f"<span>{h.escape(t)}</span></div>" for i, t in enumerate(right_items, start=1))
    right = (f"<div style='{tile};border-left:3px solid {NAVY}'><div style='{lab}'>{h.escape(right_label)}</div>"
             f"<div style='font-size:13.5px;line-height:1.45;color:{kit.TEXT_2}'>{items}</div></div>")
    return f"<div style='display:flex;gap:12px;max-width:{width}px;margin:4px 0 10px;font-family:{kit.FONT}'>{left}{right}</div>"
