#!/bin/bash
# Create a new project from the base template, optionally with a campaign overlay.
#
# Usage:
#   ./tools/new_project.sh NVDA "10-K" "2025"                      # base template
#   ./tools/new_project.sh GTBIF "10-K" "2025" cannabis_coverage    # campaign overlay
#
# Base template provides: folder structure, chart examples, slide templates, assets.
# Campaign overlay adds: COWORK_INSTRUCTIONS.md, CAMPAIGN_BRIEF.md, and any file
# overrides (e.g. custom INTRO_SLIDE.html) from campaigns/{name}/overrides/.

set -euo pipefail

TICKER="${1:?Usage: $0 TICKER FILING_TYPE YEAR [CAMPAIGN]}"
FILING="${2:-10-K}"
YEAR="${3:-2025}"
CAMPAIGN="${4:-}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Sanitize names
SAFE_FILING=$(echo "$FILING" | tr '-' '_')
PROJECT_NAME="${TICKER}_${YEAR}_${SAFE_FILING}"
PROJECT_DIR="${ROOT_DIR}/projects/${PROJECT_NAME}"

if [ -d "$PROJECT_DIR" ]; then
    echo "Project already exists: $PROJECT_DIR"
    echo "Delete it first if you want to start over:"
    echo "  rm -rf '$PROJECT_DIR'"
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
mkdir -p "$PROJECT_DIR/reports" "$PROJECT_DIR/scripts" "$PROJECT_DIR/social" "$PROJECT_DIR/videos"

# Remove generated output directory (will be recreated by pipeline)
rm -rf "$PROJECT_DIR/charts/png"

# 2. Apply campaign overlay (if specified)
if [ -n "$CAMPAIGN_DIR" ]; then
    # Override COWORK_INSTRUCTIONS with campaign-specific prompt
    cp "$CAMPAIGN_DIR/COWORK_INSTRUCTIONS.md" "$PROJECT_DIR/COWORK_INSTRUCTIONS.md"

    # Copy campaign brief (macro thesis context for Claude)
    if [ -f "$CAMPAIGN_DIR/CAMPAIGN_BRIEF.md" ]; then
        cp "$CAMPAIGN_DIR/CAMPAIGN_BRIEF.md" "$PROJECT_DIR/CAMPAIGN_BRIEF.md"
    fi

    # Apply file overrides (e.g. custom INTRO_SLIDE.html, OUTRO_SLIDE.html)
    if [ -d "$CAMPAIGN_DIR/overrides" ]; then
        cp -r "$CAMPAIGN_DIR/overrides/." "$PROJECT_DIR/"
    fi

    echo "Created project: $PROJECT_DIR"
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
echo "  1. Open Claude Desktop"
echo "  2. Start a Cowork task pointed at: $PROJECT_DIR"
echo "  3. Tell it: Analyze $TICKER ($FILING, FY$YEAR)"
echo "  4. Once Cowork finishes, run the production pipeline:"
echo "     just pipeline $PROJECT_NAME"
