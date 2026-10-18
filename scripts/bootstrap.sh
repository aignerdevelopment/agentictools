#!/usr/bin/env bash
# Copy the agentictools redirect templates into a project root.
# Usage: AGENTICTOOLS_HOME=/path/to/agentictools scripts/bootstrap.sh [target-dir]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTICTOOLS_HOME="${AGENTICTOOLS_HOME:-$(cd "$SCRIPT_DIR/.." && pwd)}"
export AGENTICTOOLS_HOME

TARGET="${1:-$PWD}"
TEMPLATES="$AGENTICTOOLS_HOME/templates/project"

[ -d "$TEMPLATES" ] || { echo "error: templates not found at $TEMPLATES" >&2; exit 1; }
[ -d "$AGENTICTOOLS_HOME" ] || { echo "error: invalid AGENTICTOOLS_HOME: $AGENTICTOOLS_HOME" >&2; exit 1; }

echo "agentictools home : $AGENTICTOOLS_HOME"
echo "target project    : $TARGET"
mkdir -p "$TARGET"

while IFS= read -r -d '' src; do
  rel="${src#"$TEMPLATES"/}"
  dest="$TARGET/$rel"
  if [ -e "$dest" ] || [ -L "$dest" ]; then
    echo "skip (exists): $rel"
    continue
  fi
  mkdir -p "$(dirname "$dest")"
  # Substitute the central home placeholder. '#' as sed delimiter (paths have '/').
  sed "s#{{AGENTICTOOLS_HOME}}#$AGENTICTOOLS_HOME#g" "$src" > "$dest"
  echo "created: $rel"
done < <(find "$TEMPLATES" -type f -print0)

echo
echo "next:"
echo "  1. edit $TARGET/agentictools.config.json (profile + modules)"
echo "  2. AGENTICTOOLS_HOME=$AGENTICTOOLS_HOME $AGENTICTOOLS_HOME/scripts/sync.sh $TARGET"
