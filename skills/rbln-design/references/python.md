# Python figures: matplotlib, seaborn, plotly, pandas

Assets:

- `${CLAUDE_SKILL_DIR}/assets/rbln.mplstyle` — matplotlib style sheet
- `${CLAUDE_SKILL_DIR}/assets/rbln_plotly.py` — plotly templates `rbln` and `rbln_dark`, plus `highlight()` and `table()` helpers

Verified 2026-09-03 with matplotlib 3.9.4 and plotly 7.0.0 (kaleido for PNG export),
Pretendard installed system-wide on macOS.

## Fonts

matplotlib finds Pretendard only if the OTF/TTF files are installed where
fontconfig or the OS sees them. On a host without it (a Linux bench box, a CI
runner), register the files explicitly before `style.use`:

```python
from matplotlib import font_manager
for f in glob.glob("/path/to/Pretendard-*.otf"):
    font_manager.addfont(f)
```

Then check `"Pretendard" in {f.name for f in font_manager.fontManager.ttflist}`.
If it is False the style silently falls back to DejaVu Sans and Korean labels
render as boxes. `axes.unicode_minus: False` in the style avoids the missing
U+2212 glyph in Korean fonts. If Pretendard genuinely cannot be installed, use
Noto Sans KR as the substitute; do not mix faces.

## matplotlib

```python
import matplotlib.pyplot as plt
plt.style.use("<skill>/assets/rbln.mplstyle")

fig, ax = plt.subplots()
bars = ax.bar(cats, vals, width=0.6, color="#24292F")   # width 0.6 ≈ deck gap width 67 %
bars[hl].set_color("#52F756")                           # the one highlight
ax.bar_label(bars, fmt="%d", padding=3)                 # data labels
ax.set_title("REBEL delivers 88 tok/s — 44% over H100") # the insight, not the chart type
fig.savefig("out.png")
```

What the style already does: horizontal gridlines only in `#D9E4ED`, top /
right / left spines removed, bottom spine `#BBC4CF`, category ticks hidden,
value ticks outward, title left-aligned SemiBold, legend frameless, line width
2.25, 16:9 figure at 200 dpi, series cycle Neon Green → neutrals.

Legend at top like the deck (`legend.loc: upper center` sits *inside* the axes;
this puts it above):

```python
ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=len(series))
```

Line charts: markers only on the highlighted series.

```python
ax.plot(x, y_rebel, label="REBEL", marker="o")          # series 1 → #52F756 from the cycle
ax.plot(x, y_h100, label="H100")                        # series 2 → #24292F
```

Dark figure (for dark slides or dashboards):

```python
with plt.rc_context({"figure.facecolor": "#1B1F23", "axes.facecolor": "#1B1F23",
                     "savefig.facecolor": "#1B1F23", "text.color": "#F6F8FA",
                     "axes.labelcolor": "#BBC4CF", "xtick.color": "#BBC4CF", "ytick.color": "#BBC4CF",
                     "grid.color": "#24292F", "axes.edgecolor": "#24292F",
                     "axes.prop_cycle": plt.cycler("color", ["#52F756", "#D9E4ED", "#BBC4CF"])}):
    ...
```

Pie / doughnut: `ax.pie(vals, colors=["#52F756", "#24292F", "#BBC4CF", "#D9E4ED"][:len(vals)], wedgeprops=dict(width=0.4, linewidth=2, edgecolor="white"))`,
four slices maximum, the first slice is the story.

Heatmap (extension, see palette.md): `ListedColormap(["#F6F8FA", "#D9E4ED", "#BBC4CF", "#24292F"])`
with `BoundaryNorm`, and draw the one cell that matters with a `#52F756` rectangle.

## seaborn

```python
import seaborn as sns
sns.set_theme(style=None, rc=plt.rcParams)              # keep the mplstyle, do not let seaborn reset it
sns.set_palette(["#52F756", "#24292F", "#BBC4CF", "#D9E4ED"])
```

Call `plt.style.use(...)` *before* `sns.set_theme`, and pass `style=None` — the
seaborn defaults re-enable vertical gridlines and change the font.

## plotly

```python
import sys; sys.path.append("<skill>/assets")
import rbln_plotly, plotly.io as pio, plotly.graph_objects as go
pio.templates.default = "rbln"                          # "rbln_dark" for dark surfaces

fig = go.Figure(go.Bar(x=cats, y=vals, text=vals,
                       marker_color=rbln_plotly.highlight(vals, hl)))
fig.update_layout(title="REBEL delivers 88 tok/s")
fig.write_html("out.html", include_plotlyjs="cdn")      # or fig.write_image("out.png", scale=2)
```

The template sets font 14 / title 24 in Pretendard, horizontal grid in `#D9E4ED`,
no zero line or axis line, legend horizontal above the plot, `bargap 0.4`, line
width 2.25, marker 8, bar labels outside, pie `sort=False` so the first slice
stays first.

Tables — one call, one type:

```python
fig = go.Figure(rbln_plotly.table(["Metric", "H100", "REBEL"],
                                  [["TPOT (ms)", "31", "22"], ["TTFT (ms)", "410", "290"]],
                                  highlight_col=2))       # or highlight_row=0, never both
```

plotly express: `px.bar(df, ..., template="rbln", color_discrete_sequence=rbln_plotly.COLORWAY_LIGHT)`.
Highlighting one bar in express needs `fig.update_traces(marker_color=rbln_plotly.highlight(df.value, hl))`.

## pandas Styler (HTML tables in notebooks / reports)

```python
sty = (df.style
       .set_table_styles([
           {"selector": "th", "props": "background:#24292F;color:#FFFFFF;font-weight:700;text-align:center;font-family:Pretendard;font-size:14px"},
           {"selector": "td", "props": "border-bottom:1px solid #D9E4ED;font-family:Pretendard;font-size:14px;color:#1B1F23"},
           {"selector": "tbody tr:nth-child(even) td", "props": "background:#F6F8FA"},
       ])
       .set_properties(subset=["REBEL"], **{"background": "#F6F8FA", "font-weight": "700"}))   # Highlight Type 1 body
sty = sty.set_table_styles([{"selector": "th.col_heading.level0.col2", "props": "background:#52F756;color:#1B1F23"}], overwrite=False)
```

## Verify

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/check_colors.py make_figure.py
```

and open the PNG: one Neon Green element, gridlines horizontal, Pretendard glyphs
(Korean text not boxed, minus signs present).
