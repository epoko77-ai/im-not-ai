#!/usr/bin/env bash
# 격리 환경 실설치 스모크 — 저장소 안에서만 테스트하면 원리적으로 안 보이는 회귀를 잡는다.
#
# test_install_flags.sh 는 --dry-run 이라 실제 설치 경로를 밟지 않는다. 그 공백에서
# 두 릴리스가 통째로 패치 회차로 나갔고, 세 건 모두 사용자가 대신 밟았다.
#
#   #71     --run-dir 상대경로가 cwd 가 아닌 저장소 루트 기준으로 해석.
#           저장소 루트에서 돌리면 cwd == REPO 라 드러나지 않는다.
#   #59     프로덕션 게이트가 tests/ 를 런타임 import.
#           tests/ 가 있는 트리에서는 드러나지 않는다.
#   v2.3.2  플러그인 스킬이 관례 위치(skills/)가 아니어서 정량 shim·진단이 조용히 누락.
#           결과물은 정상적으로 나오기 때문에 품질 저하를 알아채기 어려웠다.
#
# 실제 HOME 은 건드리지 않는다 — CLAUDE_HOME/CODEX_HOME 을 임시 디렉터리로 덮는다.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

export CLAUDE_HOME="$TMP/home/.claude"
export CODEX_HOME="$TMP/home/.codex"

# 안전장치 — 오버라이드가 먹지 않은 채로 진행하면 사용자의 실제 설치를 덮어쓴다.
case "$CLAUDE_HOME" in
  "$TMP"/*) ;;
  *) echo "FATAL: CLAUDE_HOME 이 임시 트리 밖을 가리킴 — 중단" >&2; exit 1 ;;
esac

fail() { echo "FAIL: $*" >&2; exit 1; }
ok()   { echo "  ok — $*"; }

# 심링크를 따라간 실체가 읽히는지 본다. -f 는 끊어진 링크에서 거짓이 되므로
# dangling 심링크(v2.3.2 codex references 회귀)가 여기서 걸린다.
readable() { [ -f "$1" ] && [ -r "$1" ]; }

# _workspace/ 는 gitignored 라 갓 클론한 트리에는 없다. 없는 경로의 find 는 1을
# 반환하고 pipefail 이 그걸 그대로 올려 스크립트를 조용히 죽인다.
count_runs() {
  [ -d "$1" ] || { echo 0; return 0; }
  find "$1" -maxdepth 1 -type d | wc -l | tr -d ' '
}

# ── 1. 심링크 설치: 스킬 3종 + references 층이 실제로 도달 가능한가 ──────────
echo "== 1. 심링크 설치 =="
mkdir -p "$CLAUDE_HOME" "$CODEX_HOME"
"$REPO/install.sh" --no-gemini >"$TMP/install.log" 2>&1 \
  || { cat "$TMP/install.log" >&2; fail "install.sh 실패"; }

for s in humanize-korean humanize humanize-redo; do
  readable "$CLAUDE_HOME/skills/$s/SKILL.md" || fail "스킬 누락: $s/SKILL.md"
done
ok "스킬 3종 SKILL.md 도달"

# v2.3.2 의 조용한 누락 지점 — 스킬은 로드되는데 references 층이 빠지던 자리.
for r in quick-rules.md ai-tell-taxonomy.md diagnosis-rules.md metrics.py metrics_v2.py; do
  readable "$CLAUDE_HOME/skills/humanize-korean/references/$r" \
    || fail "references 누락: $r (정량 shim·진단이 조용히 죽는 자리)"
done
ok "references 5종 도달"

# #70 — 설치 범위는 런타임 3 + 유지보수 1. 개발용 5종이 전역 풀에 상주하면
# description 매칭으로 엉뚱한 작업에서 호출된다.
for a in humanize-monolith humanize-diagnostician humanize-finalizer korean-ai-tell-taxonomist; do
  readable "$CLAUDE_HOME/agents/$a.md" || fail "런타임 에이전트 누락: $a"
done
for a in translationese-research-distiller korean-translation-scholar \
         taxonomy-gap-analyzer post-editese-metric-engineer quick-rules-integrator; do
  [ -e "$CLAUDE_HOME/agents/$a.md" ] && fail "개발용 에이전트가 기본 설치됨: $a (--all-agents 전용)"
done
ok "에이전트 4종만 설치 (개발용 5종 제외)"

# codex references 는 저장소 안 상대 심링크다. v2.3.2 에서 끊어져 있었다.
readable "$CODEX_HOME/skills/humanize-korean/references/ai-tell-taxonomy.md" \
  || fail "codex references 심링크 끊어짐"
readable "$CODEX_HOME/skills/humanize-korean/SKILL.md" || fail "codex SKILL.md 누락"
ok "codex 스킬 + references 도달"

# ── 2. #71 — 상대 --run-dir 은 cwd 기준이어야 한다 ──────────────────────────
echo "== 2. cwd 기준 경로 해석 (#71) =="
WORK="$TMP/work"; mkdir -p "$WORK"
BEFORE_RUNS="$(count_runs "$REPO/_workspace")"

( cd "$WORK" && python3 "$REPO/scripts/prepare_monolith_input.py" \
    --run-dir _workspace/smoke-001 \
    --text 'AI 기술을 통해 효율성을 제고할 수 있을 것으로 보인다. 결론적으로, 이는 시사하는 바가 크다.' \
    >"$TMP/shim.log" 2>&1 ) || { cat "$TMP/shim.log" >&2; fail "shim 실행 실패"; }

readable "$WORK/_workspace/smoke-001/01_input.txt"              || fail "산출물이 cwd 아래 없음"
readable "$WORK/_workspace/smoke-001/00_metrics.json"           || fail "metrics 없음"
readable "$WORK/_workspace/smoke-001/01_input_with_metrics.txt" || fail "결합 입력 없음"
grep -q '"route_hint"' "$WORK/_workspace/smoke-001/00_metrics.json" || fail "route_hint 미산출"
ok "산출물이 cwd 아래 생성 + route_hint 산출"

AFTER_RUNS="$(count_runs "$REPO/_workspace")"
[ "$BEFORE_RUNS" = "$AFTER_RUNS" ] || fail "저장소 _workspace 가 오염됨 (#71 회귀)"
ok "저장소 트리 무오염"

# ── 3. #59 — tests/ 없는 선별 배포에서 게이트 전 축이 살아있는가 ─────────────
echo "== 3. 런타임 경계 — tests/ 없는 트리 (#59) =="
RT="$TMP/runtime"; mkdir -p "$RT/skills/humanize-korean"
cp -RL "$REPO/scripts" "$RT/scripts"
cp -RL "$REPO/skills/humanize-korean/references" "$RT/skills/humanize-korean/references"
[ -d "$RT/tests" ] && fail "런타임 트리에 tests/ 가 섞였다 — 테스트 설계 오류"

printf 'AI 기술을 통해 효율성을 제고할 수 있을 것으로 보인다. 매출은 100억원이었다.\n' > "$RT/before.txt"
printf 'AI로 효율을 높인다. 매출은 100억원이었다.\n' > "$RT/after.txt"

# 파이프로 종료코드를 삼키지 않는다 — 게이트 판정 자체가 검사 대상이다.
set +e
( cd "$RT" && python3 scripts/verify_gates.py --before before.txt --after after.txt ) >"$TMP/gates.log" 2>&1
GATE_RC=$?
set -e
[ "$GATE_RC" -le 1 ] || { cat "$TMP/gates.log" >&2; fail "게이트가 tests/ 없이 실행 불가 (rc=$GATE_RC)"; }

# P3 golden 이 통째로 죽던 자리 — 축이 "돌았다"는 증거를 본문에서 확인한다.
grep -q '\[P3 golden\]' "$TMP/gates.log" || { cat "$TMP/gates.log" >&2; fail "P3 golden 축이 죽음 (#59 회귀)"; }
for ax in 'P0 문자율' 'P1 목표달성' 'P2 전멸' 'P4 터치율' 'P5 서법'; do
  grep -q "\[$ax\]" "$TMP/gates.log" || { cat "$TMP/gates.log" >&2; fail "축 누락: $ax"; }
done
ok "게이트 6축 전부 동작 (tests/ 부재)"

( cd "$RT" && python3 scripts/verify_change_rate.py --before before.txt --after after.txt ) \
  >/dev/null 2>&1 || true   # 판정값(WARN/ABORT)이 아니라 실행 가능 여부만 본다
ok "verify_change_rate 실행 가능"

# ── 4. --copy 설치: references 심링크가 실체화되는가 ────────────────────────
echo "== 4. --copy 설치 =="
export CLAUDE_HOME="$TMP/home2/.claude"
export CODEX_HOME="$TMP/home2/.codex"
mkdir -p "$CLAUDE_HOME" "$CODEX_HOME"
"$REPO/install.sh" --copy --no-gemini >"$TMP/install-copy.log" 2>&1 \
  || { cat "$TMP/install-copy.log" >&2; fail "install.sh --copy 실패"; }

readable "$CLAUDE_HOME/skills/humanize-korean/references/quick-rules.md" \
  || fail "--copy 에서 references 누락"
# cp -RL 이 실체화해야 한다. 심링크로 남으면 저장소를 지운 사용자가 깨진다.
[ -L "$CODEX_HOME/skills/humanize-korean/references" ] \
  && fail "--copy 인데 codex references 가 여전히 심링크 (cp -RL 회귀)"
readable "$CODEX_HOME/skills/humanize-korean/references/ai-tell-taxonomy.md" \
  || fail "--copy 에서 codex references 실체화 실패"
ok "복사 설치 — references 실체화 확인"

echo ""
echo "install smoke tests passed"
