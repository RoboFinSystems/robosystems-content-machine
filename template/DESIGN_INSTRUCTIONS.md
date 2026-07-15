# Design Instructions — Building the Deck + Thumbnail in Claude Design

This is the **Stage 2** spec. The pipeline has three stages:

1. **Cowork** → research + `script.json` + brief + social (see `COWORK_INSTRUCTIONS.md` + `PRODUCTION_CONTRACT.md`)
2. **Claude Design** → the on-brand deck + thumbnail (← *this file*)
3. **Code** → slice + voiceover + mux + ship (the pipeline)

You build the **visuals**. Cowork hands you a generated brief; you compose the deck and the
thumbnail on the brand design system and export them. You decide layout and styling; you do
**not** invent data — every number comes from the brief.

## Inputs
- **`deck/{TICKER}_deck_brief.md`** — the per-project content (generated from the script by
  `build_deck_brief.py`). One section per slide + a thumbnail section. **Numbers are exact —
  reproduce them verbatim.**
- **The "RoboSystems Content Design System" Claude Design project** — this is the source of
  brand truth for content. **Point the design task at this project** (not the base
  `@robosystems/core` app kit — that's the web-product UI system the content DS was derived
  *from*, re-framed here for slides + stories). Its `readme.md` carries the full brand voice,
  visual foundations, and component/usage rules; its `guidelines/` hold the color/type/spacing
  specimens. Read those first — don't re-derive the brand here.

## Brand (summary — the design system's `readme.md` is authoritative)
- **House brand: RoboSystems (blue)** unless the brief says otherwise. Blue `#3b7af5`, navy
  stage `#0a0e1a`, signal green/red for data, **graph teal `#00d4aa` rationed for "structure"
  moments only**.
- **Orbitron** for display headings + eyebrow labels + hero numbers; **Space Grotesk** for
  body/UI; **JetBrains Mono** for tickers/code.
- Dark "stage" theme. Accent color for the **one** thing that matters per slide. UPPERCASE
  eyebrow section labels (`01 / THE PAIN`). Subtle source-attribution footer. No emoji on slides.

## The deck
- **16:9, 1920×1080**, dark. Produce **exactly N slides, one per brief section, in order**
  (N is stated at the top of the brief). Don't add, drop, or reorder slides.
- **No separate intro/outro** — the **first slide is the open (hook), the last is the CTA**.
  The deck bookends itself.
- **Start from the design system's `templates/video-deck/` template** (it already ships one
  example of each slide kind — title / metric-cards / bar / callout / bull-vs-bear / CTA).
  Render each brief slide by its kind, using the content DS's real components:

| Brief `kind` | Render with | Notes |
|---|---|---|
| `title` | Title/CTA slide layout | Big headline, eyebrow label, lots of negative space. Little/no data. The hook and the close. |
| `chart` | `BarChart` / `LineChart` / `ComparisonTable` / `MetricCard` (per `chart_type`: bar / line / table / metric_cards) | Green = positive, red = negative, brand blue = neutral/current. Emphasize the `highlight`. **`line`** = a trend over time (single or multi-series margins/trajectories); **`bar`** = discrete-period comparison. |
| `callout` | `Callout` | One enormous number (the `headline`), label above, context line below. Color by `tone` (positive/negative/neutral/warning). |
| `dual` | Split layout (narrative bullets left, `MetricCard` stack right); use the **bull-vs-bear** variant when the brief frames two sides. |

- Keep every on-screen number **exactly** as the brief gives it. The slide and the narration
  are one unit — if the brief's narration says "1.2 billion," the slide shows that number.

### Charts show the shape, not just the values
A chart that's technically correct but rhetorically dead is a failed slide. Dumping numbers
into a component is how you get six near-level bars, or a negative value flattened to a stub.
The brief carries an auto-derived **"Chart rendering"** note on each bar/line slide — obey it.

- **Every chart slide has a `Visual takeaway`** (one sentence: what the viewer should grasp at
  a glance). Design the chart so that takeaway is unmistakable. If the brief omits it, infer it
  from the headline + narration before you draw.
- **Bars are quantitative, not decorative.** Common **zero baseline**, height strictly
  proportional to value (`height = value ÷ max × plot`), equal widths and gaps. A bar taller
  than a bigger number is a bug, not a style choice.
- **Negative values render below a zero axis in signal red** — never a floor stub, never an
  absolute-value bar.
- **Narrow-range series** (smallest value within ~70% of the largest — revenue that only
  drifts) read as flat on a zero baseline. Prefer an **honest reframe** — plot the
  period-over-period change, or a labeled-axis line — that actually shows the shape. A truncated
  baseline is a last resort, allowed only when the **axis break is visibly marked and every bar
  is labeled with its verbatim value**. An unmarked truncation is a misleading chart, which this
  brand does not ship.
- **Line charts** get a y-axis fit to the data (no forced zero), even x-spacing, and true
  slopes. A trend must read as a trend.

## The thumbnail
A **separate 16:9 frame — NOT part of the video sequence.** Start from the design system's
**`templates/thumbnail/`** template and fill it from the brief's **Thumbnail** section:
- **Hero metric** — the one cognitive-dissonance number, huge and centered (e.g. an adjusted
  P/E, an implied re-rating). This is the click driver.
- **Banner** (optional, per brief) — e.g. a campaign tag, top corner.
- **1–2 secondary metrics** — small, supporting.
- Ticker + company name, RoboSystems mark.
- **Readable at tiny sizes** — assume a 1cm-wide preview. Bold, high contrast, minimal words.

## Export + hand off (operator step, not the design agent)
The design agent's job ends once the deck and thumbnail exist in the Claude Design canvas. It
cannot write into this repo or run PowerPoint. Everything below is a **manual step the operator
does** in the Design UI and the shell; the pipeline then takes over. Export the deck as **PDF**
and the thumbnail as **PNG**.
1. **Deck -> PDF** (16:9, one slide per page) -> save to `deck/{TICKER}_deck.pdf`.
   If Claude Design's direct PDF export routes through the macOS print dialog and mangles the
   layout, export to **PPTX** instead, then use PowerPoint's **Export -> PDF** (widescreen 16:9
   is 960x540 pt, which is correct). The `slice` step force-scales each page to 1920x1080.
2. **Thumbnail -> PNG** -> save to `deck/{TICKER}_thumbnail.png`. The single-frame PDF export
   tends to misbehave, so PNG is the reliable path. The `slice` step center-crops it to 16:9 and
   writes `charts/png/{TICKER}_thumbnail.png` at 1920x1080 (a clean `deck/{TICKER}_thumbnail.pdf`
   still works if you have one).
3. Then the pipeline takes over: `just pipeline {TICKER}` (slices the deck **and** the thumbnail).

## Recommended workflow (repeatable)
The durable conventions now live in the **content design system**, not in a hand-built file.
For each new video: open the **"RoboSystems Content Design System"** project, **duplicate the
`video-deck` and `thumbnail` templates, paste the per-project brief, and fill it in.** The
per-project paste stays small; the brand stays consistent because every deck is built from the
same templates + components.

## Quality bar
- On-brand, consistent across slides, legible at video scale.
- Numbers verbatim from the brief; no invented data.
- N slides, in order; first = hook, last = CTA; thumbnail exported separately.
