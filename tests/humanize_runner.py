"""Live humanize runner — 배포된 humanize-korean 스킬을 `claude -p`로 실제 호출.

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

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_START, _END = "<<<H>>>", "<<</H>>>"
_SENTINEL = re.compile(re.escape(_START) + r"(.*?)" + re.escape(_END), re.S)

CLAUDE_BIN = shutil.which("claude")


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


def _prompt(text: str, strict: bool) -> str:
    mode = "strict(5인 파이프라인)" if strict else "Fast"
    return (
        f"다음 텍스트를 humanize-korean 스킬 {mode} 모드로 윤문해줘. "
        f"설명·헤딩·지표 전부 빼고, 윤문된 본문만 반드시 {_START} 와 {_END} 사이에 "
        f"한 덩어리로 출력해. 파일은 만들지 마.\n\n텍스트:\n" + text
    )


def run_humanize(
    text: str, *, strict: bool = False, timeout: int = 300, model: str | None = None
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
    cmd += ["-p", _prompt(text, strict)]
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
