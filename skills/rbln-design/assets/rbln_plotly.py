"""Rebellions plotly templates (rbln-design skill).

    import sys; sys.path.append("<skill>/assets")
    import rbln_plotly                       # registers "rbln" and "rbln_dark"
    import plotly.io as pio
    pio.templates.default = "rbln"           # or fig.update_layout(template="rbln_dark")

Palette and type roles: Rebellions 2026 Deck Guide. Only plotly is required.
"""
import plotly.graph_objects as go
import plotly.io as pio

GREEN, BLACK, GRAY900, GRAY400, GRAY200, GRAY050, WHITE = (
    "#52F756", "#1B1F23", "#24292F", "#BBC4CF", "#D9E4ED", "#F6F8FA", "#FFFFFF")
SECONDARY = ["#174BEB", "#9A4EFF", "#F7318B", "#FF3333", "#FFD527"]

FONT = 'Pretendard, "Pretendard Variable", "Apple SD Gothic Neo", "Noto Sans KR", sans-serif'

# Series 1 is the ONE highlighted series. Reaching the secondary accents means the
# chart has too many series - split it instead.
COLORWAY_LIGHT = [GREEN, GRAY900, GRAY400, GRAY200] + SECONDARY
COLORWAY_DARK = [GREEN, GRAY200, GRAY400, GRAY900] + SECONDARY   # #24292F vanishes on #1B1F23


def _template(bg, fg, muted, grid, colorway):
    axis_font = dict(size=14, color=muted)
    return go.layout.Template(
        layout=go.Layout(
            font=dict(family=FONT, size=14, color=fg),
            title=dict(font=dict(size=24, color=fg), x=0, xanchor="left", pad=dict(b=12)),
            paper_bgcolor=bg,
            plot_bgcolor=bg,
            colorway=colorway,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                        font=dict(size=14, color=fg), bgcolor="rgba(0,0,0,0)"),
            xaxis=dict(showgrid=False, zeroline=False, showline=False, ticks="",
                       tickfont=axis_font, title=dict(font=axis_font)),
            yaxis=dict(showgrid=True, gridcolor=grid, gridwidth=1, zeroline=False, showline=False,
                       ticks="outside", tickcolor=grid, tickfont=axis_font, title=dict(font=axis_font)),
            bargap=0.4,        # deck gap width 60-80 % of bar width
            bargroupgap=0.05,
            margin=dict(l=56, r=24, t=88, b=56),
            hoverlabel=dict(font=dict(family=FONT, size=14)),
        ),
        data=dict(
            bar=[go.Bar(marker=dict(line=dict(width=0)), textfont=dict(size=14),
                        textposition="outside")],
            scatter=[go.Scatter(line=dict(width=2.25), marker=dict(size=8))],
            pie=[go.Pie(textfont=dict(size=14), marker=dict(line=dict(color=bg, width=2)),
                        sort=False)],
        ),
    )


pio.templates["rbln"] = _template(WHITE, BLACK, GRAY900, GRAY200, COLORWAY_LIGHT)
pio.templates["rbln_dark"] = _template(BLACK, GRAY050, GRAY400, GRAY900, COLORWAY_DARK)


def highlight(values, index, dark=False):
    """Per-point marker colors: one Neon Green bar/slice, the rest neutral.

    >>> fig = go.Figure(go.Bar(x=names, y=vals, marker_color=highlight(vals, 2)))
    """
    neutral = GRAY200 if dark else GRAY900
    return [GREEN if i == index else neutral for i in range(len(values))]


def table(header, rows, highlight_col=None, highlight_row=None):
    """go.Table in Standard type, or Highlight Type 1 (column) / Type 2 (row).

    `rows` is a list of row lists (not columns). Pass at most one of highlight_col /
    highlight_row - the guide allows one highlighted column OR one row, never both.
    """
    if highlight_col is not None and highlight_row is not None:
        raise ValueError("pick one: highlight_col or highlight_row")
    ncol, nrow = len(header), len(rows)
    columns = [[r[c] for r in rows] for c in range(ncol)]
    head_fill = [GRAY900] * ncol
    head_font = [WHITE] * ncol
    cell_fill = [[WHITE if r % 2 == 0 else GRAY050 for r in range(nrow)] for _ in range(ncol)]
    cell_font = [[BLACK] * nrow for _ in range(ncol)]
    if highlight_col is not None:
        head_fill[highlight_col] = GREEN
        head_font[highlight_col] = BLACK
        cell_fill[highlight_col] = [GRAY050] * nrow
    if highlight_row is not None:
        for c in range(ncol):
            cell_fill[c][highlight_row] = GREEN
            cell_font[c][highlight_row] = BLACK
    align = ["left"] + ["right"] * (ncol - 1)
    return go.Table(
        header=dict(values=header, fill_color=head_fill, align="center", height=30,
                    font=dict(family=FONT, size=14, color=head_font)),
        cells=dict(values=columns, fill_color=cell_fill, align=align, height=30,
                   line=dict(color=GRAY200, width=1),
                   font=dict(family=FONT, size=14, color=cell_font)),
    )
