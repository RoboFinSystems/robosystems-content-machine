#!/bin/bash
# Start a showcase episode over from scratch.
#
# Usage:
#   ./tools/demo_redo.sh driftline_runway        (or: just demo-redo driftline_runway)
#
# The showcase twin of redo_video.sh. An episode's renders, audio, walkthrough specs and
# outline move to showcase/<episode>/.history/v{N}/, and the next session writes a new
# outline and specs against the current frame (template/SHOWCASE_OUTLINE.md), templates and
# motion rules. It must NOT open the archive: the one thing v{N+1} takes from v{N} is
# LOVES-HATES.md, the notes on what to keep and what to fix, in the words they were given.

set -euo pipefail

EP="${1:?Usage: $0 EPISODE (a folder under showcase/)}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
P="${ROOT_DIR}/showcase/${EP}"

[ -d "$P" ] || { echo "No episode: $P"; exit 1; }

N=1
while [ -d "$P/.history/v$N" ]; do N=$((N + 1)); done
HIST="$P/.history/v$N"
mkdir -p "$HIST"
echo "Redoing showcase/$EP - archiving v$N to .history/v$N/"

move() { [ -e "$1" ] && mv "$1" "$2" && echo "  archived $(basename "$1")" || true; }

for d in renders audio captures; do
    if [ -d "$P/$d" ] && [ -n "$(ls -A "$P/$d" 2>/dev/null)" ]; then
        mv "$P/$d" "$HIST/$d" && echo "  archived $d/"
    fi
    mkdir -p "$P/$d"
done
shopt -s nullglob
for f in "$P"/*.json "$P"/OUTLINE.md "$P"/REDO.md; do move "$f" "$HIST/"; done
if [ -f "$HIST/REDO.md" ] && ! head -1 "$HIST/REDO.md" | grep -q "^# Redo: "; then
    echo "  ! the old REDO.md was hand-written notes: carry its lasting lessons into LOVES-HATES.md"
    echo "    (episode notes) or showcase/mcp_series/recording.md (shooting lessons) before the session"
fi

if [ ! -f "$P/LOVES-HATES.md" ]; then
    cat > "$P/LOVES-HATES.md" <<EOF
# ${EP} - loves and hates

Every note on the episode, in the words it was given, with what the next version does about
it. The redo reads this file and nothing else from the prior version. Add to it; never
rewrite a note.

## Loves (keep)

-

## Hates (fix)

-
EOF
    echo "  wrote LOVES-HATES.md - fill it in before the redo session starts"
fi

sed "s/{EPISODE}/${EP}/g; s/{N}/${N}/g; s/{NEXT}/$((N + 1))/g" \
    "$SCRIPT_DIR/demo_redo_template.md" > "$P/REDO.md"
sed "s/{EPISODE}/${EP}/g" "$ROOT_DIR/template/SHOWCASE_OUTLINE.md" > "$P/OUTLINE.md"

echo ""
echo "Redo ready. v$N is in .history/v$N/."
echo "Next steps:"
echo "  1. Write the notes on v$N into showcase/$EP/LOVES-HATES.md"
echo "  2. Fill showcase/$EP/OUTLINE.md (REDO.md says how) and get the words approved"
echo "  3. just demo-pipeline <spec> <config>"
