#!/usr/bin/env python3
"""언어 무관 계측 지표 — 분산·쉼표·길이 분포.

왜 커널인가: 영어 스파이크(2026-09-02)에서 어휘·정규식형 지표는 이식에 실패했으나
(C-8 첫 정규식 재현율 0/6) 계측형은 코드 수정 0으로 넘어갔고 가장 잘 분리했다
(AI 에세이 문장길이 stdev 6.7~6.8 vs 대조 16.3~18.8).

E-1 의 불변량은 '장문 부재'가 아니라 '분산 부족'이다(Reinhart et al. 2025, PNAS).
언어별 발현형은 unit 과 threshold 로 흡수한다 — 한국어 chars/100, 영어 tokens/35.

표준 라이브러리만. 형태소 분석 없음.
"""
from __future__ import annotations

import re
import statistics

# 마침표·물음표·느낌표 + 한중일 종지부. 뒤따르는 닫는 따옴표·괄호까지 문장에 포함.
_SENT_END_RE = re.compile(r'(?<=[.!?。！？…])[\'"”’」』)\]]*\s+')

# 어절/단어 = 공백 분리. 한국어 어절과 영어 word 를 같은 규칙으로 센다
# (metrics.py 의 _EOJEOL_SPLIT_RE 와 동일 관례). 공백 없는 표기 체계
# (중국어·일본어)는 이 함수의 사정거리 밖이다.
_WS_RE = re.compile(r"\s+")

# 쉼표 — ASCII + 전각. 아랍어 쉼표(،)까지 넓히지 않는 이유는 현재 대상 언어가
# 한국어·영어뿐이고, 근거 없는 확장은 이 저장소의 증거 기준에 어긋나서다.
_COMMA_RE = re.compile(r"[,，]")

_VALID_UNITS = ("chars", "tokens")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_END_RE.split(text) if s.strip()]


def _size(sentence: str, unit: str) -> int:
    if unit == "chars":
        return len(sentence)
    if unit == "tokens":
        return len([t for t in _WS_RE.split(sentence) if t])
    raise ValueError(f"unit 은 {_VALID_UNITS} 중 하나 — 받은 값: {unit!r}")


def sentence_length_dispersion(text: str, unit: str = "tokens") -> float:
    """문장 길이의 모표준편차. 낮을수록 메트로놈처럼 균일(AI 방향)."""
    if unit not in _VALID_UNITS:
        raise ValueError(f"unit 은 {_VALID_UNITS} 중 하나 — 받은 값: {unit!r}")
    sizes = [_size(s, unit) for s in split_sentences(text)]
    if len(sizes) < 2:
        return 0.0
    return round(statistics.pstdev(sizes), 2)


def long_sentence_rate(text: str, threshold: int, unit: str = "tokens") -> float:
    """임계 이상 문장의 비율(%). 한국어 chars/100, 영어 tokens/35 가 기본 대응."""
    sentences = split_sentences(text)
    if not sentences:
        return 0.0
    hits = sum(1 for s in sentences if _size(s, unit) >= threshold)
    return round(hits / len(sentences) * 100, 2)


def comma_inclusion_rate(text: str) -> float:
    """쉼표를 1개 이상 포함한 문장의 비율(%). KatFish 인간 26% / LLM 61% 축."""
    sentences = split_sentences(text)
    if not sentences:
        return 0.0
    hits = sum(1 for s in sentences if _COMMA_RE.search(s))
    return round(hits / len(sentences) * 100, 2)


def comma_usage_rate(text: str) -> float:
    """문장당 평균 쉼표 수.

    한국어 `metrics.py::comma_usage_rate` 와 **같은 정의**다 — 두 언어의
    baseline 셀을 같은 축에서 대조하기 위해 계산식을 그대로 옮겼다.
    한국어 실측(baseline.json): abstract 1.39배 · essay 2.27 · column 4.92 · report 3.16.
    """
    sentences = split_sentences(text)
    if not sentences:
        return 0.0
    return round(sum(len(_COMMA_RE.findall(s)) for s in sentences) / len(sentences), 2)


def comma_segment_length(text: str) -> float:
    """쉼표로 분절된 절의 평균 토큰 수."""
    segments = []
    for sentence in split_sentences(text):
        for piece in _COMMA_RE.split(sentence):
            tokens = [t for t in _WS_RE.split(piece) if t]
            if tokens:
                segments.append(len(tokens))
    if not segments:
        return 0.0
    return round(statistics.mean(segments), 2)


def compute_universal(
    text: str, *, long_threshold: int, unit: str = "tokens"
) -> dict[str, float]:
    """전 지표를 한 번에. shim 이 route_hint 를 낼 때 쓰는 진입점."""
    sentences = split_sentences(text)
    tokens = [t for t in _WS_RE.split(text) if t]
    return {
        "sentences": len(sentences),
        "tokens": len(tokens),
        "sentence_length_dispersion": sentence_length_dispersion(text, unit),
        "long_sentence_rate": long_sentence_rate(text, long_threshold, unit),
        "comma_inclusion_rate": comma_inclusion_rate(text),
        "comma_usage_rate": comma_usage_rate(text),
        "comma_segment_length": comma_segment_length(text),
    }
