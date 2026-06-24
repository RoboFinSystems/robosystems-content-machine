#!/usr/bin/env bash
#
# Scaffold a new blog post: blog/<slug>/post.md from template/blog/post.md.
# A post is just one markdown file (frontmatter + body); narration / cover / social copy
# are all optional and added later.
#
# Usage:
#   ./tools/new_blog.sh financial-knowledge-graph-manifesto
set -euo pipefail

SLUG="${1:?Usage: $0 <slug>   (kebab-case, e.g. my-post-title)}"
if ! printf '%s' "$SLUG" | grep -Eq '^[a-z0-9]+(-[a-z0-9]+)*$'; then
  echo "Error: slug must be kebab-case (lowercase a-z, 0-9, hyphens): got '$SLUG'" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DST="$ROOT_DIR/blog/$SLUG"
TEMPLATE="$ROOT_DIR/template/blog/post.md"

if [ -e "$DST" ]; then
  echo "Error: blog/$SLUG already exists." >&2
  exit 1
fi

mkdir -p "$DST"
TODAY="$(date +%Y-%m-%d)"
sed -e "s/{{SLUG}}/$SLUG/g" -e "s/{{DATE}}/$TODAY/g" "$TEMPLATE" > "$DST/post.md"

echo "Created blog/$SLUG/post.md"
echo ""
echo "Next:"
echo "  1. Edit blog/$SLUG/post.md (frontmatter + body)"
echo "  2. (optional) just blog-narrate $SLUG   # ElevenLabs audio narration"
echo "  3. (optional) drop a cover.png + ${SLUG}_x_post.txt in blog/$SLUG/"
echo "  4. just blog-publish $SLUG              # upload to S3 + refresh blog/index.json"
