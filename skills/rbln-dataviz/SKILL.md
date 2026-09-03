---
name: rbln-dataviz
description: >-
  Build charts, graphs, KPI callouts and data tables that comply with the
  Rebellions 2026 Deck Guide. Use when adding or restyling a data visualization
  in a Rebellions-branded deck — bar, column, line, area, pie, doughnut or
  scatter charts, comparison and spec tables, benchmark result tables, KPI
  callouts — or when an existing chart uses off-palette colors and needs the
  Neon Green (#52F756) point color and Pretendard typography applied.
---

# Rebellions deck data visualization

All rules below are transcribed from the Rebellions 2026 Deck Guide slides
(Overview / Typography Guidelines / Color Guidelines / Graph Guidelines_W /
Chart Guidelines_W).

## When to use

Use this skill whenever you add or restyle a data visualization in a
Rebellions-branded deck:

- bar / column / line / area / pie / doughnut / scatter charts
- comparison or spec tables (competitive positioning, product specs, benchmark
  results)
- KPI or single-metric callouts
- restyling an existing chart that does not follow the brand palette

Do **not** use it for pure text slides, covers, or agenda slides — those are
covered by the master layouts directly.

## Prerequisites

- A PowerPoint editing surface exposing `list_slide_shapes`, `edit_slide_chart`,
  `edit_slide_xml`, `execute_office_js`, `verify_slides` and
  `verify_slide_visual`. Without real chart and table tools you cannot satisfy
  this guide — do not fall back to drawing shapes.
- Pretendard installed in **all weights** (ExtraLight, Regular, Medium,
  SemiBold). A missing weight is substituted silently and the hierarchy
  collapses with no error.

## Design principles (Overview)

- Design intent: **maximize readability and professional clarity to demonstrate
  Rebellions' technical substance.**
- Use the configurations already present in the slide master; do not invent new
  visual systems.
- Avoid individual design modifications outside the established guidelines — no
  custom gradients, shadows, 3-D effects, or off-palette colors.
- Never simulate a chart with geometric shapes. Always use `edit_slide_chart`
  (real OOXML charts) or `addTable` for tabular data.

## Color system (Color Guidelines)

**Point color**

| Role | Hex |
|---|---|
| Neon Green (point / highlight) | `#52F756` (theme accent1 `51F756`) |

**Primary neutrals**

| Role | Hex |
|---|---|
| Near-black (text, dark bg) | `#1B1F23` |
| Dark gray (bars, panels) | `#24292F` |
| Mid gray (secondary series) | `#BBC4CF` |
| Light blue-gray (tertiary series, gridlines) | `#D9E4ED` |
| Off-white (light bg, table zebra) | `#F6F8FA` |
| White | `#FFFFFF` |

**Secondary colors** — use only when more than one categorical accent is
unavoidable:
`#174BEB` blue · `#9A4EFF` purple · `#F7318B` pink · `#FF3333` red ·
`#FFD527` yellow

**Rules**

1. **Highlight key data with Neon Green.** Exactly one series (or one bar, one
   row, one KPI) carries `#52F756`; everything else stays neutral.
2. For **hardware schematics / diagram-heavy visuals**, maintain a **6:2:2
   ratio — Neon Green : Secondary : Secondary** so the point color stays
   dominant but readable.
3. Neon Green is a light color: text placed on it must be `#1B1F23`, never
   white. White or `#F6F8FA` text belongs on `#1B1F23` / `#24292F`.
4. Do not tint or shade palette colors to create extra steps. If a chart needs
   more than 3 neutral steps, reduce the number of series or split the chart.

**Done when:** every fill, line and font color in the visual is one of the hex
values listed above.

## Typography (Typography Guidelines)

Use **Pretendard for both Korean and English** — one font family across the
entire deck. Do not mix in Söhne or any other face; only the Pretendard weight
changes by role.

| Role | Font | Size | Line spacing |
|---|---|---|---|
| Headline | Pretendard SemiBold | 44 or 32 pt | 0.9 |
| Supporting headline / summary | Pretendard Medium | 28 or 24 pt | 1.1 |
| Body (descriptions, overviews) | Pretendard Regular | 20 or 14 pt | 1.1 |
| Footnote (source, notes) | Pretendard ExtraLight | 8 pt | — |

Applied to data visuals:

- Chart title: 24 pt (`sz="2400"`), Pretendard SemiBold.
- Axis labels, legend, data labels, table body: **14 pt** (`sz="1400"`). Never
  go below 14 pt for chart or table text.
- Source line / units note at the page footer: 8 pt footnote style, `#BBC4CF`
  on light backgrounds.
- KPI number: headline scale (44 or 32 pt) in Neon Green or near-black; its
  label uses body scale.
- When setting the face explicitly in OOXML, set **both** `<a:latin>` and
  `<a:ea>` to the same Pretendard weight so Korean and English runs render
  identically:

  ```xml
  <a:latin typeface="Pretendard SemiBold"/><a:ea typeface="Pretendard SemiBold"/>
  ```

  Leaving `<a:ea>` unset is the usual cause of Korean text falling back to a
  different family.

**Done when:** no text in the visual is under 14 pt except an intentional 8 pt
footnote, and every font face — latin and east-asian — is a Pretendard weight
from the table.

## Graphs (Graph Guidelines_W)

> When visualizing graphs, use a combination of neutral colors and Neon Green.
> Apply the point color to key data series to maximize visual contrast and
> readability.

Build with `edit_slide_chart`:

- Series 1 (the story) → `#52F756`. Series 2, 3 → `#24292F`, `#BBC4CF`.
- Gridlines: `#D9E4ED`, hairline, horizontal only. Remove vertical gridlines and
  chart-area borders.
- Category axis: `<c:majorTickMark val="none"/>`; value axis:
  `<c:majorTickMark val="out"/>`; minor ticks `none` on both.
- Legend at top (`<c:legendPos val="t"/>`, `<c:overlay val="0"/>`). Omit the
  legend entirely for single-series charts and label the bar directly.
- Data labels on with `<c:showVal val="1"/>` at 14 pt. If labels crowd, keep
  them only on the highlighted series.
- Column/bar gap width 60–80 for a solid, engineered look; stacked charts must
  also set `<c:overlap val="100"/>`.
- Line charts: 2.25 pt stroke, markers only on the highlighted series.
- Do not rely on `<c:style>` defaults for series color when a specific series
  must be highlighted — set `<c:spPr>` explicitly for that series, and leave the
  rest neutral.

**Done when:** exactly one series is Neon Green, all others neutral, and
`verify_slides` reports no overlap for the chart frame.

## Tables and charts (Chart Guidelines_W)

> For general data listing, utilize standard neutral-toned layouts. When
> emphasizing key metrics or competitive advantages, use the highlight type
> featuring our point color, Neon Green.

Pick exactly one of three table types.

**Standard Type** — neutral data listing

- Header row fill `#24292F`, header font `#FFFFFF` bold 14 pt, centered.
- Body rows: white / `#F6F8FA` alternating, font `#1B1F23` 14 pt.
- Row separators `#D9E4ED`; no vertical borders.

**Highlight Type 1** — emphasize a column (e.g. the Rebellions product column)

- That column's header fill `#52F756` with `#1B1F23` bold text; its body cells
  `#F6F8FA` with `#1B1F23` bold values.
- All other columns stay Standard Type.

**Highlight Type 2** — emphasize a row or individual metrics

- Highlighted row fill `#52F756`, text `#1B1F23` bold; or leave the row neutral
  and set only the winning values to `#52F756` bold text on `#1B1F23`.

Table mechanics:

- Always `shapes.addTable(rows, cols, {values, left, top, width, height})` —
  never text boxes.
- Left-align label columns, right-align numeric columns, center headers.
  `verticalAlignment = "Middle"`.
- Plan height at ~30 pt per single-line row:
  `maxRows = Math.floor((540 - top - 36) / 30)`. Split across slides rather than
  shrinking below 14 pt.
- To change existing cell **text**, use `edit_slide_xml` on the `<a:tbl>`;
  Office.js `cell.text` writes do not persist. Fills and fonts may be set via
  Office.js.

**Done when:** the table matches exactly one of the three types, and no more
than one column or row carries Neon Green.

## Layout and geometry

- Slide canvas is 960 × 540 pt; keep a 36 pt safe margin on all sides.
- Prefer the master layouts `Slide_W_1`, `Slide_W_2`, `Slide_W_Full` for data
  slides. `Graph Guidelines_W` and `Chart Guidelines_W` are reference layouts —
  read them for spec, do not overwrite them.
- Never hardcode the content top edge. Call `list_slide_shapes` first, then
  start content at `title.top + title.height + ≥10 pt`.
- One visual per slide plus a one-line takeaway in supporting-headline style. If
  two visuals are required, give each half the width and keep the palette
  identical.
- Write the insight, not the chart type, in the title: "TCO drops 42% at equal
  throughput", not "TCO comparison".

## Workflow

1. Confirm the data, the single message, and the visual type (graph vs. standard
   table vs. highlight table). Ask if the highlighted series/column is
   ambiguous.
   **Done when:** you can name the one element that will be Neon Green.
2. `list_slide_shapes` on the target slide; measure the title band and available
   content box.
   **Done when:** you have numeric left/top/width/height for the visual.
3. Build the visual — `edit_slide_chart` for graphs, `execute_office_js` +
   `addTable` for tables, `edit_slide_xml` for KPI callouts.
   **Done when:** the shape exists on the slide with palette-compliant fills.
4. Add the takeaway line (supporting headline, 24–28 pt) and, if the data has a
   source, the 8 pt footnote.
   **Done when:** title, visual and source are all present.
5. `verify_slides` on the slide, then `verify_slide_visual` with
   `expected_changes` describing the palette and highlight choice. Fix every
   reported defect and contrast warning, then re-verify.
   **Done when:** verdict is `done` and no contrast warnings remain.

## Compliance checklist

- [ ] Exactly one Neon Green highlight; everything else neutral (6:2:2 if a
      schematic).
- [ ] All colors from the palette tables; no tints, gradients, or shadows.
- [ ] All chart/table text ≥ 14 pt; footnote 8 pt only.
- [ ] Pretendard only, for both Korean and English, with `<a:latin>` and
      `<a:ea>` matched.
- [ ] Legend top or absent; horizontal gridlines only in `#D9E4ED`.
- [ ] Data labels visible on the key series.
- [ ] Real chart / real table — never shapes imitating data.
- [ ] Content inside the 36 pt safe area, below the measured title band.
