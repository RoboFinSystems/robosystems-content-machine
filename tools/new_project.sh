#!/bin/bash
# Create a new project from the template.
#
# Usage:
#   ./tools/new_project.sh JPM "10-K" "2025"
#   ./tools/new_project.sh NVDA "10-K" "2025"
#
# This clones the template folder into projects/{TICKER}_{YEAR}_{FILING}/
# Then point Claude Desktop Cowork at that folder.

set -euo pipefail

TICKER="${1:?Usage: $0 TICKER FILING_TYPE YEAR}"
FILING="${2:-10-K}"
YEAR="${3:-2025}"

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

# Clone template
cp -r "${ROOT_DIR}/template" "$PROJECT_DIR"

# Remove generated output directory (will be recreated by pipeline)
rm -rf "$PROJECT_DIR/charts/png"

echo "Created project: $PROJECT_DIR"
echo ""
echo "Folder structure:"
find "$PROJECT_DIR" -type d | sort | sed "s|$ROOT_DIR/||"
echo ""
echo "Next steps:"
echo "  1. Open Claude Desktop"
echo "  2. Start a Cowork task pointed at: $PROJECT_DIR"
echo "  3. Tell it: Analyze $TICKER ($FILING, FY$YEAR)"
echo "  4. Once Cowork finishes, run the production pipeline:"
echo "     ./tools/run_pipeline.sh $PROJECT_NAME"
