#!/bin/bash
# Run the full production pipeline for a project.
#
# Prerequisites: Claude Cowork has already generated the content
# (script JSON, chart HTMLs, report, social post, thumbnail)
#
# Usage:
#   ./tools/run_pipeline.sh JPM_2025_10_K
#
# Steps:
#   0. Validate & auto-fix cowork outputs
#   1. Screenshot charts (HTML -> PNG)
#   2. Generate avatar segments (HeyGen)
#   3. Generate voiceover audio for chart segments (ElevenLabs)
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

# Step 1: Screenshot charts
echo "Step 1/4: Screenshots"
uv run python tools/screenshot_charts.py "$PROJECT"
echo ""

# Step 2: Generate avatar segments
echo "Step 2/4: Avatar segments (HeyGen)"
uv run python tools/generate_avatar_segments.py "$PROJECT"
echo ""

# Step 3: Generate voiceover audio
echo "Step 3/4: Voiceover audio (ElevenLabs)"
uv run python tools/generate_voiceover_audio.py "$PROJECT"
echo ""

# Step 4: Assemble video
echo "Step 4/4: Assemble video (upload to S3 + Shotstack render)"
uv run python tools/assemble_video.py "$PROJECT"
echo ""

echo "═══════════════════════════════════════════"
echo "  Done! Opening final video..."
echo "═══════════════════════════════════════════"
open "$PROJECT_DIR/videos/"*_final.mp4
