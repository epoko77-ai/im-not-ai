#!/usr/bin/env python3
"""quick-rules.md 를 ai-tell-taxonomy.md(SSOT)에서 생성한다.

fast 경로 슬림 룰북(quick-rules.md)을 사람이 손으로 taxonomy와 동기화하다
ID 드리프트가 3건 생겼다(D-3·G-1/G-2·J-3가 서로 다른 패턴을 가리킴).
3콜 구조에서 ID는 진단→윤문 콜 간 핸드오프 계약이라 이 드리프트가 런타임
버그가 된다. 생성으로 전환해 1:1 매칭을 구조적으로 보장한다.

입력:
    ai-tell-taxonomy.md    — SSOT. 각 패턴 말미의 `_quick: …_` 이탤릭 메타를 읽는다.
    quick-rules.header.md  — 생성 결과 앞에 붙는 고정 템플릿
    quick-rules.footer.md  — 뒤에 붙는 고정 템플릿(자체검증·등급)

출력:
    quick-rules.md         — 생성물. 직접 편집 금지.

메타 형식(taxonomy 패턴 항목 말미, 이탤릭 한 줄):
    - _quick: true · quick_pattern: <표층 신호> · quick_fix: <한 줄 처방>_
    - _quick: false · …_        (strict 전용 — 생성물에서 제외)

CLI:
    python3 scripts/build_quick_rules.py            # 생성
    python3 scripts/build_quick_rules.py --check    # 생성물이 최신인지만 검사(쓰지 않음)
"""

from __future__ import annotations

import argparse
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REFS = os.path.abspath(
    os.path.join(_HERE, "..", ".claude", "skills", "humanize-korean", "references")
)
_TAXONOMY = os.path.join(_REFS, "ai-tell-taxonomy.md")
_HEADER = os.path.join(_REFS, "quick-rules.header.md")
_FOOTER = os.path.join(_REFS, "quick-rules.footer.md")
_OUT = os.path.join(_REFS, "quick-rules.md")

# ## A. 번역투 (Translation-ese) — S1~S2
_CATEGORY_RE = re.compile(r"^## ([A-J])\.\s+(.+?)\s*$")
# ### A-1. "~에 대하여" 남발 [S1]
_PATTERN_RE = re.compile(r"^### ([A-J]-\d+)\.\s+(.+?)\s*(?:\[([^\]]+)\])?\s*$")
# - _quick: true · quick_pattern: X · quick_fix: Y_
# - _quick: false_   (false는 pattern/fix 없이 값+밑줄로 끝나는 형식도 허용)
# `\b` 대신 명시적 경계(공백···밑줄)를 써야 `false_`를 놓치지 않는다.
_QUICK_RE = re.compile(
    r"_quick:\s*(true|false)"
    r"(?:\s*·\s*quick_pattern:\s*(.*?))?"
    r"(?:\s*·\s*quick_fix:\s*(.*?))?"
    r"_\s*$"
)


class ParseError(Exception):
    pass


def parse_taxonomy(text: str) -> list[dict]:
    """taxonomy에서 (category, id, title, severity, quick, pattern, fix)를 뽑는다.

    각 패턴 블록은 헤딩부터 다음 헤딩(### 또는 ##) 전까지. 블록 안에서
    _quick: 메타를 찾는다. 메타가 없으면 quick=None으로 두어 호출부가
    누락을 감지하게 한다(조용히 제외하지 않는다).
    """
    lines = text.splitlines()
    patterns: list[dict] = []
    cur_cat = cur_cat_name = None
    cur: dict | None = None

    def flush():
        if cur is not None:
            patterns.append(cur)

    for ln in lines:
        m_cat = _CATEGORY_RE.match(ln)
        if m_cat:
            flush()
            cur = None
            cur_cat, cur_cat_name = m_cat.group(1), m_cat.group(2)
            continue

        m_pat = _PATTERN_RE.match(ln)
        if m_pat:
            flush()
            cur = {
                "category": cur_cat,
                "category_name": cur_cat_name,
                "id": m_pat.group(1),
                "title": m_pat.group(2).strip(),
                "severity": (m_pat.group(3) or "").strip(),
                "quick": None,  # 메타 미발견 표식
                "pattern": None,
                "fix": None,
            }
            continue

        if cur is not None and "_quick:" in ln:
            m_q = _QUICK_RE.search(ln)
            if m_q:
                cur["quick"] = m_q.group(1) == "true"
                cur["pattern"] = (m_q.group(2) or "").strip() or None
                cur["fix"] = (m_q.group(3) or "").strip() or None

    flush()
    return patterns


def render(patterns: list[dict], header: str, footer: str) -> str:
    """quick: true 패턴만 골라 대분류별로 렌더한다."""
    out: list[str] = [header.rstrip(), ""]
    by_cat: dict[str, list[dict]] = {}
    order: list[str] = []
    for p in patterns:
        if p["quick"] is not True:
            continue
        if p["category"] not in by_cat:
            by_cat[p["category"]] = []
            order.append(p["category"])
        by_cat[p["category"]].append(p)

    for cat in order:
        items = by_cat[cat]
        name = items[0]["category_name"]
        out.append(f"## {cat}. {name}")
        out.append("")
        for p in items:
            sev = f" [{p['severity']}]" if p["severity"] else ""
            pat = p["pattern"] or p["title"]
            fix = p["fix"] or "(처방 미기재 — taxonomy 확인 필요)"
            out.append(f"- **{p['id']}**{sev} {pat} → {fix}")
        out.append("")

    out.append(footer.strip())
    out.append("")
    return "\n".join(out)


def build() -> tuple[str, list[dict]]:
    with open(_TAXONOMY, encoding="utf-8") as f:
        taxonomy = f.read()
    with open(_HEADER, encoding="utf-8") as f:
        header = f.read()
    with open(_FOOTER, encoding="utf-8") as f:
        footer = f.read()

    patterns = parse_taxonomy(taxonomy)
    missing = [p["id"] for p in patterns if p["quick"] is None]
    if missing:
        raise ParseError(
            f"quick 메타 누락 {len(missing)}건: {', '.join(missing)}\n"
            "모든 패턴에 `_quick: true|false …_` 메타가 있어야 한다."
        )
    return render(patterns, header, footer), patterns


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="quick-rules.md 생성기")
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

    n_true = sum(1 for p in patterns if p["quick"] is True)
    n_false = sum(1 for p in patterns if p["quick"] is False)

    if args.check:
        existing = ""
        if os.path.exists(_OUT):
            with open(_OUT, encoding="utf-8") as f:
                existing = f.read()
        if existing.rstrip() != rendered.rstrip():
            print(
                "error: quick-rules.md 가 taxonomy와 어긋난다. "
                "`python3 scripts/build_quick_rules.py` 로 재생성하라.",
                file=sys.stderr,
            )
            return 1
        print(f"quick-rules.md 최신 (quick: true {n_true} / false {n_false})")
        return 0

    with open(_OUT, "w", encoding="utf-8") as f:
        f.write(rendered)
    lines = rendered.count("\n") + 1
    print(
        f"quick-rules.md 생성 — {lines}줄 / {len(rendered)}자 "
        f"(quick: true {n_true} / false {n_false} / 전체 {len(patterns)})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
