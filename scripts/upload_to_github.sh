#!/usr/bin/env bash
set -euo pipefail
REPO_URL='https://github.com/Brentph505/snake-game.git'
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

command -v git >/dev/null 2>&1 || { echo 'Git is not installed.' >&2; exit 1; }

if [[ ! -d .git ]]; then
  git init --initial-branch=main
fi
if [[ "$(git branch --show-current)" != main ]]; then
  git branch -M main
fi

if git remote get-url origin >/dev/null 2>&1; then
  current_url="$(git remote get-url origin)"
  [[ "$current_url" == "$REPO_URL" ]] || {
    echo "origin points to '$current_url', not '$REPO_URL'. Refusing to push to the wrong repository." >&2
    exit 1
  }
else
  git remote add origin "$REPO_URL"
fi

git add -A
if ! git rev-parse --verify HEAD >/dev/null 2>&1 || ! git diff --cached --quiet; then
  if ! git config user.name >/dev/null || ! git config user.email >/dev/null; then
    echo 'Configure git user.name and user.email first, then rerun.' >&2
    exit 1
  fi
  if git rev-parse --verify HEAD >/dev/null 2>&1; then
    git commit -m 'Update cleaned Repair Terminal project'
  else
    git commit -m 'Import cleaned Repair Terminal project'
  fi
else
  echo 'No changes to commit; uploading the current main branch.'
fi

git push -u origin main
echo 'Upload complete: https://github.com/Brentph505/snake-game'
