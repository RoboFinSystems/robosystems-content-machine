Author the full Cowork-stage output set for a project directly in this session — the Code-native replacement for the claude.ai Cowork handoff. Same artifacts, same contract, no clipboard round-trip. `/review` stays the quality gate afterward.

## Arguments
- `$ARGUMENTS` — ticker symbol (e.g., NFLX)

## Prerequisites
- Project scaffolded (`just new TICKER` or `just campaign TICKER name`)
- Sources collected (`/collect TICKER` or files dropped into `sources/`)

## Steps

### 1. Load the contract
Read, in order:
- `projects/{TICKER}/COWORK_INSTRUCTIONS.md` — the authoring spec (campaign overlay already baked in at scaffold time). Follow it exactly.
- `projects/{TICKER}/PRODUCTION_CONTRACT.md` — schema, slide kinds, `data` shapes, TTS spoken-form rules, the per-segment `eyebrow` field.
- `projects/{TICKER}/KICKOFF.md` and everything in `sources/`.

Non-negotiables that reviews keep catching: narration is spoken-form (no `$ % x / &`), the brief's Hook carries an early ` $TICKER` cashtag (space before `$`, never `($TICKER)`), no em/en dashes anywhere, slide `data` matches narration numbers exactly, every segment except the CTA gets an `eyebrow`.

### 2. Verify the numbers against the graph
Pull the XBRL facts through the robosystems MCP (`financial-statement-analysis`, `read-graph-cypher`, `search-documents`) rather than trusting press coverage. Every number that lands on a slide or in narration should trace to a filing or be explicitly labeled as guidance/consensus with its source.

### 3. Author the outputs (this order — later files derive from earlier ones)
1. `reports/{TICKER}_brief.md` — the narrative brief (ships verbatim as the X Article). Markdown tables render as native Article tables — use them wherever 3+ rows of figures line up (results vs. estimates, DCF scenarios, multiples grid); 1-3 per brief.
2. `scripts/{TICKER}_script.json` — segments with narration, slides, eyebrows; set `metadata.coverage_label`.
3. `scripts/{TICKER}_qa.json` — the two-voice Q&A podcast script.
4. `social/` — X post, YouTube description, `{TICKER}_publish.json`.

Use subagents for scale where useful (e.g., parallel section drafts), but the fact-check pass belongs to `/review`, not here.

### 4. Validate
```bash
just validate {TICKER}
```
Fix and re-run until clean (`just validate-fix` for mechanical schema issues).

### 5. Hand off
Tell the user the outputs are ready and recommend `/review {TICKER}` (multi-agent fact + TTS review) before spending render/TTS credits. After review passes, either path works:
- **Deck path (default):** `just deck-brief {TICKER}` → Claude Design → `just pipeline {TICKER}`
- **Webdeck path (pilot):** `just webdeck-pipeline {TICKER}` — no Claude Design step
