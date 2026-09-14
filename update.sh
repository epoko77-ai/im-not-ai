#!/usr/bin/env bash
# Humanize KR — 업데이트 감지 + 자동 적용
# upstream(git)을 확인해 새 커밋이 있으면 fast-forward pull 후 install.sh를 재적용한다.
# 심링크 설치는 pull만으로도 내용이 반영되지만, 신규 스킬/에이전트/구조 변경까지 확실히
# 연결하려고 install.sh를 다시 실행한다(멱등).
#
# 사용:
#   ./update.sh            업데이트 감지 → 있으면 자동 적용
#   ./update.sh --check    감지만(적용 안 함). 최신=exit 0, 업데이트 있음=exit 10
#   그 외 인자는 install.sh로 전달 (예: ./update.sh --copy --force, ./update.sh --codex-only)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
g() { git -C "$REPO" "$@"; }

usage() { sed -n '2,11p' "$0"; }

CHECK_ONLY=0
ARGS=()
for a in "$@"; do
  case "$a" in
    --check) CHECK_ONLY=1 ;;
    -h|--help) usage; exit 0 ;;
    *) ARGS+=("$a") ;;
  esac
done

g rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "git 저장소가 아닙니다: $REPO"; exit 2; }

ver() { grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' "$REPO/.claude-plugin/plugin.json" 2>/dev/null \
          | head -1 | grep -o '[0-9][0-9.]*' \
       || grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' "$REPO/gemini-extension.json" 2>/dev/null \
          | head -1 | grep -o '[0-9][0-9.]*' \
       || echo "?"; }

UPSTREAM="$(g rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || echo origin/main)"
UP_REMOTE="${UPSTREAM%%/*}"
echo "업데이트 확인 중… (upstream: $UPSTREAM)"
g fetch --quiet "$UP_REMOTE" || { echo "fetch 실패 — 네트워크/원격을 확인하세요."; exit 2; }

LOCAL="$(g rev-parse HEAD)"
REMOTE="$(g rev-parse "$UPSTREAM" 2>/dev/null || true)"
[ -z "$REMOTE" ] && { echo "upstream($UPSTREAM)을 찾을 수 없습니다."; exit 2; }
BASE="$(g merge-base HEAD "$UPSTREAM" 2>/dev/null || echo "")"

if [ "$LOCAL" = "$REMOTE" ]; then
  echo "이미 최신입니다 — v$(ver) ($(g rev-parse --short HEAD))."
  exit 0
elif [ "$BASE" = "$REMOTE" ]; then
  echo "로컬이 upstream보다 앞서 있습니다 — 적용할 업데이트 없음."
  exit 0
elif [ "$BASE" != "$LOCAL" ]; then
  echo "로컬이 upstream과 갈라져 있어 자동 업데이트를 멈춥니다(수동 병합 필요)."
  echo "  local=$(g rev-parse --short HEAD)  upstream=$(g rev-parse --short "$UPSTREAM")"
  exit 1
fi

# 여기 도달 = behind, fast-forward 가능
BEHIND="$(g rev-list --count "HEAD..$UPSTREAM")"
echo "🔔 업데이트 있음: $BEHIND개 커밋 ($UPSTREAM)"
g --no-pager log --oneline "HEAD..$UPSTREAM" 2>/dev/null | head -10 | sed 's/^/    /'

if [ "$CHECK_ONLY" = 1 ]; then
  echo "(--check: 적용하지 않음. 적용하려면 ./update.sh)"
  exit 10
fi

OLD="$(ver)"
echo "fast-forward pull…"
g pull --ff-only
echo "설치 재적용(install.sh, 멱등)…"
"$REPO/install.sh" ${ARGS[@]+"${ARGS[@]}"}
echo "✅ 자동 업데이트 완료: v$OLD → v$(ver)."
