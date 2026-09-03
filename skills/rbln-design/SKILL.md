---
name: rbln-design
description: >-
  Apply the Rebellions brand visual system — Neon Green (#52F756) point color,
  neutral palette, Pretendard typography, one-highlight rule — to any design
  output: HTML/React artifacts and dashboards, web pages and UI, SVG and Mermaid
  diagrams, matplotlib / seaborn / plotly figures, Word / PDF / Markdown reports,
  Excel tables, and PowerPoint decks (Rebellions 2026 Deck Guide). Use when
  building or restyling charts, graphs, data tables, KPI tiles, dashboards,
  architecture or hardware schematics, landing pages, mockups or slides that must
  look Rebellions-branded, or when an existing visual uses off-palette colors or
  a non-Pretendard font and needs the brand applied.
---

# Rebellions design system

One visual language for every medium. The palette, type roles and highlight
rules are transcribed from the Rebellions 2026 Deck Guide; where this skill
extends them to media the guide does not cover (web, Python figures, SVG,
documents) the section says **extension**, and the extension never contradicts
the guide.

## When to use

- Any chart, table, KPI callout, dashboard, diagram, page or slide that will be
  seen as Rebellions work — external decks, customer reports, internal
  dashboards, benchmark write-ups, README figures, artifacts shown to the team.
- Restyling something that already exists but uses another palette or font.

Do not use for: throwaway debugging plots nobody else sees, or third-party
brand work.

## Design intent

> Maximize readability and professional clarity to demonstrate Rebellions'
> technical substance.

Which means: neutral by default, one deliberate accent, real data marks (never
shapes imitating a chart), no decoration — no gradients, shadows, 3-D, rounded
chart elements, or off-palette colors. If a visual needs more than the system
offers, it is carrying more than one message; split it.

## Color

Twelve colors, nothing else (full pairings and contrast in
[references/palette.md](references/palette.md)):

| Role | Hex |
|---|---|
| **Neon Green — point / highlight** | `#52F756` |
| Near-black — text on light, background on dark | `#1B1F23` |
| Dark gray — series 2, panels, table header | `#24292F` |
| Mid gray — series 3, muted text on dark | `#BBC4CF` |
| Light blue-gray — series 4, gridlines, borders | `#D9E4ED` |
| Off-white — light surface, zebra rows | `#F6F8FA` |
| White | `#FFFFFF` |
| Secondary (only when a further category color is unavoidable) | `#174BEB` blue · `#9A4EFF` purple · `#F7318B` pink · `#FF3333` red · `#FFD527` yellow |

Rules:

1. **One highlight.** Exactly one series, bar, row, column, tile, block or edge
   per view is Neon Green. Everything else is neutral. If you cannot name the
   one element that will be green, the message is not decided yet.
2. **Schematics use 6 : 2 : 2** — Neon Green : secondary : secondary — so the
   point color stays dominant when a diagram needs three subsystems.
3. **Text on Neon Green is `#1B1F23`**, never white.
4. **No tints, shades, alpha steps or gradients** of any palette color. A
   sequential encoding steps through the four neutrals and reserves green for
   the single cell that matters (extension, palette.md).
5. **Extension for screens:** Neon Green on white is 1.4 : 1 and `#BBC4CF` on
   white is 1.8 : 1. On light surfaces green is a *mark* (fill, rule, dot) and
   the label next to it is near-black; muted text on light is `#24292F`. Neon
   Green text is fine on `#1B1F23` / `#24292F` (11.7 : 1), which is how dark
   dashboards show the highlighted number.

Series order — light: `#52F756 → #24292F → #BBC4CF → #D9E4ED`;
dark surface: `#52F756 → #D9E4ED → #BBC4CF` (`#24292F` vanishes on `#1B1F23`).
Reaching a fifth color means the chart is too crowded.

**Done when:** every fill, stroke and text color is one of the twelve hex values,
and one element is green.

## Typography

**Pretendard, for Korean and English alike**, in one family; only the weight
changes by role. Never mix in another face. Fallback stack when Pretendard is
unavailable: `"Pretendard Variable", Pretendard, "Apple SD Gothic Neo", "Noto Sans KR", system sans` —
always with a Korean-capable face, or mixed-script text splits into two
families.

| Role | Weight | Deck size (pt) | Screen size (px, extension) | Line height |
|---|---|---|---|---|
| Headline | SemiBold 600 | 44 / 32 | 44 / 32 | 0.9 deck · 1.0 screen |
| Supporting headline, chart title, takeaway | Medium 500 | 28 / 24 | 28 / 24 | 1.1 |
| Body, axis labels, legend, data labels, table cells | Regular 400 | 20 / 14 | 14 (16 for long reading) | 1.1 deck · 1.5 screen |
| Footnote, source, units | ExtraLight 200 | 8 | 12 | — |

- Chart and table text is **never below 14** (pt or px). Footnotes are the one
  exception.
- Title the visual with the insight: "TCO drops 42% at equal throughput", not
  "TCO comparison". Supporting-headline style.
- Numbers in tables and KPIs use tabular figures (`font-variant-numeric: tabular-nums`, `tnum`).
- When a format has separate Latin and East-Asian font slots (OOXML `<a:latin>`
  / `<a:ea>`, Word `w:eastAsia`), set **both** to the same Pretendard weight;
  leaving the East-Asian slot unset is why Korean falls back to another face.
- Install all four weights. A missing weight is substituted silently and the
  hierarchy collapses without an error.

**Done when:** every text run is a Pretendard weight from the table, nothing in a
chart or table is under 14, and the East-Asian slot matches where one exists.

## Charts

Same rules in every library:

- Series 1 (the story) → Neon Green; the rest follow the neutral order. Single
  series: all bars neutral and the one that matters green.
- Gridlines **horizontal only**, hairline, `#D9E4ED` on light / `#24292F` on
  dark. No vertical gridlines, axis lines, zero line, or chart border.
- Category ticks hidden; value ticks outward.
- Legend at the top, left-aligned, or **absent** for single-series charts —
  label the bar directly instead.
- Data labels on the highlighted series at body size; if labels crowd, keep
  them only there.
- Bars: gap 60–80 % of bar width (plotly `bargap 0.4`, matplotlib `width 0.6`,
  Chart.js `barPercentage 0.6`, OOXML `gapWidth 60–80`); stacked bars overlap 100.
- Lines: 2.25 pt/px stroke; markers only on the highlighted series.
- Pie / doughnut: four slices maximum, first slice green, white 2 px separators,
  no explode, no 3-D. Prefer a bar when values are close.
- Scatter: neutral points, the highlighted cluster or point green, 8 px markers.
- One visual per slide or card, with its takeaway line. Two visuals share the
  width and use identical palettes.

**Done when:** exactly one green series or element per chart, horizontal grid
only, legend top or absent, title states the insight.

## Tables

Pick exactly one of three types (Chart Guidelines_W):

| Type | Use | Spec |
|---|---|---|
| **Standard** | neutral data listing | header fill `#24292F`, header text `#FFFFFF` bold, centered; body rows white / `#F6F8FA` alternating, text `#1B1F23`; rules `#D9E4ED` horizontal only, no vertical borders |
| **Highlight 1 — column** | emphasize one column (usually the Rebellions product) | that column's header `#52F756` with `#1B1F23` bold text; its body cells `#F6F8FA` with `#1B1F23` bold; other columns Standard |
| **Highlight 2 — row / cells** | emphasize one row or the winning metrics | row fill `#52F756`, text `#1B1F23` bold; or row neutral and only winning values `#52F756` bold on `#1B1F23` |

- Label columns left-aligned, numeric columns right-aligned, headers centered,
  vertical middle. Body text 14; ~30 pt/px row height. Split a long table rather
  than shrink it.
- Never two highlighted columns, never a column and a row together.
- Always a real table object (HTML `<table>`, OOXML `<a:tbl>`, `go.Table`,
  docx table, xlsx cells) — never text boxes lined up.

**Done when:** the table matches one type and at most one column or row carries
green.

## KPI callouts

- Value in headline scale (44 / 32) SemiBold, label in body scale, optional
  delta in body scale.
- Deck: value in Neon Green or near-black. Screens (extension): on light
  surfaces the value is `#1B1F23` and a 4 px green rule or chip marks the
  highlighted tile; on dark surfaces the highlighted value itself is green.
- One highlighted tile per row of tiles; the rest neutral.

## Diagrams and schematics

6 : 2 : 2. Green on the block or path the diagram is about; two secondaries for
two other subsystems; everything else `#F6F8FA` fills with `#D9E4ED` 1 px
strokes and `#24292F` 1.5 px edges. Square corners, no shadows, 14 px labels.
Mechanics for SVG and Mermaid in [references/diagrams.md](references/diagrams.md).

## Layout

- Deck canvas 960 × 540 pt with a 36 pt safe margin; screens use a gutter of
  `clamp(16px, 3.75vw, 36px)` (extension, same 3.75 %).
- Content starts below the measured title band, never at a hardcoded top.
- Light surfaces: page `#FFFFFF`, panels `#F6F8FA`. Dark surfaces: page
  `#1B1F23`, panels `#24292F`. Do not invent a third surface.
- Radius 0 on charts and tables; 4 px at most on UI cards and controls
  (extension). No drop shadows anywhere.
- Wide tables and charts scroll inside their own container; a page never
  scrolls sideways.

## Documents and spreadsheets (extension)

- **Word / PDF / Markdown → PDF:** Pretendard for body and headings with the
  role table above; set the `w:eastAsia` font too (python-docx:
  `rPr.rFonts.set(qn('w:eastAsia'), 'Pretendard')`). Tables in one of the three
  types; figures at text-column width with an 8–9 pt source line beneath.
- **Excel:** header fill `24292F`, header font `FFFFFF` bold, body font
  Pretendard 11, zebra `F6F8FA`, thin bottom borders `D9E4ED`, no vertical
  borders; Highlight Type 1 = one header cell `52F756` with `1B1F23` text.
  Charts inside the workbook follow the chart rules.
- **Markdown-only surfaces** (GitHub, Slack, Notion) cannot carry the palette in
  text; put the brand into the embedded figure or Mermaid diagram and keep the
  prose plain.

## Medium routing

| You are producing | Read | Use |
|---|---|---|
| HTML / CSS / React, Claude artifacts, dashboards, landing pages, UI | [references/web.md](references/web.md) | `assets/rbln-tokens.css`, `assets/rbln-tokens.json` |
| Chart.js, Recharts, ECharts, D3, Plotly.js, Vega-Lite | web.md § Chart libraries | tokens |
| matplotlib, seaborn, plotly (Python), pandas Styler | [references/python.md](references/python.md) | `assets/rbln.mplstyle`, `assets/rbln_plotly.py` |
| SVG, Mermaid, architecture / hardware diagrams | [references/diagrams.md](references/diagrams.md) | — |
| PowerPoint `.pptx` through slide tools (OOXML, Office.js) | [references/pptx.md](references/pptx.md) | — |
| Word, PDF, Excel, Markdown | this file, § Documents | tokens JSON for hex values |
| Design canvas / mockups | this file + web.md § Type scale | tokens CSS |

Asset paths resolve as `${CLAUDE_SKILL_DIR}/assets/<file>`.

## Workflow

1. **Decide the message.** Name the one element that will be Neon Green and the
   one sentence the title will say. Ask the user only if the highlight is
   ambiguous (two candidate products, two candidate metrics).
   **Done when:** you can write the title and point at the green element.
2. **Pick the surface and medium.** Light or dark; then the row in Medium
   routing. Load the reference and asset for that row.
   **Done when:** the tokens (CSS / mplstyle / plotly template / OOXML values)
   are in the working file.
3. **Build** with real chart, table and shape objects. Set the highlighted
   series explicitly; never rely on a library's default cycle to land green on
   the right series.
   **Done when:** the visual exists with palette-only colors and Pretendard.
4. **Add the takeaway and the source line.** Supporting-headline title; 8 pt /
   12 px footnote with source and units if the data has them.
5. **Verify.**
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/check_colors.py <files>
   python3 ${CLAUDE_SKILL_DIR}/scripts/check_colors.py --pair 52F756 FFFFFF   # any text/background pair in doubt
   ```
   Exit 0 means no off-palette hex. Then look at the output — screenshot, PNG,
   rendered slide — in the surface it will be shown on (both color schemes for
   web) and walk the checklist. Fix and re-run until clean.
   **Done when:** the checklist passes and the medium's own verifier
   (`verify_slides`, browser screenshot, saved PNG) shows the intended
   highlight.

## Compliance checklist

- [ ] Exactly one Neon Green highlight per view (6 : 2 : 2 if a schematic).
- [ ] All colors from the twelve; no tints, gradients, shadows, 3-D.
- [ ] Neon Green is never text on a light surface; muted text on light is `#24292F`.
- [ ] Pretendard only, Korean and English, East-Asian slot matched; all four weights available.
- [ ] Chart / table text ≥ 14; footnote is the only smaller text.
- [ ] Horizontal gridlines only; legend top or absent; data labels on the key series.
- [ ] Table is one of the three types; real table / chart objects, never shapes.
- [ ] Title states the insight; source line present when data has a source.
- [ ] Inside the safe margin (36 pt) or gutter; no horizontal page scroll.
- [ ] `check_colors.py` exits 0 on the produced files.
