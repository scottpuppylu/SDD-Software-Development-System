#!/usr/bin/env bash
set -euo pipefail
if [[ $# -lt 1 ]]; then
  echo "Usage: $0 /path/to/project"
  exit 2
fi
SOURCE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="$(cd "$1" 2>/dev/null && pwd || true)"
if [[ -z "$TARGET" ]]; then
  mkdir -p "$1"
  TARGET="$(cd "$1" && pwd)"
fi
if [[ -e "$TARGET/.sdd" ]]; then
  echo "Refusing to overwrite existing $TARGET/.sdd"
  exit 3
fi
cp -R "$SOURCE_ROOT/.sdd" "$TARGET/.sdd"
mkdir -p "$TARGET/docs/handoff" "$TARGET/docs/decisions" "$TARGET/src" "$TARGET/tests"
if [[ ! -d "$TARGET/.git" ]]; then
  git -C "$TARGET" init >/dev/null
fi
echo "Initialized SDD runtime in: $TARGET"
echo "Next: commit the initialized repository inputs, install this package, then run:"
echo "  sdd --repo \"$TARGET\" authority-state-bootstrap"
echo "The bootstrap requires a clean Git worktree and never infers substantive authority."
