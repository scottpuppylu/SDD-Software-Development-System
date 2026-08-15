#!/usr/bin/env bash
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)/skills/sdd-system"
DEST="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}/skills/sdd-system"
mkdir -p "$(dirname "$DEST")"
rm -rf "$DEST"
cp -R "$SRC" "$DEST"
echo "Installed sdd-system skill to: $DEST"
echo "Run: openclaw skills list"
echo "If needed, restart/new session so OpenClaw reloads the skill."
