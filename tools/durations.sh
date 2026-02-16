#!/bin/bash
# Show media durations for a project via ffprobe.
#
# Usage:
#   ./tools/durations.sh JPM_2025_10_K

set -euo pipefail

PROJECT="${1:?Usage: $0 PROJECT_NAME}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="${ROOT_DIR}/projects/${PROJECT}"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "Error: Project not found at $PROJECT_DIR"
    exit 1
fi

echo "Videos:"
for f in "$PROJECT_DIR/videos/"*.mp4; do
    [ -f "$f" ] && printf "  %-40s %s\n" "$(basename "$f")" "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")s"
done

echo "Audio:"
for f in "$PROJECT_DIR/videos/audio/"*.mp3; do
    [ -f "$f" ] && printf "  %-40s %s\n" "$(basename "$f")" "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")s"
done
