# Avatar Short - the canonical short (`just short TICKER`)

The 9:16 short is a HeyGen studio avatar (our ElevenLabs voice) keyed out of green and composited
over a gpt-image-2 backdrop, with brand chrome + word-synced captions. Fully headless from the brief.
**Shipped 2026-07-16 as `tools/gen_avatar_short.py` (`just short TICKER`); it replaced the retired
motion-card renderer** (`assemble_short.py`/`short_classify.py`, deleted). This doc is the reference
for how the chain works and how to run/extend the individual pieces (POC scripts below).

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

## Status: BUILT (`just short TICKER` = tools/gen_avatar_short.py)
Both former TODOs shipped 2026-07-16:
1. **Animated word-synced captions** - whisper-1 word timings -> Pillow renders a caption frame
   sequence (the spoken word highlighted) -> overlaid as an animated track in the composite.
2. **The renderer** - `tools/gen_avatar_short.py` wires the whole chain: brief -> gpt-5 script ->
   HeyGen avatar (green) -> whisper -> gpt-image-2 backdrop -> Pillow brand overlay + captions ->
   ffmpeg key + composite -> `videos/{T}_short.mp4`. Run: `just short TICKER` (add `--test` for a
   free watermarked HeyGen render). Needs Pillow (added as a dep).

Remaining polish (not blockers): keep the gpt-5 script ~30s (currently can run long), dynamic
backdrops per beat, avatar/look choice, and captions are chunk-of-3 with a per-word highlight.
The standalone POC scripts below still work for one-off experiments.

## Related capabilities (already shipped this session)
- `just thumbnails TICKER` - `tools/gen_thumbnails.py`, gpt-image-2 thumbnails from the brief (the
  clear, kept win). Same OpenAI key/pattern used here for the backdrop.
- Sora-2 b-roll (`sora-2` on the OpenAI API) - proven, ~$0.40/4s, but parked: b-roll is texture
  behind the avatar, not the engine.
