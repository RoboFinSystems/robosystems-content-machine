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
- **`@robosystems/core` design system** (synced into your claude.ai/design project; see its
  `conventions.md` for component/usage rules). This is the source of brand truth.

## Brand
- **House brand: RoboSystems (blue)** unless the brief says otherwise.
- **Orbitron** for display headings + eyebrow labels; **Space Grotesk** for body/UI.
- Dark theme. Accent color for the one thing that matters per slide. Eyebrow section labels
  (e.g. `01 / THE PAIN`). Subtle source-attribution footer.

## The deck
- **16:9, 1920×1080**, dark. Produce **exactly N slides, one per brief section, in order**
  (N is stated at the top of the brief). Don't add, drop, or reorder slides.
- **No separate intro/outro** — the **first slide is the open (hook), the last is the CTA**.
  The deck bookends itself.
- Render each slide by its kind:

| Kind | Render as |
|---|---|
| `title` | Big headline, eyebrow label, lots of negative space. Little/no data. The hook and the close. |
| `chart` | The headline + the data as the stated `chart_type` (bar / line / table / metric_cards). Green = positive, red = negative, brand accent = neutral/current. Emphasize the `highlight`. |
| `callout` | One enormous number (the `headline`) with a label above and a context line below. Color by `tone` (positive/negative/neutral/warning). |
| `dual` | Split: narrative bullets on the left, compact data/metrics on the right. |

- Keep every on-screen number **exactly** as the brief gives it. The slide and the narration
  are one unit — if the brief's narration says "1.2 billion," the slide shows that number.

## The thumbnail
A **separate 16:9 frame — NOT part of the video sequence.** Build it from the brief's
**Thumbnail** section:
- **Hero metric** — the one cognitive-dissonance number, huge and centered (e.g. an adjusted
  P/E, an implied re-rating). This is the click driver.
- **Banner** (optional, per brief) — e.g. a campaign tag, top corner.
- **1–2 secondary metrics** — small, supporting.
- Ticker + company name, RoboSystems logo.
- **Readable at tiny sizes** — assume a 1cm-wide preview. Bold, high contrast, minimal words.

## Export
Claude Design exports **PDF only** — export *both* as PDF; the pipeline rasterizes them.
1. **Deck → PDF** (16:9, one slide per page) → save to `deck/{TICKER}_deck.pdf`.
2. **Thumbnail → PDF** (16:9, single page) → save to `deck/{TICKER}_thumbnail.pdf`.
   The `slice` step rasterizes it to `charts/png/{TICKER}_thumbnail.png` at 1920×1080 — you
   don't export a PNG by hand.
3. Then the pipeline takes over: `just pipeline {TICKER}` (slices the deck **and** the thumbnail).

## Recommended workflow (repeatable)
Build a **reusable house-brand "video deck" template** in Claude Design **once** — one
example of each slide kind + a thumbnail frame, all on `@robosystems/core`. For each new
video: **duplicate the template, paste the per-project brief, fill it in.** The durable
conventions live in the template; the per-project paste stays small.

## Quality bar
- On-brand, consistent across slides, legible at video scale.
- Numbers verbatim from the brief; no invented data.
- N slides, in order; first = hook, last = CTA; thumbnail exported separately.
