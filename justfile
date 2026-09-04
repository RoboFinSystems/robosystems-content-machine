# =============================================================================
# ROBOSYSTEMS CONTENT MACHINE — VIDEO CONTENT PIPELINE
# =============================================================================
#
# QUICK START:
#   just new NVDA                                 # Generic template
#   just campaign GTBIF cannabis_coverage         # Campaign coverage
#   just webdeck-pipeline GTBIF                   # Run the full pipeline
#
# STEP BY STEP:
#   just validate TICKER              # Gate the authored output
#   just voiceover TICKER             # Generate ElevenLabs voiceovers
#   just webdeck TICKER               # Build the animated HTML deck
#   just webdeck-render TICKER        # Render it via headless Chrome
#   just webdeck-mux TICKER           # Mux narration + ducked music
#   just webdeck-short-pipeline TICKER  # The 9:16 short, same engine
#
# Rendering is entirely local (puppeteer + ffmpeg). No cloud render service.
#
# =============================================================================

_env := ".env"

default:
    @just --list

[private]
ensure-env:
    @test -f {{_env}} || cp .env.example {{_env}}

# ─── Coverage Setup ──────────────────────────────────────────

# Initiate coverage on a company (generic template)
new ticker:
    ./tools/new_project.sh {{ticker}}

# Initiate coverage on a company with a campaign
campaign ticker campaign_name:
    ./tools/new_project.sh {{ticker}} {{campaign_name}}

# Re-cover an existing ticker for a new quarter (archives prior outputs -> .history, keeps sources)
recover ticker campaign_name="":
    ./tools/new_project.sh {{ticker}} "{{campaign_name}}" --recover

# List all coverage projects
projects:
    @ls -1 projects/ 2>/dev/null || echo "No projects yet. Run: just new TICKER"

# List available campaigns
campaigns:
    @ls -1 campaigns/ 2>/dev/null || echo "No campaigns yet."

# Open a project folder
open project:
    open projects/{{project}}

# Print the cold-start authoring prompt for a project (also copies it to the clipboard)
kickoff project:
    @./tools/kickoff.sh {{project}}

# ─── QA ──────────────────────────────────────────────────────

# Validate the authored outputs before running the pipeline
validate project:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/validate_project.py {{project}}

# Validate and auto-fix common schema issues
validate-fix project:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/validate_project.py {{project}} --fix

# ─── Pipeline Steps ──────────────────────────────────────────

# Generate the YouTube thumbnail via OpenAI (brief -> gpt-image-2 -> assets/yt.png -> charts/png/)
# --with-x / --with-spot add the 5:2 and 1:1 variants, both off by default.
thumbnails project *args:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/gen_thumbnails.py {{project}} {{args}}

# Generate voiceover audio via ElevenLabs
voiceover project *args:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/generate_voiceover_audio.py {{project}} {{args}}

# RETIRED - the Shotstack cloud-render path was torn out 2026-08-08
assemble project *args:
    @echo "'just assemble' is retired. The Shotstack cloud-render path was removed 2026-08-08."
    @echo "Rendering is local now: just webdeck-pipeline {{project}}"
    @echo "(tools/assemble_video.py lives in git history if you ever need it back.)"
    @exit 1

# RETIRED - the deck path (Claude Design PPTX -> slice -> Shotstack) was torn out 2026-08-08
pipeline project:
    @echo "'just pipeline' is retired. It rendered via Shotstack, which is no longer used."
    @echo "Use: just webdeck-pipeline {{project}}   (validate -> voiceover -> build -> render -> mux)"
    @echo "(tools/run_pipeline.sh lives in git history if you ever need it back.)"
    @exit 1

# ─── Webdeck (pilot): animated HTML deck → frame render → mux ─

# Full webdeck pipeline: validate → voiceover → build → render → mux (no PPTX, no Shotstack)
# Validates with --pre-render: the render-freshness check would otherwise refuse to let
# the pipeline run precisely when a re-render is what the project needs.
webdeck-pipeline project: (validate-pre-render project) (voiceover project) (webdeck project) (webdeck-render project) (webdeck-mux project)

# Validate everything except render freshness (used as the pipeline's pre-render gate)
validate-pre-render project:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/validate_project.py {{project}} --pre-render

# Build the animated webdeck HTML from script.json + VO durations
webdeck project *args:
    python3 tools/build_webdeck.py {{project}} {{args}}

# Render the webdeck to silent.mp4, frame by frame via headless Chrome (1080p30)
webdeck-render project *args:
    cd tools/webdeck && node render_webdeck.mjs --html ../../projects/{{project}}/webdeck/{{project}}_webdeck.html --out ../../projects/{{project}}/webdeck/render {{args}}

# QA stills for the long-form (comma-separated seconds), e.g. just webdeck-stills CALM "78,140"
# A still takes ~10s against a ~16-min render - use it to check any template change.
webdeck-stills project times:
    cd tools/webdeck && node render_webdeck.mjs --html ../../projects/{{project}}/webdeck/{{project}}_webdeck.html --out ../../projects/{{project}}/webdeck/stills --stills "{{times}}"

# Mux narration (A) and narration+music with ducking (B) onto the silent render
webdeck-mux project *args:
    python3 tools/webdeck/mux_webdeck.py {{project}} {{args}}

# ─── Webdeck SHORT (9:16): purpose-built vertical short for X + YT Shorts ─

# Full short pipeline: voice → build → render (1080x1920) → mux → videos/{T}_short.mp4 (+ _short_music.mp4)
webdeck-short-pipeline project: (webdeck-short-vo project) (webdeck-short project) (webdeck-short-render project) (webdeck-short-mux project)

# Voice the 9:16 short script (T_short_script.json) into T_short_segment_* mp3s (--force to re-voice)
webdeck-short-vo project *args:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/generate_voiceover_audio.py {{project}} --short {{args}}

# Build the vertical short HTML from T_short_script.json (+ --estimate for a pre-VO stills check)
webdeck-short project *args:
    python3 tools/build_webdeck_short.py {{project}} {{args}}

# Render the short to silent.mp4 frame-by-frame at 1080x1920
webdeck-short-render project *args:
    cd tools/webdeck && node render_webdeck.mjs --html ../../projects/{{project}}/webdeck/{{project}}_short.html --out ../../projects/{{project}}/webdeck/short_render --width 1080 --height 1920 {{args}}

# QA stills for the short (comma-separated seconds), e.g. just webdeck-short-stills NFLX "3,10,20"
webdeck-short-stills project times:
    cd tools/webdeck && node render_webdeck.mjs --html ../../projects/{{project}}/webdeck/{{project}}_short.html --out ../../projects/{{project}}/webdeck/short_stills --width 1080 --height 1920 --stills "{{times}}"

# Mux narration + ducked music onto the short's silent render -> videos/{T}_short.mp4
webdeck-short-mux project *args:
    python3 tools/webdeck/mux_webdeck.py {{project}} --short {{args}}

# ─── YouTube (Data API) ──────────────────────────────────────

# One-time YouTube OAuth (opens a browser; writes YT_REFRESH_TOKEN to .env)
yt-auth:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/upload_youtube.py auth

# Upload the final video to YouTube (private by default; --public to skip the gate)
yt-upload project *args:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/upload_youtube.py upload {{project}} {{args}}

# Flip the uploaded video to public after the watch gate
yt-publish project *args:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/upload_youtube.py publish {{project}} {{args}}

# Upload the 9:16 short as a YouTube Short (#Shorts, own sidecar; long-form link auto-fills if uploaded first)
yt-short project *args:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/upload_youtube.py upload {{project}} --short {{args}}

# Flip the uploaded Short to public after the watch gate
yt-short-publish project *args:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/upload_youtube.py publish {{project}} --short {{args}}

# Post the first comment (written-brief link) on an uploaded video; publish does this automatically (--short / --force / --text)
yt-comment project *args:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/upload_youtube.py comment {{project}} {{args}}

# ─── X (API v2) ──────────────────────────────────────────────

# One-time X auth: verify the user token in .env (or mint one via the PIN flow - run as `! just x-auth`)
x-auth:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/post_x.py auth

# Generate the branded 5:2 X Article cover (local Chrome render - no OpenAI)
article-cover project *args:
    python3 tools/gen_article_cover.py {{project}} {{args}}

# Create the brief as an X Article DRAFT (review in the X editor, then --publish)
x-article project *args: (article-cover project)
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/post_x.py article {{project}} {{args}}

# Send the single X post (native video + Article link from the sidecar; --dry-run first)
x-post project *args:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/post_x.py post {{project}} {{args}}

# Post the 9:16 short natively to X (own copy + sidecar; --dry-run first)
x-short project *args:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/post_x.py post {{project}} --short {{args}}

# ─── Analytics (reach/retention feedback loop) ───────────────

# Pull X + YouTube performance into projects/*/analytics.json (all tickers, or named ones)
analytics *tickers:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/pull_analytics.py {{tickers}}

# Channel/account-level reach (YouTube traffic sources + retention, X post impressions)
insights *args:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/pull_insights.py {{args}}

# ─── Media libraries ─────────────────────────────────────────

# Show the b-roll library + coverage across shoot-list categories
broll:
    UV_ENV_FILE={{_env}} uv run python tools/list_broll.py

# Sync assets/broll/manifest.json with the clips present (run after dropping in new b-roll)
broll-sync:
    UV_ENV_FILE={{_env}} uv run python tools/sync_broll.py

# Sync assets/music/manifest.json with the tracks present (run after dropping in music)
music-sync:
    UV_ENV_FILE={{_env}} uv run python tools/sync_music.py

# Generate a music bed via the ElevenLabs Music API (preset name or literal prompt)
music prompt *args:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/generate_music.py "{{prompt}}" {{args}}


# Assemble a per-platform publish pack (paste-ready copy + S3 media links)
postpack project:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/build_postpack.py {{project}}

# Publish a project's final deliverables to the public S3 artifact store
publish project:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/publish_artifacts.py {{project}}

# Rebuild the research catalog (content/index.json) the /research portal reads
reindex:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/reindex.py

# ─── Tier 1: brief-only coverage (volume → /research + SEO, no video) ─────────
# The brief admits a ticker to the catalog, so a /research page needs no render,
# no voiceover and no upload. Reserve the video treatment (webdeck-pipeline +
# YouTube/X) for the few names per batch whose finding is story-shaped.

# Validate a brief-only project (skips every script/deck/render check)
validate-brief project:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/validate_project.py {{project}} --brief-only

# Validate + publish a brief-only ticker straight to /research
publish-brief project: (validate-brief project)
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/publish_artifacts.py {{project}}

# ─── Blog Pipeline (markdown essays → S3 blog/ + blog/index.json) ─────────────

# Scaffold a new blog post: blog/<slug>/post.md from the template (site: robosystems | roboledger)
blog-new slug site='robosystems':
    @bash tools/new_blog.sh {{slug}} {{site}}

# Narrate a post via ElevenLabs TTS → blog/<slug>/<slug>_narration.mp3 (optional)
blog-narrate slug *args:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/narrate_blog.py {{slug}} {{args}}

# Assemble a paste-ready distribution pack for a post (optional)
blog-social slug:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/build_blog_postpack.py {{slug}}

# Publish a post to S3 (blog/<slug>/) + refresh blog/index.json (auto-narrates; --no-audio to skip)
blog-publish slug *args:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/publish_blog.py {{slug}} {{args}}

# Generate the branded 5:2 X Article cover for a blog post
blog-article-cover slug *args:
    python3 tools/gen_article_cover.py {{slug}} --blog {{args}}

# Create a blog post as an X Article DRAFT on @RoboFinSystems (review, then --publish).
# The X Article is the account's best format (~2x plain text) - this is what lets the
# concept/education lane use it instead of only ticker briefs.
blog-x-article slug *args: (blog-article-cover slug)
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/post_x.py article {{slug}} --blog {{args}}

# Rebuild the blog catalog (blog/index.json) the /blog routes read
blog-reindex:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/reindex_blog.py

# Capture YouTube URLs into the catalog via the channel RSS feed (run after uploading)
sync-youtube *tickers:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/sync_youtube.py {{tickers}}

# ─── Infrastructure (CloudFormation, deployed locally via CLI — no GHA) ───────

# Validate the content infra template (S3 bucket + CloudFront CDN)
infra-validate:
    @just ensure-env
    @bash tools/deploy_infra.sh validate

# Create/update the content infra stack (creates the new bucket; reads .env)
infra-deploy:
    @just ensure-env
    @bash tools/deploy_infra.sh deploy

# Print the content stack outputs (bucket, CDN url, distribution id)
infra-outputs:
    @just ensure-env
    @bash tools/deploy_infra.sh outputs

# One-time: copy existing published content from the legacy bucket into the new one
content-migrate from="robosystems-marketing-assets":
    @just ensure-env
    @bash tools/migrate_content.sh {{from}}

# ─── Content design system (design-system/ ↔ Claude Design project 746ae7a4) ──

# Rebuild design-system/_ds_bundle.js from the component sources. Run after editing
# components/*.jsx, then push the bundle (+ any changed files) back to Claude Design via
# DesignSync / the /design-sync skill. Tokens, CSS, and templates push as-is — no build.
design-build:
    cd design-system && npm install --no-audit --no-fund --silent && npm run build

# ─── Renderer (renderer/ — Playwright: UI capture + 9:16 motion) ──────────────

# Install the renderer's Node deps + the Playwright Chromium browser (run once).
render-setup:
    cd renderer && npm install --no-audit --no-fund --silent && npx playwright install chromium

# Capture the live RoboLedger UI (headless login → demo screens → dark-theme stills).
# Needs the UI running (default localhost:3001) + creds. company = showcase slug (e.g. coffee_roaster);
# entity = UI name prefix (e.g. Driftline). Stills → showcase/<company>/captures/ (gitignored product).
# e.g. just render-capture <config> coffee_roaster Driftline
render-capture config company entity="" scenes="home,transactions,close,statements,reports":
    node renderer/src/cli.mjs capture --config {{config}} --scenes {{scenes}} --out showcase/{{company}}/captures {{ if entity != "" { "--entity '" + entity + "'" } else { "" } }}

# Render a scene spec (a per-episode product in showcase/<company>/, gitignored) to a silent mp4.
# Mux VO/music downstream in the Python short path. e.g. just render-short showcase/coffee_roaster/driftline.demo.json
render-short spec:
    node renderer/src/cli.mjs short --spec {{spec}}

# ─── Product demos (live UI walkthrough: real cursor, real clicks, component zoom) ───

# List the anchors a walkthrough can aim at, read off the RUNNING app rather than
# guessed from source. "fit" is the largest zoom that still frames the element.
# e.g. just demo-probe <config> Driftline "/ledger/close,/reports,/plan"
demo-probe config entity="" routes="/home,/ledger/close,/ledger/statements,/reports,/plan":
    node renderer/src/cli.mjs probe --config {{config}} --routes "{{routes}}" {{ if entity != "" { "--entity '" + entity + "'" } else { "" } }}

# 1. Voiceover + timing. Writes durationMs into the spec so narration owns the clock.
demo-narrate spec *args="":
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/demo_narrate.py {{spec}} {{args}}

# 2. Record the walkthrough against the live UI -> silent mp4 in showcase/<company>/renders/.
demo-render spec config *args="":
    node renderer/src/cli.mjs demo --spec {{spec}} --config {{config}} {{args}}

# 3. Mux the per-beat VO (+ ducked music bed) onto the silent render.
demo-mux spec *args="":
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/demo_mux.py {{spec}} {{args}}

# The whole demo pipeline. Needs the RoboLedger UI running (default localhost:3001).
# e.g. just demo-pipeline showcase/coffee_roaster/driftline.walkthrough.json ~/Projects/robosystems/.local/config.json
demo-pipeline spec config: (demo-narrate spec) (demo-render spec config) (demo-mux spec)

# Single-frame fit check before committing to a full render (~10s vs minutes).
# Shoots the first frame of each beat so a bad zoom target is caught early.
demo-stills spec config:
    node renderer/src/cli.mjs demo --spec {{spec}} --config {{config}} --stills

# ─── Utilities ────────────────────────────────────────────────

# Play the final video
play project:
    open projects/{{project}}/videos/*_final.mp4

# Get media durations via ffprobe
durations project:
    ./tools/durations.sh {{project}}

# Clean generated assets (keep sources/scripts/deck, remove videos + sliced PNGs)
clean project:
    rm -rf projects/{{project}}/videos projects/{{project}}/charts/png
    echo "Cleaned generated assets for {{project}}"
