#!/usr/bin/env python3
"""영어 정량 지표 + route_hint.

한국어와 다른 점: 정규식 티 탐지에 기대지 않는다. 영어 스파이크(2026-09-02)에서
C-8 대구 정규식의 첫 재현율이 0/6 이었다 — 한국어는 교착어라 티가 형태소에
고정되지만 영어는 같은 수사를 여러 통사 프레임으로 흩뿌린다. 그래서 결정적
사전 채점은 **계측형 + 렉시콘**만 하고, 통사 프레임 탐지는 윤문 콜에 맡긴다.

근거 등급: 렉시콘 E2(Kobak, 원자료 확인) · 계측 임계 E3(자체 스파이크 1회).
E1 없음 — 그래서 heavy 는 길이 기준에서만 신뢰하고 finalize 경로는 열지 않는다.

표준 라이브러리만.
"""
from __future__ import annotations

import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_CORE = os.path.abspath(os.path.join(_HERE, "..", "..", "core"))
if _CORE not in sys.path:
    sys.path.insert(0, _CORE)

from metrics_universal import compute_universal  # noqa: E402

# 영어 장문 임계 — 35 단어. 한국어 100자에 대응하는 발현형 임계다
# (E-1 의 불변량은 분산이고 임계는 언어별, taxonomy E-1 참조).
LONG_SENTENCE_TOKENS = 35

# 한국어 shim 과 같은 규약 — 길이로 heavy 가 되는 유일한 조건.
ROUTE_HEAVY_MIN_CHARS = 15000

# 렉시콘 히트 임계(/1000 tokens). **E3 — 자체 스파이크 1회의 잠정값.**
# router_eligible 12건만 세므로 히트는 희소하다 — 1건만 나와도 유의한 신호다.
# (전체 407건을 세면 this·across·however 때문에 평범한 영어도 100+/1k 가 된다.)
LIGHT_MAX_LEXICON_PER_1K = 0.0
HEAVY_MIN_LEXICON_PER_1K = 4.0

# ⚠️ 분산 임계 폐기 (2026-09-03, E1 실측).
# 초판 UNIFORM_DISPERSION_MAX = 8.0 은 **인간 학술 초록 42편 중 21편(50%)을
# AI 로 오판**했다. 스파이크의 '대조군'이 마크다운 표·리스트가 섞인 문서라
# 분산이 16~18 로 부풀려져 있었고, 그걸 인간 범위로 착각한 결과다.
# 실측: 인간 중앙값 8.01 (2.32~16.3) vs AI 6.98 (3.5~12.37) — AUC 0.380,
# |0.5차| 0.120 으로 **판별력 약함**. 라우터 판정에서 뺀다.
#
# 대신 쉼표 계열을 쓴다 — 같은 실측에서 훨씬 강했다:
#   comma_segment_length  AUC 0.149 (|0.5차| 0.351)  AI 가 짧게 끊는다
#   comma_inclusion_rate  AUC 0.719 (|0.5차| 0.219)  AI 가 많이 쓴다
# 임계는 인간 사분위수 기반 (lang/en/baseline.json recommended_thresholds).
# ── 시대 강건성 우선 배치 (2026-09-03) ──────────────────────────
# 인간 코퍼스는 2015~2020, AI 는 2026 이다. 인간 초기 vs 후기로 시대 효과만
# 따로 재보니 지표마다 오염도가 크게 달랐다(baseline.json era_confound):
#   EN-2 be동사 13% · EN-1 분사절 15% · 분산 40% · 쉼표 계열 55~58%
# 쉼표는 인간 사용이 연 +0.079 로 오르는 중이라, 외삽하면 2026 인간(1.59)이
# AI(1.67)에 근접한다. R²=0.487 이라 외삽은 못 믿지만 위험은 실재한다.
# → **시대에 강건한 EN-1·EN-2 를 주 신호로, 쉼표는 보조로 쓴다.**
EN1_PARTICIPIAL_AI_MIN = 6.37   # 인간 상위 25% — 초과면 AI 방향 (AUC 0.726, 시대 15%)
EN2_BE_VERB_AI_MAX = 12.87      # 인간 하위 25% — 미만이면 AI 방향 (AUC 0.238, 시대 13%)

# 보조 — 판별력은 높으나 시대 교란이 크다(55~58%).
COMMA_USAGE_AI_MIN = 1.26      # 인간 상위 25% — 이 초과면 AI 방향 (AUC 0.888, 최강)
COMMA_SEGMENT_AI_MAX = 10.82   # 인간 하위 25% — 이 미만이면 AI 방향 (AUC 0.851)
COMMA_INCLUSION_AI_MIN = 73.3  # 인간 상위 25% — 이 초과면 AI 방향 (AUC 0.719)

# 밀도 지표를 쓰기 위한 최소 분량. 39토큰 글에서 렉시콘 1건이면 25.6/1k 가
# 나와 heavy 로 튄다 — 비율이 아니라 분모가 만든 수다.
# `core/principles.md` G3 의 "밀도 지표를 볼 때는 분모를 함께 본다"가
# 라우터 자신에게도 적용된다. 이 아래에서는 판정을 하지 않고 standard 로 보낸다.
#
# ⚠️ **초판 200 은 과잉 보정이었다(2026-09-03 실측).** 39토큰 사고 하나를 보고
# 잡은 값인데, arXiv 초록 중앙값이 162토큰이라 **코퍼스의 71~86% 를 삼켰다** —
# 라우터가 사실상 꺼져 있었고, "인간 83% standard" 같은 검증 수치가 신호가
# 아니라 이 가드를 측정한 값이었다.
# 임계별 분리도(AI heavy율−인간 heavy율 + 인간 light율−AI light율):
#     200 → +0.19   150 → +0.88   120 → +0.95   100 → +0.95
# 120 에서 포화하므로 120 을 쓴다. 120토큰에서 EN-1 1건 = 8.3/1k 로 임계(6.37)를
# 넘는데, 인간 중앙값이 0.00 이라 1건도 유의하다.
MIN_TOKENS_FOR_RATE = 120

_WORD_BOUNDARY_CACHE: dict[int, re.Pattern] = {}

# 시대 강건 신호 — 통사 프레임으로 잡는다(표면 어휘 목록은 장르를 타서 실패한다).
_EN1_RE = re.compile(r",\s+\w+ing\b", re.I)
_EN2_RE = re.compile(r"\b(?:is|are|was|were)\b", re.I)
# 3항 등위(blader #10 forced groups of three) — `A, B, and C` 프레임.
# R2 블로그 실측에서 이 장르 최강 신호였다: AUC 0.681, 인간 중앙값이 세 출처
# 모두 0.00, 3모델 0.655~0.704. 승격 기준(0.20)에는 0.019 미달이라 **규칙으로는
# 승격하지 않았지만**, 라우터 신호로는 쓴다 — 라우터는 규칙이 아니라 경로 배정이다.
# EN-3(3항 등위). 라우터 신호이자 룰북 규칙이다 — 라우터가 지목하면 윤문 콜이
# 고칠 처방을 갖고 있어야 한다. AUC 0.737(인간 100 vs AI 136, 4모델 2계열).
_TRICOLON_RE = re.compile(
    r"\b[\w-]+(?:\s+[\w-]+){0,2},\s+[\w-]+(?:\s+[\w-]+){0,2},\s+and\s+[\w-]+", re.I
)

# ── 장르별 임계 (R2 실측 2026-09-04) ────────────────────────────────────
#
# **임계는 장르에 종속된다.** 초록 보정 임계(쉼표 절 < 10.82)를 블로그에 그대로
# 쓰면 인간 중앙값 9.68 이 통째로 AI 쪽에 떨어져 라우터가 죽는다 — 분리도 0.29,
# 인간 에세이의 21% 를 heavy 로 오탐했다. 블로그 셀 보정값으로 바꾸면 0.65 다
# (모델별 0.58~0.78 · 인간 출처 홀드아웃 0.53~0.74 · 독립 코퍼스 0.65).
#
# 분리도 정의: AI heavy율 − 인간 heavy율 + 인간 light율 − AI light율.
THRESHOLD_SETS = {
    "abstract": {
        "separation": 0.95,
        "source": "arXiv cs.CL 인간 42 vs AI 21",
    },
    "blog": {
        "comma_segment_max": 8.57,   # 인간 하위 25% (블로그 100편)
        "tricolon_min": 0.0,         # 1건이라도 있으면 AI 방향
        "en1_min": 0.0,
        "separation": 0.65,
        "source": "LessWrong·Paul Graham·SSC 인간 100 vs AI 102",
    },
}
# shim 의 --genre 값을 임계 셀로 푼다. 측정된 셀은 둘뿐이라 나머지는 blog 로
# 보낸다(shim 기본값이 essay 이고, 산문 장르가 초록보다 블로그에 가깝다).
GENRE_TO_SET = {"abstract": "abstract"}
DEFAULT_SET = "blog"


def _per_1k(text: str, rx: re.Pattern, tokens: int) -> float:
    return round(len(rx.findall(text)) / (tokens or 1) * 1000, 2)


def load_lexicon(path: str | None = None) -> dict:
    with open(path or os.path.join(_HERE, "lexicon.json"), encoding="utf-8") as f:
        return json.load(f)


def _entries(lexicon: dict, router_only: bool) -> list[dict]:
    if not router_only:
        return lexicon["entries"]
    return [e for e in lexicon["entries"] if e.get("router_eligible")]


def _matcher(lexicon: dict, router_only: bool = True) -> re.Pattern:
    key = (id(lexicon), router_only)
    cached = _WORD_BOUNDARY_CACHE.get(key)
    if cached is not None:
        return cached
    # 표면형을 그대로 매칭한다. 원자료가 굴절형을 각각 담고 있으므로
    # 접미사 확장은 불필요하고, 측정되지 않은 형태를 만들어 오탐이 된다.
    # 긴 표제어를 먼저 둬야 교체 우선순위가 맞는다.
    words = sorted(
        {e["word"] for e in _entries(lexicon, router_only)}, key=len, reverse=True
    )
    rx = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in words) + r")\b", re.I)
    _WORD_BOUNDARY_CACHE[key] = rx
    return rx


def lexicon_hits(
    text: str, lexicon: dict, router_only: bool = True
) -> tuple[int, dict[str, int]]:
    """총 히트 수와 family 별 분해. 매칭은 표면형 완전일치(단어 경계).

    ``router_only=True``(기본)는 ``router_eligible`` 항목만 센다 — 목록 전체는
    '기준선 대비 증가분'이라 초고빈도어를 포함하며 라우터 신호로 쓸 수 없다
    (lexicon.json 의 ``router_policy`` 참조). ``False`` 는 룰북·감사용 전수 계수.
    """
    fam_of = {e["word"]: e["family"] for e in lexicon["entries"]}
    per: dict[str, int] = {}
    total = 0
    for m in _matcher(lexicon, router_only).finditer(text):
        fam = fam_of.get(m.group(0).lower(), "unclassified")
        per[fam] = per.get(fam, 0) + 1
        total += 1
    return total, per


def compute_all_en(
    text: str, lexicon_path: str | None = None, genre: str = "essay"
) -> dict:
    """영어 정량 점수 + route_hint. shim 의 유일한 진입점.

    ``genre`` 는 임계 셀을 고른다(THRESHOLD_SETS). 측정된 셀은 abstract·blog 뿐이다.
    """
    universal = compute_universal(
        text, long_threshold=LONG_SENTENCE_TOKENS, unit="tokens"
    )
    lexicon = load_lexicon(lexicon_path)
    total, per = lexicon_hits(text, lexicon, router_only=True)
    all_total, _ = lexicon_hits(text, lexicon, router_only=False)
    tokens = universal["tokens"] or 1
    per_1k = round(total / tokens * 1000, 2)
    chars = len(text)
    dispersion = universal["sentence_length_dispersion"]

    threshold_set = GENRE_TO_SET.get(genre, DEFAULT_SET)

    if chars > ROUTE_HEAVY_MIN_CHARS:
        hint = "heavy"
        reason = f"{chars:,} chars (>{ROUTE_HEAVY_MIN_CHARS:,}) — 초장문"
    elif tokens < MIN_TOKENS_FOR_RATE:
        hint = "standard"
        reason = (
            f"{tokens} tokens (<{MIN_TOKENS_FOR_RATE}) — 밀도 판정 불가, "
            f"기본 경로 (렉시콘 {total}건 · 분산 {dispersion})"
        )
    elif threshold_set == "blog":
        # 블로그 셀 보정 3신호. 쉼표 계열 나머지·EN-2·분산은 이 장르에서
        # **모델마다 부호가 반대**라(G1 미통과) 라우터에 넣지 않는다.
        cfg = THRESHOLD_SETS["blog"]
        seg = universal["comma_segment_length"]
        en1 = _per_1k(text, _EN1_RE, tokens)
        tri = _per_1k(text, _TRICOLON_RE, tokens)
        signals = []
        if seg and seg < cfg["comma_segment_max"]:
            signals.append(f"쉼표 절 {seg}어(<{cfg['comma_segment_max']})")
        if tri > cfg["tricolon_min"]:
            signals.append(f"3항 등위 {tri}/1k")
        if en1 > cfg["en1_min"]:
            signals.append(f"분사절 {en1}/1k")
        # 렉시콘은 이 장르에서 거의 발화하지 않는다(R2 실측: 인간 0건율 100% ·
        # AI 99% · AUC 0.505 — Kobak 목록이 생의학 초록 어휘라서다). 그래도
        # 남긴다: 독립 근거선(E2)이고, 실제로 뜨면 그건 의미 있는 신호다.
        # 분리도 영향은 0.65 → 0.66 으로 잡음 수준이다.
        if per_1k >= HEAVY_MIN_LEXICON_PER_1K:
            signals.append(f"렉시콘 {per_1k}/1k")
        if len(signals) >= 2:
            hint, reason = "heavy", "AI 신호 " + " + ".join(signals)
        elif signals:
            hint, reason = "standard", "AI 신호 " + " · ".join(signals)
        else:
            hint = "light"
            reason = (
                f"쉼표 절 {seg}어 · 3항 등위 {tri}/1k · 분사절 {en1}/1k — "
                f"인간 범위(블로그 셀 보정)"
            )
    else:
        seg = universal["comma_segment_length"]
        incl = universal["comma_inclusion_rate"]
        usage = universal["comma_usage_rate"]
        # 판별력 순으로 센다. 교차언어 확인: 한국어 abstract 셀에서도
        # usage 1.39배·inclusion 1.37배로 같은 방향이다(baseline.json cross_language).
        en1 = _per_1k(text, _EN1_RE, tokens)
        en2 = _per_1k(text, _EN2_RE, tokens)
        # 시대 강건 신호 우선.
        signals = []
        if en1 > EN1_PARTICIPIAL_AI_MIN:
            signals.append(f"분사절 {en1}/1k(>{EN1_PARTICIPIAL_AI_MIN})")
        if en2 < EN2_BE_VERB_AI_MAX:
            signals.append(f"be동사 {en2}/1k(<{EN2_BE_VERB_AI_MAX})")
        if usage > COMMA_USAGE_AI_MIN:
            signals.append(f"문장당 쉼표 {usage}(>{COMMA_USAGE_AI_MIN})")
        if seg and seg < COMMA_SEGMENT_AI_MAX:
            signals.append(f"쉼표 절 {seg}어(<{COMMA_SEGMENT_AI_MAX})")
        if incl > COMMA_INCLUSION_AI_MIN:
            signals.append(f"쉼표 포함률 {incl}%(>{COMMA_INCLUSION_AI_MIN})")
        if per_1k >= HEAVY_MIN_LEXICON_PER_1K:
            signals.append(f"렉시콘 {per_1k}/1k")

        if len(signals) >= 2:
            hint = "heavy"
            reason = "AI 신호 " + " + ".join(signals)
        elif signals:
            hint = "standard"
            reason = "AI 신호 " + " · ".join(signals)
        else:
            hint = "light"
            reason = (
                f"문장당 쉼표 {usage} · 절 {seg}어 · 포함률 {incl}% · "
                f"렉시콘 {per_1k}/1k — 인간 범위, 이미 잘 쓴 글"
            )

    return {
        "lang": "en",
        "char_count": chars,
        "universal": universal,
        "lexicon": {
            "total": total,
            "per_1k": per_1k,
            "by_family": per,
            "all_entries_total": all_total,
        },
        "genre": genre,
        "threshold_set": threshold_set,
        "route_hint": hint,
        "route_reason": reason,
        "route_signals": {
            "en1_participial_per_1k": _per_1k(text, _EN1_RE, tokens),
            "en2_be_verb_per_1k": _per_1k(text, _EN2_RE, tokens),
            "tricolon_per_1k": _per_1k(text, _TRICOLON_RE, tokens),
            "lexicon_total": total,
            "lexicon_per_1k": per_1k,
            "dispersion": dispersion,
            "long_sentence_rate": universal["long_sentence_rate"],
            "comma_inclusion_rate": universal["comma_inclusion_rate"],
            "char_count": chars,
        },
        "evidence_note": (
            "렉시콘 E2(Kobak, 생의학 초록 — 장르 불일치 캐비엇). 라우터에는 "
            "논문이 명시 호명한 12건만 쓴다(목록 전체는 증가분 집합이라 "
            "초고빈도어 포함 — lexicon.json router_policy). 임계 E3(자체 "
            "스파이크 1회). 임계 셀 E1 — abstract(분리도 0.95) · blog(0.65). "
            "heavy 는 길이 기준에서만 신뢰하고 finalize 경로는 열지 않는다."
        ),
    }
