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
- `sources/*_filing.txt` / `*_10K_filing.txt` — SEC filing text
- `sources/*_earnings_release.txt` — earnings release
- `sources/*_earnings_transcript.txt` — earnings transcript

**Cowork outputs:**
- `reports/*_brief.md` — narrative brief
- `scripts/*_script.json` — video script (also holds the `thumbnail` + `short` blocks)
- `scripts/*_qa.json` — Q&A podcast script
- `social/*_x_post.txt` — X post
- `social/*_youtube_description.txt` — YouTube description

**Design outputs (Claude Design):**
- `deck/*_deck.pdf` — the composed 16:9 deck
- `charts/png/*_thumbnail.png` — the YouTube thumbnail

**Pipeline outputs:**
- `charts/png/{visual_ref}.png` — sliced deck slides
- `videos/audio/*_voiceover.mp3` — voiceover segments
- `videos/*_final.mp4` — long-form video
- `videos/*_short.mp4` — 9:16 teaser short
- `videos/*_qa_podcast.mp3` / `*_qa_podcast.mp4` — Q&A podcast (Spotify + YouTube)
- `videos/*_podcast.mp3` — long-form audio extract

### 3. Print dashboard
```
Content Machine — Production Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  TICKER   SOURCES   COWORK   DECK   VIDEO   SHORT   Q&A
  ──────   ───────   ──────   ────   ─────   ─────   ───
  GTBIF    3/3       done     —      —       —       —
  TRLV     done      done     done   done    done    done
  CURLF    scaffold  —        —      —       —       —

  Legend: scaffold = project exists but no sources
          3/3 = 3 of 3 source files present
          done = outputs present  ·  — = not started
```

### 4. Highlight next actions
Based on the state, suggest what to do next:
- Projects needing sources → `/collect TICKER`
- Projects with sources but no Cowork → "Point Cowork at projects/TICKER/"
- Projects with Cowork outputs but no deck → `just deck-brief TICKER`, then build the deck in Claude Design
- Projects with a deck PDF → `just pipeline TICKER`
- Projects with a video → `just short TICKER` · `just podcast-qa TICKER`
