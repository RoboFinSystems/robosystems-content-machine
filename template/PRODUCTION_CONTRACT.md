
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
    + per-slide content)                  ▼
                                     paste into claude.ai/design (RoboSystems Content Design System)
                                     → compose 16:9 deck  → deck/{TICKER}_deck.pdf
                                     (thumbnails: made in ChatGPT → dropped in assets/ → (slice) → charts/png/{TICKER}_thumbnail.png)
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
    "campaign": "Optional campaign name"
  },

  "deck": {
    "slide_count": 12,                  // MUST equal the number of segments below
    "source": "deck/GTBIF_deck.pdf"     // filled in after the deck is built/exported
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
        "visual_takeaway": "growth surged FY22 to FY23, then flattened; last three bars read nearly level",
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
- `duration_estimate_seconds` — integer estimate ≈ **narration characters ÷ 16** (real TTS pace
  is ~16 chars/sec; under-counting makes draft timestamps ~2× short). (NOT `duration_seconds`.)
  Actual timing comes from the voiceover at assembly, which also writes
  `videos/{TICKER}_timestamps.txt` with the real YouTube chapter times.
- `slide` — the on-screen content (see slide kinds). Put **exact numbers** here; this is
  what the deck renders, so vague data here = vague slides.
- `deck.slide_count` — set it to the number of segments. **Validation fails if they differ.**
- Thumbnails are made in ChatGPT from the brief, **not authored here** — no `thumbnail` block.
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
glance ("up five years straight," "one segment negative," "flat until the last bar"). The deck
renderer designs the chart around it; the deck-brief generator additionally flags narrow-range
and negative series automatically, so a flat series gets an honest reframe and negatives get a
zero axis.

Put raw numbers in base units where you have them (revenue $1.2B = `1200000000`) **and** a
display form in `headline`/`highlight` if the phrasing matters. Claude Design formats for
display; the raw numbers keep it honest.

---

## How the deck gets built (after your script)

You don't do these steps, but understanding them tells you what a good script enables:

1. **`build_deck_brief.py`** renders `deck/{TICKER}_deck_brief.md` from your script — one
   section per slide (kind, headline, the data as a table, narration as speaker context),
   with a header pinning: *build in the **RoboSystems Content Design System** project (start
   from its `video-deck` template), RoboSystems house brand, dark 16:9, produce exactly N
   slides in this order.*
2. A human pastes that brief into **claude.ai/design** and the deck is composed on-brand.
3. The deck is exported to `deck/{TICKER}_deck.pdf` (or per-slide PNGs).
4. **`slice_deck.py`** turns it into `charts/png/{visual_ref}.png`, one per slide.
5. Voiceover + Shotstack assemble the final video.

**Implications for your script:** every slide's `headline` and `data` must be complete and
exact — they become the literal content of the slide. The first slide is the intro, the
last is the close/CTA (no separate intro/outro files in deck mode).

---

## Thumbnails (made in ChatGPT, not authored here)

Thumbnails are generated in **ChatGPT** from the brief (better output than we build) and dropped
into `assets/` per platform: `yt.png` (16:9 → YouTube + website), `x.png` (5:2 → X), `spot.png`
(1:1 → Spotify). The `slice` step ingests them into `charts/png/`. Cowork authors **no thumbnail
block** — the brief is the source. They are publish-only assets, not part of the video sequence.

---

## Companion formats — Short and Q&A podcast

From the *same* research, the pipeline produces two more deliverables. Author them when your
`COWORK_INSTRUCTIONS.md` asks for them. Both reuse the analyst (narrator) voice for brand
continuity and follow the **same spoken-form TTS rules** below.

### A. Short — auto-generated 9:16 avatar video (`just short {TICKER}`)

**You author no `short` block in the video script.** Two 9:16 shorts are produced headless by
`tools/gen_avatar_short.py` (`just shorts {TICKER}` makes both), each teasing a different destination:
- **Hook short** (`just short {TICKER}` -> `videos/{TICKER}_short.mp4`): gpt-5 writes a tight ~30s hook
  from the brief, a HeyGen studio avatar reads it in our ElevenLabs voice, keyed over a gpt-image-2
  backdrop with word-synced captions. **Teases the long-form** (`short_pinned_comment` -> `[YOUTUBE_LINK]`).
- **Q&A short** (`just short {TICKER} --qa` -> `videos/{TICKER}_short_qa.mp4`): two avatars read the
  authored `short.turns` exchange from the Q&A file (see B), cut-between over one shared backdrop.
  **Teases the podcast** (`short_qa_pinned_comment` -> `[PODCAST_LINK]`).

Your short-related job in the video script is the **posting copy** in the publish metadata
(`short_title`/`short_pinned_comment` and `short_qa_title`/`short_qa_pinned_comment`, see #7).

### B. Q&A podcast — `scripts/{TICKER}_qa.json`

A CNBC-style two-voice conversation (host + analyst), written for audio. ~5–8 min. Rendered by
`just podcast-qa {TICKER}` → `{TICKER}_qa_podcast.mp3` (Spotify / Apple / Amazon) +
`{TICKER}_qa_podcast.mp4` (static thumbnail background, for YouTube). Interviewer = a fixed
host voice (`ELEVEN_LABS_INTERVIEWER_VOICE_ID`); analyst = the brand narrator voice.

```jsonc
{
  "ticker": "TRLV",
  "company": "Trulieve Cannabis Corp.",
  "title": "Trulieve: Tax Relief Is Finally Here — Now What?",
  "intro_sting": false,
  "turns": [
    { "speaker": "interviewer", "text": "Let's start with the setup — why look at this name now?" },
    { "speaker": "analyst",     "text": "Two things changed this quarter..." }
  ],
  "short": {
    "turns": [
      { "speaker": "interviewer", "text": "Trulieve — ticker T R L V — just got the tax break it waited years for. What changes?" },
      { "speaker": "analyst",     "text": "Everything on the cash-flow line. Last year they paid..." },
      { "speaker": "interviewer", "text": "So is it suddenly cheap?" },
      { "speaker": "analyst",     "text": "That's the debate. It trades at..." }
    ]
  }
}
```

- **`turns`** — the full podcast. Alternate `interviewer` / `analyst`. Open with the host framing the name; close on the RoboSystems angle and a short sign-off.
- Written for the **ear**: contractions, natural cadence, no on-screen references. Cover the deck's beats as *dialogue*: setup → the numbers → the catalyst → valuation range → bull/bear → the RoboSystems angle.
- Same spoken-form TTS rules as the main narration (spell out agencies, never space `AI`, numbers as words). The host asks; the analyst delivers the substance and the numbers.
- **`short.turns`** - a **separate, purpose-written 2-4 turn exchange** for the two-avatar Q&A video short (`just short {TICKER} --qa`, `tools/gen_avatar_short.py`). NOT a slice of the podcast: a self-contained ~45-second micro-story. Host's first line names the company + ticker and poses the tension; the analyst lands the single defining number/contrast in one tight answer (~10-15s per turn); end on a hook or pointed question, **no CTA/promo**. Each speaker is rendered as its own HeyGen avatar (host = `HEYGEN_AVATAR_LOOK_ID2` + `HEYGEN_VOICE_ID2`; analyst = `HEYGEN_AVATAR_LOOK_ID` + `HEYGEN_VOICE_ID`), cut-between over one shared backdrop.

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
  field, `deck.slide_count` == segment count, unique ordered `visual_ref`s) and every output
  your `COWORK_INSTRUCTIONS.md` lists exists. The task isn't done until all files are saved.
