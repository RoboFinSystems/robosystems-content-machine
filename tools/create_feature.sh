#!/usr/bin/env bash
#
# Create a branch the safe way: from origin/<base>, with its own upstream, pushed at once,
# so a later plain `git push` can never land on main. Uncommitted work is carried across.
#
# Usage:
#   ./tools/create_feature.sh feature brand-film          # feature/brand-film from origin/main
#   ./tools/create_feature.sh bugfix publish-exit-codes main
set -euo pipefail

TYPE="${1:-feature}"
NAME="${2:-}"
BASE="${3:-main}"

case "$TYPE" in
  feature | bugfix | hotfix | chore | refactor) ;;
  *)
    echo "Invalid branch type: $TYPE (feature, bugfix, hotfix, chore, refactor)" >&2
    exit 1
    ;;
esac
if [ -z "$NAME" ]; then
  echo "Usage: $0 <type> <name> [base]   e.g. $0 feature brand-film" >&2
  exit 1
fi

NAME=$(echo "$NAME" | sed 's/[^a-zA-Z0-9._-]/-/g; s/--*/-/g; s/^-//; s/-$//')
BRANCH="$TYPE/$NAME"

git fetch origin
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  echo "Branch $BRANCH already exists locally" >&2
  exit 1
fi
if git show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
  echo "Branch $BRANCH already exists on the remote (git switch $BRANCH to check it out)" >&2
  exit 1
fi
if ! git show-ref --verify --quiet "refs/remotes/origin/$BASE"; then
  echo "Base branch $BASE does not exist on the remote" >&2
  exit 1
fi

STASHED=no
if ! git diff --quiet || ! git diff --cached --quiet; then
  git stash push -m "create_feature: $BRANCH"
  STASHED=yes
fi

git checkout -b "$BRANCH" "origin/$BASE"
git push -u origin "$BRANCH"

if [ "$STASHED" = yes ]; then
  git stash pop
fi
echo "On $BRANCH (from origin/$BASE, upstream set). Commit, git push, then open a PR."
