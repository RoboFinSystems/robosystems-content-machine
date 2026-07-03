Queue a ticker's Buffer-able posts as **drafts** via the Buffer MCP, then print the manual tail that still needs a human. Buffer's clean win for the research lane is the 9:16 **Short** (small native video + caption); the long-form X post, the X Article, first comments, YouTube, and Spotify stay native/manual (see `/buffer-draft` notes below and the publish pack).

## Arguments
- `$ARGUMENTS` — ticker, plus optional flags:
  - `--main` — also queue the **X main post** with the long-form video attached (only if the X account is Premium — non-Premium caps X video at 2:20 and the ~10-min long-form will fail; the X Article + first comment are still manual regardless). Default: off.
  - `--linkedin` — also queue `linkedin_post` as a text draft on the connected personal LinkedIn. Default: off (the postpack model reserves LinkedIn for the blog lane; the promo-code first comment stays manual).

**Draft-only, always.** This skill NEVER schedules or auto-publishes — every post lands as a Buffer **draft**. The human opens Buffer and posts each one, coordinating timing with the X-native pieces (the Article, first comments) they stage in X. There is deliberately no queue/schedule/publish path here.

## What Buffer can/can't do here (why this skill queues so little)
- ✅ **X — Short**: 9:16, ~40s, <2MB, public CDN URL → Buffer uploads it natively. This is the queue candidate.
- ❌ **X — main post**: the native long-form-video upload IS the discovery, and Buffer can't publish the brief as an **X Article** or add the **first comment** — so this stays a native manual post.
- ➖ **YouTube / Spotify**: long-form + Short go up natively (discovery + watch-time); the podcast auto-mirrors YouTube via Anchor RSS. Buffer would be redundant. Skip.

## Steps

### 1. Resolve the ticker + refresh the pack
Parse the ticker and flags from `$ARGUMENTS`. Regenerate the pack so its manual checklist + resolved copy are current (pack lives in gitignored `projects/`, so this is free):
```bash
just postpack {TICKER}
```

### 2. Gather the queue candidates
Read the Cowork copy and verify the media is actually live on the CDN:
```bash
# caption source
cat projects/{TICKER}/social/{TICKER}_publish.json | python3 -c "import json,sys; d=json.load(sys.stdin); print('SHORT_TITLE:', d.get('short_title','')); print('HAS_LINKEDIN:', bool(d.get('linkedin_post')))"
# short render present locally?
ls -lh projects/{TICKER}/videos/{TICKER}_short.mp4 2>/dev/null
# and reachable on the CDN (Buffer fetches by URL)?
curl -sI "https://assets.robosystems.ai/content/{TICKER}/{TICKER}_short.mp4" -o /dev/null -w "short.mp4 -> HTTP %{http_code}, %{size_header}B header\n"
```
- If the Short isn't rendered → nothing to queue; tell the user to `just short {TICKER}` first and stop.
- If the local render is **newer** than what's published (compare `just publish` was run since the last `just short`), warn that Buffer will pull the **published** copy — they may want `just publish {TICKER}` first so the queued Short is the current render.
- Pull the caption from `short_title`. If it contains any `[PROMO_CODE]`/`[YOUTUBE_LINK]` placeholder, resolve/flag it before queuing (captions normally have none).

### 3. Select the Buffer org + channels (never guess IDs)
```
get_account   → confirm the org (expected: "Harbinger FinLab"). If >1 org, ask which.
list_channels → map service → channelId for that org:
                twitter  = the X profile (robofinsystems)
                linkedin = the personal profile (only if --linkedin)
                youtube  = present but unused here
```
Use the exact `id` values returned — do not hardcode. Note the plan limits from `get_account` (free = 3 channels / 10 scheduled / 100 ideas); drafts don't consume the scheduled cap.

### 4. Build the draft set, then PREVIEW before writing
Assemble the payloads (default = just the Short) and print a table for the user to confirm — **do not create anything yet**:
```
Buffer drafts for {TICKER}  (org: Harbinger FinLab, mode: draft)
  CHANNEL   KIND         CAPTION (trunc)                    MEDIA                 CHARS
  X         Short 9:16   How was a profitable company…      {TICKER}_short.mp4    72
  [X        Main post    COVERAGE UPDATE: …   (--main)      {TICKER}_final.mp4   2893]   ← only with --main + Premium
  [LinkedIn Post text    We first covered Trulieve…(--linkedin)  —              1180]
Still manual after this: X main post (native + Article + first comment), YouTube long-form, Spotify.
Create these drafts? (y/n)
```

### 5. Create the drafts (on confirm)
For each selected payload, call `create_post` with:
- `channelId`: the exact id from step 3
- `schedulingType`: `"automatic"` — **X/twitter rejects `"notification"`** ("Notification scheduling is not supported for twitter channels"). Since these are drafts, nothing publishes regardless of this value.
- `saveToDraft`: `true` — always. Never `addToQueue`/`shareNow`/`customScheduled`; this skill only drafts.
- `text`: the caption / post body
- for video posts, `assets`: `[{ "video": { "url": "https://assets.robosystems.ai/content/{TICKER}/{TICKER}_short.mp4", "metadata": { "title": "{TICKER} — Short" } } }]`

X — Short payload (the default):
- channel = twitter, text = `short_title`, video asset = the CDN `{TICKER}_short.mp4`.

`--main` payload (X main post): text = the **resolved** X post body from the pack's Reference "X" section (already has `[YOUTUBE_LINK]` stripped + promo code resolved), video asset = `{TICKER}_final.mp4`. Warn about the Premium/2:20 cap before creating.

`--linkedin` payload: channel = linkedin, text = `linkedin_post`, no media (or the thumbnail). Note the promo-code first comment stays manual.

### 6. Report + hand off the manual tail
Print the created draft ids and the review link, then restate what the human still owns (pull the ✋ list straight from `projects/{TICKER}/{TICKER}_publish_pack.md`):
```
✅ Drafted to Buffer (post them yourself at https://publish.buffer.com, in coordination with your X Article/first comments):
   • X — Short 9:16   (draft {id})

✋ Still on you (native, Buffer can't):
   1. YouTube long-form — upload, copy URL → [YOUTUBE_LINK]
   2. X — main post — native long-form upload + post body
   3. X — Article — publish the brief; link it in the first comment
   4. X — Short pinned comment — paste [YOUTUBE_LINK] after YT is live
   5. Spotify — upload the podcast MP3
   6. just sync-youtube {TICKER}
   (full copy + media URLs: projects/{TICKER}/{TICKER}_publish_pack.md)
```

## Notes
- **Idempotency**: before creating, `list_posts` with `status: ["draft"]` on the X channel and check for an existing draft whose text matches this Short's caption — if found, offer to skip or `edit_post` instead of making a duplicate.
- **Batch**: draft across many tickers in one pass (`for t in TRLV GTBIF ...; /buffer-draft $t`) — all land as drafts you post from Buffer. Drafts don't hit the free plan's 10-scheduled cap, but watch the 100-draft/idea ceiling if you stage a big backlog.
- **Blog lane**: Buffer is a *better* fit for `blog/<slug>` posts (LinkedIn + X are pure text + cover image — no native-video requirement). A `/buffer-draft-blog` sibling is the natural follow-on if this proves out.
