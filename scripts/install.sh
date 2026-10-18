#!/usr/bin/env bash
# Install Python dependencies for enabled directory tools into per-tool venvs.
# Venvs live at .agentictools/tools/<id>/.venv (local, gitignored).
#
# Usage: [AGENTICTOOLS_HOME=/path] scripts/install.sh [target-dir]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTICTOOLS_HOME="${AGENTICTOOLS_HOME:-$(cd "$SCRIPT_DIR/.." && pwd)}"
export AGENTICTOOLS_HOME

TARGET="${1:-$PWD}"
ACTIVE="$TARGET/.agentictools/active.json"
PYTHON="${PYTHON:-python3}"

command -v jq >/dev/null 2>&1 || { echo "error: jq is required" >&2; exit 1; }
[ -f "$ACTIVE" ] || { echo "error: $ACTIVE not found; run scripts/sync.sh $TARGET first" >&2; exit 1; }
command -v "$PYTHON" >/dev/null 2>&1 || { echo "error: $PYTHON not found (set PYTHON=...)" >&2; exit 1; }

installed=0
while IFS= read -r id; do
  [ -n "$id" ] || continue
  dir="$TARGET/.agentictools/tools/$id"
  req="$dir/requirements.txt"
  [ -f "$req" ] || continue
  venv="$dir/.venv"
  if [ ! -x "$venv/bin/python" ]; then
    echo "creating venv: ${venv#"$TARGET"/}"
    "$PYTHON" -m venv "$venv"
  fi
  echo "installing dependencies for '$id'"
  "$venv/bin/python" -m pip install --upgrade pip >/dev/null
  "$venv/bin/python" -m pip install -r "$req"
  installed=$((installed + 1))
done < <(jq -r '.tools[]? // empty' "$ACTIVE")

if [ "$installed" -eq 0 ]; then
  echo "no directory tools with requirements.txt are enabled"
else
  echo "installed dependencies for $installed tool(s)"
fi
