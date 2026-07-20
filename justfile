# =============================================================================
# ROBOSYSTEMS CONTENT MACHINE — VIDEO CONTENT PIPELINE
# =============================================================================
#
# QUICK START:
#   just new NVDA                                # Generic template
#   just campaign GTBIF cannabis_coverage         # Campaign coverage
#   just pipeline GTBIF                           # Run full pipeline
#
# STEP BY STEP:
#   just deck-brief TICKER      # Generate the Claude Design hand-off brief
#   just slice TICKER           # Slice the exported deck PDF into slide PNGs
#   just voiceover TICKER       # Generate ElevenLabs voiceovers
#   just assemble TICKER        # Assemble final video via Shotstack
#   just podcast TICKER         # Extract podcast audio (MP3)
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

# Print the Cowork cold-start prompt for a project (also copies it to the clipboard, ready to paste into Cowork)
kickoff project:
    @./tools/kickoff.sh {{project}}

# ─── QA ──────────────────────────────────────────────────────

# Validate cowork outputs before running pipeline
validate project:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/validate_project.py {{project}}

# Validate and auto-fix common schema issues
validate-fix project:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/validate_project.py {{project}} --fix

# ─── Pipeline Steps ──────────────────────────────────────────

# Generate the Claude Design hand-off brief from the script (deck mode); also copies DESIGN_INSTRUCTIONS + brief to the clipboard
deck-brief project:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/build_deck_brief.py {{project}}

# Slice a Claude Design deck PDF into 1920x1080 slide PNGs (deck mode)
slice project:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/slice_deck.py {{project}}

# Generate the 3 platform thumbnails via OpenAI (brief -> gpt-image-2 -> assets/{yt,x,spot}.png)
thumbnails project *args:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/gen_thumbnails.py {{project}} {{args}}

# Generate voiceover audio via ElevenLabs
voiceover project:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/generate_voiceover_audio.py {{project}}

# Assemble final video via Shotstack (add --production to use credits)
assemble project *args:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/assemble_video.py {{project}} {{args}}

# Run full deck pipeline: validate → slice → voiceover → assemble
pipeline project:
    @just ensure-env
    ./tools/run_pipeline.sh {{project}}

# ─── Webdeck (pilot): animated HTML deck → frame render → mux ─

# Full webdeck pipeline: validate → voiceover → build → render → mux (no PPTX, no Shotstack)
webdeck-pipeline project: (validate project) (voiceover project) (webdeck project) (webdeck-render project) (webdeck-mux project)

# Build the animated webdeck HTML from script.json + VO durations
webdeck project *args:
    python3 tools/build_webdeck.py {{project}} {{args}}

# Render the webdeck to silent.mp4, frame by frame via headless Chrome (1080p30)
webdeck-render project *args:
    cd tools/webdeck && node render_webdeck.mjs --html ../../projects/{{project}}/webdeck/{{project}}_webdeck.html --out ../../projects/{{project}}/webdeck/render {{args}}

# Mux narration (A) and narration+music with ducking (B) onto the silent render
webdeck-mux project *args:
    python3 tools/webdeck/mux_webdeck.py {{project}} {{args}}

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

# 9:16 avatar short from the brief: HeyGen avatar (our voice) + gpt-image backdrop + word-synced captions.
# Default = hook short (videos/{T}_short.mp4, teases the long-form); --qa = two-avatar Q&A short
# (videos/{T}_short_qa.mp4, teases the podcast). Add --test for a free watermarked HeyGen render.
short project *args:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/gen_avatar_short.py {{project}} {{args}}

# Generate BOTH shorts for a name: the hook short (-> long-form) and the Q&A short (-> podcast).
shorts project *args:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/gen_avatar_short.py {{project}} {{args}}
    UV_ENV_FILE={{_env}} uv run python tools/gen_avatar_short.py {{project}} --qa {{args}}

# Generate a two-voice Q&A podcast (MP3 for Spotify + MP4 for YouTube)
podcast-qa project *args:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/generate_podcast_qa.py {{project}} {{args}}

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

# ─── Blog Pipeline (markdown essays → S3 blog/ + blog/index.json) ─────────────

# Scaffold a new blog post: blog/<slug>/post.md from the template
blog-new slug:
    @bash tools/new_blog.sh {{slug}}

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

# Extract podcast audio (MP3) from final video
podcast project:
    @./tools/extract_podcast.sh {{project}}

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
