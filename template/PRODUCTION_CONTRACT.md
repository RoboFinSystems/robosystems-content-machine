
# Production Contract — How Written Outputs Become a Video

This is the **shared, campaign-agnostic** contract for the content pipeline. Your
`AUTHORING_INSTRUCTIONS.md` (base or campaign) defines the *editorial* work — what to analyze,
the angle, the tone. **This file defines the *mechanical* work** — the exact file formats
the production pipeline consumes. Both the generic template and every campaign reference
this file, so the schema and rules below are identical for every video.

> If anything here conflicts with your `AUTHORING_INSTRUCTIONS.md`, the editorial direction in
> that file wins for *content*; this file wins for *format and schema*.

---

## The production model (one-shot)

You produce **written artifacts**. Code turns them into narrated video with no other app in
the loop — no Cowork hand-off, no Claude Design step, no clipboard. You do **not** author
slide HTML or do any layout: the renderer builds every slide from your `script.json`.

```
/author  (this session)                    Code (just webdeck-pipeline / webdeck-short-pipeline)
──────────────────────                     ────────────────────────────────────────────────
reports/{TICKER}_brief.md          ──►  validate
scripts/{TICKER}_script.json       ──►  voiceover (ElevenLabs)  →  build_webdeck (HTML)
scripts/{TICKER}_short_script.json ──►  headless-Chrome frame render  →  ffmpeg mux
social/                                 →  videos/{TICKER}_final.mp4   (16:9 long-form)
                                        →  videos/{TICKER}_short.mp4   (9:16 short)
                                        thumbnails: just thumbnails {TICKER} (OpenAI)
                                              │
                                              ▼
                                        publish → yt-upload / yt-short / x-article / x-short
```

Your job ends at the **written artifacts**. The only thing that makes the video good is a
complete, accurate script: every `headline` and every `data` value renders on screen verbatim.

**The 16:9 deck path is retired.** `build_deck_brief.py`, `slice_deck.py`, `assemble_video.py`
(Shotstack) and `DESIGN_INSTRUCTIONS.md` remain in the repo as history and are not part of a
run. Ignore any instruction to produce a deck brief, a PPTX or a PDF.

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
    "campaign": "Optional campaign name"
  },

  "deck": {
    "slide_count": 12                   // MUST equal the number of segments below
  },

  "segments": [
    {
      "id": 1,                          // sequential integer, starts at 1
      "type": "visual",                 // every segment is "visual"
      "narration": "Spoken-form narration for this slide (see TTS rules below).",
      "visual_type": "title",           // title | chart | callout | dual  (the slide kind)
      "visual_ref": "hook",             // stable, unique slug — this IS the slide id,
                                        //   ordered 1:1 with the rendered slides
      "eyebrow": "Initiating Coverage", // 2-4 word section label ("01 / INITIATING COVERAGE");
                                        //   every segment except the closing CTA
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
        "visual_takeaway": "growth surged FY22 to FY23, then flattened; last three bars read nearly level",
        "source": "SEC 10-K, FY2025"
      }
    }
  ]
}
```

### Field rules (the pipeline parses these programmatically — use them EXACTLY)

- `id` — integer, sequential from 1. (NOT `segment_id`.)
- `type` — always `"visual"`.
- `narration` — spoken-form text (see TTS rules). This is what ElevenLabs reads.
- `visual_type` — one of `title | chart | callout | dual`. This is the slide *kind*.
- `visual_ref` — a short, unique, stable slug (`hook`, `revenue_trend`, `tax_burden`). **It
  is the slide id**: slide *i* maps to segment *i*. Keep them unique and in narration order.
  The renderer treats `visual_ref: "cta"` specially and gives that segment the CTA layout,
  so use it for the closing segment and nowhere else.
- `eyebrow` — a 2-4 word section label rendered as the slide's numbered eyebrow
  ("03 / THE TREND"; numbering is automatic from segment order). Give one to every
  segment except the closing CTA. Mirror the deck's editorial voice: "The Top Line",
  "Read the Split", "Capital Returns" — a beat name, not a chart caption.
- `duration_estimate_seconds` — integer estimate ≈ **narration characters ÷ 16** (real TTS pace
  is ~16 chars/sec; under-counting makes draft timestamps ~2× short). (NOT `duration_seconds`.)
  Actual timing comes from the real voiceover durations at build time, which also write
  `videos/{TICKER}_timestamps.txt` with the real YouTube chapter times.
- `slide` — the on-screen content (see slide kinds). Put **exact numbers** here; this is
  what the renderer draws verbatim, so vague data here = vague slides.
- `deck.slide_count` — set it to the number of segments. **Validation fails if they differ.**
- Thumbnails are generated by `just thumbnails` from the brief, **not authored here** — no
  `thumbnail` block.
  See `DESIGN_INSTRUCTIONS.md`.

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
| `chart` | A data visualization. | `headline`, `chart_type` (`bar`/`line`/`table`/`metric_cards`), `data` (the numbers/rows), `highlight`, `visual_takeaway` (one line: what the chart must make obvious), `source` |
| `callout` | One big number that tells the story ("280E cost: $147M / year"). | `headline` (the big value), `subhead` (label above), `slide.data.context` (line below), optional `tone`: `positive`/`negative`/`neutral`/`warning` |
| `dual` | "What this means" — explanation + supporting data side by side. | `headline`, `bullets` (left, 2-4 short points), `data` (right, compact metrics/rows), `source` |

**`data` shape by chart_type:**
- `bar` / `line`: an ordered map of label → number (`{"FY2022": 1017375000, …}`), or for
  multi-series, `{ "series": { "Gross margin": {...}, "Net margin": {...} } }`.
- `table`: `{ "columns": ["Metric","FY2024","FY2025"], "rows": [["Revenue","$1.09B","$1.20B"], …] }`.
- `metric_cards`: a map of label → `{ "value": "$1.20B", "change": "+10% YoY" }`.

**`visual_takeaway`** (chart slides) — one sentence naming what the viewer should see at a
glance ("up five years straight," "one segment negative," "flat until the last bar"). Write it
honestly: a flat series should say so rather than being framed as growth, and a series with
negatives needs one, because the renderer will draw exactly what the numbers say.

Put raw numbers in base units where you have them (revenue $1.2B = `1200000000`) **and** a
display form in `headline`/`highlight` if the phrasing matters. The renderer formats for
display; the raw numbers keep it honest.

---

## How the video gets built (after your script)

You don't do these steps, but understanding them tells you what a good script enables.
`just webdeck-pipeline {TICKER}` runs them in order:

1. **`validate_project.py`** checks the schema, the spoken-form narration rules and the
   publish metadata. Errors abort the run.
2. **Voiceover** (ElevenLabs) renders one MP3 per segment; their real durations set the
   timing for everything downstream.
3. **`build_webdeck.py`** turns the script + those durations into a single animated HTML
   page, `webdeck/{TICKER}_webdeck.html`, and writes the chapter list to
   `videos/{TICKER}_timestamps.txt`.
4. **`render_webdeck.mjs`** renders it frame by frame in headless Chrome at 1080p30.
5. **`mux_webdeck.py`** lays the narration onto the silent render at exact offsets and adds
   a music bed ducked under the VO, producing **`videos/{TICKER}_final.mp4`** (the publish
   candidate) plus a VO-only compare at `webdeck/{TICKER}_webpilot.mp4`.

**Implications for your script:** every slide's `headline` and `data` must be complete and
exact — the page renders them verbatim, so there is no design pass to catch a wrong number
or a headline that does not fit. The first segment is the intro, the last is the close/CTA
(no separate intro/outro files). The `eyebrow` field is rendered, so every segment except
the CTA needs one.

---

## Thumbnails (generated, not authored here)

`just thumbnails {TICKER}` reads the brief and generates all three per-platform images via
OpenAI (gpt-5 writes the prompt, gpt-image-2 renders): `assets/yt.png` (16:9 → YouTube +
website), `assets/x.png` (5:2 → X), `assets/spot.png` (1:1). Author **no thumbnail block** —
the brief is the source. They are publish-only assets, not part of the video sequence.

---

## Companion format — the 9:16 short (REQUIRED)

Every name ships a vertical short alongside the long-form. It is **not** a crop of the 16:9
video: it is a purpose-built vertical piece from its own script,
`scripts/{TICKER}_short_script.json`, rendered by the same engine at 1080x1920 via
`just webdeck-short-pipeline {TICKER}` → `videos/{TICKER}_short.mp4`. One asset serves both
the X native-video post and the YouTube Short. Its schema (5-6 beats; `hook` / `stat` /
`cards` / `points` / `cta`) is specified in the `/author` skill, along with the two social
files it needs: `social/{TICKER}_short_x_post.txt` and `social/{TICKER}_short_youtube.txt`.

The Q&A podcast has been **retired** (2026-07-21): author no `qa.json` and no `podcast_*`
fields. The avatar-short renderer (`tools/gen_avatar_short.py`, `just short` / `just shorts`)
is retired too and is not part of a run.

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
- **`center` mispronounces** — it comes out like "centandar." Respell it phonetically as
  `senter` / `senters` (e.g. "data senters"). Narration is audio-only, so the respelling never
  shows on screen (the slide keeps "center").

*(Confirmed-bad by ear 2026-06: spaced `A I`, spaced `D E A`, and the word `center` (→ `senter`).
Campaigns may add their own pronunciation hints — e.g. a sector tax code or a company name TTS
reads wrong.)*

---

## Universal rules

- **No em-dashes or en-dashes - ever.** Use a spaced hyphen ` - ` for a clause break (or
  restructure with commas / colons / periods); use a plain hyphen for numeric and date ranges
  (`$8.9-9.2B`, `FY2021-FY2025`), never an en-dash. This governs *everything you generate* - the
  brief (it ships verbatim as an X Article), all social and publish copy, on-screen slide text,
  and narration. Stray dashes in the on-screen deck text and the published copy are the ones that
  bite, so keep them out as you write - do not leave them for a cleanup pass.
- **The brief is render-safe plain markdown.** The research portal renders the published brief
  with ReactMarkdown + remark-gfm — GFM tables, headings, lists, bold/italic, and links render,
  but **YAML frontmatter and raw HTML (`<sub>`, `<br>`, etc.) do NOT** (frontmatter shows as a
  garbled block; raw HTML vanishes). Start the brief with a `# Heading`, write footnotes/fine-print
  as *italic* markdown lines (never `<sub>`), and include **no frontmatter** — the catalog takes
  its metadata from `script.json` + `publish.json`, not the brief.
- **Never fabricate numbers.** Every figure comes from the MCP filing data or an attributed
  web source. If a metric is missing, note the gap and attribute the fallback.
- **Data on the slide must match the narration.** If the voice says "1.2 billion," the
  slide's `data`/`headline` shows that same number. Slide and words are one unit.
- **Completeness check before finishing:** confirm `script.json` is valid (every required
  field, `deck.slide_count` == segment count, unique ordered `visual_ref`s), that
  `scripts/{TICKER}_short_script.json` and its two `social/` files exist, and that every
  output your `AUTHORING_INSTRUCTIONS.md` lists exists. The task isn't done until all files
  are saved.
