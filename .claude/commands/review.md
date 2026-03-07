Post-Cowork quality review before running the pipeline. This is where you spend time reviewing what Claude Cowork produced before committing to API costs (ElevenLabs, Shotstack).

## Arguments
- `$ARGUMENTS` — ticker symbol (e.g., GTBIF)

## Steps

### 1. Run the validator
```bash
just validate {TICKER}
```
Report any errors or warnings.

### 2. Show the narrative brief
Read and display `projects/{TICKER}/reports/{TICKER}_brief.md` in full.

This is the most important output to review. Ask the user:
- Does the hook grab attention?
- Is the financial story accurate and compelling?
- Are the catalyst scenarios backed by specific numbers?
- Is the tone right (fact-based, not promotional)?

### 3. Script summary
Read `projects/{TICKER}/scripts/{TICKER}_script.json` and show:
- Total segments and estimated duration
- Segment breakdown by slide type (title/chart/callout/dual)
- Word count of total narration
- Whether the RoboSystems plug is present
- Short version segment selection

### 4. Chart inventory
List all chart HTML files that were created (excluding templates/examples):
```bash
ls projects/{TICKER}/charts/html/*.html | grep -v EXAMPLE_ | grep -v CHART_TEMPLATE | grep -v AVATAR_BG
```
For each chart, show the filename and the visual_type from the script.

### 5. Social posts preview
Show the X post and StockTwits post content:
- `social/{TICKER}_x_post.txt`
- `social/{TICKER}_stocktwits_post.txt`

### 6. Narration quality spot-check
Pick 2-3 narration segments and check for:
- Raw symbols ($, %, x) that should be spelled out for TTS
- Sentences that are too long or complex for spoken delivery
- Numbers that aren't rounded for speech

### 7. Print review summary
```
Review: {TICKER}
━━━━━━━━━━━━━━━━
  Validator:  PASSED (2 warnings)
  Brief:      1,847 words — review above
  Script:     14 segments, ~4:20 estimated
              3 title | 5 chart | 3 callout | 2 dual | 1 outro
  Charts:     8 HTML files
  Social:     X post (2,341 chars) + StockTwits (487 chars)
  Narration:  2 TTS issues found (see above)

  Ready for pipeline?
  → Fix TTS issues, then: just pipeline {TICKER}
```

### 8. Offer to fix
If there are TTS narration issues or other fixable problems, offer to fix them. Do NOT auto-fix without asking — the user has creative discretion over the content.
