#!/usr/bin/env python3
"""내용 보존 게이트 — 문체가 아니라 **내용**이 살아 있는지 본다.

영어 게이트는 셋 다 문체 축이었다(`verify_change_rate`·`reinjection`·`underedit`).
수치·직접 인용·인용문헌·제목은 무방비였다 — 철칙 #1(의미 불변)에 코드 방어가
하나도 없는 상태였다. 한국어 `scripts/checks.py` 의 대응물이다.

한국어에서 검증된 설계 결정 둘을 그대로 가져온다.

1. **수치는 방향성 게이트.** 주입만 FAIL, 소실은 advisory.
   문장 병합·표기 통합에서도 수치는 사라지므로 소실을 게이트하면 양치기
   소년이 된다(`checks.dropped_numbers` 주석). 없던 수치가 생기는 것은
   새 주장 주입이라 언제나 FAIL.
2. **집합 비교.** 순서·반복 횟수 차이는 보지 않는다. 오탐 최소화가 우선.

한국어에서 **가져오지 않은** 것: 발화 인용 분류기(`_is_protected_quote`).
영어는 강조·용어 언급에도 큰따옴표를 쓴다(`the so-called "alignment problem"`).
대신 **따옴표가 아니라 그 안의 글자가 남았는지**만 본다 — 따옴표를 벗기는
편집은 통과하고 내용 삭제만 잡힌다. 사전 없이 같은 것을 지킨다.

표준 라이브러리만. 언어 무관(수사 단위만 영어).
"""
from __future__ import annotations

import argparse
import re
import sys

MIN_QUOTE_LEN = 8  # 이보다 짧으면 강조 용법으로 본다 (checks.MIN_QUOTE_LEN 동일)

_NUM_TOKEN = re.compile(r"\d+(?:[.,]\d+)*")
_SCALE = {
    "hundred": 100,
    "thousand": 10**3,
    "million": 10**6,
    "billion": 10**9,
    "trillion": 10**12,
}
_SCALE_AFTER = re.compile(r"\s*-?\s*(" + "|".join(_SCALE) + r")s?\b", re.I)

# `[12]` · `[3, 5]` · `[1-4]` / `(Smith, 2020)` · `(Lee et al., 2019)` · `(2020)`
_CITE_BRACKET = re.compile(r"\[\d{1,3}(?:\s*[,–-]\s*\d{1,3})*\]")
_CITE_AUTHOR_YEAR = re.compile(r"\([^()]{0,60}?(?:19|20)\d{2}[a-z]?\)")

_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$")
_SUMMARY_BLOCK = re.compile(r"<!--\s*HUMANIZE-SUMMARY\b.*", re.DOTALL)
_WS = re.compile(r"\s+")


def _norm_ws(s: str) -> str:
    return _WS.sub(" ", s).strip()


def _canon(token: str, mult: int = 1) -> str:
    v = float(token.replace(",", "")) * mult
    return str(int(v)) if v == int(v) else str(v)


def number_values(text: str) -> set[str]:
    """텍스트의 수치 값 집합. 표기 차이를 흡수한다.

    `10,000` == `10000`, `40%` == `40 percent`, `2 million` == `2,000,000`.
    """
    values: set[str] = set()
    for m in _NUM_TOKEN.finditer(text):
        scale = _SCALE_AFTER.match(text, m.end())
        try:
            values.add(
                _canon(m.group(0), _SCALE[scale.group(1).lower()] if scale else 1)
            )
        except ValueError:  # "1.2.3" 같은 비수치 토큰
            continue
    return values


def extract_quotes(text: str, min_len: int = MIN_QUOTE_LEN) -> list[str]:
    quotes = re.findall(r"“([^”]+)”", text)
    parts = text.split('"')
    if len(parts) % 2 == 1:  # 짝이 맞을 때만 — 홑따옴표는 축약형과 구분 불가라 제외
        quotes += parts[1::2]
    return [q for q in (_norm_ws(q) for q in quotes) if len(q) >= min_len]


def extract_citations(text: str) -> set[str]:
    return {
        _norm_ws(m.group(0))
        for rx in (_CITE_BRACKET, _CITE_AUTHOR_YEAR)
        for m in rx.finditer(text)
    }


def extract_headings(text: str) -> list[str]:
    return [m.group(1).strip() for m in (_HEADING.match(l) for l in text.splitlines()) if m]


def strip_summary_block(text: str) -> str:
    return _SUMMARY_BLOCK.sub("", text).strip()


def check(before: str, after: str) -> dict:
    """내용 보존 판정.

    반환:
        ``failed``   — FAIL 이 하나라도 있으면 True
        ``failures`` — [{kind, message}] · kind 는 안정 API
        ``advisory`` — 판정에 쓰지 않는 관측치 (수치 소실)
    """
    before, after = strip_summary_block(before), strip_summary_block(after)
    failures: list[dict] = []

    if not after.strip():
        failures.append({"kind": "empty_output", "message": "윤문본이 비어 있다"})

    nb, na = number_values(before), number_values(after)
    injected = sorted(na - nb, key=len)
    if injected:
        failures.append({
            "kind": "number_injected",
            "message": f"원문에 없던 수치가 등장했다: {injected} (없던 주장 주입 위험)",
        })

    after_body = _norm_ws(after)
    for q in extract_quotes(before):
        if q.strip(" .,;:") not in after_body:
            failures.append({
                "kind": "quote_dropped",
                "message": f'직접 인용 "{q[:40]}…" 의 내용이 사라졌다 (인용 불변 철칙)',
            })

    for c in sorted(extract_citations(before) - extract_citations(after)):
        failures.append({
            "kind": "citation_dropped",
            "message": f"인용문헌 {c} 가 사라졌다 (전거는 불변)",
        })

    out_headings = set(extract_headings(after))
    for h in extract_headings(before):
        if h in out_headings:
            continue
        kind = "heading_absorbed" if _norm_ws(h) in after_body else "heading_lost"
        failures.append({"kind": kind, "message": f"제목 '{h}' 이 제목 줄에서 사라졌다"})

    return {
        "failed": bool(failures),
        "failures": failures,
        "advisory": {"dropped_numbers": sorted(nb - na, key=len)},
    }


def main(argv: list[str] | None = None) -> int:
    """Exit code: 0 보존 / 1 위반 / 3 실행 오류."""
    ap = argparse.ArgumentParser(description="내용 보존 게이트 (철칙 #1)")
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    args = ap.parse_args(argv)

    try:
        with open(args.before, encoding="utf-8") as f:
            before = f.read()
        with open(args.after, encoding="utf-8") as f:
            after = f.read()
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3

    out = check(before, after)
    dropped = out["advisory"]["dropped_numbers"]
    if dropped:
        print(f"advisory: 수치 소실 {dropped} — 게이트 아님, 문장 병합일 수 있다")
    if out["failed"]:
        for f in out["failures"]:
            print(f"FAIL [{f['kind']}] {f['message']}")
        print("gate: FAIL — 내용이 훼손됐다. 해당 구간을 원문으로 되돌릴 것")
        return 1
    print("gate: OK — 수치·인용·전거·제목 보존")
    return 0


if __name__ == "__main__":
    sys.exit(main())
