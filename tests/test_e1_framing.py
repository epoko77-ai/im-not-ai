"""E-1 의 실체 서술 회귀 — 언어 불변 축은 분산이지 장문 수가 아니다.

근거: Reinhart et al. 2025 (PNAS, arXiv:2410.16107) — LLM 문장은 인간보다
길면서 변이는 작다. 한국어의 "장문 부재"(G2=60.9)는 그 발현형이다.
영어팩이 "장문을 늘려라"는 잘못된 처방을 물려받지 않도록 서술을 못박는다.
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


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _e1_section(text: str) -> str:
    """E-1 헤딩부터 다음 E-2 헤딩 직전까지."""
    start = re.search(r"^#{3,4}\s+\*{0,2}E-1\b", text, re.M)
    assert start, "taxonomy 에서 E-1 헤딩을 찾지 못함"
    tail = text[start.start():]
    end = re.search(r"^#{3,4}\s+\*{0,2}E-2\b", tail, re.M)
    return tail[: end.start()] if end else tail


class E1FramingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.section = _e1_section(_read(_TAXONOMY))

    def test_names_dispersion_as_the_invariant(self) -> None:
        self.assertIn(
            "분산",
            self.section,
            "E-1 이 불변량으로서의 '분산'을 명시하지 않는다",
        )

    def test_marks_long_sentence_absence_as_korean_manifestation(self) -> None:
        """장문 부재는 유지하되, 한국어 발현형임이 드러나야 한다."""
        self.assertIn("장문", self.section)
        self.assertRegex(
            self.section,
            r"한국어[^\n]{0,40}발현|발현[^\n]{0,40}한국어",
            "장문 부재가 '한국어 발현형'으로 한정되지 않았다",
        )

    def test_cites_cross_language_evidence(self) -> None:
        self.assertIn(
            "Reinhart",
            self.section,
            "교차언어 근거(Reinhart 2025) 인용이 없다",
        )

    def test_keeps_korean_measurement_anchor(self) -> None:
        """기존 실측 근거(G²=60.9)를 잃지 않는다 — 재framing 이지 근거 폐기가 아니다."""
        self.assertIn("60.9", self.section)


if __name__ == "__main__":
    unittest.main()
