Post-Cowork quality review before running the pipeline. This is where you spend time reviewing what Claude Cowork produced before committing to API costs (ElevenLabs, Shotstack).

## Arguments
- `$ARGUMENTS` — ticker symbol (e.g., GTBIF)

## Steps

### 1. Run the validator
```bash
just validate {TICKER}
```
Report any errors or warnings (it also checks the deck contract + the `qa` companion format).

### 2. Show the narrative brief
Read and display `projects/{TICKER}/reports/{TICKER}_brief.md` in full.

This is the most important output to review. Ask the user:
- Does the hook grab attention?
- Does the Hook carry the `$TICKER` cashtag at the first company mention (the brief ships
  verbatim as the X Article; a space must precede the `$`, never `($TICKER)`)?
- Is the financial story accurate and compelling?
- Are the catalyst scenarios backed by specific numbers?
- Is the tone right (fact-based, not promotional)?

### 3. Script summary
Read `projects/{TICKER}/scripts/{TICKER}_script.json` and show:
- Total segments and estimated duration (≈ narration chars ÷ 16)
- Segment breakdown by slide type (title / chart / callout / dual)
- Word count of total narration
- Whether the RoboSystems plug (`visual_ref: "cta"`) is present

### 4. Deck contract check
The deck is built in Claude Design from the script (no chart HTML). Confirm:
- `deck.slide_count` equals the number of `visual` segments
- `visual_ref`s are unique and in narration order
- If the deck is built: `deck/{TICKER}_deck.pdf` exists (and slices to `charts/png/{visual_ref}.png`)

### 5. Companion formats
- (Shorts backburnered and the Q&A podcast retired - nothing authored, nothing to review.)

### 6. Social posts preview
Show the X post and YouTube description:
- `social/{TICKER}_x_post.txt`
- `social/{TICKER}_youtube_description.txt`

### 7. Narration quality spot-check
Across the script narration and the Q&A turns, check for:
- Raw symbols (`$ % x /`) that should be spelled out for TTS
- Spaced `A I` (use `AI`) or `D E A` (spell out "Drug Enforcement Administration")
- Sentences too long/complex for spoken delivery; numbers not rounded for speech

### 8. Print review summary
```
Review: {TICKER}
━━━━━━━━━━━━━━━━
  Validator:  PASSED (2 warnings)
  Brief:      1,847 words — review above
  Script:     14 segments, ~9:00 estimated
              3 title | 5 chart | 3 callout | 3 dual
  Deck:       slide_count matches (14) · deck PDF: not built yet
  Q&A:        22 turns
  Social:     X post (2,341 chars) + YouTube description
  Narration:  2 TTS issues found (see above)

  Ready for pipeline?
  → Fix TTS issues, build the deck, then: just pipeline {TICKER}
```

### 9. Offer to fix
If there are TTS narration issues or other fixable problems, offer to fix them. Do NOT auto-fix without asking — the user has creative discretion over the content.
