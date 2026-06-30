
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
                                     paste into claude.ai/design (RoboSystems Content Design System)
                                     → compose 16:9 deck  → deck/{TICKER}_deck.pdf
                                     → compose thumbnail  → deck/{TICKER}_thumbnail.pdf  → (slice) → charts/png/{TICKER}_thumbnail.png
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
    "banner": "INITIATING COVERAGE",    // "INITIATING COVERAGE" for a new name; "COVERAGE UPDATE" if previously covered; omit if none
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
- `duration_estimate_seconds` — integer estimate ≈ **narration characters ÷ 16** (real TTS pace
  is ~16 chars/sec; under-counting makes draft timestamps ~2× short). (NOT `duration_seconds`.)
  Actual timing comes from the voiceover at assembly, which also writes
  `videos/{TICKER}_timestamps.txt` with the real YouTube chapter times.
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

## Thumbnail (`charts/png/{TICKER}_thumbnail.png`)

The thumbnail is **built in Claude Design**, not hand-authored — Cowork authors **no HTML at
all**. You spec the content in the script's `thumbnail` block (hero metric, optional banner,
1–2 secondary metrics); Claude Design builds it as a separate 16:9 frame (see
`DESIGN_INSTRUCTIONS.md`) and exports it as a **16:9 PDF** to `deck/{TICKER}_thumbnail.pdf`
(Claude Design exports PDF only); the `slice` step rasterizes that to
`charts/png/{TICKER}_thumbnail.png` at 1920×1080. It is *not* part of the video sequence — the
pipeline treats it as a publish-only asset.

---

## Companion formats — Short and Q&A podcast

From the *same* research, the pipeline produces two more deliverables. Author them when your
`COWORK_INSTRUCTIONS.md` asks for them. Both reuse the analyst (narrator) voice for brand
continuity and follow the **same spoken-form TTS rules** below.

### A. Short — the `short` block (inside `scripts/{TICKER}_script.json`)

A **self-contained** 9:16 piece (~20–45s) for **YouTube Shorts + Instagram Reels** — a complete
micro-story (hook → the numbers → a payoff), NOT a trailer. It drives to the long-form via the
*pinned comment*, never by withholding the point. Rendered by `just short {TICKER}` (b-roll bed +
ducked music + ElevenLabs VO + caption cards — all local ffmpeg).

```jsonc
"short": {
  "duration_target_seconds": 30,
  "narration": "Self-contained ~20–45s story for the ear (NOT a slice of the main VO). Name the company; land the payoff; end on a question.",
  "broll": ["wide_low_angle", "canopy_push", "macro_detail"],       // explicit ids in play order, OR omit and use:
  // "broll_theme": ["cultivation", "city", "macro"],               // auto-pick clips whose tags match (most-relevant first)
  "music": "tech_corporate",                                        // explicit id, OR omit and use "music_mood": ["uplifting","corporate"] to auto-pick
  "cards": [                                                        // curated overlays — must stand alone for muted viewers
    { "text": "$1.2B revenue, 60% margins", "at_seconds": 2.0 },
    { "text": "TAXED AT 228%",             "at_seconds": 13.0 },
    { "text": "TRULIEVE — NYSE: TRLV",     "at_seconds": 17.5 },  // name + ticker reveal
    { "text": "WHAT DOES IT BUY FIRST?",   "at_seconds": 41.5 }   // payoff, not "go to YouTube"
  ]
}
```

- `narration` — a fresh, standalone script for the ear (no "as you can see here"); tell a complete micro-story, don't just tease. Budget ~20–45s — the voice runs ~14–15 chars/sec (slower than the ÷16 draft estimate), so ~600 chars ≈ ~43s. Spoken-form rules apply.
- `broll` / `broll_theme` — either an explicit ordered list of clip `id`s, OR omit `broll` and set `broll_theme` (a list of tags) to auto-select matching clips from `assets/broll/manifest.json` (most-relevant first); with neither, all clips are used. The renderer plays clips at **full length**, rotates the order each pass so nothing repeats back-to-back, and trims only the last clip to fit the runtime. (Clips are produced manually in ElevenLabs Studio / Veo and dropped into the library — there is no video-generation API.)
- `music` / `music_mood` — an explicit track `id`, OR omit it and set `music_mood` (a list of mood tags) to auto-pick the best-matching track from `assets/music/manifest.json` (most mood overlaps wins; ties → first); with neither, the first track is used.
- `cards` — 4–8 curated text overlays (the hook + hero stats + the ticker reveal), timed to VO beats via `at_seconds`. Keep them short and punchy; ~80% of Shorts play muted, so the cards must carry the story alone. (Card text is *rendered*, not spoken — the `$ % x` ban does not apply here.) `at_seconds` are estimates — re-time them to the actual VO after the first render (the spoken pace rarely matches the guess).
- **Name the company + show the ticker.** A brief anonymous mystery hook is fine, but the Short MUST name the company in the VO and show the ticker on a card (e.g. a `TRULIEVE — NYSE: TRLV` reveal card) — viewers can't act on a name they never heard.
- **Resolve, don't withhold.** A Short is self-contained content, not a trailer. Land the actual payoff and end on a provocative question or takeaway; the long-form link goes in the **pinned comment / caption**, NOT on a card.
- This supersedes the legacy `short_version` (segment-id list); you can omit `short_version`.

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
  ]
}
```

- Alternate `interviewer` / `analyst`. Open with the host framing the name; close on the RoboSystems angle and a short sign-off.
- Written for the **ear**: contractions, natural cadence, no on-screen references. Cover the deck's beats as *dialogue*: setup → the numbers → the catalyst → valuation range → bull/bear → the RoboSystems angle.
- Same spoken-form TTS rules as the main narration (spell out agencies, never space `AI`, numbers as words). The host asks; the analyst delivers the substance and the numbers.

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

- **Never fabricate numbers.** Every figure comes from the MCP filing data or an attributed
  web source. If a metric is missing, note the gap and attribute the fallback.
- **Data on the slide must match the narration.** If the voice says "1.2 billion," the
  slide's `data`/`headline` shows that same number. Slide and words are one unit.
- **Completeness check before finishing:** confirm `script.json` is valid (every required
  field, `deck.slide_count` == segment count, unique ordered `visual_ref`s) and every output
  your `COWORK_INSTRUCTIONS.md` lists exists. The task isn't done until all files are saved.
