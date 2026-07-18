#!/usr/bin/env bash
# Humanize KR — 전역 설치 제거 스크립트
# install.sh가 만든 "이 저장소를 가리키는 심링크"만 제거한다. 사용자가 직접 둔 파일이나
# 다른 곳을 가리키는 링크, .bak.* 백업은 건드리지 않는다. (--copy 설치본은 자동 삭제 대상 아님)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
DRYRUN=0

case "${1:-}" in
  --dry-run) DRYRUN=1 ;;
  -h|--help) echo "Usage: ./uninstall.sh [--dry-run]"; exit 0 ;;
  "") ;;
  *) echo "unknown arg: $1" >&2; exit 2 ;;
esac

remove_if_ours() {
  local dest="$1" src="$2"
  if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$src" ]; then
    echo "+ rm $dest"; [ "$DRYRUN" = 1 ] || rm "$dest"
  elif [ -e "$dest" ]; then
    echo "skip (우리 것 아님): $dest"
  fi
}

for s in humanize-korean humanize humanize-redo; do
  remove_if_ours "$CLAUDE_HOME/skills/$s" "$REPO/.claude/skills/$s"
done
remove_if_ours "$CODEX_HOME/skills/humanize-korean" "$REPO/codex/skills/humanize-korean"
for a in "$REPO/agents"/*.md; do
  remove_if_ours "$CLAUDE_HOME/agents/$(basename "$a")" "$a"
done

# ---- Gemini CLI ----
if command -v gemini >/dev/null 2>&1; then
  echo "Gemini extension 제거 시도..."
  if [ "$DRYRUN" = 1 ]; then
    echo "+ gemini extensions uninstall im-not-ai (dry-run)"
  else
    gemini extensions uninstall im-not-ai 2>/dev/null && echo "removed: Gemini extension (im-not-ai)" \
      || echo "  (Gemini extension 미설치 또는 이미 제거됨)"
  fi
fi

echo "제거 완료. (.bak.* 백업·--copy 설치본은 보존)"
