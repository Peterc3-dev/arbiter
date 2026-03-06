#!/usr/bin/env bash
# Launch Arbiter TUI
# Usage: ./run.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Install deps if needed
if ! python3 -c "import textual" 2>/dev/null; then
    echo "[arbiter] Installing dependencies..."
    pip install textual rich --break-system-packages -q
fi

python3 -m arbiter_core.app
