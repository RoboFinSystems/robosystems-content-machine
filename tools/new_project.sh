#!/bin/bash
# Create a new company coverage project, optionally with a campaign overlay.
#
# Usage:
#   ./tools/new_project.sh NVDA                          # base template
#   ./tools/new_project.sh GTBIF cannabis_coverage        # campaign overlay
#   ./tools/new_project.sh GTBIF cannabis_coverage --recover   # re-cover (new quarter)
#
# Each project is a company-centric coverage file (named by ticker).
# Sources accumulate over time. Each video run produces outputs in the
# standard directories (reports/, scripts/, charts/, social/, videos/).
#
# RE-COVER LIFECYCLE (--recover, or `just recover TICKER [campaign]`):
# when the project already exists, archive the prior OUTPUTS to
# projects/{T}/.history/{prior-quarter}/, KEEP sources/ (they accumulate),
# refresh the campaign overlay, and distill a sources/_prior_coverage.md card
# so the next run is written as continuing coverage. S3 archiving happens
# separately at `just publish` (keyed on the same quarter); kickoff stays local.

set -euo pipefail

TICKER="${1:?Usage: $0 TICKER [CAMPAIGN] [--recover]}"
shift

RECOVER=0
CAMPAIGN=""
for arg in "$@"; do
    case "$arg" in
        --recover) RECOVER=1 ;;
        "") ;;                       # ignore empty (from `just recover TICKER`)
        *) CAMPAIGN="$arg" ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="${ROOT_DIR}/projects/${TICKER}"

# Validate campaign exists (if specified) — needed by both fresh + recover paths
CAMPAIGN_DIR=""
if [ -n "$CAMPAIGN" ]; then
    CAMPAIGN_DIR="${ROOT_DIR}/campaigns/${CAMPAIGN}"
    if [ ! -d "$CAMPAIGN_DIR" ]; then
        echo "Campaign not found: $CAMPAIGN_DIR"
        echo ""
        echo "Available campaigns:"
        ls -1 "${ROOT_DIR}/campaigns/" 2>/dev/null || echo "  (none)"
        exit 1
    fi
    if [ ! -f "$CAMPAIGN_DIR/AUTHORING_INSTRUCTIONS.md" ]; then
        echo "Campaign missing AUTHORING_INSTRUCTIONS.md: $CAMPAIGN_DIR"
        exit 1
    fi
fi

apply_campaign() {
    [ -n "$CAMPAIGN_DIR" ] || return 0
    cp "$CAMPAIGN_DIR/AUTHORING_INSTRUCTIONS.md" "$PROJECT_DIR/AUTHORING_INSTRUCTIONS.md"
    [ -f "$CAMPAIGN_DIR/CAMPAIGN_BRIEF.md" ] && cp "$CAMPAIGN_DIR/CAMPAIGN_BRIEF.md" "$PROJECT_DIR/CAMPAIGN_BRIEF.md"
    [ -d "$CAMPAIGN_DIR/overrides" ] && cp -r "$CAMPAIGN_DIR/overrides/." "$PROJECT_DIR/"
    if [ -d "$CAMPAIGN_DIR/sources" ]; then
        cp "$CAMPAIGN_DIR/sources/"* "$PROJECT_DIR/sources/" 2>/dev/null || true
    fi
}

# ── Existing project ───────────────────────────────────────────────────────
if [ -d "$PROJECT_DIR" ]; then
    if [ "$RECOVER" -ne 1 ]; then
        echo "Project already exists: $PROJECT_DIR"
        echo "To re-cover for a new quarter:  just recover $TICKER${CAMPAIGN:+ $CAMPAIGN}"
        echo "To start over:                  rm -rf '$PROJECT_DIR'"
        exit 1
    fi

    # --- RE-COVER: archive prior outputs, keep sources, emit continuing-coverage card ---
    PRIOR_VERSION="$(python3 -c "import os,datetime,sys
p=sys.argv[1]
d=datetime.date.fromtimestamp(os.path.getmtime(p)) if os.path.exists(p) else datetime.date.today()
print(f'{d.year}-Q{(d.month-1)//3+1}')" "$PROJECT_DIR/reports/${TICKER}_brief.md")"

    HIST="$PROJECT_DIR/.history/$PRIOR_VERSION"
    echo "Re-covering $TICKER — archiving prior outputs as $PRIOR_VERSION -> .history/$PRIOR_VERSION/"
    mkdir -p "$HIST"
    for d in reports scripts social deck videos charts; do
        if [ -d "$PROJECT_DIR/$d" ] && [ -n "$(ls -A "$PROJECT_DIR/$d" 2>/dev/null)" ]; then
            mkdir -p "$HIST/$d"
            mv "$PROJECT_DIR/$d/"* "$HIST/$d/" 2>/dev/null || true
        fi
    done

    # distill the "previously on..." card from the archived outputs (kickoff appends it)
    python3 "$ROOT_DIR/tools/prior_coverage.py" "$TICKER" ".history/$PRIOR_VERSION" "$PRIOR_VERSION" \
        || echo "  (prior-coverage card skipped)"

    apply_campaign
    [ -n "$CAMPAIGN_DIR" ] && echo "  Refreshed campaign overlay: $CAMPAIGN"

    # recreate empty output dirs for the new run (sources/ kept as-is, accumulating)
    mkdir -p "$PROJECT_DIR/reports" "$PROJECT_DIR/scripts" "$PROJECT_DIR/social" "$PROJECT_DIR/deck" "$PROJECT_DIR/videos"

    echo ""
    echo "Re-cover ready. Prior outputs in .history/$PRIOR_VERSION/; sources/ kept."
    echo "Next steps:"
    echo "  1. Drop the new quarter's filings/research into sources/"
    echo "  2. just kickoff $TICKER   (prompt now includes the prior-coverage card)"
    exit 0
fi

# ── Fresh project ──────────────────────────────────────────────────────────
# 1. Clone base template (folder structure + stage instructions + assets)
cp -r "${ROOT_DIR}/template" "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR/reports" "$PROJECT_DIR/scripts" "$PROJECT_DIR/social" "$PROJECT_DIR/videos" "$PROJECT_DIR/sources" "$PROJECT_DIR/deck"
rm -rf "$PROJECT_DIR/charts/png"

# 2. Apply campaign overlay (if specified)
if [ -n "$CAMPAIGN_DIR" ]; then
    apply_campaign
    SHARED_COUNT=$(ls -1 "$CAMPAIGN_DIR/sources/" 2>/dev/null | wc -l | tr -d ' ')
    [ -d "$CAMPAIGN_DIR/sources" ] && echo "  Shared sources: $SHARED_COUNT files copied"
    echo "Initiated coverage: $PROJECT_DIR"
    echo "  Campaign: $CAMPAIGN"
else
    echo "Created project: $PROJECT_DIR"
    echo "  Template: base"
fi

echo ""
echo "Folder structure:"
find "$PROJECT_DIR" -type d | sort | sed "s|$ROOT_DIR/||"
echo ""
echo "Next steps:"
echo "  1. /collect $TICKER   (or drop filings/transcripts into sources/)"
echo "  2. /author $TICKER    (one-shot authoring in Claude Code: brief + script + social + publish.json)"
echo "  3. /review $TICKER    (quality gate before spending render credits)"
echo "  4. just webdeck-pipeline $TICKER   (animated deck -> render -> mux)"
echo "  5. just thumbnails $TICKER   then   just publish $TICKER   ·   yt-upload / x-article / x-post"
echo "     (Legacy deck path, kept in parallel: just kickoff -> Claude Design deck -> just pipeline.)"
