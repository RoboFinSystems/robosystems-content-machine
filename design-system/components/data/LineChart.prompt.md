# LineChart

The chart for a `chart` slide whose `chart_type` is `line` — a trend over an ordered
axis (label → number). Reach for it when the **shape over time** is the story
(revenue trajectory, margins, price). Use `BarChart` instead to compare discrete
periods, and `Callout` when a single number is the point.

## Props

| Prop | Type | Notes |
|---|---|---|
| `data` | `{label: number}` **or** `{ series: {name: {label: number}} }` | Single or multi-series. Same shape the brief emits for `chart_type: line`. |
| `highlight` | `string` | Multi-series: the series **name** drawn in the accent; the rest are muted. |
| `format` | `(value) => string` | Formats the current-value tag, e.g. `(v) => '$' + (v/1e9).toFixed(2) + 'B'`. |
| `height` | `number` | px (default 260). |

The lead series is the brand blue with point dots and a glow on the final point; the
current value is tagged at the right. Other series are muted (graph teal, then grey).

## Single series

```jsx
<LineChart
  data={{ FY2021: 893560000, FY2022: 1017375000, FY2023: 1054553000, FY2024: 1137141000, FY2025: 1175295000 }}
  format={(v) => '$' + (v / 1e9).toFixed(2) + 'B'}
  height={300}
/>
```

## Multi-series — line's sweet spot (two trajectories at once)

```jsx
<LineChart
  data={{ series: {
    'Gross margin': { FY22: 49, FY23: 50, FY24: 52, FY25: 51 },
    'Net margin':   { FY22: 8,  FY23: 11, FY24: 14, FY25: 13 },
  }}}
  highlight="Net margin"
  format={(v) => v + '%'}
  height={300}
/>
```

Keep it to **~3 lines max** on a slide — one accent series, the rest muted. Numbers
verbatim from the brief; the axis labels are the series' keys, in order.
