# Avatar Short - recipe (validated POC, parked)

A repeatable recipe for a 9:16 talking-head short: a HeyGen avatar (in our ElevenLabs voice)
keyed out of green and composited over a branded backdrop, with brand chrome + captions on top.
Every piece below was proven in a POC on 2026-07-16. **Not wired into the pipeline** - shorts are
disabled (see `PRODUCTION_CONTRACT.md`). This doc exists so we can rebuild/run it later.

## Why (the strategic frame)
Shorts are **top-of-funnel discovery**, not the product. They exist to get reach and nudge the
algorithm toward our real content (the long-form video + robosystems.ai). So "our weakest link,
but ok" clears the bar - discovery is a volume game. Judge it as **customer-acquisition cost**,
not production value. Before building an automated renderer, **run a ~$20 test batch (5-10 shorts)
and see if they actually drive views/subs/traffic.** Build the pipeline only if the funnel pays.

## Cost
~**$1-2 per short all-in** (HeyGen ~$0.016/sec -> ~$0.50-0.75 for 30-45s; gpt-image backdrop ~$0.20
at high quality). Levers to get toward ~$0.60-0.80: reusable brand backdrop instead of a fresh
gpt-image each time, shorter ~25s cuts, medium-quality images, HeyGen monthly-plan minutes vs API
pay-as-you-go.

## Env (already in `.env`)
- `HEYGEN_API_KEY` - v2 key (`sk_V2_...`)
- `HEYGEN_AVATAR_LOOK_ID` - the value that goes in the API's `avatar_id` field (e.g.
  `Brandon_expressive2_public`, a HeyGen studio avatar). **A filmed stock avatar is what fixes the
  frozen-body / uncanny problem a personal photo-avatar has.**
- `HEYGEN_AVATAR_ID` - the avatar-group uuid (fallback; the look id is what the generate call wants)
- `HEYGEN_VOICE_ID` - a HeyGen voice wired to our ElevenLabs account, so the avatar speaks in our
  brand narration voice (voice stays consistent with the long-form)
- `OPENAI_API_KEY` - for the gpt-image-2 backdrop

## Steps (scripts in this folder)

### 1. Render the avatar on green -> `heygen_green.py`
`POST https://api.heygen.com/v2/video/generate` with `character.avatar_id = <LOOK_ID>`,
`voice = {type:text, input_text:<script>, voice_id:<HEYGEN_VOICE_ID>}`, **`background = {type:color,
value:"#00FF00"}`**, `dimension = {720,1280}`. Poll `v1/video_status.get`, download `video_url`.
Set `"test": true` for a **free watermarked** render (POC); drop it for a clean paid render.

### 2. Backdrop (pick one)
- **gpt-image-2 (default: automated, rich)** -> `gen_backdrop.py`. Native 720x1280. The prompt MUST
  enforce the **avatar safe-zone**: rich imagery (chart, product silhouettes) in the UPPER third,
  a clean/dark/empty lower two-thirds where the presenter sits. ~$0.20 high quality.
- **Claude Design** - a 9:16 slide, for when you need a *precise data chart* behind him on a number
  beat. Same safe-zone rule. Mix per beat: generated backdrop for the hook, a data-slide for figures.

### 3. Overlay (brand + hook + caption) -> `overlay.html`
A transparent PNG rendered from HTML via headless Chrome (see `--default-background-color=00000000`),
carrying the RoboSystems wordmark + ticker (top), the hook headline (top, above his head), and the
caption (bottom). Kept as an **overlay, not baked into the backdrop**, so text stays crisp/legible.
```
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu \
  --hide-scrollbars --force-device-scale-factor=1 --default-background-color=00000000 \
  --window-size=720,1280 --screenshot=overlay.png "file://.../overlay.html"
```

### 4. Composite -> `composite.sh`
Keys the green, composites backdrop + avatar + overlay, keeps the avatar audio:
```
./composite.sh backdrop.png avatar_green.mp4 overlay.png out.mp4
```
Core filter: `chromakey=0x00FF00:0.13:0.06,despill=type=green` then two overlays. The `despill`
kills green fringing on hair/edges - important.

## What's proven vs. still TODO
Proven: stock avatar gestures naturally (no frozen body); green-screen + local composite gives full
control; ElevenLabs voice via HeyGen keeps the voice on-brand; gpt-image-2 honors the safe-zone with
the right prompt and beats a flat brand card on richness; the whole chain composites cleanly.

**TODO for production (the two unbuilt pieces):**
1. **Animated word-synced captions** - the POC caption is a single static line. Real version:
   transcribe the VO (e.g. Whisper), time each word, burn in word-by-word highlights. **This is the
   single biggest retention lever and the main unproven build.**
2. **The renderer** - glue the chain into a tool (`just short-avatar TICKER`): short script ->
   ElevenLabs/HeyGen -> key -> backdrop -> captions -> 9:16 MP4. Optionally dynamic backdrops per beat.

## Related capabilities (already shipped this session)
- `just thumbnails TICKER` - `tools/gen_thumbnails.py`, gpt-image-2 thumbnails from the brief (the
  clear, kept win). Same OpenAI key/pattern used here for the backdrop.
- Sora-2 b-roll (`sora-2` on the OpenAI API) - proven, ~$0.40/4s, but parked: b-roll is texture
  behind the avatar, not the engine.
