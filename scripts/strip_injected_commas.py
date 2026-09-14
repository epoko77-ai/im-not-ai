#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C-11 역주입 제거 — 윤문이 새로 만든 문장에서만 연결어미 뒤 쉼표를 걷어낸다.

light 경로 실측(오염쌍 28편)에서 윤문 **후** 연결어미 쉼표가 원문보다 늘어난
문서가 16/28(57%)였다. 규칙 문구("주입 금지")로는 편집 모델의 영어 comma
감각을 막지 못한다 — restore_modality.py와 같은 결정적 후처리로 막는다.

원칙 (사람 쉼표 보호):
- 원문에 그대로 있던 문장은 **불가침** — 필자의 연결어미 쉼표(설명문 인간
  기저율 32.9~41.0%)를 건드리지 않는다.
- 윤문이 새로 쓴 문장(원문에 없는 문장)에서만 연결어미 직후 쉼표를 제거한다.
  새 문장의 연결어미 쉼표는 필자의 것일 수 없다 — 편집 모델의 습관이다.
- 따옴표(" " ' ' 「」 『』) 안은 건드리지 않는다.

사용:
    python3 scripts/strip_injected_commas.py --before a.txt --after b.md --out b.md --json

`--out` 없으면 결과를 stdout으로 낸다. 종료 코드는 항상 0 — 게이트가 아니다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

# 연결어미 + 쉼표. '자,'는 감탄사("자, 이제")와 충돌하므로 제외.
# -아서/-어서의 모음 축약형(-져서/-해서/-여서)은 포함하되, 조사와 겹치는
# 맨몸 '서'("~에서,")는 다루지 않는다.
_CONN_COMMA_RE = re.compile(r"(고|며|지만|면서|는데|아서|어서|여서|해서|져서),(\s)")

# 따옴표 스팬 — 이 안의 쉼표는 발화 원문이므로 불가침.
_QUOTE_RE = re.compile(r"“[^”]*”|‘[^’]*’|\"[^\"]*\"|「[^」]*」|『[^』]*』")

_SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+")


def _sentences(text: str) -> list[str]:
    return [s for s in _SENT_SPLIT.split(text) if s.strip()]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())


def _strip_in_sentence(sent: str) -> tuple[str, int]:
    """한 문장에서 따옴표 밖 연결어미 쉼표를 제거. (결과, 제거 수) 반환."""
    spans = [m.span() for m in _QUOTE_RE.finditer(sent)]

    def in_quote(pos: int) -> bool:
        return any(a <= pos < b for a, b in spans)

    removed = 0
    out = []
    last = 0
    for m in _CONN_COMMA_RE.finditer(sent):
        if in_quote(m.start()):
            continue
        out.append(sent[last : m.start()])
        out.append(m.group(1) + m.group(2))
        last = m.end()
        removed += 1
    out.append(sent[last:])
    return "".join(out), removed


def strip_injected(before: str, after: str, all_sentences: bool = False) -> tuple[str, dict]:
    """all_sentences=False: 윤문이 새로 쓴 문장만(기본 — 필자 쉼표 보호).
    all_sentences=True: 전 문장(따옴표 안 제외) — 진단이 문서를 AI 산출물로
    판정하고 C-11을 티로 지목한 standard/heavy 경로 전용. 사람 532편 실측에서
    연결어미 쉼표는 사람 중앙값이 문장의 15%라 밀도만으로는 사람/주입을 못
    가른다 — 그래서 이 모드는 밀도가 아니라 경로 판정(진단)에만 묶는다."""
    originals = set() if all_sentences else {_norm(s) for s in _sentences(before)}
    total_removed = 0
    touched = 0
    parts: list[str] = []
    # 문장 단위로 처리하되 원문 화이트스페이스를 보존하기 위해 split 지점을 기억한다.
    pieces = _SENT_SPLIT.split(after)
    seps = _SENT_SPLIT.findall(after)
    for i, piece in enumerate(pieces):
        if piece.strip() and _norm(piece) not in originals:
            fixed, n = _strip_in_sentence(piece)
            if n:
                total_removed += n
                touched += 1
            parts.append(fixed)
        else:
            parts.append(piece)
        if i < len(seps):
            parts.append(seps[i])
    report = {"commas_removed": total_removed, "sentences_touched": touched}
    return "".join(parts), report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="윤문이 새로 만든 문장의 연결어미 쉼표(C-11 역주입)를 제거한다")
    ap.add_argument("--before", required=True, help="원문 파일")
    ap.add_argument("--after", required=True, help="윤문본 파일")
    ap.add_argument("--out", help="결과를 쓸 파일(없으면 stdout)")
    ap.add_argument("--json", action="store_true", help="리포트를 stderr에 JSON으로")
    ap.add_argument(
        "--all", action="store_true",
        help="전 문장 제거(따옴표 안 제외) — 진단이 C-11을 지목한 standard/heavy 경로 전용",
    )
    args = ap.parse_args(argv)

    with open(args.before, encoding="utf-8") as f:
        before = f.read()
    with open(args.after, encoding="utf-8") as f:
        after = f.read()

    fixed, report = strip_injected(before, after, all_sentences=args.all)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(fixed)
    else:
        sys.stdout.write(fixed)
    if args.json:
        print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
