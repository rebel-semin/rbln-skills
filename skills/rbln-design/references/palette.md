# Palette reference

Source: Rebellions 2026 Deck Guide, Color Guidelines. Contrast ratios were computed
with `scripts/check_colors.py --matrix` (WCAG 2.x relative luminance).

## The twelve colors

| Token | Hex | Role |
|---|---|---|
| green | `#52F756` | Point / highlight. Theme file stores accent1 as `51F756`; treat as the same color. |
| black | `#1B1F23` | Near-black: body text on light, background on dark |
| gray-900 | `#24292F` | Dark gray: series 2, panels, table header, muted text on light |
| gray-400 | `#BBC4CF` | Mid gray: series 3, muted text on dark, footnotes on slides |
| gray-200 | `#D9E4ED` | Light blue-gray: series 4, gridlines, borders, rules |
| gray-050 | `#F6F8FA` | Off-white: light surface, zebra rows, highlighted-column body |
| white | `#FFFFFF` | Page background |
| blue | `#174BEB` | Secondary accent |
| purple | `#9A4EFF` | Secondary accent |
| pink | `#F7318B` | Secondary accent |
| red | `#FF3333` | Secondary accent |
| yellow | `#FFD527` | Secondary accent |

No other hex value is allowed. No tints, shades, opacity steps, gradients or
shadows derived from these. If a visual seems to need more colors, it has too
many series or too many categories — split it.

## Text pairings (contrast)

| Text | Background | Ratio | Verdict |
|---|---|---|---|
| `#1B1F23` | `#FFFFFF` / `#F6F8FA` | 16.6 / 15.6 | body text |
| `#24292F` | `#FFFFFF` / `#F6F8FA` | 14.7 / 13.8 | body text, muted text on light |
| `#1B1F23` | `#52F756` | 11.7 | the only text color on Neon Green |
| `#F6F8FA` / `#FFFFFF` | `#1B1F23` | 15.6 / 16.6 | body text on dark |
| `#F6F8FA` / `#FFFFFF` | `#24292F` | 13.8 / 14.7 | table header text, text on panels |
| `#BBC4CF` | `#1B1F23` / `#24292F` | 9.4 / 8.3 | muted text on dark |
| `#D9E4ED` | `#1B1F23` | 12.8 | secondary text on dark |
| `#52F756` | `#1B1F23` / `#24292F` | 11.7 / 10.3 | Neon Green text is fine **on dark** |
| `#52F756` | `#FFFFFF` / `#F6F8FA` | 1.4 / 1.3 | **fails** — never Neon Green text on light |
| `#BBC4CF` | `#FFFFFF` | 1.8 | **fails** as web text; deck footnotes accept it at 8 pt on print/slides only |
| `#174BEB` | `#FFFFFF` | 6.5 | the one secondary usable as body text on light |
| `#9A4EFF` | `#FFFFFF` | 4.3 | large text (≥ 24 px / 18 pt) only |
| `#F7318B` / `#FF3333` | `#FFFFFF` | 3.6 | large text only |
| `#FFD527` | `#FFFFFF` | 1.4 | fills only; text on it is `#1B1F23` (11.7) |

Consequences for media the deck guide did not cover:

- On light surfaces Neon Green is a **mark** (bar, line, rule, dot, cell fill),
  and the text that names it is `#1B1F23`. A KPI number in Neon Green on white is
  a slide convention that tolerates 1.4:1 at 44 pt; on the web put the number in
  `#1B1F23` and let a 4 px green rule or a green chip carry the highlight, or use
  a dark tile.
- Muted text on light is `#24292F`, not `#BBC4CF`.
- Neon Green text is acceptable on `#1B1F23` / `#24292F` surfaces, which is why
  dark dashboards can use it for the highlighted KPI value.

## Series order

| Slot | Light surface | Dark surface (`#1B1F23`) |
|---|---|---|
| 1 — the story | `#52F756` | `#52F756` |
| 2 | `#24292F` | `#D9E4ED` |
| 3 | `#BBC4CF` | `#BBC4CF` |
| 4 | `#D9E4ED` | `#24292F` (barely visible — avoid) |
| 5+ | secondary accents, and the chart is too crowded | same |

On dark surfaces `#24292F` disappears against the background, so the neutral
order is reversed. Prefer ≤ 3 series on dark.

## Sequential / ordinal encodings (extension)

The deck guide has no heatmap or choropleth rule and forbids tints. When a
sequential encoding is unavoidable, step through the neutrals in order —
`#F6F8FA → #D9E4ED → #BBC4CF → #24292F` (4 steps max) — and reserve `#52F756`
for the single cell, bin or region the visual is about. Do not interpolate
between palette colors.

## Diagram ratio

Hardware schematics and diagram-heavy visuals: **6 : 2 : 2** — Neon Green :
secondary : secondary. Green remains dominant; the two secondaries distinguish
subsystems (e.g. blue = data path, purple = control). Everything else is neutral
strokes and fills.
