#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_HOME="$(mktemp -d)"
trap 'rm -rf "$TMP_HOME"' EXIT

MINIMAL_PATH="/usr/bin:/bin:/usr/sbin:/sbin"

run_installer() {
  env -i HOME="$TMP_HOME" PATH="$MINIMAL_PATH" bash "$ROOT/install.sh" "$@" --dry-run
}

assert_contains() {
  local output="$1" expected="$2"
  if [[ "$output" != *"$expected"* ]]; then
    printf 'expected output to contain: %s\n' "$expected" >&2
    printf 'actual output:\n%s\n' "$output" >&2
    exit 1
  fi
}

assert_not_contains() {
  local output="$1" unexpected="$2"
  if [[ "$output" == *"$unexpected"* ]]; then
    printf 'expected output not to contain: %s\n' "$unexpected" >&2
    printf 'actual output:\n%s\n' "$output" >&2
    exit 1
  fi
}

codex_output="$(run_installer --codex-only)"
assert_contains "$codex_output" "== Codex =="
assert_contains "$codex_output" "+ ln -s $ROOT/codex/skills/humanize-korean $TMP_HOME/.codex/skills/humanize-korean"
assert_not_contains "$codex_output" "Codex: "

claude_output="$(run_installer --claude-only)"
assert_contains "$claude_output" "== Claude Code =="
assert_contains "$claude_output" "+ ln -s $ROOT/.claude/skills/humanize-korean $TMP_HOME/.claude/skills/humanize-korean"
assert_not_contains "$claude_output" "Claude Code: "

mkdir -p "$TMP_HOME/.codex"
codex_desktop_output="$(run_installer)"
assert_contains "$codex_desktop_output" "== Codex =="
assert_contains "$codex_desktop_output" "+ ln -s $ROOT/codex/skills/humanize-korean $TMP_HOME/.codex/skills/humanize-korean"
assert_not_contains "$codex_desktop_output" "Codex: "
rm -rf "$TMP_HOME/.codex"

mkdir -p "$TMP_HOME/.claude"
claude_desktop_output="$(run_installer)"
assert_contains "$claude_desktop_output" "== Claude Code =="
assert_contains "$claude_desktop_output" "+ ln -s $ROOT/.claude/skills/humanize-korean $TMP_HOME/.claude/skills/humanize-korean"
assert_not_contains "$claude_desktop_output" "Claude Code: "
rm -rf "$TMP_HOME/.claude"

echo "install flag tests passed"
