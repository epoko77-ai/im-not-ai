#!/usr/bin/env bash
# Humanize KR — Claude Code + Codex CLI + Gemini CLI 전역 설치 스크립트
# 저장소를 클론한 뒤 `./install.sh` 한 번이면 설치된 CLI(claude/codex/gemini)를 자동 감지해
# humanize-korean 스킬(+ 에이전트)을 전역으로 연결한다. 기본은 심링크(저장소 수정 즉시 반영).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"

MODE=symlink          # symlink | copy
DO_CLAUDE=auto        # auto | yes | no
DO_CODEX=auto
DO_GEMINI=auto
FORCE=0
DRYRUN=0
TS="$(date +%Y%m%d-%H%M%S)"

print_help() {
  cat <<'H'
Usage: ./install.sh [options]

  설치된 CLI를 자동 감지해 humanize-korean 스킬을 전역 설치한다.
  Claude: ~/.claude/skills/{humanize-korean,humanize,humanize-redo} + ~/.claude/agents/*.md
  Codex : ~/.codex/skills/humanize-korean
  Gemini: gemini extensions link (gemini-extension.json + GEMINI.md + commands/)

Options:
  --copy          심링크 대신 복사(저장소를 지워도 유지, references 심링크는 실체화).
                  ※ 복사본은 uninstall.sh가 자동 삭제하지 않음(수동 삭제).
  --claude-only   Claude만 설치 시도(claude 명령 또는 ~/.claude 감지 시)
  --codex-only    Codex만 설치 시도(codex 명령 또는 ~/.codex 감지 시)
  --gemini-only   Gemini만 설치
  --no-gemini     Gemini 건너뜀 (claude/codex만)
  --force         대상에 일반 파일/디렉토리가 있어도 .bak.<ts> 백업 후 덮어씀
  --dry-run       실제 변경 없이 수행할 작업만 출력
  -h, --help      이 도움말

Env overrides: CLAUDE_HOME(기본 ~/.claude), CODEX_HOME(기본 ~/.codex)
H
}

while [ $# -gt 0 ]; do
  case "$1" in
    --copy) MODE=copy ;;
    --claude-only) DO_CODEX=no; DO_GEMINI=no ;;
    --codex-only) DO_CLAUDE=no; DO_GEMINI=no ;;
    --gemini-only) DO_CLAUDE=no; DO_CODEX=no; DO_GEMINI=yes ;;
    --no-gemini) DO_GEMINI=no ;;
    --force) FORCE=1 ;;
    --dry-run) DRYRUN=1 ;;
    -h|--help) print_help; exit 0 ;;
    *) echo "unknown arg: $1" >&2; print_help; exit 2 ;;
  esac
  shift
done

run() { echo "+ $*"; [ "$DRYRUN" = 1 ] || "$@"; }

# rc: 0=대상 비었음(설치 진행) / 1=이미 우리 심링크(스킵) / 2=충돌(거부)
prepare_target() {
  local dest="$1" src="$2"
  if [ -L "$dest" ]; then
    if [ "$(readlink "$dest")" = "$src" ]; then
      echo "ok (already linked): $dest"; return 1
    fi
    run mv "$dest" "$dest.bak.$TS"
  elif [ -e "$dest" ]; then
    if [ "$FORCE" != 1 ]; then
      echo "refuse: $dest 가 이미 있음 (--force 로 백업 후 덮어쓰기 또는 --copy)"; return 2
    fi
    run mv "$dest" "$dest.bak.$TS"
  fi
  return 0
}

install_one() {
  local src="$1" dest="$2"
  run mkdir -p "$(dirname "$dest")"
  local rc=0
  prepare_target "$dest" "$src" || rc=$?
  [ "$rc" = 1 ] && return 0
  [ "$rc" = 2 ] && return 1
  case "$MODE" in
    symlink) run ln -s "$src" "$dest" ;;
    copy)    run cp -RL "$src" "$dest" ;;   # -L: references 심링크를 실체로 복사
  esac
  echo "installed: $dest"
}

# CLI 명령 또는 홈 디렉터리(앱만 설치한 사용자)로 대상 감지
has_claude_target() { command -v claude >/dev/null 2>&1 || [ -d "$CLAUDE_HOME" ]; }
has_codex_target()  { command -v codex  >/dev/null 2>&1 || [ -d "$CODEX_HOME" ]; }

# ---- Claude ----
if [ "$DO_CLAUDE" != no ] && { [ "$DO_CLAUDE" = yes ] || has_claude_target; }; then
  echo "== Claude Code =="
  run mkdir -p "$CLAUDE_HOME/skills" "$CLAUDE_HOME/agents"
  for s in humanize-korean humanize humanize-redo; do
    install_one "$REPO/.claude/skills/$s" "$CLAUDE_HOME/skills/$s"
  done
  for a in "$REPO/agents"/*.md; do
    install_one "$a" "$CLAUDE_HOME/agents/$(basename "$a")"
  done
else
  echo "== Claude Code: 건너뜀 (claude 또는 $CLAUDE_HOME 미감지) =="
fi

# ---- Codex ----
if [ "$DO_CODEX" != no ] && { [ "$DO_CODEX" = yes ] || has_codex_target; }; then
  echo "== Codex =="
  run mkdir -p "$CODEX_HOME/skills"
  install_one "$REPO/codex/skills/humanize-korean" "$CODEX_HOME/skills/humanize-korean"
else
  echo "== Codex: 건너뜀 (codex 또는 $CODEX_HOME 미감지) =="
fi

# ---- Gemini CLI ----
if [ "$DO_GEMINI" != no ] && { [ "$DO_GEMINI" = yes ] || command -v gemini >/dev/null 2>&1; }; then
  echo "== Gemini CLI =="
  if [ "$DRYRUN" = 1 ]; then
    echo "+ gemini extensions link $REPO (dry-run)"
  else
    echo "gemini extensions link \"$REPO\" 실행 (확장 등록)..."
    echo "Y" | gemini extensions link "$REPO" 2>/dev/null && echo "installed: Gemini extension (im-not-ai)" \
      || echo "  (이미 등록됨 또는 수동 등록 필요: gemini extensions link $REPO)"
  fi
else
  echo "== Gemini CLI: 건너뜀 (gemini 미감지 — 강제하려면 --gemini-only) =="
fi

echo ""
echo "완료 (mode=$MODE)."
echo "  Claude: 새 세션에서 /humanize-korean (또는 /humanize)"
echo "  Codex : \$humanize-korean"
echo "  Gemini: 새 세션에서 /humanize-korean (또는 /humanize)"
echo "  업데이트: ./update.sh (새 버전 자동 감지 + 적용) · 제거: ./uninstall.sh"
exit 0
