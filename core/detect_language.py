#!/usr/bin/env python3
"""언어 감지 — 유니코드 스크립트 비율.

통계 모델도 의존성도 쓰지 않는다. 한글 음절 블록 대 라틴 문자의 비율만으로
ko/en 은 갈린다. 한국어 글은 전문용어 병기(B-1)로 라틴 문자가 많이 섞이므로
"한글이 유의하게 있으면 한국어"로 판정한다 — 반대 방향(영어 글에 한국어를
인용하는 경우)은 한글 비율이 훨씬 낮게 나오기 때문에 이 비대칭이 안전하다.

셋째 언어가 필요해지면 그때 확장한다. 공백 없는 표기 체계(중국어·일본어)는
이 함수의 사정거리 밖이다 — 그 언어를 다룰 때 스크립트 판정을 추가한다.
"""
from __future__ import annotations

import re

_HANGUL_RE = re.compile(r"[가-힣ᄀ-ᇿㄱ-ㆎ]")
_LATIN_RE = re.compile(r"[A-Za-z]")

# 한글 비율이 이 값을 넘으면 한국어. 병기가 많은 한국어 글도 한글이 보통
# 40% 이상이고, 한국어를 인용하는 영어 글은 5% 미만이다.
KO_MIN_RATIO = 0.15


def detect_language(text: str) -> str:
    """``"ko"`` | ``"en"`` | ``"unknown"``."""
    hangul = len(_HANGUL_RE.findall(text))
    latin = len(_LATIN_RE.findall(text))
    total = hangul + latin
    if total == 0:
        return "unknown"
    if hangul / total >= KO_MIN_RATIO:
        return "ko"
    return "en" if latin else "unknown"
