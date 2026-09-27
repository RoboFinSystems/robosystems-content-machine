#!/bin/bash
# Vendor the landing-demo motion runtime from @robosystems/core into motion/runtime.js.
#
# The runtime (easings, blurIn, rise, push, swap, steps, mount) is written once, in
# robosystems-core/demos/runtime.ts, and every surface that animates runs that one file:
# roboledger-app and roboinvestor-app commit a copy at public/demos/runtime.js, and this
# repo commits one at motion/runtime.js, inlined into the research deck and imported by
# the renderer. The pinned version lives in motion/runtime.version.
#
# Usage:
#   ./tools/motion_sync.sh            # re-vendor the pinned version
#   ./tools/motion_sync.sh 0.13.0     # move the pin, then vendor
#   ./tools/motion_sync.sh --check    # exit 1 if motion/runtime.js differs from the pin

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PIN="$ROOT_DIR/motion/runtime.version"
DEST="$ROOT_DIR/motion/runtime.js"

CHECK=0
case "${1:-}" in
    --check) CHECK=1 ;;
    "") ;;
    *) echo "$1" > "$PIN" ;;
esac
VERSION="$(tr -d '[:space:]' < "$PIN")"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
(cd "$TMP" && npm pack "@robosystems/core@$VERSION" --silent >/dev/null && tar xzf ./*.tgz package/demos/runtime.js)

if [ "$CHECK" -eq 1 ]; then
    if cmp -s "$TMP/package/demos/runtime.js" "$DEST"; then
        echo "motion/runtime.js matches @robosystems/core@$VERSION"
    else
        echo "motion/runtime.js has drifted from @robosystems/core@$VERSION - run just motion-sync"
        exit 1
    fi
else
    cp "$TMP/package/demos/runtime.js" "$DEST"
    echo "motion/runtime.js <- @robosystems/core@$VERSION"
fi
