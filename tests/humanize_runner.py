"""Live humanize runner — 배포된 humanize-korean 스킬을 `claude -p`로 실제 호출.

⚠️ 범위: 비대화형 실행에서 권한이 필요한 도구를 쓰지 않도록 "파일은 만들지 마"로 호출한다.
그래서 스킬의 **스크립트 단계(입력 shim·서법/쉼표/어휘 복원·구조 게이트)는 여기서 돌지 않는다** —
이 층은 모델이 룰북만으로 내는 윤문을 잰다. 스크립트 사슬은 `test_pipeline_scripts.py`가 얼린
윤문본으로 결정적으로 검증한다(v2.4.2).

살아있는 스킬을 돌려 갓 나온 윤문본을 얻는다. test_humanize_live.py와
generate_fixtures.py가 공유한다. `claude` CLI(Claude Code, 구독 인증)만 있으면 되고
별도 API 키는 필요 없다. 스킬은 이 레포의 skills/humanize-korean 에서 탐색됨
(claude 를 레포 루트에서 실행).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_START, _END = "<<<H>>>", "<<</H>>>"
# 닫는 표지는 꺾쇠 2~3개까지 받는다. 모델이 `<<</H>>>`를 `<</H>>>`로 줄여 쓰는 일이 반복됐고
# (본문은 멀쩡한데 파싱만 실패해 live 테스트가 회귀로 오판), 여는 표지·본문·닫는 표지가 모두
# 있어야 한다는 계약의 핵심은 그대로다.
_SENTINEL = re.compile(re.escape(_START) + r"(.*?)" + r"<{2,3}/H>{2,3}", re.S)

CLAUDE_BIN = shutil.which("claude")

# 철칙 #4 게이트 상수의 SSOT(metrics_v2)를 그대로 쓴다 — 러너가 문턱을 따로 들고 있지 않게.
_REFS = os.path.join(_REPO_ROOT, "skills", "humanize-korean", "references")
if _REFS not in sys.path:
    sys.path.insert(0, _REFS)
import metrics_v2 as _m  # noqa: E402


class SkillUnavailable(RuntimeError):
    """하네스가 스킬을 **돌리지 못했다** — claude CLI 부재 / 타임아웃.

    환경 문제이므로 호출자는 이를 "판정 불가"로 다뤄도 된다(live 테스트는 skip).
    """


class SkillOutputInvalid(SkillUnavailable):
    """스킬이 **돌았는데** 출력이 계약을 위반했다 — 센티넬 파싱 실패.

    이건 환경이 아니라 회귀 신호다. live 테스트는 이것만은 skip 하지 않고
    실패로 남긴다 — 출력 계약이 깨진 것을 환경 탓으로 넘기면 "검증이 조용히
    죽는" 실패 형태가 된다(#59·#84 와 같은 계열).

    기존 호출자가 `except SkillUnavailable` 로 받고 있어 하위 클래스로 둔다.
    """


# SKILL.md Phase 2.5 exit 2 분기의 재실행 지시 — "윤문본 채택 금지, 롤백 지시 후 1회 재실행,
# 보수 강도 재강조". 픽스처 정답(보호 토큰·픽스처별 상한)은 넣지 않는다(계측 무효화 방지).
_ROLLBACK = (
    "직전 윤문본은 변경률 게이트(50% 이상 강제 중단)에 걸려 폐기됐다. 원문에서 다시 시작해 "
    "보수 강도로 윤문해 — 내용 앵커를 원형대로 두고, 확신 없는 구간은 그대로 둔다. "
)


def _prompt(text: str, strict: bool, rollback: bool = False) -> str:
    mode = "strict(5인 파이프라인)" if strict else "Fast"
    return (
        f"다음 텍스트를 humanize-korean 스킬 {mode} 모드로 윤문해줘. "
        + (_ROLLBACK if rollback else "")
        + f"설명·헤딩·지표 전부 빼고, 윤문된 본문만 반드시 {_START} 와 {_END} 사이에 "
        f"한 덩어리로 출력해. 파일은 만들지 마.\n\n텍스트:\n" + text
    )


def run_humanize(
    text: str, *, strict: bool = False, timeout: int = 300, model: str | None = None,
    rollback: bool = False,
) -> str:
    """스킬을 실제 호출해 윤문본을 반환. 실패 시 SkillUnavailable.

    model: `claude --model` 로 넘길 모델 ID(예: "claude-sonnet-5").
           None 이면 CLI 기본 모델. 모델 간 품질 비교(scripts/eval_baseline.py)에 쓴다.
    """
    if not CLAUDE_BIN:
        raise SkillUnavailable("`claude` CLI를 찾을 수 없음 (Claude Code 설치 필요)")
    cmd = [CLAUDE_BIN]
    if model:
        cmd += ["--model", model]
    cmd += ["-p", _prompt(text, strict, rollback)]
    try:
        proc = subprocess.run(
            cmd,
            cwd=_REPO_ROOT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise SkillUnavailable(f"claude 호출 타임아웃 ({timeout}s)") from exc

    out = proc.stdout or ""
    match = _SENTINEL.search(out)
    if not match:
        raise SkillOutputInvalid(f"센티넬 파싱 실패. 원출력 앞부분: {out[:200]!r}")
    return match.group(1).strip()


def run_humanize_gated(
    text: str, *, strict: bool = False, timeout: int = 300, model: str | None = None
) -> tuple[str, bool]:
    """스킬 호출 + Phase 2.5 강제 중단 분기 흉내. (윤문본, 롤백 재실행 여부)를 돌려준다.

    라이브 호출은 비대화형이라 스킬의 `verify_gates.py`가 돌지 않는다. 그러면 실제 사용에서는
    게이트가 잡아 롤백했을 과윤문(≥50%)이 그대로 채점돼, 과윤문 가드 픽스처가 상한 근처에서
    흔들렸다(실측 18회 중 1회 0.530). 오케스트레이터와 같은 문턱·같은 1회 재실행을 여기서 한다.
    재실행 뒤에도 ≥50%면 그대로 돌려준다 — 그건 hold_and_report 사례라 채점이 실패로 잡아야 한다.
    """
    out = run_humanize(text, strict=strict, timeout=timeout, model=model)
    if _m.change_rate(text, out) < _m.CHANGE_RATE_ABORT:
        return out, False
    return run_humanize(text, strict=strict, timeout=timeout, model=model, rollback=True), True

