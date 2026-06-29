#!/bin/bash
# Print the Cowork cold-start prompt for a project — {TICKER} resolved to the real
# ticker — and copy it to the clipboard (macOS pbcopy) ready to paste into Cowork.
#
# Reads projects/{PROJECT}/KICKOFF.md (falls back to template/KICKOFF.md) and appends
# the prior-coverage card (sources/_prior_coverage.md) when one exists. stdout stays the
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
if [ -f "$PRIOR" ]; then
    OUT="$OUT"$'\n\n---\n\n'"$(cat "$PRIOR")"
fi

printf '%s\n' "$OUT"

if command -v pbcopy >/dev/null 2>&1; then
    printf '%s' "$OUT" | pbcopy
    printf '\n\033[32m✓ Copied to clipboard (%s chars) — paste into Cowork.\033[0m\n' "${#OUT}" >&2
fi
