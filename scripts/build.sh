#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-deb}"
if [[ $# -gt 0 ]]; then shift; fi
cd "$ROOT"

if [[ "$TARGET" == "exe" ]]; then
  echo "The Windows .exe target must be built on Windows; use scripts/build.ps1 there." >&2
  exit 2
fi

if [[ "$TARGET" == "flatpak" ]]; then
  python3 -m venv .venv-build
  . .venv-build/bin/activate
  python -m pip install --upgrade pip
  python -m pip install -r requirements-build.txt
fi

exec python3 scripts/build.py --target "$TARGET" "$@"
