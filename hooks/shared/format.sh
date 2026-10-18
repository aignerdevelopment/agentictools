#!/usr/bin/env sh
# Shared formatter hook.
# Called after an edit by any agent adapter.
# Contract: $1 = path to the edited file (may be empty).
set -eu

file="${1:-${CLAUDE_FILE_PATHS:-${AGENTICTOOLS_EDITED_FILE:-}}}"

[ -n "$file" ] || exit 0
[ -f "$file" ] || exit 0

case "$file" in
  *.js|*.jsx|*.ts|*.tsx|*.json|*.css|*.md)
    if command -v prettier >/dev/null 2>&1; then
      prettier --write "$file" >/dev/null 2>&1 || true
    fi
    ;;
  *.py)
    if command -v ruff >/dev/null 2>&1; then
      ruff format "$file" >/dev/null 2>&1 || true
    fi
    ;;
  *.go)
    if command -v gofmt >/dev/null 2>&1; then
      gofmt -w "$file" >/dev/null 2>&1 || true
    fi
    ;;
esac

exit 0
