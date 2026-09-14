#!/usr/bin/env python3
"""텍스트 위생(sanitize) — 결정적 처리, LLM 호출 0회.

imnotai-web 의 lib/sanitize.ts 와 같은 규칙을 구현한 쌍둥이 모듈이다.
둘 중 하나를 고치면 다른 하나도 같이 고쳐야 한다 (tests/test_sanitize.py 가 규칙을 고정).

─── 이것이 하는 일 / 하지 않는 일 ─────────────────────────────────
하는 일: 눈에 보이지 않으면서 실제로 문제를 일으키는 문자들을 정리한다.
  - 한글 자모 분해(NFD) → 완성형(NFC) 정규화. macOS 에서 만든 파일·파일명에서
    온 텍스트는 한글이 자모로 분해 저장돼 있는 경우가 많다. 눈에는 똑같아
    보이지만 글자수·검색·정렬이 전부 어긋나고, 변경률 게이트(철칙 #4)가
    오작동한다.
  - 제로폭 문자·BOM·소프트하이픈: 복사 과정에서 섞여 들어와 글자수를 부풀린다.
  - 양방향 제어 문자(bidi override): 보이는 순서와 저장 순서를 다르게 만든다.
  - 태그 문자(U+E0000~): 본문에 안 보이는 텍스트를 숨겨 넣는 용도로만 쓰인다.
  - NBSP·전각 공백 등 특수 공백 → 보통 공백. HWP·워드 붙여넣기에서 흔하다.
  - CRLF·유니코드 줄바꿈 → LF 통일, 줄 끝 공백 제거.

하지 않는 일 (중요):
  - **AI 워터마크를 제거하지 않는다.** Anthropic 은 워터마크가 "별도 문자를
    추가하지 않고 숨겨진 문자도 넣지 않는다"고 명시했다. SynthID-Text 는 문자가
    아니라 단어 선택의 통계 패턴에 실린다. 따라서 이 모듈의 어떤 처리도
    워터마크와 무관하다. 문서·UI 에서 워터마크 제거로 표기해서는 안 된다.
  - 맞춤법·띄어쓰기·문장부호를 고치지 않는다. 따옴표·대시는 필자의 선택이다.
  - 글자를 추가하거나 바꾸지 않는다. 오직 제거·정규화만 한다.

설계 원칙
  - 멱등(idempotent): sanitize(sanitize(x)) == sanitize(x)
  - stdlib only (re / unicodedata) — 프로젝트 정책 유지.
  - **소스에 비가시 문자를 리터럴로 쓰지 않는다.** 전부 chr(0x....) 로 조립한다.
    리터럴로 적으면 파일 자체가 오염되고 diff 리뷰가 불가능해진다.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, asdict

# ---------------------------------------------------------------------------
# 코드포인트 (소스에 비가시 문자를 넣지 않기 위해 전부 숫자로 둔다)
# ---------------------------------------------------------------------------

SOFT_HYPHEN = 0x00AD
NBSP = 0x00A0
MONGOLIAN_VOWEL_SEP = 0x180E
OGHAM_SPACE = 0x1680
ZWSP = 0x200B
ZWNJ = 0x200C
ZWJ = 0x200D
WORD_JOINER = 0x2060
BOM = 0xFEFF
NARROW_NBSP = 0x202F
MED_MATH_SPACE = 0x205F
IDEOGRAPHIC_SPACE = 0x3000
LINE_SEP = 0x2028
PARA_SEP = 0x2029


def _cls(*ranges) -> str:
    """코드포인트/범위 목록 → 정규식 문자 클래스 본문."""
    out = []
    for r in ranges:
        if isinstance(r, tuple):
            out.append(f"\\U{r[0]:08x}-\\U{r[1]:08x}")
        else:
            out.append(f"\\U{r:08x}")
    return "".join(out)


# 항상 제거해도 안전한 비가시 문자
INVISIBLE_ALWAYS = re.compile(
    "[" + _cls(SOFT_HYPHEN, MONGOLIAN_VOWEL_SEP, ZWSP, WORD_JOINER, BOM) + "]"
)

# 양방향 제어 문자 — U+061C / U+200E-200F / U+202A-202E / U+2066-2069
BIDI = re.compile(
    "[" + _cls(0x061C, (0x200E, 0x200F), (0x202A, 0x202E), (0x2066, 0x2069)) + "]"
)

# 태그 문자 — 숨은 텍스트 삽입 외 쓰임이 없다
TAG_CHARS = re.compile("[" + _cls((0xE0000, 0xE007F)) + "]")

# 특수 공백 → 보통 공백. 전각공백(U+3000)은 눈에 보이는 폭이라 여기서 제외 —
# 필요하면 normalize_ideographic_space 옵션으로 따로 켠다.
SPECIAL_SPACES = re.compile(
    "["
    + _cls(
        NBSP,
        OGHAM_SPACE,
        (0x2000, 0x200A),
        NARROW_NBSP,
        MED_MATH_SPACE,
    )
    + "]"
)

IDEOGRAPHIC_SPACE_RE = re.compile("[" + _cls(IDEOGRAPHIC_SPACE) + "]")

# 유니코드 줄/문단 구분자
UNI_BREAKS = re.compile("[" + _cls(LINE_SEP, PARA_SEP) + "]")

# 조합용 한글 자모 (초성 U+1100-1112 + 중성 U+1161-1175 + 선택적 종성 U+11A8-11C2)
DECOMPOSED_HANGUL = re.compile(
    "[" + _cls((0x1100, 0x1112)) + "]"
    "[" + _cls((0x1161, 0x1175)) + "]"
    "[" + _cls((0x11A8, 0x11C2)) + "]?"
)

# ZWJ/ZWNJ 는 이모지 결합에 필수라 무조건 제거하면 안 된다.
# 양옆이 모두 "평범한 문자"일 때만 잘라낸다.
PLAIN_NEIGHBOR = re.compile(r"[가-힣0-9A-Za-z\s.,!?;:'\"()\[\]{}-]")

_ZWNJ_CH = chr(ZWNJ)
_ZWJ_CH = chr(ZWJ)


@dataclass
class SanitizeReport:
    changed: bool = False
    before_chars: int = 0
    after_chars: int = 0
    counts: dict = field(default_factory=dict)
    summary: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _strip_joiners_outside_emoji(text: str) -> tuple[str, int]:
    if _ZWJ_CH not in text and _ZWNJ_CH not in text:
        return text, 0
    removed = 0
    kept: list[str] = []
    n = len(text)
    for i, c in enumerate(text):
        if c in (_ZWNJ_CH, _ZWJ_CH):
            prev = kept[-1] if kept else ""
            nxt = text[i + 1] if i + 1 < n else ""
            prev_plain = prev == "" or bool(PLAIN_NEIGHBOR.match(prev))
            next_plain = nxt == "" or bool(PLAIN_NEIGHBOR.match(nxt))
            if prev_plain and next_plain:
                removed += 1
                continue
        kept.append(c)
    return "".join(kept), removed


def _summary(counts: dict, changed: bool) -> str:
    if not changed:
        return ""
    parts = []
    if counts.get("hangul_recomposed"):
        parts.append(f"분해된 한글 {counts['hangul_recomposed']}자 결합")
    if counts.get("invisible"):
        parts.append(f"보이지 않는 문자 {counts['invisible']}개 제거")
    if counts.get("bidi"):
        parts.append(f"방향 제어 문자 {counts['bidi']}개 제거")
    if counts.get("tag_chars"):
        parts.append(f"숨은 태그 문자 {counts['tag_chars']}개 제거")
    if counts.get("special_spaces"):
        parts.append(f"특수 공백 {counts['special_spaces']}개 정리")
    if counts.get("line_breaks"):
        parts.append(f"줄바꿈 {counts['line_breaks']}개 통일")
    if counts.get("trailing_space_lines"):
        parts.append(f"줄 끝 공백 {counts['trailing_space_lines']}줄 정리")
    return " · ".join(parts)


def sanitize(
    text: str,
    *,
    normalize_unicode: bool = True,
    strip_invisible: bool = True,
    normalize_spaces: bool = True,
    normalize_lines: bool = True,
    # ── 아래 둘은 기본 off ────────────────────────────────────────────
    # 나머지 항목이 "고장을 고치는" 처리(제로폭이 글자수를 부풀리고, NFD 가 검색·
    # 게이트를 깨뜨림)인 것과 달리, 이 둘은 **고장이 아닌데 눈에 보이는 것**을 바꾼다.
    # 전각공백을 들여쓰기로 쓰는 필자가 있고, 빈 줄 간격은 필자의 선택이다.
    # 철칙 #1(의미 불변)과 충돌하지 않도록 opt-in 으로 둔다.
    normalize_ideographic_space: bool = False,
    collapse_blank_lines: bool = False,
) -> tuple[str, SanitizeReport]:
    """텍스트 위생 처리. (정리된 텍스트, 보고서) 를 돌려준다."""
    original = text
    counts = {
        "hangul_recomposed": 0,
        "invisible": 0,
        "bidi": 0,
        "tag_chars": 0,
        "special_spaces": 0,
        "line_breaks": 0,
        "trailing_space_lines": 0,
    }

    # 1) 비가시 문자 — 정규화보다 먼저. 자모 사이에 낀 제로폭이 NFC 결합을 막는다.
    if strip_invisible:
        counts["invisible"] = len(INVISIBLE_ALWAYS.findall(text))
        text = INVISIBLE_ALWAYS.sub("", text)

        counts["bidi"] = len(BIDI.findall(text))
        text = BIDI.sub("", text)

        counts["tag_chars"] = len(TAG_CHARS.findall(text))
        text = TAG_CHARS.sub("", text)

        text, removed = _strip_joiners_outside_emoji(text)
        counts["invisible"] += removed

    # 2) 한글 NFD → NFC
    if normalize_unicode:
        counts["hangul_recomposed"] = len(DECOMPOSED_HANGUL.findall(text))
        text = unicodedata.normalize("NFC", text)

    # 3) 특수 공백 → 보통 공백
    if normalize_spaces:
        counts["special_spaces"] = len(SPECIAL_SPACES.findall(text))
        text = SPECIAL_SPACES.sub(" ", text)
    if normalize_ideographic_space:
        counts["special_spaces"] += len(IDEOGRAPHIC_SPACE_RE.findall(text))
        text = IDEOGRAPHIC_SPACE_RE.sub(" ", text)

    # 4) 줄바꿈 정리
    if normalize_lines:
        counts["line_breaks"] = (
            text.count("\r\n")
            + len(re.findall(r"\r(?!\n)", text))
            + len(UNI_BREAKS.findall(text))
        )
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = UNI_BREAKS.sub("\n", text)

        counts["trailing_space_lines"] = len(re.findall(r"[ \t]+$", text, re.MULTILINE))
        text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)

    # 빈 줄 3개 이상 → 2개. 기본 off — 문단 간격은 필자의 선택이다.
    if collapse_blank_lines:
        text = re.sub(r"\n{3,}", "\n\n", text)

    changed = text != original
    return text, SanitizeReport(
        changed=changed,
        before_chars=len(original),
        after_chars=len(text),
        counts=counts,
        summary=_summary(counts, changed),
    )


def inspect(text: str, **kw) -> SanitizeReport:
    """텍스트를 바꾸지 않고 무엇이 걸리는지만 센다."""
    return sanitize(text, **kw)[1]


def _main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    import sys

    p = argparse.ArgumentParser(
        description="텍스트 위생 — 보이지 않는 오염 문자 정리 (워터마크 제거 아님)"
    )
    p.add_argument("path", nargs="?", help="입력 파일 (없으면 stdin)")
    p.add_argument("--in-place", action="store_true", help="파일을 제자리에서 수정")
    p.add_argument("--report", action="store_true", help="본문 대신 JSON 보고서만 출력")
    a = p.parse_args(argv)

    src = open(a.path, encoding="utf-8").read() if a.path else sys.stdin.read()
    out, rep = sanitize(src)

    if a.report:
        print(json.dumps(rep.to_dict(), ensure_ascii=False, indent=2))
        return 0
    if a.in_place:
        if not a.path:
            p.error("--in-place 는 파일 경로가 필요합니다")
        if rep.changed:
            open(a.path, "w", encoding="utf-8").write(out)
        print(rep.summary or "정리할 항목 없음")
        return 0
    sys.stdout.write(out)
    return 0


# ── 콘솔 하드닝 (#84) ───────────────────────────────────────────────
# Windows(cp949)에서 한글·em-dash 출력이 UnicodeEncodeError 로 죽는 것을 막는다.
import os as _os  # noqa: E402
import sys as _sys  # noqa: E402

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import console as _console  # noqa: E402

if __name__ == "__main__":
    _console.force_utf8_console()
    raise SystemExit(_main())
