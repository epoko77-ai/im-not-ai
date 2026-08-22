"""humanize-korean E2E 판정 헬퍼 (순수 함수, stdlib only, CI-safe).

비결정적인 부분(원문 -> 윤문본)은 스킬이 out-of-band로 생성한다.
여기 함수들은 주어진 (src, out) 쌍을 불변식/밴드/지표델타로 검증한다.
문자열 정답 비교는 하지 않는다.
"""
from __future__ import annotations

import difflib
import os
import re
import sys

def _find_ref() -> str:
    """metrics.py 위치를 레이아웃 무관하게 탐색.

    - 스킬-로컬 설치: tests/ 옆 ../references
    - 포크 레포 루트: tests/../skills/humanize-korean/references
    """
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = (
        "../references",
        "../skills/humanize-korean/references",
    )
    for rel in candidates:
        cand = os.path.abspath(os.path.join(here, rel))
        if os.path.exists(os.path.join(cand, "metrics.py")):
            return cand
    return os.path.abspath(os.path.join(here, candidates[0]))


_REF = _find_ref()


def change_rate(src: str, out: str) -> float:
    """문자 단위 변경률 [0,1]. 0=동일. difflib 유사도의 여집합.

    autojunk=False 는 SSOT(metrics_v2.change_rate)와 동일 조건이다. 켜진 채 두면
    200자 이상 반복 텍스트에서 빈출 문자가 정크 처리돼 게이트와 전혀 다른 값이 나온다.
    """
    return 1.0 - difflib.SequenceMatcher(None, src, out, autojunk=False).ratio()


def missing_protected_tokens(out: str, tokens: list[str]) -> list[str]:
    """윤문본에서 사라진 보호 토큰(고유명사·수치·인용 등) 목록. 비어야 fidelity PASS."""
    return [t for t in tokens if t not in out]


_SENT = re.compile(r"[.!?…\n]+")
_TAIL = re.compile(r"[\"'”’》」』)\]]+$")
_HAMNIDA = re.compile(r"(니다|니까)$")
_HAEYO = re.compile(r"(요|죠)$")


def register_of(text: str) -> str:
    """종결어미 기반 대략적 화계 분류: 합니다 / 해요 / 반말 / unknown (최빈값)."""
    counts = {"합니다": 0, "해요": 0, "반말": 0}
    for raw in _SENT.split(text):
        s = _TAIL.sub("", raw.strip()).strip()
        if not s:
            continue
        if _HAMNIDA.search(s):
            counts["합니다"] += 1
        elif _HAEYO.search(s):
            counts["해요"] += 1
        else:
            counts["반말"] += 1
    top = max(counts, key=counts.get)
    return top if counts[top] > 0 else "unknown"


def signal(text: str, name: str) -> float:
    """references/metrics.py의 정량 시그널 함수를 이름으로 호출."""
    if _REF not in sys.path:
        sys.path.insert(0, _REF)
    import metrics  # noqa: E402 (sys.path mutation intentional)

    fn = getattr(metrics, name, None)
    if fn is None:
        # v2 전용 시그널(double_passive_count·by_passive_count 등)은 metrics_v2 에만
        # 있다. v1 에서 못 찾으면 v2 로 넘어가야 eval 스냅샷에서 통째로 빠지지 않는다.
        import metrics_v2  # noqa: E402

        fn = getattr(metrics_v2, name)
    return float(fn(text))
