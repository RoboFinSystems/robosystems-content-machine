#!/bin/bash
# Print the cold-start authoring prompt for a project — {TICKER} resolved to the real
# ticker — and copy it to the clipboard (macOS pbcopy). `/author TICKER` covers the same
# ground in-session; this is for driving a run by hand or handing it to a second session.
#
# Reads projects/{PROJECT}/KICKOFF.md (falls back to template/KICKOFF.md) and appends
# the prior-coverage card (sources/_prior_coverage.md) when one exists, or REDO.md when
# `just redo` has set the project up to remake its video. stdout stays the
# clean prompt; the clipboard confirmation goes to stderr so pipes/redirects are unaffected.
#
# Usage:
#   ./tools/kickoff.sh MRMD

set -euo pipefail

PROJECT="${1:?Usage: $0 PROJECT_NAME}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

SRC="${ROOT_DIR}/projects/${PROJECT}/KICKOFF.md"
[ -f "$SRC" ] || SRC="${ROOT_DIR}/template/KICKOFF.md"

OUT="$(sed "s/{TICKER}/${PROJECT}/g" "$SRC")"

PRIOR="${ROOT_DIR}/projects/${PROJECT}/sources/_prior_coverage.md"
REDO="${ROOT_DIR}/projects/${PROJECT}/REDO.md"
if [ -f "$REDO" ]; then
    # a redo remakes the video only; the brief and its coverage thread are already done
    OUT="$OUT"$'\n\n---\n\n'"$(cat "$REDO")"
elif [ -f "$PRIOR" ]; then
    # the card itself is NOT appended: the brief is drafted from the current filing first
    OUT="$OUT"$'\n\n---\n\n'"Prior coverage exists (sources/_prior_coverage.md). Draft the brief from the current filing first; open the card only afterwards, per \"Prior coverage\" in AUTHORING_INSTRUCTIONS.md."
fi

printf '%s\n' "$OUT"

if command -v pbcopy >/dev/null 2>&1; then
    printf '%s' "$OUT" | pbcopy
    printf '\n\033[32m✓ Copied to clipboard (%s chars).\033[0m\n' "${#OUT}" >&2
fi
