#!/bin/bash
# Create a new company coverage project, optionally with a campaign overlay.
#
# Usage:
#   ./tools/new_project.sh NVDA                          # base template
#   ./tools/new_project.sh GTBIF cannabis_coverage        # campaign overlay
#
# Each project is a company-centric coverage file (named by ticker).
# Sources accumulate over time. Each video run produces outputs in the
# standard directories (reports/, scripts/, charts/, social/, videos/).
#
# Base template provides: folder structure, chart examples, slide templates, assets.
# Campaign overlay adds: COWORK_INSTRUCTIONS.md, CAMPAIGN_BRIEF.md, and any file
# overrides (e.g. custom INTRO_SLIDE.html) from campaigns/{name}/overrides/.

set -euo pipefail

TICKER="${1:?Usage: $0 TICKER [CAMPAIGN]}"
CAMPAIGN="${2:-}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

PROJECT_NAME="${TICKER}"
PROJECT_DIR="${ROOT_DIR}/projects/${PROJECT_NAME}"

if [ -d "$PROJECT_DIR" ]; then
    echo "Project already exists: $PROJECT_DIR"
    echo "To add sources or re-run, work directly in the project folder."
    echo "To start over: rm -rf '$PROJECT_DIR'"
    exit 1
fi

# Validate campaign exists (if specified)
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
    if [ ! -f "$CAMPAIGN_DIR/COWORK_INSTRUCTIONS.md" ]; then
        echo "Campaign missing COWORK_INSTRUCTIONS.md: $CAMPAIGN_DIR"
        exit 1
    fi
fi

# 1. Clone base template (folder structure + chart examples + assets)
cp -r "${ROOT_DIR}/template" "$PROJECT_DIR"

# Ensure standard output directories exist
mkdir -p "$PROJECT_DIR/reports" "$PROJECT_DIR/scripts" "$PROJECT_DIR/social" "$PROJECT_DIR/videos" "$PROJECT_DIR/sources"

# Remove generated output directory (will be recreated by pipeline)
rm -rf "$PROJECT_DIR/charts/png"

# 2. Apply campaign overlay (if specified)
if [ -n "$CAMPAIGN_DIR" ]; then
    cp "$CAMPAIGN_DIR/COWORK_INSTRUCTIONS.md" "$PROJECT_DIR/COWORK_INSTRUCTIONS.md"

    if [ -f "$CAMPAIGN_DIR/CAMPAIGN_BRIEF.md" ]; then
        cp "$CAMPAIGN_DIR/CAMPAIGN_BRIEF.md" "$PROJECT_DIR/CAMPAIGN_BRIEF.md"
    fi

    if [ -d "$CAMPAIGN_DIR/overrides" ]; then
        cp -r "$CAMPAIGN_DIR/overrides/." "$PROJECT_DIR/"
    fi

    # Copy campaign-level shared sources (comps tables, sector data, etc.)
    if [ -d "$CAMPAIGN_DIR/sources" ]; then
        cp "$CAMPAIGN_DIR/sources/"* "$PROJECT_DIR/sources/" 2>/dev/null || true
        SHARED_COUNT=$(ls -1 "$CAMPAIGN_DIR/sources/" 2>/dev/null | wc -l | tr -d ' ')
        echo "  Shared sources: $SHARED_COUNT files copied"
    fi

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
echo "  1. Collect sources:  /collect $TICKER"
echo "  2. Add earnings transcript to sources/ (manual)"
echo "  3. Point Claude Desktop Cowork at: $PROJECT_DIR"
echo "  4. Tell it: Analyze $TICKER"
echo "  5. Run the pipeline: just pipeline $TICKER"
