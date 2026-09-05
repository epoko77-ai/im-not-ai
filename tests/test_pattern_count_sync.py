"""패턴 수 동기화 — 문서가 선언한 수와 SSOT 실물의 drift 를 막는다.

v2.6 에서 패턴이 10건 늘었는데 CLAUDE.md·SKILL.md·diagnosis-rules 헤더가
"70/71" 에 멈춰 있었다(2026-09-02 발견, 7곳). 사람이 세는 방식으로는 또 어긋난다.

주의: `ai-tell-taxonomy.md` 의 버전 히스토리에 있는 "전 71개 패턴" 은
**v2.0.1 시점의 기록**이라 갱신 대상이 아니다 — 검사 대상 파일에서 제외한다.

stdlib only, CI 상시 실행.
"""
from __future__ import annotations

import os
import re
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_TAXONOMY = os.path.join(
    _ROOT, "skills", "humanize-korean", "references", "ai-tell-taxonomy.md"
)
_DIAGNOSIS = os.path.join(
    _ROOT, "skills", "humanize-korean", "references", "diagnosis-rules.md"
)
_CLAUDE_MD = os.path.join(_ROOT, "CLAUDE.md")
_KO_SKILL = os.path.join(_ROOT, "skills", "humanize-korean", "SKILL.md")

# diagnosis-rules.md 는 SSOT 에서 생성된 전수 인덱스라 ID 집합의 기준으로 쓴다.
_ID_RE = re.compile(r"^- \*\*([A-J]-\d+)\*\*", re.M)
_TAXONOMY_ID_RE = re.compile(r"^#{3,4}\s+\*{0,2}([A-J]-\d+)", re.M)

# 문서들이 패턴 수를 선언하는 자리. CLAUDE.md·SKILL.md 는 **여러 형식으로
# 여러 번** 선언한다(실측 2026-09-02: 총 7곳).
# search() 로 첫 매치만 보면 나머지가 70/71 에 남아도 테스트가 통과한다 —
# finditer 로 전수 검사한다.
_DECLARATION_FORMS = (
    re.compile(r"(\d+)개 AI 티 패턴"),
    re.compile(r"(\d+)패턴 전수"),
)
_DECLARING_FILES = (_CLAUDE_MD, _KO_SKILL, _DIAGNOSIS)

# 최소 몇 곳에서 선언을 찾아야 하는지 — 정규식이 조용히 아무것도 못 잡는 것을 막는다.
_MIN_DECLARATION_SITES = 7


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def ssot_pattern_ids() -> set[str]:
    """SSOT 가 정의한 패턴 ID 전수."""
    return set(_ID_RE.findall(_read(_DIAGNOSIS)))


class PatternCountSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ids = ssot_pattern_ids()

    def test_ssot_has_patterns(self) -> None:
        self.assertGreater(len(self.ids), 50, "SSOT 파싱이 깨졌다")

    def test_declared_counts_match_ssot(self) -> None:
        actual = len(self.ids)
        found = 0
        for path in _DECLARING_FILES:
            text = _read(path)
            for pattern in _DECLARATION_FORMS:
                for match in pattern.finditer(text):
                    found += 1
                    declared = int(match.group(1))
                    line = text[: match.start()].count("\n") + 1
                    self.assertEqual(
                        declared,
                        actual,
                        f"{os.path.basename(path)}:{line} 선언 {declared} "
                        f"!= SSOT 실측 {actual}",
                    )
        self.assertGreaterEqual(
            found,
            _MIN_DECLARATION_SITES,
            f"패턴 수 선언을 {found}곳만 찾았다 — 정규식이 실물과 어긋났을 수 있다",
        )

    def test_taxonomy_and_diagnosis_agree(self) -> None:
        """빌드 산출물이 SSOT 와 같은 ID 집합을 담는지."""
        taxonomy_ids = set(_TAXONOMY_ID_RE.findall(_read(_TAXONOMY)))
        missing = self.ids - taxonomy_ids
        self.assertFalse(
            missing,
            f"diagnosis-rules 에만 있고 taxonomy 에 없는 ID: {sorted(missing)}",
        )


if __name__ == "__main__":
    unittest.main()
