Production dashboard — show the state of all coverage projects at a glance.

## Arguments
- `$ARGUMENTS` — optional campaign name to filter, or empty for all projects

## Steps

### 1. List all projects
```bash
ls -1 projects/ 2>/dev/null
```

### 2. For each project, check state
For each project directory, check for the presence of key files:

**Sources (pre-Cowork):**
- `sources/*_filing.txt` — SEC filing text
- `sources/*_earnings_release.txt` — earnings release
- `sources/*_earnings_transcript.txt` — earnings transcript
- `sources/*_market_context.txt` — market data

**Cowork outputs:**
- `reports/*_brief.md` — narrative brief
- `scripts/*_script.json` — video script
- `charts/html/*.html` — chart/slide files (count excluding EXAMPLE_, CHART_TEMPLATE, INTRO_SLIDE, OUTRO_SLIDE)
- `social/*_x_post.txt` — X post
- `social/*_stocktwits_post.txt` — StockTwits post
- `charts/html/*_thumbnail.html` — thumbnail

**Pipeline outputs:**
- `charts/png/*.png` — screenshots
- `videos/audio/*_voiceover.mp3` — voiceover files
- `videos/*_final.mp4` — final video
- `videos/*_podcast.mp3` — podcast audio

### 3. Print dashboard
```
Content Machine — Production Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  TICKER   SOURCES    COWORK     PIPELINE   VIDEO    PODCAST
  ──────   ───────    ──────     ────────   ─────    ───────
  GTBIF    3/4        not run    —          —        —
  TCNNF    0/4        —          —          —        —
  CURLF    scaffold   —          —          —        —
  VRNO     scaffold   —          —          —        —

  Legend: scaffold = project exists but no sources
          3/4 = 3 of 4 source files present
          done = all outputs present
          — = not started
```

### 4. Highlight next actions
Based on the state, suggest what to do next:
- Projects needing sources → `/collect TICKER`
- Projects with sources but no Cowork → "Point Cowork at projects/TICKER/"
- Projects with Cowork outputs → `just pipeline TICKER`
- Projects with video → `just podcast TICKER`
