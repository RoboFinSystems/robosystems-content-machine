---
description: Author the full written output set for a project in this session.
argument-hint: '[project]'
---

Author the full written output set for a project directly in this session - one shot, against the contract in `AUTHORING_INSTRUCTIONS.md` + `PRODUCTION_CONTRACT.md`. You produce written artifacts only; the renderer builds every slide from `script.json`. `/review` is the quality gate afterward.

## Arguments
- `$ARGUMENTS` — ticker symbol (e.g., NFLX)

## Prerequisites
- Project scaffolded (`just new TICKER` or `just campaign TICKER name`)
- Sources collected (`/collect TICKER` or files dropped into `sources/`)

## Steps

### 1. Load the contract
Read, in order:
- `projects/{TICKER}/AUTHORING_INSTRUCTIONS.md` — the authoring spec (campaign overlay already baked in at scaffold time). Follow it exactly.
- `projects/{TICKER}/PRODUCTION_CONTRACT.md` — schema, slide kinds, `data` shapes, TTS spoken-form rules, the per-segment `eyebrow` field.
- `projects/{TICKER}/KICKOFF.md` and everything in `sources/`.

Non-negotiables that reviews keep catching: narration is spoken-form (no `$ % x / &`), the brief's Hook carries an early ` $TICKER` cashtag (space before `$`, never `($TICKER)`), no em/en dashes anywhere, slide `data` matches narration numbers exactly, every segment except the CTA gets an `eyebrow`.

Reach alignment (measured on our own analytics): the `youtube_title` is **search-first** (Company + Ticker + quarter + the specific angle a viewer would search; it is ALSO the `/research` page `<title>`, so it must name the ticker or company and a period token, see the publish.json rules in `AUTHORING_INSTRUCTIONS.md`) and **DIFFERENT from the X hook** - YouTube discovery is ~all search, X rewards the curiosity line; the YouTube description's first line restates those search keywords. The video **opens with the most surprising number in the first ~15 seconds** (retention gate). The X post leads with substantive text + an early cashtag. **Publish the brief as a native X Article on every name** - measured 2026-07-26 it is our highest-reach format (median 380 vs 272 for text+video), and the old "never a bare-link post" rule was retracted as a measurement artifact that filed Articles with outbound links.

**Per-surface framing (see the Surface rules section in `AUTHORING_INSTRUCTIONS.md`).** Every name ships every asset; the copy differs per surface because the discovery mechanisms do. **Never reuse a string across surfaces** - the `youtube_title` is a search query, the X hook is a curiosity line, the Short title is a third string, the brief headline is the analytical claim. And the niche rule **inverts** between them: an underserved cashtag is an advantage on X (quiet feed, right readers) but a liability on YouTube (nobody searches the name), so for a thin-demand name the YouTube title must earn traffic on the *topic* - the accounting mechanism, the sector question - rather than on the ticker.

**Two closing beats, in this order.** (a) **The generalization** - one or two flat, concrete sentences that no analyst wrote this, the same pipeline reads any filer's XBRL, and a private company reporting in the same format is the same job. Written fresh per name so it hangs off that company's specific finding. Without it the piece sells the analysis and not the machine. (b) **The CTA points at the SEC Shared Repository, not the homepage** - name the repository in narration, `robosystems.ai/pricing` in the slide subhead and first in the YouTube description links. Never speak a price.

### 2. Verify the numbers against the graph
Pull the XBRL facts through the robosystems MCP (`financial-statement-analysis`, `read-graph-cypher`, `search-documents`) rather than trusting press coverage. Every number that lands on a slide or in narration should trace to a filing or be explicitly labeled as guidance/consensus with its source.

### 3. Author the outputs (this order — later files derive from earlier ones)
1. `reports/{TICKER}_brief.md` — the narrative brief (ships verbatim as the X Article). Markdown tables render as native Article tables — use them wherever 3+ rows of figures line up (results vs. estimates, DCF scenarios, multiples grid); 1-3 per brief.
2. `scripts/{TICKER}_script.json` — segments with narration, slides, eyebrows; set `metadata.coverage_label`.
3. `social/` — X post, YouTube description, `{TICKER}_publish.json`.
4. **The 9:16 short** — X's native-video post + a YouTube Short (the vertical companion):
   - `scripts/{TICKER}_short_script.json` — 5-6 beats, **aim ~45s (~700 narration chars); it runs long fast, so keep the sentences few and short**. `metadata{ticker, company, quarter, tags}`; each segment `{id, kind, narration, slide}`, `kind` ∈:
     - `hook` — `slide{headline, punch, tone}`: the surprising turn (e.g. "Beat Earnings. Crashed Anyway." + punch "-8% to a 52-week low")
     - `stat` — `slide{kicker, big, context, tone}`: one huge number (a price / record figure)
     - `cards` — `slide{eyebrow, headline, cards:[{label,value,change}], highlight}`: 2-3 stacked metric cards
     - `points` — `slide{eyebrow, headline, points:[{text,value,tone,highlight}], footnote}`: 3-4 rows; `tone` bear/base/bull colors the marker + value; `footnote` for a disclaimer
     - `cta` - `slide{headline, subhead}`: the SEC Shared Repository, subhead `robosystems.ai/pricing`
     Narration is spoken-form (captions auto-derive from it); reuse the already-verified long-form numbers; arc = hook → the beat → the crash/turn → why → valuation → CTA.
   - `social/{TICKER}_short_x_post.txt` — the X post body: substantive, early ` $TICKER` cashtag (`x-short` appends the Article link - that link is native and helps, it is only *outbound* links that suppress), ~200-270 chars, framed as a 60-second clip (distinct from the long-form `x_post`).
   - `social/{TICKER}_short_youtube.txt` - **line 1 = the Short title** (hook-first, DIFFERENT from both the long-form YouTube title and the X hook, ≤100 chars); the rest = description with `[LONGFORM_URL]` (auto-filled from the long-form upload), a `robosystems.ai/pricing` line, and `#Shorts`.

(No `qa.json` - the Q&A podcast is retired.)

Use subagents for scale where useful (e.g., parallel section drafts), but the fact-check pass belongs to `/review`, not here.

### 4. Validate
```bash
just validate {TICKER}
```
Fix and re-run until clean (`just validate-fix` for mechanical schema issues).

### 5. Hand off
Tell the user the outputs are ready and recommend `/review {TICKER}` (fact + TTS review) before
spending render/TTS credits. After review passes:
- **Long-form:** `just webdeck-pipeline {TICKER}` → `videos/{TICKER}_final.mp4`
- **9:16 short:** `just webdeck-short-pipeline {TICKER}` → `videos/{TICKER}_short.mp4`

Both run the same engine (validate → ElevenLabs VO → build HTML → headless-Chrome frames →
ffmpeg mux) and are entirely local; the only cost is wall clock.
Publish/post order (each asset in its best format): **YouTube long-form** (`just yt-upload`) → **YouTube Short** (`just yt-short` — its description auto-links the long-form) → **X**: publish the brief as an Article (`just x-article {TICKER} --publish`) then post the **9:16 short as the native video** (`just x-short`). The 16:9 long-form is not posted natively to X.
