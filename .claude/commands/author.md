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
**If `projects/{TICKER}/REDO.md` exists, this is a video redo (`just redo`) and that file governs:** keep the brief as published, read `LOVES-HATES.md`, never open `.history/`, and author only the scripts and the video-facing copy it lists.

Read, in order:
- `projects/{TICKER}/AUTHORING_INSTRUCTIONS.md` — the authoring spec (campaign overlay already baked in at scaffold time). Follow it exactly.
- `projects/{TICKER}/PRODUCTION_CONTRACT.md` — schema, slide kinds, `data` shapes, TTS spoken-form rules, the per-segment `eyebrow` field.
- `projects/{TICKER}/KICKOFF.md` and everything in `sources/`.

Non-negotiables that reviews keep catching: narration is spoken-form (no `$ % x / &`), the brief's Hook carries an early ` $TICKER` cashtag (space before `$`, never `($TICKER)`), no em/en dashes anywhere, slide `data` matches narration numbers exactly, every segment except the CTA gets an `eyebrow`.

Reach alignment (measured on our own analytics): the `youtube_title` is **search-first** (Company + Ticker + quarter + the specific angle a viewer would search; it is ALSO the `/research` page `<title>`, so it must name the ticker or company and a period token, see the publish.json rules in `AUTHORING_INSTRUCTIONS.md`) and **DIFFERENT from the X hook** - YouTube discovery is ~all search, X rewards the curiosity line; the YouTube description's first line restates those search keywords. The video **opens with the most surprising number in the first ~15 seconds** (retention gate). The X post leads with substantive text + an early cashtag. **Publish the brief as a native X Article on every name** - measured 2026-07-26 it is our highest-reach format (median 380 vs 272 for text+video), and the old "never a bare-link post" rule was retracted as a measurement artifact that filed Articles with outbound links.

**Per-surface framing (see the Surface rules section in `AUTHORING_INSTRUCTIONS.md`).** Every name ships every asset; the copy differs per surface because the discovery mechanisms do. **Never reuse a string across surfaces** - the `youtube_title` is a search query, the X hook is a curiosity line, the brief headline is the analytical claim. And the niche rule **inverts** between them: an underserved cashtag is an advantage on X (quiet feed, right readers) but a liability on YouTube (nobody searches the name), so for a thin-demand name the YouTube title must earn traffic on the *topic* - the accounting mechanism, the sector question - rather than on the ticker.

**Two closing beats, in this order.** (a) **The generalization** - one or two flat, concrete sentences that no analyst wrote this, the same pipeline reads any filer's XBRL, and a private company reporting in the same format is the same job. Written fresh per name so it hangs off that company's specific finding. Without it the piece sells the analysis and not the machine. It goes in **both** the script (before or inside the CTA) and the brief's Bottom Line; the brief is the X Article, and it is the one that keeps losing it. (b) **The CTA points at the SEC Shared Repository, not the homepage** - name the repository in narration, `robosystems.ai/pricing` in the slide subhead and first in the YouTube description links. Never speak a price.

### 2. Verify the numbers against the graph
Pull the XBRL facts through the robosystems MCP (`financial-statement-analysis`, `read-graph-cypher`, `search-documents`) rather than trusting press coverage. Every number that lands on a slide or in narration should trace to a filing or be explicitly labeled as guidance/consensus with its source.

### 3. Author the outputs (this order — later files derive from earlier ones)
1. `reports/{TICKER}_brief.md` — the narrative brief (ships verbatim as the X Article). Markdown tables render as native Article tables — use them wherever 3+ rows of figures line up (results vs. estimates, DCF scenarios, multiples grid); 1-3 per brief.
2. `scripts/{TICKER}_script.json` — segments with narration, slides, eyebrows; set `metadata.coverage_label`.
3. `social/` — X post, YouTube description, `{TICKER}_publish.json`.
(No 9:16 short: retired 2026-09-26, see `AUTHORING_INSTRUCTIONS.md` #5.)

(No `qa.json` - the Q&A podcast is retired. The audio edition that replaced it is *generated*
from the brief by `just narrate` / `just publish`, so author nothing for it - but write the
findings into the prose rather than only into table cells, because tables are stripped before
the read.)

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

It runs validate → ElevenLabs VO → word timings → build HTML → headless-Chrome frames → pop
scan → ffmpeg mux, entirely local; the only cost is wall clock.
Publish/post order (each asset in its best format): **YouTube long-form** (`just yt-upload`) → **X**: publish the brief as an Article (`just x-article {TICKER} --publish`). No 9:16 short on either platform (retired 2026-09-26), and the 16:9 long-form is not posted natively to X.
