#!/bin/bash
# Extract podcast audio (MP3) from a project's final video (the long-form narration track).
# For the two-voice Q&A podcast see tools/generate_podcast_qa.py (just podcast-qa).
#
# Usage:
#   ./tools/extract_podcast.sh GTBIF

set -euo pipefail

PROJECT="${1:?Usage: $0 PROJECT_NAME}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="${ROOT_DIR}/projects/${PROJECT}"

VIDEO=$(ls "$PROJECT_DIR/videos/"*_final.mp4 2>/dev/null | head -1) || true
if [ -z "$VIDEO" ]; then
    echo "No final video found. Run the pipeline first."
    exit 1
fi

OUTPUT="${PROJECT_DIR}/videos/${PROJECT}_podcast.mp3"
echo "Extracting audio: $VIDEO → $OUTPUT"
ffmpeg -i "$VIDEO" -vn -acodec libmp3lame -q:a 2 -y "$OUTPUT" 2>/dev/null

DURATION=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$OUTPUT" | cut -d. -f1)
MINS=$((DURATION / 60))
SECS=$((DURATION % 60))
SIZE=$(du -h "$OUTPUT" | cut -f1)
echo "Done: $OUTPUT ($SIZE, ${MINS}m${SECS}s)"
