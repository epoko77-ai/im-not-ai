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

codex_without_target_output="$(run_installer --codex-only)"
assert_contains "$codex_without_target_output" "== Codex: 건너뜀"
assert_not_contains "$codex_without_target_output" "+ ln -s $ROOT/codex/skills/humanize-korean"

mkdir -p "$TMP_HOME/.codex"
codex_output="$(run_installer --codex-only)"
assert_contains "$codex_output" "== Codex =="
assert_contains "$codex_output" "+ ln -s $ROOT/codex/skills/humanize-korean $TMP_HOME/.codex/skills/humanize-korean"
assert_not_contains "$codex_output" "Codex: "
rm -rf "$TMP_HOME/.codex"

claude_without_target_output="$(run_installer --claude-only)"
assert_contains "$claude_without_target_output" "== Claude Code: 건너뜀"
assert_not_contains "$claude_without_target_output" "+ ln -s $ROOT/.claude/skills/humanize-korean"

mkdir -p "$TMP_HOME/.claude"
claude_output="$(run_installer --claude-only)"
assert_contains "$claude_output" "== Claude Code =="
assert_contains "$claude_output" "+ ln -s $ROOT/.claude/skills/humanize-korean $TMP_HOME/.claude/skills/humanize-korean"
assert_not_contains "$claude_output" "Claude Code: "
rm -rf "$TMP_HOME/.claude"

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

hermes_without_target_output="$(run_installer --hermes-only)"
assert_contains "$hermes_without_target_output" "== Hermes Agent: 건너뜀"
assert_not_contains "$hermes_without_target_output" "+ ln -s $ROOT/hermes/skills/humanize-korean"

mkdir -p "$TMP_HOME/bin"
printf '#!/usr/bin/env bash\nexit 0\n' > "$TMP_HOME/bin/hermes"
chmod +x "$TMP_HOME/bin/hermes"
hermes_command_output="$(
  env -i HOME="$TMP_HOME" PATH="$TMP_HOME/bin:$MINIMAL_PATH" \
    bash "$ROOT/install.sh" --hermes-only --dry-run
)"
assert_contains "$hermes_command_output" "== Hermes Agent =="
assert_contains "$hermes_command_output" "+ ln -s $ROOT/hermes/skills/humanize-korean $TMP_HOME/.hermes/skills/humanize-korean"
rm -rf "$TMP_HOME/bin"

mkdir -p "$TMP_HOME/.hermes"
hermes_output="$(run_installer --hermes-only)"
assert_contains "$hermes_output" "== Hermes Agent =="
assert_contains "$hermes_output" "+ ln -s $ROOT/hermes/skills/humanize-korean $TMP_HOME/.hermes/skills/humanize-korean"
assert_not_contains "$hermes_output" "Hermes Agent: "

hermes_disabled_output="$(run_installer --no-hermes)"
assert_contains "$hermes_disabled_output" "== Hermes Agent: 건너뜀"
assert_not_contains "$hermes_disabled_output" "+ ln -s $ROOT/hermes/skills/humanize-korean"
rm -rf "$TMP_HOME/.hermes"

echo "install flag tests passed"
