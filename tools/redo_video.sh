#!/bin/bash
# Start a project's video over from scratch, keeping the brief.
#
# Usage:
#   ./tools/redo_video.sh GME        (or: just redo GME)
#
# The brief is the primary document: it is versioned on the CDN and its figures are
# verified, so a redo keeps reports/ and sources/ as they are. The video is not versioned
# anywhere but YouTube, so its local outputs move to .history/video-v{N}/ and the next
# session writes a new script and video copy from the brief (no short), against the current
# contract and slide kinds. It must NOT open the archived script: reading v1 pulls v2
# back toward it. The one thing v2 takes from v1 is LOVES-HATES.md, the notes on what
# to keep and what to fix, in the words they were given.
#
# A new upload writes a new videos/{T}_youtube.json, and `just sync-youtube T` then
# points the research page at it. v1 stays on YouTube until it is unlisted by hand.

set -euo pipefail

TICKER="${1:?Usage: $0 TICKER}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
P="${ROOT_DIR}/projects/${TICKER}"

[ -d "$P" ] || { echo "No project: $P"; exit 1; }
[ -f "$P/reports/${TICKER}_brief.md" ] || { echo "No brief at reports/${TICKER}_brief.md - a redo starts from the brief"; exit 1; }
if [ ! -f "$P/scripts/${TICKER}_script.json" ]; then
    if [ -f "$P/REDO.md" ]; then echo "A redo is already set up: see projects/$TICKER/REDO.md"
    else echo "No script to redo - author the first video with /author $TICKER"; fi
    exit 1
fi

N=1
while [ -d "$P/.history/video-v$N" ]; do N=$((N + 1)); done
HIST="$P/.history/video-v$N"
mkdir -p "$HIST/scripts" "$HIST/social"
echo "Redoing the $TICKER video - archiving v$N to .history/video-v$N/"

move() { [ -e "$1" ] && mv "$1" "$2" && echo "  archived $(basename "$1")" || true; }

move "$P/scripts/${TICKER}_script.json" "$HIST/scripts/"
move "$P/scripts/${TICKER}_short_script.json" "$HIST/scripts/"
for d in webdeck short_9x16 videos deck; do
    if [ -d "$P/$d" ] && [ -n "$(ls -A "$P/$d" 2>/dev/null)" ]; then
        mv "$P/$d" "$HIST/$d" && echo "  archived $d/"
    fi
    mkdir -p "$P/$d"
done
# Copied, not moved: publish.json also carries the brief's X comment, and the thumbnail in
# charts/ is the published brief's card image too. The session rewrites only the
# video-facing files and fields (see REDO.md).
cp -R "$P/social/." "$HIST/social/" 2>/dev/null || true
[ -d "$P/charts" ] && cp -R "$P/charts" "$HIST/charts"

# the redo is written against the current contract (slide kinds, cues, capacity limits)
cp "$ROOT_DIR/template/PRODUCTION_CONTRACT.md" "$P/PRODUCTION_CONTRACT.md"
if [ -f "$P/CAMPAIGN_BRIEF.md" ]; then
    echo "  campaign project: run /refresh $TICKER if its AUTHORING_INSTRUCTIONS.md has changed"
else
    cp "$ROOT_DIR/template/AUTHORING_INSTRUCTIONS.md" "$P/AUTHORING_INSTRUCTIONS.md"
fi

if [ ! -f "$P/LOVES-HATES.md" ]; then
    cat > "$P/LOVES-HATES.md" <<EOF
# ${TICKER} video - loves and hates

Every note on the video, in the words it was given, with what the next version does about
it. The redo reads this file and nothing else from the prior version. Add to it; never
rewrite a note.

## Loves (keep)

-

## Hates (fix)

-
EOF
    echo "  wrote LOVES-HATES.md - fill it in before the redo session starts"
fi

sed "s/{TICKER}/${TICKER}/g; s/{N}/${N}/g; s/{NEXT}/$((N + 1))/g" \
    "$SCRIPT_DIR/redo_template.md" > "$P/REDO.md"

echo ""
echo "Redo ready. v$N is in .history/video-v$N/; the brief and sources/ are untouched."
echo "Next steps:"
echo "  1. Write the notes on v$N into projects/$TICKER/LOVES-HATES.md"
echo "  2. /author $TICKER   (or: just kickoff $TICKER - the prompt carries REDO.md)"
echo "  3. just webdeck-pipeline $TICKER"
