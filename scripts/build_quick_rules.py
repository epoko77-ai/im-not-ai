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
    python3 scripts/build_quick_rules.py --check    # 최신 여부 + fast 토큰 예산 상한 검사(쓰지 않음)
"""

from __future__ import annotations

import argparse
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REFS = os.path.abspath(
    os.path.join(_HERE, "..", "skills", "humanize-korean", "references")
)
_TAXONOMY = os.path.join(_REFS, "ai-tell-taxonomy.md")
_HEADER = os.path.join(_REFS, "quick-rules.header.md")
_FOOTER = os.path.join(_REFS, "quick-rules.footer.md")
_OUT = os.path.join(_REFS, "quick-rules.md")

# ## A. 번역투 (Translation-ese) — S1~S2
_CATEGORY_RE = re.compile(r"^## ([A-J])\.\s+(.+?)\s*$")
# ### A-1. "~에 대하여" 남발 [S1]
_PATTERN_RE = re.compile(r"^### ([A-J]-\d+)\.\s+(.+?)\s*(?:\[([^\]]+)\])?\s*$")
# 심각도는 제목 **어디에** 있어도 뽑는다. 위 _PATTERN_RE 의 세 번째 그룹은 줄
# 끝의 `[...]` 만 잡으므로, `[S1] · v1.1 신규 · v2.3 실측 최강 신호` 처럼 버전
# 접미가 뒤에 붙은 제목에서는 심각도를 잃는다. 그 결과 quick: true 53건 중
# 31건(C-8 포함)이 심각도 태그 없이 quick-rules.md 에 실려, monolith 가 S1
# 우선순위를 볼 수 없었다. PR #94 가 같은 결함을 지적했다.
_SEVERITY_RE = re.compile(r"\[(S[1-9][^\]]*)\]")
# - _quick: true · quick_pattern: X · quick_fix: Y_
# - _quick: false_   (false는 pattern/fix 없이 값+밑줄로 끝나는 형식도 허용)
# `\b` 대신 명시적 경계(공백···밑줄)를 써야 `false_`를 놓치지 않는다.
_QUICK_RE = re.compile(
    r"_quick:\s*(true|false)"
    r"(?:\s*·\s*quick_pattern:\s*(.*?))?"
    r"(?:\s*·\s*quick_fix:\s*(.*?))?"
    r"_\s*$"
)


# ── fast 토큰 예산 가드 ─────────────────────────────────────────────
# `quick-rules.md` 는 fast(light) 경로에서 monolith 에이전트에게 매 호출 통째로
# 주입된다(SKILL.md). 건수가 늘면 모든 빠른 윤문의 프롬프트 비용에 그대로 얹힌다.
# 정책은 taxonomy 머리말이 SSOT다 — 아래 상수는 그 문장과 일치해야 하고,
# `tests/test_quick_rules_build.py` 가 둘의 일치를 검사한다.
#
# 2026-09-22: quick:true 가 61건까지 새어 상한(60)을 넘겼다. drift 검사만 있고
# 건수 검사가 없어 한 방향으로만 올라갔다. 8건 강등(53건) 후 이 가드를 넣는다.
QUICK_BUDGET_TARGET = 50
QUICK_BUDGET_TOLERANCE_PCT = 20
QUICK_BUDGET_MAX = QUICK_BUDGET_TARGET * (100 + QUICK_BUDGET_TOLERANCE_PCT) // 100

# - fast 토큰 예산 보호: `quick: true`는 50개 내외(현행 quick-rules 규모 ±20%)를 유지한다.
_BUDGET_POLICY_RE = re.compile(
    r"`quick:\s*true`\s*는\s*(\d+)\s*개\s*내외.*?±\s*(\d+)\s*%"
)


def budget_policy_from_taxonomy(text: str) -> tuple[int, int]:
    """taxonomy 머리말이 선언한 (목표 건수, 허용 오차 %) 를 읽는다.

    정책을 문서에서만 고치고 가드는 그대로 두는 드리프트를 막기 위한 통로다.
    문장을 못 찾으면 ParseError — 조용히 통과시키지 않는다.
    """
    m = _BUDGET_POLICY_RE.search(text)
    if not m:
        raise ParseError(
            "taxonomy 머리말에서 quick 예산 정책 문장을 찾지 못했다. "
            "문구를 바꿨다면 build_quick_rules.py 의 _BUDGET_POLICY_RE 도 맞춰라."
        )
    return int(m.group(1)), int(m.group(2))


class ParseError(Exception):
    pass


def _extract_severity(heading: str, tail_group: str | None) -> str:
    """제목에서 심각도(S1/S2/S3)를 뽑는다.

    `[S1]` 이 줄 끝에 있으면 tail_group 이 이미 담고 있다. 버전 접미가 뒤에
    붙어 tail 로 잡히지 않는 경우를 위해 제목 전체를 다시 훑는다. 줄 끝
    `[...]` 가 심각도가 아닌 다른 메모일 수도 있으므로 S 패턴만 신뢰한다.
    """
    if tail_group:
        m = _SEVERITY_RE.fullmatch(f"[{tail_group.strip()}]")
        if m:
            return m.group(1).strip()
    m = _SEVERITY_RE.search(heading)
    return m.group(1).strip() if m else ""


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
                # 줄 끝 `[...]`(group 3)을 우선 쓰되, 비었으면 제목 전체에서
                # `[S…]` 를 찾는다. 두 경로 모두 실패하면 빈 문자열.
                "severity": _extract_severity(ln, m_pat.group(3)),
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
        if n_true > QUICK_BUDGET_MAX:
            print(
                f"error: fast 토큰 예산 초과 — quick: true {n_true}건 "
                f"(상한 {QUICK_BUDGET_MAX} = {QUICK_BUDGET_TARGET}건 "
                f"±{QUICK_BUDGET_TOLERANCE_PCT}%). quick-rules.md 는 fast 경로 "
                "매 호출에 주입된다. 신규 패턴은 `quick: false` 가 기본값이고, "
                "true 가 필요하면 실측 판별력이 약한 기존 항목을 먼저 강등하라.",
                file=sys.stderr,
            )
            return 1
        print(
            f"quick-rules.md 최신 (quick: true {n_true} / false {n_false} "
            f"· 예산 {n_true}/{QUICK_BUDGET_MAX})"
        )
        return 0

    with open(_OUT, "w", encoding="utf-8") as f:
        f.write(rendered)
    lines = rendered.count("\n") + 1
    print(
        f"quick-rules.md 생성 — {lines}줄 / {len(rendered)}자 "
        f"(quick: true {n_true} / false {n_false} / 전체 {len(patterns)})"
    )
    if n_true > QUICK_BUDGET_MAX:
        # 생성은 막지 않는다 — 강등 작업 중에도 재생성은 돌아가야 한다.
        # 대신 --check(CI)에서 실패하므로 커밋 전에 반드시 걸린다.
        print(
            f"warning: quick: true {n_true}건이 예산 상한 {QUICK_BUDGET_MAX}건을 "
            "넘었다. CI(--check)에서 실패한다.",
            file=sys.stderr,
        )
    return 0


# ── 콘솔 하드닝 (#84) ───────────────────────────────────────────────
# Windows(cp949)에서 한글·em-dash 출력이 UnicodeEncodeError 로 죽는 것을 막는다.
import os as _os  # noqa: E402
import sys as _sys  # noqa: E402

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import console as _console  # noqa: E402

if __name__ == "__main__":
    _console.force_utf8_console()
    sys.exit(main())
