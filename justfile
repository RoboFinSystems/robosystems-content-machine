# =============================================================================
# ROBOSYSTEMS MARKETING — VIDEO CONTENT PIPELINE
# =============================================================================
#
# QUICK START:
#   just new NVDA 10-K 2025                          # Generic template
#   just campaign GTBIF 10-K 2025 cannabis_coverage   # Campaign template
#   just pipeline NVDA_2025_10_K                      # Run full pipeline
#
# STEP BY STEP:
#   just screenshots PROJECT      # Screenshot charts/slides to PNG
#   just voiceover PROJECT        # Generate ElevenLabs voiceovers
#   just assemble PROJECT         # Assemble final video via Shotstack
#   just podcast PROJECT          # Extract podcast audio (MP3)
#   just avatar PROJECT           # Generate HeyGen avatar segments (mixed mode only)
#
# =============================================================================

_env := ".env"

default:
    @just --list

[private]
ensure-env:
    @test -f {{_env}} || cp .env.example {{_env}}

# ─── Project Setup ────────────────────────────────────────────

# Create a new project from generic template
new ticker filing="10-K" year="2025":
    ./tools/new_project.sh {{ticker}} {{filing}} {{year}}

# Create a new project from a campaign template
campaign ticker filing="10-K" year="2025" campaign_name="":
    ./tools/new_project.sh {{ticker}} {{filing}} {{year}} {{campaign_name}}

# List all projects
projects:
    @ls -1 projects/ 2>/dev/null || echo "No projects yet. Run: just new TICKER"

# List available campaigns
campaigns:
    @ls -1 campaigns/ 2>/dev/null || echo "No campaigns yet."

# Open a project folder
open project:
    open projects/{{project}}

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

# Screenshot chart HTMLs to PNGs
screenshots project:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/screenshot_charts.py {{project}}

# Generate avatar video segments via HeyGen
avatar project:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/generate_avatar_segments.py {{project}}

# Resume polling HeyGen (if interrupted)
avatar-poll project:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/generate_avatar_segments.py {{project}} --poll

# Generate voiceover audio via ElevenLabs
voiceover project:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/generate_voiceover_audio.py {{project}}

# Assemble final video via Shotstack
assemble project:
    @just ensure-env
    UV_ENV_FILE={{_env}} uv run python tools/assemble_video.py {{project}}

# Run full pipeline: validate → screenshots → avatar → voiceover → assemble
pipeline project:
    @just ensure-env
    ./tools/run_pipeline.sh {{project}}

# Extract podcast audio (MP3) from final video
podcast project:
    #!/usr/bin/env bash
    set -euo pipefail
    VIDEO=$(ls projects/{{project}}/videos/*_final.mp4 2>/dev/null | head -1)
    if [ -z "$VIDEO" ]; then
        echo "No final video found. Run the pipeline first."
        exit 1
    fi
    TICKER=$(echo "{{project}}" | cut -d_ -f1)
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

# Clean generated assets (keep scripts/charts HTML, remove videos/PNGs)
clean project:
    rm -rf projects/{{project}}/videos projects/{{project}}/charts/png
    echo "Cleaned generated assets for {{project}}"
