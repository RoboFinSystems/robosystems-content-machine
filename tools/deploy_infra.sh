#!/usr/bin/env bash
#
# Deploy the content infrastructure stack (S3 bucket + CloudFront CDN) LOCALLY.
# Mirrors the platform repo's `just bootstrap` pattern (bin/setup/bootstrap.sh): idempotent
# create-or-update + wait. No GitHub Actions.
#
# Usage (via justfile):
#   just infra-validate     # validate the template
#   just infra-deploy       # create or update the stack
#   just infra-outputs      # print stack outputs
#
# Config is read from .env: AWS_PROFILE, AWS_S3_BUCKET, AWS_CDN_DOMAIN_URL (optional).
# AWS_ROUTE53_HOSTED_ZONE_ID is optional — auto-resolved from the CDN domain; set only to override.
#
# This CREATES a NEW bucket ($AWS_S3_BUCKET, default robosystems-content) — a plain
# create-stack, no import dance. The legacy robosystems-marketing-assets bucket is left
# untouched; copy its content into the new bucket once with `just content-migrate`, then
# cut consumers over to the CDN domain.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Load .env (AWS_PROFILE / AWS_S3_BUCKET / domain vars)
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

STACK_NAME="${CONTENT_STACK_NAME:-RoboSystemsContent}" # platform PascalCase stack convention
TEMPLATE="cloudformation/content.yaml"
REGION="us-east-1" # CloudFront ACM certs must live in us-east-1
BUCKET="${AWS_S3_BUCKET:?set AWS_S3_BUCKET in .env}"

# Custom domain is optional; derive the bare host from AWS_CDN_DOMAIN_URL.
DOMAIN="${AWS_CDN_DOMAIN_URL:-}"
DOMAIN="${DOMAIN#https://}"
DOMAIN="${DOMAIN#http://}"
DOMAIN="${DOMAIN%/}"
HOSTED_ZONE="${AWS_ROUTE53_HOSTED_ZONE_ID:-}"

AWS=(aws)
[ -n "${AWS_PROFILE:-}" ] && AWS+=(--profile "$AWS_PROFILE")

# Find the public Route53 hosted zone that hosts $1: the longest zone name that is a
# dot-boundary suffix of the domain (so assets.robosystems.ai -> the robosystems.ai zone,
# correctly handling multi-part TLDs and any delegated subdomain zone). Route53 is global.
resolve_hosted_zone() {
  "${AWS[@]}" route53 list-hosted-zones --output json | python3 -c '
import json, sys
domain = sys.argv[1].rstrip(".")
best = ("", "")
for z in json.load(sys.stdin)["HostedZones"]:
    if z["Config"].get("PrivateZone"):
        continue
    name = z["Name"].rstrip(".")
    if (domain == name or domain.endswith("." + name)) and len(name) > len(best[0]):
        best = (name, z["Id"].split("/")[-1])
print(best[1])
' "$1"
}

# Auto-resolve the hosted zone from the CDN domain unless it is pinned in .env.
if [ -n "$DOMAIN" ] && [ -z "$HOSTED_ZONE" ]; then
  HOSTED_ZONE="$(resolve_hosted_zone "$DOMAIN")"
  if [ -z "$HOSTED_ZONE" ]; then
    echo "Error: no public Route53 hosted zone found for $DOMAIN." >&2
    echo "       Confirm the zone exists, or pin AWS_ROUTE53_HOSTED_ZONE_ID in .env." >&2
    exit 1
  fi
  echo "Resolved hosted zone for $DOMAIN -> $HOSTED_ZONE"
fi

PARAMS=(
  "ParameterKey=BucketName,ParameterValue=$BUCKET"
  "ParameterKey=DomainName,ParameterValue=$DOMAIN"
  "ParameterKey=HostedZoneId,ParameterValue=$HOSTED_ZONE"
)

validate() {
  "${AWS[@]}" cloudformation validate-template --template-body "file://$TEMPLATE" >/dev/null
  echo "✓ template valid"
}

outputs() {
  "${AWS[@]}" cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" \
    --query "Stacks[0].Outputs[*].[OutputKey,OutputValue]" --output table
}

stack_exists() {
  "${AWS[@]}" cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" >/dev/null 2>&1
}

deploy() {
  validate
  if stack_exists; then
    echo "Updating stack $STACK_NAME ..."
    if "${AWS[@]}" cloudformation update-stack --stack-name "$STACK_NAME" \
        --template-body "file://$TEMPLATE" --region "$REGION" \
        --parameters "${PARAMS[@]}" --capabilities CAPABILITY_NAMED_IAM 2>/tmp/cfn_err.txt; then
      "${AWS[@]}" cloudformation wait stack-update-complete --stack-name "$STACK_NAME" --region "$REGION"
    elif grep -q "No updates are to be performed" /tmp/cfn_err.txt; then
      echo "  No changes."
    else
      cat /tmp/cfn_err.txt >&2
      exit 1
    fi
  else
    # A brand-new bucket name should not already exist. If it does, it's a global name
    # collision (someone else owns it) or a stray leftover — not something to clobber.
    if "${AWS[@]}" s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
      echo "Bucket '$BUCKET' already exists but stack '$STACK_NAME' does not." >&2
      echo "Pick a different AWS_S3_BUCKET (S3 names are global), or remove the stray bucket." >&2
      exit 1
    fi
    echo "Creating stack $STACK_NAME ..."
    "${AWS[@]}" cloudformation create-stack --stack-name "$STACK_NAME" \
      --template-body "file://$TEMPLATE" --region "$REGION" \
      --parameters "${PARAMS[@]}" --capabilities CAPABILITY_NAMED_IAM
    "${AWS[@]}" cloudformation wait stack-create-complete --stack-name "$STACK_NAME" --region "$REGION"
  fi
  echo ""
  echo "Stack $STACK_NAME outputs:"
  outputs
}

case "${1:-deploy}" in
  validate) validate ;;
  outputs) outputs ;;
  deploy) deploy ;;
  *) echo "Usage: $0 [deploy|validate|outputs]" >&2; exit 2 ;;
esac
