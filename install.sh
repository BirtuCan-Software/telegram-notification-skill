#!/usr/bin/env bash
# ==============================================================================
# Script: install.sh
# Purpose: Installs the telegram-notification skill globally or to a project repository.
# Usage:
#   ./install.sh --global [--link]
#   ./install.sh --project [path] [--agent agentskills|antigravity|cursor|claude] [--pin 1.0.0]
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN=""

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "❌ Error: Python 3.8+ is required to execute skill-manager." >&2
  exit 1
fi

exec "$PYTHON_BIN" "$SCRIPT_DIR/bin/skill-manager.py" install "$@"
