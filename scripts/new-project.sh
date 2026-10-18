#!/usr/bin/env bash
# One-shot: bootstrap a project with agentictools redirect files and sync the
# modules enabled by its config.
#
# Usage: [AGENTICTOOLS_HOME=/path] scripts/new-project.sh [target-dir]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTICTOOLS_HOME="${AGENTICTOOLS_HOME:-$(cd "$SCRIPT_DIR/.." && pwd)}"
export AGENTICTOOLS_HOME

TARGET="${1:-$PWD}"

"$SCRIPT_DIR/bootstrap.sh" "$TARGET"
echo
"$SCRIPT_DIR/sync.sh" "$TARGET"
