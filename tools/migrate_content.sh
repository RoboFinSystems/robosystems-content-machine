#!/usr/bin/env bash
#
# One-time migration: copy published content from the legacy bucket into the new
# content bucket (AWS_S3_BUCKET). Run AFTER `just infra-deploy` has created the new bucket.
# The legacy bucket is only read from — never modified or deleted.
#
# Usage:
#   just content-migrate                         # from robosystems-marketing-assets
#   just content-migrate other-legacy-bucket     # from a different source
#
# After this, run `just reindex` to regenerate content/index.json on the new bucket with
# CDN URLs (AWS_CDN_DOMAIN_URL), then cut consumers over to the CDN domain.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

SRC="${1:-robosystems-marketing-assets}"
DST="${AWS_S3_BUCKET:?set AWS_S3_BUCKET in .env}"

if [ "$SRC" = "$DST" ]; then
  echo "Error: source and destination bucket are both '$SRC'. Set AWS_S3_BUCKET to the new bucket." >&2
  exit 1
fi

AWS=(aws)
[ -n "${AWS_PROFILE:-}" ] && AWS+=(--profile "$AWS_PROFILE")

echo "Syncing s3://$SRC/content/  ->  s3://$DST/content/"
echo "(legacy bucket is read-only; nothing is deleted)"
# No --delete: purely additive. Re-runnable.
"${AWS[@]}" s3 sync "s3://$SRC/content/" "s3://$DST/content/" --only-show-errors
echo ""
echo "Done. Next: 'just reindex' (regenerates content/index.json with CDN URLs)."
