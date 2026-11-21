---
name: status
description: "Production dashboard: the state of every coverage project at a glance. Use for \"status\", \"where are the projects\", or \"production dashboard\"."
metadata:
  lane: gtm
---

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

**Sources (pre-authoring):**
- `sources/*_filing.txt` / `*_10K_filing.txt` — SEC filing text
- `sources/*_earnings_release.txt` — earnings release
- `sources/*_earnings_transcript.txt` — earnings transcript

**Authoring outputs (`/author`):**
- `reports/*_brief.md` — narrative brief
- `scripts/*_script.json` — video script
- `social/*_x_post.txt` — X post
- `social/*_youtube_description.txt` — YouTube description

**Pipeline outputs:**
- `videos/audio/*_voiceover.mp3` — voiceover segments
- `charts/webdeck/` — the built HTML deck + rendered frames
- `videos/*_final.mp4` — long-form 16:9 video
- `assets/yt.png` — the YouTube thumbnail (`just thumbnails`)

### 3. Print dashboard
```
Content Machine — Production Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  TICKER   SOURCES   AUTHORED   VIDEO   THUMB
  ──────   ───────   ────────   ─────   ─────
  GTBIF    3/3       done       —       —
  TRLV     done      done       done    done
  CURLF    scaffold  —          —       —

  Legend: scaffold = project exists but no sources
          3/3 = 3 of 3 source files present
          done = outputs present  ·  — = not started
```

### 3b. Batch board (research batches)
Projects in a `/batch-research` batch carry `projects/{T}/STATUS.md`, written by the subagent
authoring that brief and synced from whichever machine runs it. When any exist, print a second
table read from them, newest first:

```
Research batch - brief runs
━━━━━━━━━━━━━━━━━━━━━━━━━━━

  TICKER   STAGE       TIER     FILING                   VALIDATE       ANGLE
  WK       COMPLETE    middle   10-Q 2026-09-30          PASSED (1 w)   Buybacks took 100.8% of FCF, then stopped
  MSFT     drafting    deep     10-Q 2026-09-30          -              -
  INTU     queued      middle   10-Q 2026-10-31          -              -

  4 tickers: 1 complete, 1 running, 1 queued, 1 stopped
```

`stage` other than queued or COMPLETE, unchanged for more than an hour, is probably an
interrupted run (a usage limit, a closed session): say so. `projects/.batch/*.md` holds each
lead's final table.

### 4. Highlight next actions
Based on the state, suggest what to do next:
- Projects needing sources → `/collect TICKER`
- Projects with sources but no brief → `/author TICKER` (one-shot authoring), or several at once with `/batch-research`
- Batch briefs at COMPLETE → `/review TICKER`, then Joey's read before anything publishes
- Projects with authoring outputs → `/review TICKER`, then `just webdeck-pipeline TICKER`
- Projects with a long-form video → `just thumbnails TICKER` → `just publish TICKER` → post (`yt-upload` / `x-article`)
