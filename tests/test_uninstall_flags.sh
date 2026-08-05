#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_HOME="$(mktemp -d)"
trap 'rm -rf "$TMP_HOME"' EXIT

HERMES_HOME="$TMP_HOME/.hermes"
DEST="$HERMES_HOME/skills/humanize-korean"
SRC="$ROOT/hermes/skills/humanize-korean"
mkdir -p "$(dirname "$DEST")"
ln -s "$SRC" "$DEST"

run_uninstaller() {
  HOME="$TMP_HOME" \
  CLAUDE_HOME="$TMP_HOME/.claude" \
  CODEX_HOME="$TMP_HOME/.codex" \
  HERMES_HOME="$HERMES_HOME" \
  PATH="/usr/bin:/bin" \
  bash "$ROOT/uninstall.sh" "$@"
}

output="$(run_uninstaller --dry-run)"
if [[ "$output" != *"+ rm $DEST"* ]]; then
  printf 'expected Hermes uninstall dry-run to remove: %s\n' "$DEST" >&2
  printf 'actual output:\n%s\n' "$output" >&2
  exit 1
fi

[ -L "$DEST" ] || { echo "dry-run unexpectedly removed Hermes skill" >&2; exit 1; }

run_uninstaller >/dev/null
[ ! -e "$DEST" ] && [ ! -L "$DEST" ] || { echo "owned Hermes link was not removed" >&2; exit 1; }

FOREIGN_SRC="$TMP_HOME/foreign-skill"
mkdir -p "$FOREIGN_SRC"
ln -s "$FOREIGN_SRC" "$DEST"
run_uninstaller >/dev/null
[ -L "$DEST" ] || { echo "foreign Hermes link was removed" >&2; exit 1; }

rm "$DEST"
mkdir -p "$DEST"
run_uninstaller >/dev/null
[ -d "$DEST" ] && [ ! -L "$DEST" ] || { echo "copied Hermes skill was removed" >&2; exit 1; }

echo "uninstall flag tests passed"
