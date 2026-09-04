---
description: Production dashboard — state of all coverage projects.
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
- `videos/*_short.mp4` — the 9:16 short
- `assets/yt.png` — the YouTube thumbnail (`just thumbnails`)

### 3. Print dashboard
```
Content Machine — Production Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  TICKER   SOURCES   AUTHORED   VIDEO   SHORT   THUMB
  ──────   ───────   ────────   ─────   ─────   ─────
  GTBIF    3/3       done       —       —       —
  TRLV     done      done       done    done    done
  CURLF    scaffold  —          —       —       —

  Legend: scaffold = project exists but no sources
          3/3 = 3 of 3 source files present
          done = outputs present  ·  — = not started
```

### 4. Highlight next actions
Based on the state, suggest what to do next:
- Projects needing sources → `/collect TICKER`
- Projects with sources but no brief → `/author TICKER` (one-shot authoring)
- Projects with authoring outputs → `/review TICKER`, then `just webdeck-pipeline TICKER`
- Projects with a long-form video → `just webdeck-short-pipeline TICKER` for the 9:16 short
- Projects with both → `just thumbnails TICKER` → `just publish TICKER` → post (`yt-upload` / `x-article` / `x-short`)
