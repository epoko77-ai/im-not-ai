#!/usr/bin/env python3
"""commit-lexicon.md의 taxonomy ID 참조가 SSOT와 어긋나지 않는지 검사한다.

commit-lexicon.md는 quick-rules.md와 달리 ai-tell-taxonomy.md에서 자동
생성되지 않는다 — 커밋 메시지 register로 손수 파생시킨 소형 참조표라
생성기를 두기엔 과하다는 판단이었다. 하지만 손 파생은 build_quick_rules.py
가 애초에 막으려 했던 것과 같은 종류의 ID 드리프트를 그대로 재현한다.
실제로 헤더 인용문(A-7·A-8·A-9·F-4)과 5절 표 본문(A-12 추가 인용)이
어긋난 채로 코드 리뷰를 통과할 뻔했다. 이 스크립트는 생성 대신 검사로
같은 위험을 결박한다.

검사 두 가지:
    1. commit-lexicon.md에 등장하는 모든 taxonomy ID가 실제로
       ai-tell-taxonomy.md에 존재하는가 (taxonomy가 갱신·재번호되며
       참조가 낡는 경우 검출).
    2. 문서 상단 파생 선언 블록(첫 `## ` 헤딩 이전)이 인용한 ID 집합과
       표 본문(그 이후)이 실제로 인용한 ID 집합이 정확히 일치하는가
       (헤더-본문 정합 — 한쪽만 갱신되고 다른 쪽이 낡는 경우 검출).

CLI:
    python3 scripts/check_commit_lexicon_ids.py
"""

from __future__ import annotations

import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, ".."))
_TAXONOMY = os.path.join(
    _REPO, ".claude", "skills", "humanize-korean", "references", "ai-tell-taxonomy.md"
)
# commit-ko는 기본 플러그인(.claude/skills/)에서 제외된 opt-in 스킬이라
# extras/skills/ 아래 산다 — 위치가 바뀌어도 taxonomy와의 드리프트 결박은 유지한다.
_LEXICON = os.path.join(
    _REPO, "extras", "skills", "commit-ko", "references", "commit-lexicon.md"
)

# `\b`는 쓸 수 없다 — Python re의 `\w`는 한글 음절도 단어 문자로 취급해서
# "F-4를"처럼 조사가 공백 없이 바로 붙으면 경계가 사라져 매치가 실패한다.
# ASCII 영숫자만 경계 판정에 쓰도록 lookaround로 명시한다.
_ID_RE = re.compile(r"(?<![A-Za-z0-9])([A-J]-\d+)(?!\d)")
_TAXONOMY_HEADING_RE = re.compile(r"^### ([A-J]-\d+)\.", re.MULTILINE)


class DriftError(Exception):
    pass


def parse_taxonomy_ids(text: str) -> set[str]:
    return set(_TAXONOMY_HEADING_RE.findall(text))


def parse_lexicon_ids(text: str) -> tuple[set[str], set[str]]:
    """(헤더 선언 ID 집합, 본문 인용 ID 집합)을 반환한다.

    헤더 = 첫 `## ` 대분류 헤딩 이전(파생 선언 블록쿼트).
    본문 = 그 이후 전체(각 절 헤딩 + 표).
    """
    m = re.search(r"^## ", text, re.MULTILINE)
    split_at = m.start() if m else len(text)
    header, body = text[:split_at], text[split_at:]
    return set(_ID_RE.findall(header)), set(_ID_RE.findall(body))


def validate() -> list[str]:
    with open(_TAXONOMY, encoding="utf-8") as f:
        taxonomy_ids = parse_taxonomy_ids(f.read())
    with open(_LEXICON, encoding="utf-8") as f:
        header_ids, body_ids = parse_lexicon_ids(f.read())

    errors: list[str] = []

    unknown = (header_ids | body_ids) - taxonomy_ids
    if unknown:
        errors.append(
            f"taxonomy에 없는 ID 인용: {', '.join(sorted(unknown))} "
            "(taxonomy가 재번호되었거나 오타)"
        )

    only_in_body = body_ids - header_ids
    if only_in_body:
        errors.append(
            f"본문에서 인용했지만 헤더 파생 선언에 없는 ID: "
            f"{', '.join(sorted(only_in_body))} "
            "(commit-lexicon.md 상단 블록쿼트에 추가할 것)"
        )

    only_in_header = header_ids - body_ids
    if only_in_header:
        errors.append(
            f"헤더가 선언했지만 본문에서 인용하지 않는 ID: "
            f"{', '.join(sorted(only_in_header))} "
            "(더 이상 쓰지 않으면 헤더에서 제거, 여전히 쓰면 본문에 근거로 명시할 것)"
        )

    return errors


def main(argv: list[str] | None = None) -> int:
    errors = validate()
    if errors:
        print("error: commit-lexicon.md ID 드리프트 발견", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print("commit-lexicon.md ID 정합 확인 완료 (헤더 == 본문, 전부 taxonomy에 실재)")
    return 0


# ── 콘솔 하드닝 (#84) ───────────────────────────────────────────────
# Windows(cp949)에서 한글·em-dash 출력이 UnicodeEncodeError 로 죽는 것을 막는다.
sys.path.insert(0, _HERE)
import console as _console  # noqa: E402

if __name__ == "__main__":
    _console.force_utf8_console()
    sys.exit(main())
