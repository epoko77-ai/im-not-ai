#!/usr/bin/env python3
"""commit-ko 커밋 메시지 경고 린터 — git commit-msg 훅 전용, 경고만 하고 절대 커밋을 막지 않는다.

`extras/skills/commit-ko/references/commit-lexicon.md`(SSOT)의 1~5절 패턴을
직접 실행 가능한 정규식으로 파생시킨 것이다. lexicon이 갱신되면 이 목록도 함께
점검할 것 — LLM 없이 도는 스크립트라 lexicon의 "표에 없어도 같은 원칙 적용"
같은 일반화는 흉내낼 수 없고, 여기 등록된 패턴만 잡는다.

동작:
    python3 commit_msg_lint.py <commit-msg-file>
    - 매칭된 패턴이 있으면 stderr에 경고 + commit-ko 스킬 안내를 출력하고 exit 1.
    - 없으면 조용히 exit 0.
    - 실제 git 훅(.githooks/commit-msg)은 이 exit code를 무시하고 항상 0으로
      끝난다 — "경고만, 차단 없음"이 이 훅의 정책이다. exit code는 이 스크립트를
      다른 용도(CI 등)로 재사용할 사람을 위해 정직하게 남겨둔다.

건너뛰기:
    - 커밋 메시지 어디에나 "[skip-commit-ko]" 포함
    - 환경변수 COMMIT_KO_HOOK_SKIP=1
    - Merge/Revert/fixup!/squash! 커밋 (첫 줄 접두사로 자동 판별)
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass

SKIP_MARKER = "[skip-commit-ko]"
SKIP_ENV = "COMMIT_KO_HOOK_SKIP"

_AUTO_SKIP_PREFIXES = ("Merge ", "Revert ", "fixup!", "squash!")


@dataclass
class Finding:
    code: str
    matched: str
    suggestion: str

    def __str__(self) -> str:
        return f"  - '{self.matched}' — {self.suggestion}"


# (code, regex, suggestion) — commit-lexicon.md 절 번호를 주석으로 명시해 SSOT와
# 대응 관계를 추적 가능하게 유지한다.
_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (  # lexicon §1 — 사무적 동사(수행/진행/실시)
        "bureaucratic_verb",
        re.compile(r"(?:수행|진행|실시)(?:함|하였|했|하였습니다|했습니다|하는|할|하여)"),
        "사무적 격식 동사 — '~함' 또는 구체 동사로 (예: '리팩터링을 진행함' → '리팩터링')",
    ),
    (  # lexicon §4 — "작업을 완료/수행/진행/실시" 장황한 명사구
        "wordy_completion",
        re.compile(r"작업을\s*(?:완료|수행|진행|실시)"),
        "'~작업을 완료/수행/진행함' → 작업 이름만 (예: '버그 수정 작업을 완료함' → '버그 수정')",
    ),
    (  # lexicon §3 — 과공손 종결
        "over_polite_ending",
        re.compile(r"하였습니다|했습니다|하였음"),
        "커밋 메시지는 '~함'·명사형 종결이 관용 (예: '수정하였습니다' → '수정')",
    ),
    (  # lexicon §5 (A-8) — 이중 피동
        "double_passive",
        re.compile(r"되어지(?:는|도록|었|ㄴ다|다)"),
        "이중 피동 — 단일 피동 또는 능동으로 (예: '검증되어지는' → '검증되는'/'검증하는')",
    ),
    (  # lexicon §5 (A-9) — by-passive "~에 의해"
        "by_passive",
        re.compile(r"에\s*의해\s*\S{0,12}(?:되|됨|된)"),
        "by-passive 번역투 — 행위자를 주어로 복귀 (예: '사용자에 의해 트리거되는' → '사용자가 트리거하는')",
    ),
    (  # lexicon §5 (A-7) — have 직역
        "have_literal",
        re.compile(r"가지도록|가지고\s*있"),
        "'가지다' have 직역 — 동사로 환원 (예: '캐시를 가지도록' → '캐시를 추가하도록')",
    ),
    (  # lexicon §5 (A-12) — 자동화된 피동
        "automated_passive",
        re.compile(r"하게\s*되는|하게\s*되었"),
        "자동화된 피동 — 능동 서술로 (예: '실패하게 되는 원인' → '실패 원인')",
    ),
]


def _strip_comment_lines(text: str) -> str:
    """git이 comment_char(기본 '#')로 시작하는 줄을 아직 안 지웠을 수 있어 걸러낸다."""
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )


def should_skip(text: str) -> bool:
    if os.environ.get(SKIP_ENV) == "1":
        return True
    if SKIP_MARKER in text:
        return True
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    return first_line.startswith(_AUTO_SKIP_PREFIXES)


def scan(text: str) -> list[Finding]:
    if should_skip(text):
        return []
    body = _strip_comment_lines(text)
    findings: list[Finding] = []
    for code, pattern, suggestion in _PATTERNS:
        m = pattern.search(body)
        if m:
            findings.append(Finding(code, m.group(0), suggestion))
    return findings


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python3 commit_msg_lint.py <commit-msg-file>", file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as f:
        text = f.read()
    findings = scan(text)
    if not findings:
        return 0
    print("commit-ko: 커밋 메시지에 AI 티 사무적·번역투 표현이 보입니다 (경고 — 커밋은 진행됩니다)",
          file=sys.stderr)
    for finding in findings:
        print(finding, file=sys.stderr)
    print("  자연스럽게 다듬으려면: Claude Code에서 \"커밋 메시지 자연스럽게\" 요청 (commit-ko 스킬)",
          file=sys.stderr)
    print(f"  이번만 건너뛰려면: {SKIP_ENV}=1 git commit ... 또는 메시지에 {SKIP_MARKER} 포함",
          file=sys.stderr)
    return 1


# ── 콘솔 하드닝 (#84) ───────────────────────────────────────────────
# Windows(cp949)에서 한글·em-dash 출력이 UnicodeEncodeError 로 죽는 것을 막는다.
import os as _os  # noqa: E402
import sys as _sys  # noqa: E402

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import console as _console  # noqa: E402

if __name__ == "__main__":
    _console.force_utf8_console()
    raise SystemExit(main(sys.argv))
