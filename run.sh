#!/usr/bin/env bash
# Launch Arbiter TUI
# Usage: ./run.sh
#
# Creates a project-local virtualenv (.venv) on first run and installs the
# package into it. Avoids touching the system Python.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="${ARBITER_VENV:-$SCRIPT_DIR/.venv}"

if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "[arbiter-os] Creating virtualenv at $VENV_DIR ..."
    python3 -m venv "$VENV_DIR"
fi

# Install (or update) the package into the venv if textual is missing.
if ! "$VENV_DIR/bin/python" -c "import textual" 2>/dev/null; then
    echo "[arbiter-os] Installing dependencies..."
    "$VENV_DIR/bin/pip" install -q -e .
fi

exec "$VENV_DIR/bin/python" -m arbiter_core.app
