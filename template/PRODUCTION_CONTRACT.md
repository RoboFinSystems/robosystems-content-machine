
# Production Contract — How Written Outputs Become a Video

This is the **shared, campaign-agnostic** contract for the content pipeline. Your
`COWORK_INSTRUCTIONS.md` (base or campaign) defines the *editorial* work — what to analyze,
the angle, the tone. **This file defines the *mechanical* work** — the exact file formats
the production pipeline consumes. Both the generic template and every campaign reference
this file, so the schema and rules below are identical for every video.

> If anything here conflicts with your `COWORK_INSTRUCTIONS.md`, the editorial direction in
> that file wins for *content*; this file wins for *format and schema*.

---

## The production model (deck mode)

You produce **written artifacts**. A largely-automated pipeline turns them into a narrated
video. You do **not** author slide HTML or do any layout — slides are built in Claude
Design from the brand design system.

```
You (Cowork)                          Claude Design (DESIGN_INSTRUCTIONS.md)
─────────────                         ─────────────────────────
scripts/{TICKER}_script.json   ──►  build_deck_brief → deck/{TICKER}_deck_brief.md
   (source of truth: narration            │
    + per-slide content + thumbnail)      ▼
                                     paste into claude.ai/design (on @robosystems/core)
                                     → compose 16:9 deck  → deck/{TICKER}_deck.pdf
                                     → compose thumbnail  → charts/png/{TICKER}_thumbnail.png
                                          │
                                          ▼
                                     Pipeline (code)
                                     slice_deck → charts/png/{visual_ref}.png
                                     voiceover (ElevenLabs) → assemble (Shotstack) → MP4
```

Your job ends at the **script** (plus the editorial outputs your `COWORK_INSTRUCTIONS.md`
lists — brief, social, etc.). The deck brief is *generated from your script* — you don't
write it. The only thing that makes the deck good is a complete, accurate script.

---

## Output: Video Script (`scripts/{TICKER}_script.json`)

The script is the **single source of truth** for the video. The ordered list of segments
defines the slides — their count, their order, and the narration timed to each.

```jsonc
{
  "metadata": {
    "ticker": "GTBIF",
    "company": "Green Thumb Industries Inc.",
    "filing_type": "10-K",
    "filing_date": "2026-02-25",
    "video_title": "Short, engaging YouTube title (under 70 chars)",
    "video_description": "YouTube description (2-3 sentences, keywords)",
    "tags": ["tag1", "tag2"],
    "thumbnail_text": "Bold text for thumbnail (2-4 words)",
    "campaign": "Optional campaign name"
  },

  "deck": {
    "slide_count": 12,                  // MUST equal the number of segments below
    "source": "deck/GTBIF_deck.pdf"     // filled in after the deck is built/exported
  },

  "thumbnail": {                        // content for the YouTube thumbnail (built in Claude Design)
    "hero": "9x adjusted P/E",          // the one cognitive-dissonance number (huge, centered)
    "banner": "INITIATING COVERAGE",    // optional top banner (campaign-specific; omit if none)
    "secondary": ["Revenue $1.1B", "280E cost $147M/yr"],  // 1–2 small supporting metrics
    "file": "charts/png/GTBIF_thumbnail.png"  // where the exported PNG lands
  },

  "segments": [
    {
      "id": 1,                          // sequential integer, starts at 1
      "type": "visual",                 // deck mode: every segment is "visual"
      "narration": "Spoken-form narration for this slide (see TTS rules below).",
      "visual_type": "title",           // title | chart | callout | dual  (the slide kind)
      "visual_ref": "hook",             // stable, unique slug — this IS the slide id,
                                        //   ordered 1:1 with the deck; → charts/png/hook.png
      "duration_estimate_seconds": 8,
      "slide": {                        // the slide's CONTENT (drives the generated brief)
        "headline": "Nobody covers this $1.2B company",
        "subhead": "GTBIF · FY2025 10-K",
        "data": {},                     // numbers/rows the slide must show (see per-kind below)
        "bullets": [],                  // for dual / list slides
        "highlight": "",                // the one value/row to emphasize
        "source": "SEC 10-K, FY2025"
      },
      "notes": "Optional production note (not shown on screen)"
    },
    {
      "id": 2,
      "type": "visual",
      "narration": "Revenue grew to one point two billion dollars in fiscal twenty twenty five …",
      "visual_type": "chart",
      "visual_ref": "revenue_trend",
      "duration_estimate_seconds": 12,
      "slide": {
        "headline": "Revenue, FY2022–FY2025",
        "subhead": "Annual, USD",
        "chart_type": "bar",            // chart slides: bar | line | table | metric_cards
        "data": { "FY2022": 1017375000, "FY2023": 1054553000,
                  "FY2024": 1090000000, "FY2025": 1200000000 },
        "highlight": "FY2025",
        "source": "SEC 10-K, FY2025"
      }
    }
  ],

  "short_version": {
    "description": "60-second vertical Short cut",
    "segment_ids": [1, 2, 5, 8],
    "notes": "Hook + key metric + pivot + CTA"
  }
}
```

### Field rules (the pipeline parses these programmatically — use them EXACTLY)

- `id` — integer, sequential from 1. (NOT `segment_id`.)
- `type` — always `"visual"` in deck mode.
- `narration` — spoken-form text (see TTS rules). This is what ElevenLabs reads.
- `visual_type` — one of `title | chart | callout | dual`. This is the slide *kind*.
- `visual_ref` — a short, unique, stable slug (`hook`, `revenue_trend`, `tax_burden`). **It
  is the slide id**: deck slide *i* maps to segment *i*, and the sliced image is named
  `{visual_ref}.png`. Keep them unique and in narration order.
- `duration_estimate_seconds` — integer estimate. (NOT `duration_seconds`.) Actual timing
  comes from the voiceover length at assembly; this is only for planning + Short cuts.
- `slide` — the on-screen content (see slide kinds). Put **exact numbers** here; this is
  what the deck renders, so vague data here = vague slides.
- `deck.slide_count` — set it to the number of segments. **Validation fails if they differ.**
- `thumbnail` — content for the YouTube thumbnail (hero metric + optional banner + 1–2
  secondary metrics). Built in Claude Design (see `DESIGN_INSTRUCTIONS.md`), exported to
  `thumbnail.file`. You spec the content here; you do **not** author any thumbnail HTML.

### Mapping rule

`segments` order **is** the deck order. The *i*-th segment ↔ the *i*-th deck slide ↔
`charts/png/{visual_ref}.png`. Don't reorder one without the other.

---

## Slide kinds and their content

Vary the kinds for rhythm — never run many `chart` slides back to back. A good cadence:
`title → chart → chart → callout → dual → chart → callout → title (close)`.

| `visual_type` | Use for | `slide` fields to fill |
|---|---|---|
| `title` | The hook, section breaks, the closing line. Big text, little/no data. | `headline` (required), `subhead`, optional one `highlight` stat |
| `chart` | A data visualization. | `headline`, `chart_type` (`bar`/`line`/`table`/`metric_cards`), `data` (the numbers/rows), `highlight`, `source` |
| `callout` | One big number that tells the story ("280E cost: $147M / year"). | `headline` (the big value), `subhead` (label above), `slide.data.context` (line below), optional `tone`: `positive`/`negative`/`neutral`/`warning` |
| `dual` | "What this means" — explanation + supporting data side by side. | `headline`, `bullets` (left, 2-4 short points), `data` (right, compact metrics/rows), `source` |

**`data` shape by chart_type:**
- `bar` / `line`: an ordered map of label → number (`{"FY2022": 1017375000, …}`), or for
  multi-series, `{ "series": { "Gross margin": {...}, "Net margin": {...} } }`.
- `table`: `{ "columns": ["Metric","FY2024","FY2025"], "rows": [["Revenue","$1.09B","$1.20B"], …] }`.
- `metric_cards`: a map of label → `{ "value": "$1.20B", "change": "+10% YoY" }`.

Put raw numbers in base units where you have them (revenue $1.2B = `1200000000`) **and** a
display form in `headline`/`highlight` if the phrasing matters. Claude Design formats for
display; the raw numbers keep it honest.

---

## How the deck gets built (after your script)

You don't do these steps, but understanding them tells you what a good script enables:

1. **`build_deck_brief.py`** renders `deck/{TICKER}_deck_brief.md` from your script — one
   section per slide (kind, headline, the data as a table, narration as speaker context),
   with a header pinning: *use the `@robosystems/core` design system, RoboSystems house
   brand, dark 16:9, produce exactly N slides in this order.*
2. A human pastes that brief into **claude.ai/design** and the deck is composed on-brand.
3. The deck is exported to `deck/{TICKER}_deck.pdf` (or per-slide PNGs).
4. **`slice_deck.py`** turns it into `charts/png/{visual_ref}.png`, one per slide.
5. Voiceover + Shotstack assemble the final video.

**Implications for your script:** every slide's `headline` and `data` must be complete and
exact — they become the literal content of the slide. The first slide is the intro, the
last is the close/CTA (no separate intro/outro files in deck mode).

---

## Thumbnail (`charts/png/{TICKER}_thumbnail.png`)

The thumbnail is **built in Claude Design**, not hand-authored — Cowork authors **no HTML at
all**. You spec the content in the script's `thumbnail` block (hero metric, optional banner,
1–2 secondary metrics); Claude Design builds it as a separate 16:9 frame (see
`DESIGN_INSTRUCTIONS.md`) and exports a PNG to `charts/png/{TICKER}_thumbnail.png`. It is
*not* part of the video sequence — the pipeline treats it as a publish-only asset.

---

## Narration must be spoken-form (for text-to-speech)

`narration` is sent directly to ElevenLabs. Symbols and abbreviations get mispronounced.
Never use `$ % x / &` in narration — spell everything out:

- Dollars: `$39.3B` → "39.3 billion dollars"; `$302.68` → "302 dollars and 68 cents"
- Billions: never "1,181 million" — say "one point two billion". Write words, not digits,
  for big numbers; round to one decimal where possible.
- Percentages: `25%` → "25 percent"; `+8.3%` → "up 8.3 percent"
- Multiples: `15.9x` → "15.9 times"
- Ratios: `P/E` → "price to earnings"; `P/S` → "price to sales"; `EV/EBITDA` → "E V to EBITDA"
- Abbreviations: `YoY` → "year over year"; `QoQ` → "quarter over quarter"; `EPS` → "earnings
  per share"; `ROE` → "return on equity"; `ROA` → "return on assets"; `FCF` → "free cash
  flow"; `GAAP` → "gap"
- Filings: `10-K` → "10 K"; `10-Q` → "10 Q"; `40-F` → "40 F"
- Symbols: `&` → "and"; `/` → spell out the context
- **Acronyms read as letters:** space them — `SEC` → "S E C", `CFO` → "C F O", `XBRL` →
  "X B R L", `LP` → "L P" (all confirmed clean). But spacing occasionally *drags* on
  vowel-heavy ones — `D E A` came out "Deeee… Aaa" — so when in doubt **spell the agency
  out fully** (`DEA` → "Drug Enforcement Administration"). Periods-no-space (`D.E.A.`) is
  the fallback.
- **`AI` is special — never space it.** `A I` gets read as the *word* "ai" (sounds like
  "eh"/"eye"). Write `AI` or `A.I.` instead.

*(Confirmed-bad spacings, by ear 2026-06: `A I`, `D E A`. Campaigns may add their own
pronunciation hints — e.g. a sector tax code or a company name TTS reads wrong.)*

---

## Universal rules

- **Never fabricate numbers.** Every figure comes from the MCP filing data or an attributed
  web source. If a metric is missing, note the gap and attribute the fallback.
- **Data on the slide must match the narration.** If the voice says "1.2 billion," the
  slide's `data`/`headline` shows that same number. Slide and words are one unit.
- **Completeness check before finishing:** confirm `script.json` is valid (every required
  field, `deck.slide_count` == segment count, unique ordered `visual_ref`s) and every output
  your `COWORK_INSTRUCTIONS.md` lists exists. The task isn't done until all files are saved.
