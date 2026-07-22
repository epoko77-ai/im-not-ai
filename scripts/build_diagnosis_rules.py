#!/usr/bin/env python3
"""diagnosis-rules.md 를 ai-tell-taxonomy.md(SSOT)에서 생성한다.

진단(humanize-diagnostician)의 핸드오프 계약은 "정확한 본진 ID + 지배도
판단"이지 예문·처방·버전주석이 아니다. 그런데 진단 콜이 taxonomy 전량
(74.8KB)을 읽고 있었다 — 부피 대부분이 진단에 불필요한 처방·학술 인용·
버전 히스토리다. quick-rules와 같은 방식으로 SSOT에서 진단 전용 슬림
인덱스를 결정적으로 생성한다.

quick-rules와 다른 점: quick-rules는 `quick: true`(표층 패턴)만 담지만,
진단은 문서 레벨 패턴(C-8 대구·E-1 리듬·D-6 결말공식 등 quick: false
23종)을 반드시 봐야 한다. 그래서 이 인덱스는 **71패턴 전수**를 담는다 —
quick-rules로 대체할 수 없는 이유가 이것이다.

입력:
    ai-tell-taxonomy.md   — SSOT (read-only, 절대 수정하지 않는다)
출력:
    diagnosis-rules.md    — 생성물. 직접 편집 금지.

패턴당 2줄: ①ID + 심각도 + 이름 + 1줄 정의  ②1줄 탐지 시그니처.
S1급 패턴엔 시그니처 예문 1개를 덧붙인다(경계 사례 ID 오판 방지).

CLI:
    python3 scripts/build_diagnosis_rules.py            # 생성
    python3 scripts/build_diagnosis_rules.py --check    # 최신 여부만 검사(CI용)
"""

from __future__ import annotations

import argparse
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# 파서 재사용 — quick-rules 빌더와 같은 SSOT 계약(카테고리·패턴 헤더·_quick 메타).
from build_quick_rules import (  # noqa: E402
    _CATEGORY_RE,
    _PATTERN_RE,
    ParseError,
    parse_taxonomy,
)

_REFS = os.path.abspath(
    os.path.join(_HERE, "..", ".claude", "skills", "humanize-korean", "references")
)
_TAXONOMY = os.path.join(_REFS, "ai-tell-taxonomy.md")
_OUT = os.path.join(_REFS, "diagnosis-rules.md")

# 콘텐츠가 아닌 불릿 프리픽스 — 정의 추출에서 제외.
_NON_DEF_BULLET = re.compile(r"^- (?:예[:：\s]|처방[:：]|주의[:：]|예외[:：]|_)")
_DEF_LINE = re.compile(r"^- (?:패턴|정의)[:：]\s*(.+)$")
_EXAMPLE_LINE = re.compile(r"^- 예[:：]?\s*(.+)$")
_BOLD = re.compile(r"\*\*")

# 진단 인덱스 길이 상한(문자 수) — 부피 게이트용.
# (한글 UTF-8 3바이트 — 문자 컷이 곧 부피 컷이다)
_DEF_MAX = 38
_SIG_MAX = 42
_EX_MAX = 28

# 헤더 잡음: 버전주석(· v1.1 신규 등)·심각도 대괄호 — 인덱스에선 제거.
_VERSION_SUFFIX = re.compile(r"\s*·\s*v[\d.]+\s*\S*.*$")
_SEV_BRACKET = re.compile(r"\s*\[[^\]]*\]")


def _clean(s: str) -> str:
    s = _BOLD.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def _cut(s: str, limit: int) -> str:
    return s if len(s) <= limit else s[: limit - 1].rstrip() + "…"


def extract_details(text: str) -> dict[str, dict[str, str | None]]:
    """블록별 {id: {definition, example}} 추출.

    definition = 첫 `- 패턴:`/`- 정의:` 줄, 없으면 첫 콘텐츠 불릿
    (예·처방·주의·예외·메타 제외). example = 첫 `- 예:` 줄.
    """
    details: dict[str, dict[str, str | None]] = {}
    cur_id: str | None = None
    for ln in text.splitlines():
        m = _PATTERN_RE.match(ln)
        if m:
            cur_id = m.group(1)
            details[cur_id] = {"definition": None, "example": None}
            continue
        if _CATEGORY_RE.match(ln):
            cur_id = None
            continue
        if cur_id is None:
            continue
        d = details[cur_id]
        m_def = _DEF_LINE.match(ln)
        if m_def and d["definition"] is None:
            d["definition"] = _clean(m_def.group(1))
            continue
        m_ex = _EXAMPLE_LINE.match(ln)
        if m_ex and d["example"] is None:
            d["example"] = _clean(m_ex.group(1))
            continue
        if (
            d["definition"] is None
            and ln.startswith("- ")
            and not _NON_DEF_BULLET.match(ln)
        ):
            d["definition"] = _clean(ln[2:])
    return details


def render(patterns: list[dict], details: dict[str, dict[str, str | None]]) -> str:
    out: list[str] = [
        "# 진단 전용 슬림 인덱스 (diagnosis-rules)",
        "",
        "> **자동 생성 — 직접 편집 금지.** `scripts/build_diagnosis_rules.py`가",
        "> SSOT `ai-tell-taxonomy.md`에서 생성한다. 진단 콜 전용 — 예문 전수·",
        "> 처방·학술 인용·버전주석은 SSOT 참조. **71패턴 전수** 수록",
        "> (문서 레벨 quick:false 패턴 포함 — quick-rules로 대체 불가).",
        "",
        "심각도: **S1** 결정적(1회로 확신) / **S2** 강함(3회+ 반복 시 티) / "
        "**S3** 약함(중첩 시 강화) / 미표기 = SSOT의 카테고리 서술 참조.",
        "",
    ]
    cur_cat = None
    for p in patterns:
        if p["category"] != cur_cat:
            if cur_cat is not None:
                out.append("")
            cur_cat = p["category"]
            cat_name = _SEV_BRACKET.sub(
                "", re.sub(r"\s*—\s*S\d.*$", "", p["category_name"])
            ).strip()
            out.append(f"## {cur_cat}. {cat_name}")
            out.append("")
        pid = p["id"]
        raw_title = _clean(p["title"])
        # 심각도: 헤더 대괄호 캡처 우선, 없으면 title 안의 [S..]에서.
        sev_src = p["severity"] or raw_title
        m_sev = re.search(r"S\d", sev_src)
        sev = f" [{m_sev.group(0)}]" if m_sev else ""
        # title에서 심각도 대괄호·버전주석 잡음 제거.
        title = _VERSION_SUFFIX.sub("", _SEV_BRACKET.sub("", raw_title)).strip()

        d = details.get(pid, {})
        definition = d.get("definition") or title
        example = d.get("example")
        sig = p.get("pattern") or definition  # quick_pattern 우선

        is_hold = "hold" in raw_title or "보류" in raw_title
        if is_hold:
            title = re.sub(r"^\(보류[^)]*\)\s*", "", title)
            definition = "v2.0 hold — 지배 패턴 지목 금지, 관찰 기록만"
            sig = "무정물·추상명사 + '-들' 기계적 부착"

        # 예문의 "→ 처방" 꼬리는 진단에 불필요 — 원문 예만 남긴다.
        if example:
            example = example.split("→")[0].strip().rstrip('"').strip()

        # 중복 생략(부피 절약): 정의가 제목·시그니처와 실질 동일하면 생략.
        dup = (
            definition == title
            or definition == sig
            or definition in sig
            or sig in definition
            or definition in title
        )
        line1 = f"- **{pid}**{sev} {title}"
        if is_hold or not dup:
            line1 += f" — {_cut(definition, _DEF_MAX)}"
        out.append(line1)

        line2 = f"  시그니처: {_cut(sig, _SIG_MAX)}"
        if "S1" in sev and example:
            line2 += f" · 예: {_cut(example, _EX_MAX)}"
        out.append(line2)
    out.append("")
    return "\n".join(out)


def build() -> tuple[str, list[dict]]:
    with open(_TAXONOMY, encoding="utf-8") as f:
        taxonomy = f.read()
    patterns = parse_taxonomy(taxonomy)
    missing = [p["id"] for p in patterns if p["quick"] is None]
    if missing:
        raise ParseError(
            f"quick 메타 누락 {len(missing)}건: {', '.join(missing)}"
        )
    details = extract_details(taxonomy)
    rendered = render(patterns, details)

    # 구조 자가 검증 — 71 ID 전수 + 빈 항목 0 (조용한 누락 금지).
    ids_in = {p["id"] for p in patterns}
    ids_out = set(re.findall(r"^- \*\*([A-J]-\d+)\*\*", rendered, re.M))
    if ids_in != ids_out:
        raise ParseError(
            f"ID 누락/과잉: 누락 {sorted(ids_in - ids_out)} "
            f"/ 과잉 {sorted(ids_out - ids_in)}"
        )
    for m in re.finditer(r"^  시그니처:\s*(\S?)", rendered, re.M):
        if not m.group(1):
            raise ParseError("빈 시그니처 항목 발견")
    return rendered, patterns


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="diagnosis-rules.md 생성기")
    ap.add_argument(
        "--check",
        action="store_true",
        help="생성물이 SSOT와 일치하는지만 검사(파일을 쓰지 않음). CI용.",
    )
    args = ap.parse_args(argv)

    try:
        rendered, patterns = build()
    except ParseError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    size = len(rendered.encode("utf-8"))
    if args.check:
        existing = ""
        if os.path.exists(_OUT):
            with open(_OUT, encoding="utf-8") as f:
                existing = f.read()
        if existing.rstrip() != rendered.rstrip():
            print(
                "error: diagnosis-rules.md 가 taxonomy와 어긋난다. "
                "`python3 scripts/build_diagnosis_rules.py` 로 재생성하라.",
                file=sys.stderr,
            )
            return 1
        print(f"diagnosis-rules.md 최신 (패턴 {len(patterns)} / {size}B)")
        return 0

    with open(_OUT, "w", encoding="utf-8") as f:
        f.write(rendered)
    print(
        f"diagnosis-rules.md 생성 — {rendered.count(chr(10)) + 1}줄 / "
        f"{size}B ({size / 1024:.1f}KB, 패턴 {len(patterns)})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
