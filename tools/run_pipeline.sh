#!/bin/bash
# Run the full production pipeline for a project.
#
# Prerequisites: Claude Cowork has already generated the content
# (script JSON, chart HTMLs, brief/report, social posts, thumbnail)
#
# Usage:
#   ./tools/run_pipeline.sh JPM_2025_10_K
#
# Steps:
#   0. Validate & auto-fix cowork outputs
#   1. Screenshot charts/slides (HTML -> PNG)
#   2. Generate avatar segments (HeyGen) — skipped in slides-only mode
#   3. Generate voiceover audio (ElevenLabs)
#   4. Assemble final video (upload to S3 + Shotstack render)

set -euo pipefail

PROJECT="${1:?Usage: $0 PROJECT_NAME}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="${ROOT_DIR}/projects/${PROJECT}"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "Error: Project not found at $PROJECT_DIR"
    exit 1
fi

cd "$ROOT_DIR"
export UV_ENV_FILE=.env

echo "═══════════════════════════════════════════"
echo "  Pipeline: $PROJECT"
echo "═══════════════════════════════════════════"
echo ""

# Load AWS_PROFILE from .env so aws CLI works regardless of direnv
if grep -q '^AWS_PROFILE=' .env 2>/dev/null; then
    export $(grep '^AWS_PROFILE=' .env)
fi

# Detect pipeline mode from script JSON
SCRIPT_FILE=$(ls "$PROJECT_DIR/scripts/"*_script.json 2>/dev/null | head -1)
if [ -z "$SCRIPT_FILE" ]; then
    echo "Error: No script JSON found in $PROJECT_DIR/scripts/"
    exit 1
fi

# Check if any avatar segments exist
HAS_AVATAR=$(python3 -c "
import json, sys
with open('$SCRIPT_FILE') as f:
    segs = json.load(f).get('segments', [])
print('yes' if any(s.get('type') == 'avatar' for s in segs) else 'no')
")

if [ "$HAS_AVATAR" = "yes" ]; then
    MODE="mixed"
    STEPS=4
    echo "  Mode: Avatar + Visual (HeyGen + ElevenLabs)"
else
    MODE="slides"
    STEPS=3
    echo "  Mode: Slides only (ElevenLabs voiceover)"
fi
echo ""

# Pre-flight: check AWS creds before doing expensive API work
echo "Pre-flight: Checking AWS credentials..."
aws sts get-caller-identity --query Account --output text > /dev/null 2>&1 || {
    echo "ERROR: AWS credentials not configured or SSO session expired."
    echo "  Run: aws sso login --profile robosystems-sso"
    exit 1
}
echo "  AWS OK"
echo ""

# Step 0: Validate & fix
echo "Step 0: Validate & fix"
uv run python tools/validate_project.py "$PROJECT" --fix
echo ""

# Step 1: Screenshot charts/slides
echo "Step 1/$STEPS: Screenshots"
uv run python tools/screenshot_charts.py "$PROJECT"
echo ""

if [ "$MODE" = "mixed" ]; then
    # Step 2: Generate avatar segments (mixed mode only)
    echo "Step 2/$STEPS: Avatar segments (HeyGen)"
    uv run python tools/generate_avatar_segments.py "$PROJECT"
    echo ""

    # Step 3: Generate voiceover audio
    echo "Step 3/$STEPS: Voiceover audio (ElevenLabs)"
    uv run python tools/generate_voiceover_audio.py "$PROJECT"
    echo ""

    # Step 4: Assemble video
    rm -f "$PROJECT_DIR/videos/shotstack_assets.json" "$PROJECT_DIR/videos/media_durations.json"
    echo "Step 4/$STEPS: Assemble video (upload to S3 + Shotstack render)"
    uv run python tools/assemble_video.py "$PROJECT"
    echo ""
else
    # Step 2: Generate voiceover audio (slides-only — all segments)
    echo "Step 2/$STEPS: Voiceover audio (ElevenLabs)"
    uv run python tools/generate_voiceover_audio.py "$PROJECT"
    echo ""

    # Step 3: Assemble video
    # Clear asset cache so fresh audio/screenshots are uploaded
    rm -f "$PROJECT_DIR/videos/shotstack_assets.json" "$PROJECT_DIR/videos/media_durations.json"
    echo "Step 3/$STEPS: Assemble video (upload to S3 + Shotstack render)"
    uv run python tools/assemble_video.py "$PROJECT"
    echo ""
fi

echo "═══════════════════════════════════════════"
echo "  Done! Opening final video..."
echo "═══════════════════════════════════════════"
open "$PROJECT_DIR/videos/"*_final.mp4
