#!/usr/bin/env python3
"""변경률 — 철칙 #4 의 계측. 언어 무관(문자 diff).

metrics_v2.py 에서 분리했다. 영어 스파이크(2026-09-02)에서 이 함수가 무수정으로
영어에 동작함이 확인됐고(12.8%, gate exit 0), 언어팩이 한국어 스킬 디렉터리에
의존하지 않도록 커널로 올린다. metrics_v2 는 하위 호환을 위해 재수출한다.

로직은 이동 시점에 한 글자도 바꾸지 않았다.
"""
from __future__ import annotations

import difflib
import re


# 철칙 #4 게이트 임계값. change_rate() 반환값과 직접 비교한다.
CHANGE_RATE_WARN = 0.30   # 30% 초과 — 경고, 과윤문 점검
CHANGE_RATE_ABORT = 0.50  # 50% 초과 — 강제 중단

# 마크업 전용 줄: 코드 펜스·수평선·표 구분선 등 — ignore_markup 모드에서 제거.
_MARKUP_ONLY_LINE_RE = re.compile(
    r"^\s*(?:```.*|~~~.*|-{3,}|\*{3,}|={3,}|\|[\s:\-|]*)\s*$"
)
# 줄머리 마크업 장식: 헤딩(#)·불릿(-·*·+)·번호 목록·인용(>) — 장식만 벗기고
# 텍스트 내용은 보존한다.
_MARKUP_PREFIX_RE = re.compile(r"^\s*(?:#{1,6}\s+|>\s?|[-*+]\s+|\d{1,3}[.)]\s+)")


def _strip_markup(text: str) -> str:
    """Drop markup-only lines and leading markup decoration, keep content."""
    kept: list[str] = []
    for line in text.splitlines():
        if _MARKUP_ONLY_LINE_RE.match(line):
            continue
        kept.append(_MARKUP_PREFIX_RE.sub("", line))
    return "\n".join(kept)


def change_rate(before: str, after: str, ignore_markup: bool = False) -> float:
    """윤문 전후 문자 기반 변경률 — 철칙 #4 게이트의 SSOT.

    이 함수의 반환값이 변경률의 단일 진실 원천(SSOT)이며, 에이전트의
    재량(눈대중) 자가 산출을 대체한다. 게이트 판정은 반드시 이 값과
    ``CHANGE_RATE_WARN``(0.30 경고) / ``CHANGE_RATE_ABORT``(0.50 강제 중단)
    상수를 비교해 내린다.

    계산: ``difflib.SequenceMatcher`` 문자 단위 유사도의 보수
    (``1 - ratio``). 0.0(동일) ~ 1.0(전면 교체) 범위.

    ``ignore_markup=True``이면 양쪽 텍스트에서 마크업 전용 줄(코드 펜스·
    수평선·표 구분선)을 제거하고 줄머리 장식(헤딩 #·불릿·번호·인용 >)을
    벗긴 뒤 비교한다 — 헤딩·마크업 삭제가 본문 변경률을 부풀리는 문제
    (2026-04-26-001 run에서 44.7% 중 상당분이 마크업 삭제)의 보정용.
    기본값은 순수 문자 diff.
    """
    if ignore_markup:
        before = _strip_markup(before)
        after = _strip_markup(after)
    if not before and not after:
        return 0.0
    matcher = difflib.SequenceMatcher(None, before, after, autojunk=False)
    return 1.0 - matcher.ratio()
