# Web, HTML artifacts and chart libraries

Use with `${CLAUDE_SKILL_DIR}/assets/rbln-tokens.css`. Paste the file inline
into single-file artifacts; link it in multi-file projects.

## 1. Load Pretendard

Pretendard is open source (SIL OFL, github.com/orioncactus/pretendard) and on
jsDelivr. Variable build (one file, all weights):

```html
<link rel="stylesheet" as="style" crossorigin
      href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css">
```

Static build (separate weight files, use if variable fonts are a problem):

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
```

Both URLs returned 200 on 2026-09-03. Then:

```css
body { font-family: var(--rbln-font); font-feature-settings: "tnum"; }
```

**Claude artifacts and other CSP-restricted hosts** allow stylesheets only from
`fonts.googleapis.com`, so the jsDelivr link is silently blocked. The font stack
in the tokens file still picks up a locally installed Pretendard; for viewers
without it, add Noto Sans KR from Google Fonts as the Korean-capable fallback:

```html
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@200;400;500;600&display=swap">
```

Never leave the stack without a Korean-capable face — mixed-script text will
render Korean in a different family, which is the exact failure the guide bans.

## 2. Type scale (extension of the deck scale)

| Role | Size | Weight | Line height | Deck equivalent |
|---|---|---|---|---|
| Display | 44 px / 2.75rem | 600 | 1.0 | Headline 44 pt |
| H1 | 32 px | 600 | 1.0 | Headline 32 pt |
| H2 | 28 px | 500 | 1.1 | Supporting 28 pt |
| H3 | 24 px | 500 | 1.1 | Supporting 24 pt |
| Lead | 20 px | 400 | 1.4 | Body 20 pt |
| Body / chart text | 14 px (16 px for long reading) | 400 | 1.5 | Body 14 pt |
| Caption / source | 12 px | 200 or 400 | 1.4 | Footnote 8 pt |

Chart and table text never goes below 14 px; captions never below 12 px. Pretendard
ExtraLight (200) at 12 px is legible on desktop but thin on low-DPI screens — use
400 for captions that must be read, 200 for decorative source lines.

Title the visual with the insight, in H3 weight 500: "TCO drops 42% at equal
throughput", not "TCO comparison".

## 3. Dark mode

The tokens file follows the three-state pattern: light on bare `:root`, dark
under `@media (prefers-color-scheme: dark)` guarded by `:root:not([data-theme="light"])`,
dark again under `:root[data-theme="dark"]`. Use only the semantic tokens
(`--rbln-bg`, `--rbln-fg`, `--rbln-series-2`, ...) in components; never the raw
palette names. Then every component flips correctly and series 2 becomes
`#D9E4ED` on dark instead of the invisible `#24292F`.

Charts drawn on `<canvas>` do not read CSS variables. Read them once:

```js
const t = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const SERIES = [t('--rbln-series-1'), t('--rbln-series-2'), t('--rbln-series-3')];
```

and re-render on `matchMedia('(prefers-color-scheme: dark)').addEventListener('change', ...)`.

## 4. Chart libraries

Common rules, whatever the library: horizontal gridlines only in `--rbln-grid`,
no vertical gridlines, no axis lines or chart border, category ticks hidden,
legend top-left or absent (single series → label directly), data labels 14 px
on the highlighted series, bar gap 60–80 % of bar width, line stroke 2.25 px,
markers only on the highlighted series, no animation-easing gimmicks, no 3-D.

### Chart.js (v4)

```js
Chart.defaults.font.family = t('--rbln-font');
Chart.defaults.font.size = 14;
Chart.defaults.color = t('--rbln-fg');
new Chart(ctx, {
  type: 'bar',
  data: { labels, datasets: [{
    data,
    backgroundColor: data.map((_, i) => i === hl ? t('--rbln-series-1') : t('--rbln-series-2')),
    borderWidth: 0, barPercentage: 0.6, categoryPercentage: 1.0,
  }]},
  options: {
    plugins: { legend: { display: false }, tooltip: { bodyFont: { size: 14 } } },
    scales: {
      x: { grid: { display: false }, border: { display: false }, ticks: { color: t('--rbln-fg-muted') } },
      y: { grid: { color: t('--rbln-grid') }, border: { display: false }, ticks: { color: t('--rbln-fg-muted') } },
    },
  },
});
```

Multi-series: `datasets[i].backgroundColor = SERIES[i]`, legend `{ position: 'top', align: 'start' }`.
Line: `borderWidth: 2.25`, `pointRadius: 0` on neutral series, `pointRadius: 4` on the highlighted one.

### Recharts

```jsx
<BarChart data={rows} barCategoryGap="40%">
  <CartesianGrid vertical={false} stroke="var(--rbln-grid)" />
  <XAxis dataKey="name" tickLine={false} axisLine={false} tick={{ fill: 'var(--rbln-fg-muted)', fontSize: 14 }} />
  <YAxis tickLine={false} axisLine={false} tick={{ fill: 'var(--rbln-fg-muted)', fontSize: 14 }} />
  <Bar dataKey="value" isAnimationActive={false} label={{ position: 'top', fontSize: 14, fill: 'var(--rbln-fg)' }}>
    {rows.map((r, i) => <Cell key={i} fill={i === hl ? 'var(--rbln-series-1)' : 'var(--rbln-series-2)'} />)}
  </Bar>
</BarChart>
```

Recharts passes `var(--…)` through to SVG `fill`, so tokens work directly and
dark mode needs no JS. Multi-series: `<Legend verticalAlign="top" align="left" iconType="square" />`.

### ECharts

```js
echarts.registerTheme('rbln', {
  color: SERIES,
  backgroundColor: 'transparent',
  textStyle: { fontFamily: t('--rbln-font'), fontSize: 14, color: t('--rbln-fg') },
  categoryAxis: { axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: false },
                  axisLabel: { color: t('--rbln-fg-muted') } },
  valueAxis: { axisLine: { show: false }, axisTick: { show: true }, splitLine: { lineStyle: { color: t('--rbln-grid') } },
               axisLabel: { color: t('--rbln-fg-muted') } },
  legend: { top: 0, left: 0, icon: 'rect', textStyle: { fontSize: 14 } },
  bar: { barCategoryGap: '40%', itemStyle: { borderWidth: 0 } },
  line: { lineStyle: { width: 2.25 }, symbol: 'none' },
});
echarts.init(el, 'rbln');
```

Highlight one bar with `data: values.map((v, i) => i === hl ? { value: v, itemStyle: { color: SERIES[0] } } : v)`
and set the series `color` to `SERIES[1]`.

### D3

```js
const color = d3.scaleOrdinal().domain(keys).range(SERIES);
svg.selectAll('.grid line').attr('stroke', t('--rbln-grid'));   // y grid only
svg.select('.x-axis').call(d3.axisBottom(x).tickSize(0)).select('.domain').remove();
svg.select('.y-axis').call(d3.axisLeft(y).tickSize(4)).select('.domain').remove();
```

### Plotly.js

Mirror `assets/rbln_plotly.py`: `layout.colorway = SERIES`, `layout.font = { family, size: 14 }`,
`xaxis: { showgrid: false, zeroline: false, ticks: '' }`, `yaxis: { gridcolor, zeroline: false, ticks: 'outside' }`,
`legend: { orientation: 'h', y: 1.02, yanchor: 'bottom', x: 0 }`, `bargap: 0.4`.

### Vega-Lite

```json
"config": {
  "font": "Pretendard",
  "range": { "category": ["#52F756", "#24292F", "#BBC4CF", "#D9E4ED"] },
  "axis": { "domain": false, "gridColor": "#D9E4ED", "labelFontSize": 14, "titleFontSize": 14, "labelColor": "#24292F" },
  "axisX": { "grid": false, "ticks": false },
  "legend": { "orient": "top", "labelFontSize": 14 },
  "bar": { "discreteBandSize": { "band": 0.6 } },
  "line": { "strokeWidth": 2.25 },
  "view": { "stroke": null }
}
```

## 5. Tables and KPI tiles

The tokens file ships the three table types and a KPI tile as classes.

```html
<table class="rbln-table rbln-table--col">
  <thead><tr><th>Metric</th><th>H100</th><th class="rbln-hl">REBEL</th></tr></thead>
  <tbody>
    <tr><td class="rbln-label">TPOT (ms)</td><td class="rbln-value">31</td><td class="rbln-value rbln-hl">22</td></tr>
  </tbody>
</table>
```

- Standard: `.rbln-table` alone.
- Highlight Type 1 (one column): add `.rbln-table--col` and put `.rbln-hl` on that column's `<th>` and `<td>`s.
- Highlight Type 2 (one row or single cells): add `.rbln-table--row`; `.rbln-hl` on the `<tr>`, or `.rbln-win` on the winning `<td>`s.
- Never both modifiers on one table; never two highlighted columns.

```html
<div class="rbln-kpi rbln-kpi--highlight">
  <span class="rbln-kpi__label">Throughput at o250</span>
  <span class="rbln-kpi__value">5,300 <small>users</small></span>
</div>
```

One tile in a row carries `.rbln-kpi--highlight`. On light surfaces the value
stays near-black and the green top rule marks it; on dark surfaces the value
itself turns Neon Green (11.7:1).

## 6. UI chrome (extension, minimal)

The deck guide covers data visuals, not application UI. When a page needs
controls, keep them inside the same system:

- Primary action: `background: var(--rbln-highlight); color: var(--rbln-on-highlight)`; there is one per view, the same way there is one highlighted series.
- Secondary action: `border: 1px solid var(--rbln-fg); color: var(--rbln-fg); background: transparent`.
- Focus ring: `outline: 2px solid var(--rbln-highlight); outline-offset: 2px` on dark; `outline: 2px solid var(--rbln-fg)` on light (green on white is 1.4:1 and fails as a focus indicator).
- Radius 4 px on controls; 0 on charts and tables. No shadows, no gradients.
- Wide tables and charts sit inside `.rbln-scroll-x`; the page never scrolls horizontally.

## 7. Verify

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/check_colors.py index.html styles.css
```

Exit 0 and a single `#52F756` highlight (or one per chart, if several charts).
Then view the page in both color schemes and confirm the highlighted element is
the one the title talks about.
