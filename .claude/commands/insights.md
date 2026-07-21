Reach review - pull the channel/account-level analytics and interpret them, not just dump numbers. This is the weekly bird's-eye read; `/status` is production state and `just analytics TICKER` is the per-post rollup.

## Arguments
- `$ARGUMENTS` - optional flags passed through (e.g. `--posts 100`, `--no-youtube`)

## Steps

### 1. Pull the data
```bash
just insights {ARGUMENTS}
```
This hits the YouTube Analytics API (channel totals, traffic sources, per-video retention, daily trend) and the X API (recent original posts with impressions/engagement). If YouTube 403s, the token needs `just yt-auth` (yt-analytics.readonly scope) and the YouTube Analytics API enabled in the GCP project.

### 2. Interpret it (do NOT just repeat the table)
Read the output and write a short analytical brief. Work through:

**YouTube - where is discovery coming from?**
- Traffic sources: what share is `YT_SEARCH` vs `RELATED_VIDEO`/browse vs `EXT_URL` vs `SHORTS`? For this channel, search has been the engine (~60%) and browse is dead - so it's a search-SEO game (win low-competition long-tail terms), not a browse game. Flag any shift.
- Retention (AVD%): finance long-form runs ~40-50% normal. Call out the outliers - which videos hold 55%+ (what did they do right?) and which fall below ~25%. **Before flagging a very-low-AVD video (~1-2%) as broken, check the format:** the Q&A podcast is auto-mirrored from Spotify/Anchor to YouTube via RSS as audio-on-a-static-image, so ~1-2% retention is NORMAL for those and is not a defect - never recommend deleting a podcast mirror (it regenerates from the feed). Exclude podcast mirrors from retention analysis; they are a different format from the analysis videos. A genuinely broken analysis-video upload is rare - confirm the format (title/duration/audio-only) before calling anything broken.
- Which NAMES win? The pattern has been uncovered/obscure names (cannabis microcaps) out-pulling marquee large-caps, because low search competition = you're the only result. Note whether that still holds.

**X - format variance and engagement.**
- Compare the `text` vs `link-only` medians in the SUMMARY line. Text+cashtag posts should dramatically out-reach bare-link posts; if half the posts are link-only and dragging the median, that's the biggest fixable leak.
- Engagement rate vs the ~4% small-account benchmark. Running below it points at the missing reply motion (broadcast-only), which also caps how far each post gets expanded out-of-network.
- Which posts topped impressions, and what did they share (an early cashtag, a real hook, an ETF anchor on a thin name)?

**Tie it back to strategy.** Connect what you see to the standing questions (see the impressions strategy review in memory): the ETF-cashtag call, the tag-footer diet, short-form video, name selection (obscure vs marquee), and whether the prompts should shift (e.g. YouTube titles more search-first). Only claim what the data supports; flag small-sample caveats honestly (this is a small channel - directional, not statistically robust).

### 3. Output
Lead with the single biggest insight, then 3-5 specific, prioritized actions tied to a number. End with any anomalies to fix (broken uploads, link-only posts, throttled batches).
