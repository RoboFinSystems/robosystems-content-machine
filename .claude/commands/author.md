Author the full written output set for a project directly in this session - the one-shot Code process that replaces the old claude.ai Cowork handoff. Same artifacts, same contract (`AUTHORING_INSTRUCTIONS.md` + `PRODUCTION_CONTRACT.md`), no clipboard round-trip. `/review` stays the quality gate afterward.

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

Reach alignment (measured on our own analytics): the `youtube_title` is **search-first** (Company + Ticker + quarter + the specific angle a viewer would search) and **DIFFERENT from the X hook** - YouTube discovery is ~all search, X rewards the curiosity line; the YouTube description's first line restates those search keywords. The video **opens with the most surprising number in the first ~15 seconds** (retention gate). The X post **never ships as a bare link** - lead with substantive text + an early cashtag.

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
     - `cta` — `slide{headline, subhead}`: robosystems.ai
     Narration is spoken-form (captions auto-derive from it); reuse the already-verified long-form numbers; arc = hook → the beat → the crash/turn → why → valuation → CTA.
   - `social/{TICKER}_short_x_post.txt` — the X post body: substantive, early ` $TICKER` cashtag, **no bare link** (`x-short` appends the Article link), ~200-270 chars, framed as a 60-second clip (distinct from the long-form `x_post`).
   - `social/{TICKER}_short_youtube.txt` — **line 1 = the Short title** (hook-first, DIFFERENT from both the long-form YouTube title and the X hook, ≤100 chars); the rest = description with `[LONGFORM_URL]` (auto-filled from the long-form upload), a `robosystems.ai` line, and `#Shorts`.

(No `qa.json` - the Q&A podcast is retired.)

Use subagents for scale where useful (e.g., parallel section drafts), but the fact-check pass belongs to `/review`, not here.

### 4. Validate
```bash
just validate {TICKER}
```
Fix and re-run until clean (`just validate-fix` for mechanical schema issues).

### 5. Hand off
Tell the user the outputs are ready and recommend `/review {TICKER}` (multi-agent fact + TTS review) before spending render/TTS credits. After review passes, either path works for the long-form:
- **Deck path (default):** `just deck-brief {TICKER}` → Claude Design → `just pipeline {TICKER}`
- **Webdeck path (pilot):** `just webdeck-pipeline {TICKER}` — no Claude Design step

The 9:16 short renders on its own: `just webdeck-short-pipeline {TICKER}` → `videos/{TICKER}_short.mp4`.
Publish/post order (each asset in its best format): **YouTube long-form** (`just yt-upload`) → **YouTube Short** (`just yt-short` — its description auto-links the long-form) → **X**: publish the brief as an Article (`just x-article {TICKER} --publish`) then post the **9:16 short as the native video** (`just x-short`). The 16:9 long-form is not posted natively to X.
