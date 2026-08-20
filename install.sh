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
ALL_AGENTS=0
CONFLICTS=0
TS="$(date +%Y%m%d-%H%M%S)"

# 스킬 런타임이 호출하는 3종 + 별도 명령으로만 트리거되는 유지보수 1종.
# agents/ 의 나머지(릴리스 회차용 개발 도구)는 --all-agents 일 때만 설치한다 —
# 서브에이전트는 description 매칭으로 자동 라우팅되므로, 윤문과 무관한 정의가
# 전역 풀에 상주하면 다른 작업에서 잘못 호출될 수 있다.
INSTALLED_AGENTS="humanize-monolith humanize-diagnostician humanize-finalizer korean-ai-tell-taxonomist"

print_help() {
  cat <<'H'
Usage: ./install.sh [options]

  설치된 CLI를 자동 감지해 humanize-korean 스킬을 전역 설치한다.
  Claude: ~/skills/{humanize-korean,humanize,humanize-redo} + ~/.claude/agents/*.md
  Codex : ~/.codex/skills/humanize-korean
  Gemini: gemini extensions link (gemini-extension.json + GEMINI.md + commands/)

Options:
  --copy          심링크 대신 복사(저장소를 지워도 유지, references 심링크는 실체화).
                  ※ 복사본은 uninstall.sh가 자동 삭제하지 않음(수동 삭제).
  --claude-only   Claude만 설치 시도(claude 명령 또는 ~/.claude 감지 시)
  --codex-only    Codex만 설치 시도(codex 명령 또는 ~/.codex 감지 시)
  --gemini-only   Gemini만 설치
  --no-gemini     Gemini 건너뜀 (claude/codex만)
  --all-agents    agents/ 전체를 전역 설치(개발용 1회성 정의 포함).
                  기본은 스킬이 실제로 쓰는 4종만 — 런타임 3(monolith·
                  diagnostician·finalizer) + 유지보수 1(taxonomist).
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
    --all-agents) ALL_AGENTS=1 ;;
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
    if [ "$(readlink "$dest")" = "$src" ] && [ "$MODE" = symlink ]; then
      echo "ok (already linked): $dest"; return 1
    fi
    # copy 모드에서 기존 심링크는 '설치됨'이 아니다. 치우고 실체 복사로 대체해야
    # 저장소 삭제 시 링크가 끊어지는 사고를 막는다.
    run mv "$dest" "$dest.bak.$TS"
  elif [ -e "$dest" ]; then
    if [ "$FORCE" != 1 ]; then
      echo "refuse: $dest 가 이미 있음 (--force 로 백업 후 덮어쓰기 또는 --copy)"; return 2
    fi
    run mv "$dest" "$dest.bak.$TS"
  fi
  return 0
}

# 구버전 설치가 남긴 전역 에이전트 링크를 정리한다 (#73).
#
# 두 부류를 지운다.
#   1) 이 저장소가 심었지만 지금 설치 범위 밖인 것 (개발용 5종 — #70 이전 설치본)
#   2) dangling — 대상이 사라진 은퇴 에이전트 링크
#      (ai-tell-detector·korean-style-rewriter·content-fidelity-auditor·
#       naturalness-reviewer·humanize-web-architect 등 v2.1 은퇴분)
#
# **소유권 판별은 심링크 대상으로만 한다.** 이 저장소의 agents/ 를 가리키는
# 심링크만 대상이며, 사용자가 직접 만든 파일이나 다른 도구가 심은 링크는
# 절대 건드리지 않는다. 복사(copy) 설치는 소유 판별이 불가능하므로 건너뛴다.
prune_stale_agents() {
  local dir="$CLAUDE_HOME/agents"
  [ -d "$dir" ] || return 0
  local keep=" $INSTALLED_AGENTS "
  local f base target pruned=0
  for f in "$dir"/*.md; do
    # glob 미매칭 시 리터럴이 들어오므로 심링크인 것만 통과
    [ -L "$f" ] || continue
    target="$(readlink "$f")"
    case "$target" in
      "$REPO/agents/"*) ;;   # 이 저장소가 심은 것 → 대상
      *) continue ;;         # 남의 것 → 손대지 않음
    esac
    base="$(basename "$f" .md)"
    if [ -e "$target" ]; then
      # 대상이 살아있음 → 설치 범위 밖일 때만 정리
      [ "$ALL_AGENTS" = 1 ] && continue
      case "$keep" in *" $base "*) continue ;; esac
    fi
    # 여기 도달 = 범위 밖이거나 dangling
    run rm -f "$f"
    echo "pruned: $f"
    pruned=$((pruned + 1))
  done
  [ "$pruned" -gt 0 ] && echo "note: 구버전·은퇴 에이전트 링크 ${pruned}건 정리됨"
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
    if install_one "$REPO/skills/$s" "$CLAUDE_HOME/skills/$s"; then
      if [ "$s" = humanize-korean ] && [ "$MODE" = copy ]; then
        # 복사 설치는 SKILL_ROOT 탐색이 저장소로 돌아갈 수 없다. 스킬 사본 안에
        # scripts/ 와 .claude-plugin/ 표식을 함께 실체화해야 shim·게이트가 산다.
        run cp -RL "$REPO/scripts" "$CLAUDE_HOME/skills/$s/scripts"
        run cp -RL "$REPO/.claude-plugin" "$CLAUDE_HOME/skills/$s/.claude-plugin"
      fi
    else
      CONFLICTS=$((CONFLICTS + 1))
      echo "skip: skills/$s (충돌 · --force 로 재실행)" >&2
    fi
  done
  agents=()
  if [ "$ALL_AGENTS" = 1 ]; then
    for a in "$REPO/agents"/*.md; do
      if [ -e "$a" ]; then agents[${#agents[@]}]="$a"; fi
    done
  else
    for n in $INSTALLED_AGENTS; do
      if [ -f "$REPO/agents/$n.md" ]; then
        agents[${#agents[@]}]="$REPO/agents/$n.md"
      else
        echo "warn: agents/$n.md 를 찾지 못해 건너뜀" >&2
      fi
    done
  fi
  if [ "${#agents[@]}" -gt 0 ]; then
    for a in "${agents[@]}"; do
      install_one "$a" "$CLAUDE_HOME/agents/$(basename "$a")" \
        || { CONFLICTS=$((CONFLICTS + 1)); echo "skip: agents/$(basename "$a") (충돌 · --force 로 재실행)" >&2; }
    done
  fi
  # 설치 후 정리 — 구버전 설치본이 남긴 범위 밖·은퇴 링크 제거 (#73).
  # 심링크 모드에서만 동작한다(복사 설치는 소유 판별 불가).
  if [ "$MODE" = symlink ]; then
    prune_stale_agents
  fi
  if [ "$ALL_AGENTS" != 1 ]; then
    echo "note: 릴리스 회차용 개발 에이전트는 설치하지 않음 (전체 설치는 --all-agents)"
  fi
else
  echo "== Claude Code: 건너뜀 (claude 또는 $CLAUDE_HOME 미감지) =="
fi

# ---- Codex ----
if [ "$DO_CODEX" != no ] && { [ "$DO_CODEX" = yes ] || has_codex_target; }; then
  echo "== Codex =="
  run mkdir -p "$CODEX_HOME/skills"
  install_one "$REPO/codex/skills/humanize-korean" "$CODEX_HOME/skills/humanize-korean" \
    || { CONFLICTS=$((CONFLICTS + 1)); echo "skip: codex 스킬 (충돌 · --force 로 재실행)" >&2; }
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
if [ "$CONFLICTS" -gt 0 ]; then
  echo "경고: 충돌로 건너뛴 대상 ${CONFLICTS}건 · --force 로 재실행하면 백업 후 덮어쓴다." >&2
  exit 1
fi
exit 0
