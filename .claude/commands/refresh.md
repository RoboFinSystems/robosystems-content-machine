Update an existing project's campaign files without touching sources or outputs. Use when you've refined the CAMPAIGN_BRIEF or COWORK_INSTRUCTIONS in the campaign directory and want to push changes to an existing project.

## Arguments
- `$ARGUMENTS` — ticker symbol (e.g., GTBIF) and optionally a campaign name. If no campaign specified, detect from CAMPAIGN_BRIEF.md in the project.

## Steps

### 1. Find the project
Check that `projects/{TICKER}/` exists. If not, tell the user to scaffold first.

### 2. Detect the campaign
- If campaign name provided in arguments, use it
- Otherwise, check if `projects/{TICKER}/CAMPAIGN_BRIEF.md` exists and try to detect the campaign from its content (look for the campaign title)
- If no campaign can be detected, ask the user

### 3. Refresh campaign files
Copy from the campaign directory, overwriting what's in the project:

```bash
# Overwrite COWORK_INSTRUCTIONS
cp campaigns/{CAMPAIGN}/COWORK_INSTRUCTIONS.md projects/{TICKER}/COWORK_INSTRUCTIONS.md

# Overwrite CAMPAIGN_BRIEF
cp campaigns/{CAMPAIGN}/CAMPAIGN_BRIEF.md projects/{TICKER}/CAMPAIGN_BRIEF.md

# Re-apply overrides (intro/outro slides, etc.)
cp -r campaigns/{CAMPAIGN}/overrides/. projects/{TICKER}/
```

### 4. DO NOT touch these
- `sources/` — user-curated materials, never overwrite
- `reports/` — Cowork outputs
- `scripts/` — Cowork outputs
- `charts/html/*.html` (except overrides like INTRO_SLIDE, OUTRO_SLIDE) — Cowork outputs
- `social/` — Cowork outputs
- `videos/` — pipeline outputs

### 5. Print summary
```
Refreshed: projects/{TICKER}
  Campaign: {CAMPAIGN}
  Updated:  COWORK_INSTRUCTIONS.md, CAMPAIGN_BRIEF.md, INTRO_SLIDE.html, OUTRO_SLIDE.html
  Kept:     sources/ (4 files), reports/ (1 file), scripts/ (1 file)
```
