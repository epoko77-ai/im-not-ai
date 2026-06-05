"""Humanize KR v2.0 quantitative metrics calculator.

Extends v1.6 metrics.py with post-editese 3축 (simplification·normalisation·
interference) and 8 translation-type detection signals from the Korean
machine-translation/post-editing literature (Toral 2019; Schmaltz 2020;
보고서 T1~T8).

Hard rule: standard library ONLY (json/re/math/collections/os/sys/argparse/
statistics). No konlpy/bareun/mecab/spaCy. Morphological analysis is
approximated with regex + suffix dictionaries (한자어 -성·-적·-화·-도·-력·-감·-원,
평서형 -한다·-된다·-이다, 진행형 -고 있다, 이중 조사 -에서의·-에로의·-으로의·-에의·-으로부터의·-로부터의).

Versioning:
- v1.6 8 functions (comma_inclusion_rate ... lexical_diversity) are imported
  *as-is* from references/metrics.py (signature + return preserved). DO NOT
  redefine them here. Regression-safe.
- v2.0 adds 14 NEW pure functions for post-editese + T1~T8 detection.

This file lives in `_workspace/v2.0-YYYY-MM-DD/03_metrics/`. Phase 6
integrator will merge it into the project's references/metrics.py.

CLI:
    python metrics_v2.py --input run/01_input.txt \
        --genre essay --output run/00_metrics_v2.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import Counter
from statistics import StatisticsError, mean, pstdev
from typing import Any

# ---------------------------------------------------------------------------
# Import v1.6 metrics module (regression-safe — signatures untouched)
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
_V1_METRICS_DIR = os.path.join(
    _PROJECT_ROOT, ".claude", "skills", "humanize-korean", "references"
)
if _V1_METRICS_DIR not in sys.path:
    sys.path.insert(0, _V1_METRICS_DIR)

import metrics as _v1  # noqa: E402  (sys.path mutation is intentional)

# Re-export the 8 v1.6 metric callables verbatim. They keep their original
# signatures and return shapes — `metrics_v2.comma_inclusion_rate(text)`
# is byte-identical to `metrics.comma_inclusion_rate(text)`.
comma_inclusion_rate = _v1.comma_inclusion_rate
comma_usage_rate = _v1.comma_usage_rate
ending_comma_rate = _v1.ending_comma_rate
comma_segment_length = _v1.comma_segment_length
conclusion_pivot_count = _v1.conclusion_pivot_count
safe_balance_count = _v1.safe_balance_count
hanja_nominalizer_density = _v1.hanja_nominalizer_density
lexical_diversity = _v1.lexical_diversity

# Reuse v1.6 internal helpers (private, regression-safe — we never mutate).
_split_sentences = _v1._split_sentences
_eojeols = _v1._eojeols
_strip_punct = _v1._strip_punct

VERSION = "v2.0"

# ---------------------------------------------------------------------------
# v2.0 module-level constants — sufix / lexicon dictionaries
# ---------------------------------------------------------------------------

# 한자어 명사화 접미사 v2.0 확장 — v1.6의 -성·-적·-화 + 보고서 T6 보강 4종.
# token-final 1글자 매칭. 토큰 길이 >= 2 가드는 함수 내부에서.
_HANJA_SUFFIXES_V2 = ("성", "적", "화", "도", "력", "감", "원")

# 평서형 종결 사전 — normalisation 축. 문장 마지막 어절의 어미를 매칭.
# 한자어 + 한다/된다/이다 형태가 가장 흔한 정규화 시그널.
_DECLARATIVE_ENDINGS = ("한다", "된다", "이다")

# 진행형 어미 — T8b. "~고 있다" 표층 매칭. 종결형/연결형 모두 포함.
# 부정형 "있지 않다", 의존명사 "있는" 은 별개. 정규식은 "고 있" 토큰
# 시작점 + 후속 "다/었/는" 등을 폭넓게 캡처.
_PROGRESSIVE_RE = re.compile(r"고\s*있(?:다|었|는|을|던|는다)")

# T2b 이중 피동 표층 어휘. 모두 "되어진/여진/혀진/려진" 등 피동 보조어간 +
# 피동 보조용언 중첩의 표층형. 단순 "되다" 는 정상 표현이므로 제외.
_DOUBLE_PASSIVE_TOKENS = (
    "되어진다",
    "되어졌다",
    "되어진",
    "되어지는",
    "여지다",
    "여진다",
    "여졌다",
    "여진",
    "잊혀진",
    "잊혀졌",
    "잊혀진다",
    "보여진다",
    "보여졌다",
    "보여진",
    "쓰여진다",
    "쓰여졌다",
    "쓰여진",
    "닫혀진",
    "열려진",
    "불려진",
    "놓여진",
)

# T2a "~에 의해 + 피동" — 피동 동사가 직후 N어절 안에 등장해야 매칭.
# 단순 "에 의해" 는 빈번한 자연 한국어이므로 제외 (보고서 T2 caveat).
_BY_PASSIVE_RE = re.compile(
    r"에\s*의(?:해|하여)\s+\S{0,12}?(?:되|받|당하|지)(?:다|었|어|ㄴ다|는다|는|ㄹ|을)"
)

# T3 인칭 대명사 — 영어 he/she/it/they 의 1대1 매핑.
# "그" 단독은 지시사·관형사로도 자주 쓰이므로 보수적으로 처리:
#   - "그" 뒤에 조사 "는/가/를/의/에게/에서/와/도/만" 이 붙은 경우만 인칭으로 본다.
#   - 그녀/그들/그것 은 거의 항상 인칭 대명사이므로 단독 매칭.
_PRONOUN_RE = re.compile(
    r"(?:그녀(?:는|가|를|의|에게|와|도|만)?"
    r"|그것(?:은|이|을|의|에|에게)?"
    r"|그들(?:은|이|을|의|에게|과|도)?"
    r"|그(?:는|가|를|의|에게|와|도|만)(?=\s|[\.,!?]|$))"
)

# T4 무정물·추상명사 + -들. 토큰 단위 매칭.
# 보고서 III.3.4.2 + pe_checklist PE5에서 "거의 모두 삭제 후보" 로 거론된
# 핵심 어휘셋. 사전은 보수적(false positive 줄임).
_INANIMATE_DEUL_TOKENS = (
    "데이터들",
    "정보들",
    "결과들",
    "연구들",
    "아이디어들",
    "방법들",
    "문제들",
    "의견들",
    "시스템들",
    "기술들",
    "사실들",
    "사례들",
    "이론들",
    "개념들",
    "현상들",
    "특징들",
    "요소들",
    "원인들",
    "영향들",
    "변화들",
    "기능들",
    "조건들",
    "기준들",
    "관점들",
    "원리들",
)

# T6 light verb construction — have/make 류 직역.
# "회의를 가지다·결정을 내리다" 식 light verb.
_HAVE_MAKE_LITERAL_TOKENS = (
    "가지고 있다",
    "가지고있다",
    "가지고 있는",
    "가지고있는",
    "가지고 있었",
    "가지고있었",
    "가지고 있으",
    "가지고있으",
    "갖고 있다",
    "갖고있다",
    "갖고 있는",
    "갖고있는",
    "을 가지다",
    "를 가지다",
    "을 가졌",
    "를 가졌",
    "을 가진다",
    "를 가진다",
    "을 만들다",
    "를 만들다",
    "을 만들었",
    "를 만들었",
    "을 만들어 낸",
    "를 만들어 낸",
    "을 만들어낸",
    "를 만들어낸",
    "회의를 가지",
    "회의를 가졌",
    "한번 봄을 가지",
    "결정을 내리",
    "결정을 내렸",
)

# T7 이중 조사 결합. caveat #5 (단순 ~의 제외) 정확히 반영.
# "에서의" 등 6종만 매칭 — 단일 ~의는 절대 매칭 안 됨.
_DOUBLE_PARTICLE_RE = re.compile(
    r"(?:에서의|에로의|으로의|에의|으로부터의|로부터의)"
)

# 단락 분리: 빈 줄 1개 이상.
_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")

# 종결어미 다양성 — 문장 마지막 종결어미 표층(보통 1~2음절 끝마디)을 키로 사용.
# verb stem(예: "결정한다"의 "결정") 부분은 제외하고 어미 부분(예: "한다")만 봐야
# 다양성 신호가 의미를 가진다. 따라서 마지막 2음절을 우선 키로 사용.
_ENDING_FINAL_RE = re.compile(r"([가-힣]{2})[\.!?]\s*$")
# 한 음절만 있는 문장(예: "와.")은 별도로 1음절 매칭.
_ENDING_FINAL_FALLBACK_RE = re.compile(r"([가-힣])[\.!?]\s*$")


# ---------------------------------------------------------------------------
# Local helpers (do not shadow v1.6)
# ---------------------------------------------------------------------------


def _split_paragraphs(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    return [p.strip() for p in _PARAGRAPH_SPLIT_RE.split(text) if p.strip()]


def _last_eojeol(sentence: str) -> str:
    toks = _eojeols(sentence)
    if not toks:
        return ""
    return _strip_punct(toks[-1])


def _all_tokens(text: str) -> list[str]:
    toks = [_strip_punct(t) for t in _eojeols(text)]
    return [t for t in toks if t]


# ---------------------------------------------------------------------------
# === v2.0 NEW METRICS ===
# Group A: simplification 축
# ---------------------------------------------------------------------------


def lexical_diversity_ttr(text: str) -> float:
    """Type-token ratio (TTR) over Korean eojeols — simplification axis.

    Identical computation to v1.6 ``lexical_diversity`` but exposed under the
    Toral 2019 simplification-axis name so the post-editese score can map
    cleanly. Returns 0.0 on empty input.
    """
    return lexical_diversity(text)


def lexical_density(text: str) -> float:
    """Content-word ratio — proxy for lexical density (simplification axis).

    Standard-library proxy: a token is counted as a *content word* if its
    final character is one of the v2.0 hanja nominalizer suffixes
    (-성·-적·-화·-도·-력·-감·-원), or if it ends with a verb/adjective
    declarative marker (-한다·-된다·-이다·-했다·-된다·-였다·-이었다·-답다·-스럽다·-롭다).
    Function words (조사·접속부사) are filtered out by length<2 and a small
    stopword list.

    Returns content_word_count / total_token_count in [0, 1].
    """
    tokens = _all_tokens(text)
    if not tokens:
        return 0.0
    stop = {
        "그리고", "그러나", "하지만", "또한", "또는", "혹은", "즉", "예를", "예컨대",
        "이는", "이것은", "그것은", "그러므로", "따라서",
    }
    content_suffixes = ("성", "적", "화", "도", "력", "감", "원")
    content_endings = (
        "한다", "된다", "이다", "했다", "였다", "었다",
        "답다", "스럽다", "롭다", "하다", "되다",
    )
    hits = 0
    for t in tokens:
        if len(t) < 2:
            continue
        if t in stop:
            continue
        if t[-1] in content_suffixes:
            hits += 1
            continue
        if any(t.endswith(end) for end in content_endings):
            hits += 1
    return hits / len(tokens)


def ending_diversity(text: str) -> float:
    """Sentence-ending diversity — unique endings / total sentences.

    Approximates 종결어미 다양성. Sentence is split via v1.6 helper; the
    last 1~3 syllables (Hangul only) before the terminal punctuation are
    used as the ending key. Higher = more diverse (more human-like).
    Returns 0.0 when no sentence ends with valid punctuation.
    """
    sents = _split_sentences(text)
    keys: list[str] = []
    for s in sents:
        m = _ENDING_FINAL_RE.search(s)
        if m:
            keys.append(m.group(1))
            continue
        m2 = _ENDING_FINAL_FALLBACK_RE.search(s)
        if m2:
            keys.append(m2.group(1))
    if not keys:
        return 0.0
    return len(set(keys)) / len(keys)


# ---------------------------------------------------------------------------
# Group B: normalisation 축
# ---------------------------------------------------------------------------


def normalisation_score(text: str) -> float:
    """Declarative-form (~한다/~된다/~이다) concentration — normalisation axis.

    Returns the ratio of sentences whose final eojeol ends with one of the
    three canonical declarative markers (~한다·~된다·~이다 — variants
    `-한다.`, `-한다!` 등은 punctuation-stripped). High values (>0.7) signal
    normalised, AI-like prose; very low values (<0.3) often signal informal
    speech (해체) or heterogeneous registers. Range [0, 1].
    """
    sents = _split_sentences(text)
    if not sents:
        return 0.0
    hits = 0
    for s in sents:
        last = _last_eojeol(s)
        if not last:
            continue
        for ending in _DECLARATIVE_ENDINGS:
            if last.endswith(ending):
                hits += 1
                break
    return hits / len(sents)


def da_streak_rate(text: str) -> int:
    """Count of '-다' streak runs of length >= 4 — T8a normalisation signal.

    A *streak* = consecutive sentences whose final eojeol ends in '다'
    (any '~다' — 한다·된다·이다·었다·았다·였다 등). Streaks of length 4+
    are reported. The return value is the number of distinct streaks
    (not the total streak length). Documents with one long uniform run
    of '-다' will return 1; truly diverse docs return 0.
    """
    sents = _split_sentences(text)
    streaks = 0
    cur = 0
    for s in sents:
        last = _last_eojeol(s)
        if last.endswith("다"):
            cur += 1
        else:
            if cur >= 4:
                streaks += 1
            cur = 0
    if cur >= 4:
        streaks += 1
    return streaks


# ---------------------------------------------------------------------------
# Group C: interference 축 — T1~T8 detection signals
# ---------------------------------------------------------------------------


def inanimate_subject_rate(text: str) -> float:
    """T1: inanimate-subject + universal-verb pattern rate.

    Approximation: count sentences whose first content noun ends with one
    of the v2.0 hanja suffixes (-성·-적·-화·-도·-력·-감·-원) OR matches a
    short list of inanimate/abstract subjects (`연구·데이터·분석·결과·시스템·
    기술·사례·현상·이론·정책·보고서`) AND whose verb is a universal
    cognitive/declarative verb (보여준다·시사한다·만든다·드러낸다·제시한다·
    나타낸다·증명한다·말해준다·의미한다·가져온다). Returns
    matching_sents / total_sents in [0, 1].
    """
    sents = _split_sentences(text)
    if not sents:
        return 0.0
    inanimate_subjects = (
        "연구", "데이터", "분석", "결과", "시스템", "기술", "사례",
        "현상", "이론", "정책", "보고서", "AI", "인공지능", "모델",
        "알고리즘", "변화", "위기", "혁신", "사회", "경제",
    )
    universal_verbs = (
        "보여준다", "보여줬다", "보여주는", "시사한다", "시사하는",
        "만든다", "만들어", "드러낸다", "드러냈다", "드러내는",
        "제시한다", "제시했다", "나타낸다", "나타냈다", "나타내는",
        "증명한다", "증명했다", "말해준다", "말해주는",
        "의미한다", "의미하는", "가져온다", "가져왔다", "가져오는",
    )
    hits = 0
    for s in sents:
        toks = _all_tokens(s)
        if not toks:
            continue
        head = toks[0]
        # Subject heuristic: first token, optionally followed by 은/는/이/가.
        head_stem = head
        for josa in ("은", "는", "이", "가", "도"):
            if head.endswith(josa) and len(head) > 1:
                head_stem = head[:-1]
                break
        is_inanimate = (
            head_stem in inanimate_subjects
            or (len(head_stem) >= 2 and head_stem[-1] in _HANJA_SUFFIXES_V2)
        )
        if not is_inanimate:
            continue
        # Verb heuristic: any later token in `universal_verbs`.
        if any(any(uv in t for uv in universal_verbs) for t in toks[1:]):
            hits += 1
    return hits / len(sents)


def by_passive_count(text: str) -> int:
    """T2a: ~에 의해 + passive-verb co-occurrence count.

    Bare '에 의해' is excluded. Only the regex-anchored
    '에 의해 ... 되/받/당하/지' pattern is counted. Returns int >= 0.
    """
    if not text.strip():
        return 0
    return len(_BY_PASSIVE_RE.findall(text))


def double_passive_count(text: str) -> int:
    """T2b: double-passive (잊혀지다·보여지다·되어진다·여지다·쓰여지다 …) count.

    Surface-form lexicon. 단순 '되다' 는 제외 (자연 표현). Returns int >= 0.
    """
    if not text.strip():
        return 0
    n = 0
    for tok in _DOUBLE_PASSIVE_TOKENS:
        n += text.count(tok)
    return n


def pronoun_density(text: str) -> float:
    """T3: personal-pronoun density per paragraph (avg).

    Counts 그/그녀/그것/그들 (+ 조사 fused forms). Bare '그' is only counted
    when followed by 는/가/를/의/에게/와/도/만 to filter out demonstrative use.
    Returns paragraph-mean of (pronoun_tokens / paragraph_eojeols).
    Range [0, 1]. Empty input returns 0.0.
    """
    paragraphs = _split_paragraphs(text)
    if not paragraphs:
        return 0.0
    densities: list[float] = []
    for p in paragraphs:
        toks = _all_tokens(p)
        if not toks:
            continue
        pronoun_hits = len(_PRONOUN_RE.findall(p))
        densities.append(pronoun_hits / len(toks))
    if not densities:
        return 0.0
    try:
        return mean(densities)
    except StatisticsError:
        return 0.0


def deul_overuse_rate(text: str) -> float:
    """T4: inanimate / abstract noun + '-들' over-use ratio.

    Returns deul_overuse_hits / total_eojeols. The numerator counts
    occurrences of any token in `_INANIMATE_DEUL_TOKENS` (데이터들·정보들·
    결과들·연구들·아이디어들·방법들·문제들·의견들·시스템들·기술들 …).
    Range [0, 1] — practical AI text seldom exceeds ~0.05.
    """
    toks = _all_tokens(text)
    if not toks:
        return 0.0
    hits = 0
    for t in toks:
        # Match exact OR with one short josa suffix (-과/와/이/가/을/를/의/에/은/는/도)
        if t in _INANIMATE_DEUL_TOKENS:
            hits += 1
            continue
        for base in _INANIMATE_DEUL_TOKENS:
            if t.startswith(base) and len(t) - len(base) in (1, 2):
                # remaining tail must be hangul (likely josa)
                tail = t[len(base):]
                if all("가" <= ch <= "힣" for ch in tail):
                    hits += 1
                    break
    return hits / len(toks)


def relative_clause_nesting(text: str) -> int:
    """T5: count of sentences with relative-clause nesting depth >= 3.

    Approximation: a sentence is nested when it contains 3+ adnominal
    clause endings -ㄴ/-는/-ㄹ/-한/-된/-할 followed by a noun (heuristic:
    the syllable before whitespace). We check every sentence for the
    count of token endings in `(ㄴ|는|ㄹ|던|할|한|된|될)` followed by a
    short space-separated noun. Returns the *number of sentences*
    (not total nestings) with depth >= 3.
    """
    sents = _split_sentences(text)
    if not sents:
        return 0
    # 관형형 어미 종결 음절 매칭 — 어절 끝이 (ㄴ|는|ㄹ|던|한|된|할|될|온) 인 토큰 수.
    adnominal_re = re.compile(r"[가-힣]+(?:ㄴ|는|ㄹ|던|한|된|할|될|온|간)\s+[가-힣]")
    matches_per_sent = []
    for s in sents:
        m = adnominal_re.findall(s)
        matches_per_sent.append(len(m))
    return sum(1 for c in matches_per_sent if c >= 3)


def have_make_literal_count(text: str) -> int:
    """T6: count of literal have/make light-verb constructions.

    가지고 있다·갖고 있다·~을 가지다·~을 만들다·회의를 가지다·결정을 내리다 …
    Returns int >= 0.
    """
    if not text.strip():
        return 0
    n = 0
    for tok in _HAVE_MAKE_LITERAL_TOKENS:
        n += text.count(tok)
    return n


def double_particle_count(text: str) -> int:
    """T7: double-particle (에서의·에로의·으로의·에의·으로부터의·로부터의) count.

    Caveat #5 (single ~의 excluded) is *enforced by construction* — the
    regex never matches a bare ~의. Returns int >= 0.
    """
    if not text.strip():
        return 0
    return len(_DOUBLE_PARTICLE_RE.findall(text))


def progressive_aspect_rate(text: str) -> float:
    """T8b: progressive aspect '~고 있다' rate per sentence.

    Returns progressive_hits / total_sentences. Surface-form match; not
    every '~고 있다' is reducible (예: 진행 의미가 본질적인 동사) but
    high rates flag automatic 1대1 매핑. Range typically [0, 1+] — values
    >0.5 signal heavy literal mapping.
    """
    sents = _split_sentences(text)
    if not sents:
        return 0.0
    hits = sum(len(_PROGRESSIVE_RE.findall(s)) for s in sents)
    return hits / len(sents)


# ---------------------------------------------------------------------------
# === v2.0 INTERFERENCE INDEX ===
# Composite signal weighted across T1~T8.
# ---------------------------------------------------------------------------


def interference_index(text: str) -> dict[str, Any]:
    """T1~T8 weighted interference signal — interference axis composite.

    Returns a dict with each sub-signal score plus a `weighted_total`
    that sums per-type contributions (each capped to [0, 1] by simple
    rescaling). This is descriptive, not a z-score — calibration to
    baseline happens in compute_all_v2.
    """
    n_sents = max(len(_split_sentences(text)), 1)
    chars = max(len(text), 1)
    components = {
        "T1_inanimate_subject_rate": inanimate_subject_rate(text),
        "T2a_by_passive_per_1k": by_passive_count(text) / chars * 1000,
        "T2b_double_passive_per_1k": double_passive_count(text) / chars * 1000,
        "T3_pronoun_density": pronoun_density(text),
        "T4_deul_overuse_rate": deul_overuse_rate(text),
        "T5_nested_clause_count": relative_clause_nesting(text),
        "T6_have_make_per_1k": have_make_literal_count(text) / chars * 1000,
        "T7_double_particle_per_1k": double_particle_count(text) / chars * 1000,
        "T8b_progressive_rate": progressive_aspect_rate(text),
    }
    # Each component clamped to [0, 1] heuristically:
    weights = {
        "T1_inanimate_subject_rate": 1.0,        # already in [0,1]
        "T2a_by_passive_per_1k": 0.2,            # /5
        "T2b_double_passive_per_1k": 0.2,
        "T3_pronoun_density": 4.0,               # human <0.015, scale up
        "T4_deul_overuse_rate": 4.0,
        "T5_nested_clause_count": 0.05,          # /20
        "T6_have_make_per_1k": 0.2,
        "T7_double_particle_per_1k": 0.5,
        "T8b_progressive_rate": 1.0,
    }
    weighted_total = 0.0
    for k, v in components.items():
        weighted_total += min(1.0, max(0.0, v * weights[k]))
    return {
        "components": components,
        "weighted_total": weighted_total,
        "n_sentences": n_sents,
        "n_chars": chars,
    }


# ---------------------------------------------------------------------------
# Baseline + z-score (v2.0 extension)
# ---------------------------------------------------------------------------


def _default_baseline_v2_path() -> str:
    return os.path.join(_HERE, "baseline_v2.json")


def _load_baseline_v2(path: str | None) -> dict[str, Any]:
    p = path or _default_baseline_v2_path()
    if not os.path.exists(p):
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _z_simple(value: float, mean_v: float, stdev: float) -> float | None:
    if stdev is None or stdev <= 0:
        return None
    return (value - mean_v) / stdev


# ---------------------------------------------------------------------------
# Public entry point — v2.0 superset
# ---------------------------------------------------------------------------


def compute_all_v2(
    text: str,
    genre: str = "essay",
    baseline_path: str | None = None,
    baseline_v2_path: str | None = None,
) -> dict[str, Any]:
    """Compute v1.6 metrics + v2.0 post-editese + T1~T8 signals.

    Returns the v1.6 ``compute_all`` payload extended with:
        - ``v2_metrics``: dict of new metric values
        - ``v2_z_scores``: per-metric z against baseline_v2 (None if placeholder)
        - ``v2_baseline_warnings``: list of metric keys whose baseline cell
          carries `_placeholder: true`.
    """
    base = _v1.compute_all(text, genre=genre, baseline_path=baseline_path)
    v2_metrics: dict[str, float | int] = {
        "lexical_diversity_ttr": lexical_diversity_ttr(text),
        "lexical_density": lexical_density(text),
        "ending_diversity": ending_diversity(text),
        "normalisation_score": normalisation_score(text),
        "da_streak_rate": da_streak_rate(text),
        "inanimate_subject_rate": inanimate_subject_rate(text),
        "by_passive_count": by_passive_count(text),
        "double_passive_count": double_passive_count(text),
        "pronoun_density": pronoun_density(text),
        "deul_overuse_rate": deul_overuse_rate(text),
        "relative_clause_nesting": relative_clause_nesting(text),
        "have_make_literal_count": have_make_literal_count(text),
        "double_particle_count": double_particle_count(text),
        "progressive_aspect_rate": progressive_aspect_rate(text),
    }
    interference = interference_index(text)

    bv2 = _load_baseline_v2(baseline_v2_path)
    cells = {}
    warnings: list[str] = []
    if bv2:
        genres = bv2.get("genres", {}) or {}
        cells = genres.get(genre) or genres.get("essay") or {}
    z_scores: dict[str, float | None] = {}
    for k, v in v2_metrics.items():
        cell = cells.get(k)
        if not cell:
            z_scores[k] = None
            continue
        if cell.get("_placeholder"):
            warnings.append(k)
        z_scores[k] = _z_simple(
            float(v), float(cell.get("mean", 0.0)), float(cell.get("stdev", 0.0))
        )

    base["version"] = VERSION
    base["v2_metrics"] = v2_metrics
    base["v2_interference_index"] = interference
    base["v2_z_scores"] = z_scores
    base["v2_baseline_warnings"] = warnings
    return base


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Humanize KR v2.0 metric runner")
    parser.add_argument("--input", required=True, help="Input text file path")
    parser.add_argument("--genre", default="essay", help="essay/news/blog/qa/dialogue")
    parser.add_argument("--output", default=None, help="Output JSON path (optional)")
    parser.add_argument(
        "--baseline", default=None, help="Override v1.6 baseline JSON path"
    )
    parser.add_argument(
        "--baseline-v2", default=None, help="Override v2.0 baseline JSON path"
    )
    args = parser.parse_args(argv)

    with open(args.input, "r", encoding="utf-8") as f:
        text = f.read()

    result = compute_all_v2(
        text,
        genre=args.genre,
        baseline_path=args.baseline,
        baseline_v2_path=args.baseline_v2,
    )

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    print(result["risk_band"])
    return 0


# ---------------------------------------------------------------------------
# v1.6 호환 별칭 (prepare_monolith_input.py가 _metrics_mod.compute_all 호출)
# ---------------------------------------------------------------------------
compute_all = compute_all_v2  # v2.0 출력은 v1.6의 상위집합 (integration_note §1)


if __name__ == "__main__":
    sys.exit(_main())
