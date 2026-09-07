"""Live humanize runner — **이 레포의** humanize-korean 스킬을 `claude -p`로 실제 호출.

살아있는 스킬을 돌려 갓 나온 윤문본을 얻는다. test_humanize_live.py와
generate_fixtures.py가 공유한다. `claude` CLI(Claude Code, 구독 인증)만 있으면 되고
별도 API 키는 필요 없다.

⚠️ **실사고(2026-09-05).** 초판은 "claude 를 레포 루트에서 실행하면 레포의
skills/humanize-korean 이 탐색된다"고 적어 두었는데 **사실이 아니었다.** Claude Code
는 cwd 의 임의 `skills/` 를 보지 않고 `~/.claude/skills/`(개인)와 `.claude/skills/`
(프로젝트)를 본다. 이 머신에서는 개인 스킬이 **2026-06 에 설치된 v1.5.0** 이었고,
live 스위트는 몇 달째 레포가 아니라 그 사본을 재고 있었다. `fx_guard_overedit` 3건이
브랜치를 바꿔도 늘 같은 값으로 실패한 이유다 — v1.5 에는 변경률 게이트가 없다.

고치는 방법 둘을 함께 쓴다.
1. `--plugin-dir <repo>` 로 **레포를 플러그인으로 직접 로드**한다. 전역 설치본에
   의존하지 않는다.
2. 그래도 다른 사본이 응답할 수 있으므로, 스킬이 **자기 버전을 함께 출력**하게 하고
   레포 SKILL.md 와 대사한다. 어긋나면 통과시키지 않고 SkillUnavailable 을 던진다 —
   조용히 엉뚱한 것을 테스트하느니 "테스트 못 했다"가 낫다.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_START, _END = "<<<H>>>", "<<</H>>>"
_SENTINEL = re.compile(re.escape(_START) + r"(.*?)" + re.escape(_END), re.S)
_VERSION_TAG = re.compile(r"<<<V>>>\s*([0-9]+\.[0-9]+\.[0-9]+)\s*<<</V>>>")
_SKILL_MD = os.path.join(_REPO_ROOT, "skills", "humanize-korean", "SKILL.md")


def repo_skill_version() -> str:
    """레포 SKILL.md frontmatter 의 version — 무엇을 테스트해야 하는지의 기준."""
    with open(_SKILL_MD, encoding="utf-8") as f:
        head = f.read().split("---", 2)[1]
    match = re.search(r'^version:\s*"?([0-9]+\.[0-9]+\.[0-9]+)"?', head, re.M)
    if not match:
        raise SkillUnavailable(f"SKILL.md 에서 version 을 못 찾음: {_SKILL_MD}")
    return match.group(1)

CLAUDE_BIN = shutil.which("claude")

# 부모 Claude Code 세션의 상태가 자식 `claude -p` 로 새면, 모델이 요청한 일 대신
# 자기 도구에 대한 메타 발화를 낸다("ExitPlanMode 도구가 이 세션에 없어…").
# 코퍼스 생성기(scripts/build_en_baseline.py)는 2026-09-03 사고 뒤 이 넷을 지우는데
# **live 러너만 안 지우고 있었다** — 18콜 중 2콜이 같은 이유로 죽었다.
_LEAKY_ENV = (
    "CLAUDE_CODE_MESSAGING_SOCKET",
    "CLAUDE_CODE_MESSAGING_TOKEN",
    "CLAUDE_CODE_EMIT_SESSION_STATE_EVENTS",
    "CLAUDE_CODE_ENABLE_TASKS",
)


def _clean_env() -> dict:
    env = dict(os.environ)
    for key in _LEAKY_ENV:
        env.pop(key, None)
    return env


class QuotaExhausted(RuntimeError):
    """구독 사용량 한도 — 스킬 결함이 아니다. 테스트는 FAIL 이 아니라 SKIP 이어야 한다."""


# CLI 는 한도에 걸리면 본문 대신 이 문구를 즉시 돌려준다(콜당 7초).
# 이걸 구분하지 않으면 18콜이 전부 정체불명 오류로 보고돼, 진짜 회귀와
# 구분할 수 없다 — 실측 2026-09-05.
_QUOTA_RE = re.compile(r"hit your (?:session|usage) limit|resets \d{1,2}:\d\d", re.I)


class SkillUnavailable(RuntimeError):
    """claude CLI 부재 / 타임아웃 / 출력 파싱 실패."""


def _prompt(text: str, strict: bool) -> str:
    mode = "strict(5인 파이프라인)" if strict else "Fast"
    return (
        f"다음 텍스트를 humanize-korean 스킬 {mode} 모드로 윤문해줘. "
        f"먼저 그 스킬 SKILL.md frontmatter 의 version 값을 <<<V>>> 와 <<</V>>> 사이에 "
        f"그대로 출력하고(예: <<<V>>>2.4.0<<</V>>>), 이어서 "
        f"설명·헤딩·지표 전부 빼고 윤문된 본문만 반드시 {_START} 와 {_END} 사이에 "
        f"한 덩어리로 출력해. 파일은 만들지 마.\n\n텍스트:\n" + text
    )


_PATH_TAG = re.compile(r"<<<P>>>\s*(\S+?)\s*<<</P>>>")


def run_humanize_pipeline(
    text: str, *, skill: str = "humanize-korean", model: str | None = None,
    timeout: int = 1200,
) -> tuple[str, str]:
    """**제품이 실제로 도는 경로**로 스킬을 실행한다 — 파일 생성 허용.

    `run_humanize` 는 "파일은 만들지 마"라고 지시해서 shim·게이트가 통째로 빠진
    경로를 잰다. 그건 우리가 배포하는 동작이 아니다. 이 함수는 스킬이
    `_workspace/{run_id}/` 를 만들고 게이트를 돌리게 둔 뒤 산출물을 돌려준다.

    반환: (final.md 내용, run_dir 경로).

    `--add-dir` 에 **레포도 넣는다.** 임시 작업 디렉터리만 허용하면 monolith 가
    룰북(`references/quick-rules.md`) 읽기를 권한 거부당해 degraded mode 로 돈다
    (실측 2026-09-05 — 카테고리 ID 가 정식 룰북 대조가 아닌 근사 매핑이 된다).
    """
    if not CLAUDE_BIN:
        raise SkillUnavailable("`claude` CLI를 찾을 수 없음 (Claude Code 설치 필요)")
    workdir = tempfile.mkdtemp(prefix="humanize_pipeline_")
    with open(os.path.join(workdir, "input.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    prompt = (
        f"{skill} 스킬로 {workdir}/input.txt 의 내용을 윤문해줘. "
        f"스킬을 정상 절차대로(shim·게이트 포함) 실행해서 {workdir} 아래에 "
        f"_workspace/{{run_id}}/ 산출물을 남겨. 마지막에 final.md 의 절대경로만 "
        f"<<<P>>> 와 <<</P>>> 사이에 출력해."
    )
    cmd = [CLAUDE_BIN, "--plugin-dir", _REPO_ROOT, "--add-dir", _REPO_ROOT,
           "--add-dir", workdir, "--permission-mode", "acceptEdits"]
    if model:
        cmd += ["--model", model]
    cmd += ["-p", prompt]
    try:
        proc = subprocess.run(
            cmd, cwd=workdir, stdin=subprocess.DEVNULL, capture_output=True,
            text=True, timeout=timeout, env=_clean_env(),
        )
    except subprocess.TimeoutExpired as exc:
        raise SkillUnavailable(f"claude 호출 타임아웃 ({timeout}s)") from exc

    out = proc.stdout or ""
    if _QUOTA_RE.search(out):
        raise QuotaExhausted(out.strip()[:120])
    match = _PATH_TAG.search(out)
    if not match or not os.path.isfile(match.group(1)):
        raise SkillUnavailable(f"final.md 경로 파싱 실패. 원출력 끝부분: {out[-200:]!r}")
    final = match.group(1)
    with open(final, encoding="utf-8") as f:
        return f.read(), os.path.dirname(final)


def run_humanize(
    text: str, *, strict: bool = False, timeout: int = 300, model: str | None = None
) -> str:
    """스킬을 실제 호출해 윤문본을 반환. 실패 시 SkillUnavailable.

    model: `claude --model` 로 넘길 모델 ID(예: "claude-sonnet-5").
           None 이면 CLI 기본 모델. 모델 간 품질 비교(scripts/eval_baseline.py)에 쓴다.
    """
    if not CLAUDE_BIN:
        raise SkillUnavailable("`claude` CLI를 찾을 수 없음 (Claude Code 설치 필요)")
    # 레포를 플러그인으로 직접 로드한다 — 전역 설치본이 아니라 이 코드를 테스트한다.
    cmd = [CLAUDE_BIN, "--plugin-dir", _REPO_ROOT]
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
            env=_clean_env(),
        )
    except subprocess.TimeoutExpired as exc:
        raise SkillUnavailable(f"claude 호출 타임아웃 ({timeout}s)") from exc

    out = proc.stdout or ""
    if _QUOTA_RE.search(out):
        raise QuotaExhausted(out.strip()[:120])
    version = _VERSION_TAG.search(out)
    expected = repo_skill_version()
    if not version:
        raise SkillUnavailable(
            f"스킬 버전 태그가 없음 — 어느 사본이 응답했는지 확인 불가. "
            f"원출력 앞부분: {out[:200]!r}"
        )
    if version.group(1) != expected:
        raise SkillUnavailable(
            f"다른 사본이 응답했다: 스킬 v{version.group(1)} != 레포 v{expected}. "
            f"전역 설치본(~/.claude/skills)이 우선했을 가능성 — 그 상태의 결과는 "
            f"이 레포에 대한 판정이 아니다."
        )
    match = _SENTINEL.search(out)
    if not match:
        raise SkillUnavailable(f"센티넬 파싱 실패. 원출력 앞부분: {out[:200]!r}")
    return match.group(1).strip()
