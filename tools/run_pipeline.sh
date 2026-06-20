#!/bin/bash
# Run the deck-mode production pipeline for a project.
#
# Prerequisite: the project has a deck-mode script (scripts/{TICKER}_script.json with a
# "deck" block), the exported Claude Design deck at deck/{TICKER}_deck.pdf, and
# voiceover-ready narration. See DESIGN_INSTRUCTIONS.md for building the deck.
#
# Usage:
#   ./tools/run_pipeline.sh GTBIF
#
# Steps:  validate -> slice deck (PDF->PNG) -> voiceover (ElevenLabs) -> assemble (S3 + Shotstack)

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

# Require a deck-mode script (this pipeline is deck-only)
SCRIPT_FILE=$(ls "$PROJECT_DIR/scripts/"*_script.json 2>/dev/null | head -1)
if [ -z "$SCRIPT_FILE" ]; then
    echo "Error: No script JSON found in $PROJECT_DIR/scripts/"
    exit 1
fi

DECK_MODE=$(python3 -c "
import json
with open('$SCRIPT_FILE') as f:
    print('yes' if json.load(f).get('deck') else 'no')
")
if [ "$DECK_MODE" != "yes" ]; then
    echo "Error: $PROJECT is not a deck-mode project (script has no 'deck' block)."
    echo "  This pipeline is deck-only — see PRODUCTION_CONTRACT.md / DESIGN_INSTRUCTIONS.md."
    exit 1
fi
echo "  Mode: Deck (Claude Design slides + ElevenLabs voiceover)"
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

# Step 0: Validate
echo "Step 0/3: Validate"
uv run python tools/validate_project.py "$PROJECT" --fix
echo ""

# Step 1: Slice the deck (PDF -> 1920x1080 slide PNGs)
echo "Step 1/3: Slice deck"
uv run python tools/slice_deck.py "$PROJECT"
echo ""

# Step 2: Voiceover (ElevenLabs)
echo "Step 2/3: Voiceover audio (ElevenLabs)"
uv run python tools/generate_voiceover_audio.py "$PROJECT"
echo ""

# Step 3: Assemble (clear asset cache so fresh slides/audio upload)
rm -f "$PROJECT_DIR/videos/shotstack_assets.json" "$PROJECT_DIR/videos/media_durations.json"
echo "Step 3/3: Assemble video (upload to S3 + Shotstack render)"
uv run python tools/assemble_video.py "$PROJECT"
echo ""

echo "═══════════════════════════════════════════"
echo "  Done! Opening final video..."
echo "═══════════════════════════════════════════"
open "$PROJECT_DIR/videos/"*_final.mp4
