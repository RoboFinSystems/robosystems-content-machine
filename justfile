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

# Print the Cowork cold-start prompt for a project (ready to paste into Cowork)
kickoff project:
    #!/usr/bin/env bash
    set -euo pipefail
    SRC="projects/{{project}}/KICKOFF.md"
    [ -f "$SRC" ] || SRC="template/KICKOFF.md"
    sed "s/{TICKER}/{{project}}/g" "$SRC"
    PRIOR="projects/{{project}}/sources/_prior_coverage.md"
    if [ -f "$PRIOR" ]; then printf '\n\n---\n\n'; cat "$PRIOR"; fi

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

# Generate the Claude Design hand-off brief from the script (deck mode)
deck-brief project:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/build_deck_brief.py {{project}}

# Slice a Claude Design deck PDF into 1920x1080 slide PNGs (deck mode)
slice project:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/slice_deck.py {{project}}

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

# Assemble a 9:16 teaser Short (b-roll + ducked music + VO + caption cards)
short project *args:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run --with pillow python tools/assemble_short.py {{project}} {{args}}

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

# Extract podcast audio (MP3) from final video
podcast project:
    #!/usr/bin/env bash
    set -euo pipefail
    VIDEO=$(ls projects/{{project}}/videos/*_final.mp4 2>/dev/null | head -1)
    if [ -z "$VIDEO" ]; then
        echo "No final video found. Run the pipeline first."
        exit 1
    fi
    TICKER="{{project}}"
    OUTPUT="projects/{{project}}/videos/${TICKER}_podcast.mp3"
    echo "Extracting audio: $VIDEO → $OUTPUT"
    ffmpeg -i "$VIDEO" -vn -acodec libmp3lame -q:a 2 -y "$OUTPUT" 2>/dev/null
    DURATION=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$OUTPUT" | cut -d. -f1)
    MINS=$((DURATION / 60))
    SECS=$((DURATION % 60))
    SIZE=$(du -h "$OUTPUT" | cut -f1)
    echo "Done: $OUTPUT ($SIZE, ${MINS}m${SECS}s)"

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
