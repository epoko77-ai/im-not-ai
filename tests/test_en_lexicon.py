"""lang/en/lexicon.json 계약 — 영어 어휘 티 사전.

근거: Kobak et al. 2025 (Science Advances), PubMed 초록 15M편 2010–2024 의
excess vocabulary. 공개 데이터 `results/excess_words.csv` 에서 생성한다.

**굴절형을 원형으로 바꾸지 않는다.** 원자료가 delve·delves·delving 을 각각
개별 항목으로 담고 있다 — Kobak 이 형태별로 초과 사용을 측정했기 때문이다.
원형화 후 접미사로 재확장하면 측정되지 않은 형태를 만들어내 오탐이 된다.
"""
from __future__ import annotations

import json
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_LEXICON = os.path.join(_ROOT, "lang", "en", "lexicon.json")

# family 는 CSV 의 part_of_speech 에서 기계적으로 유도한다(손 분류 없음).
_ALLOWED_FAMILIES = {"F-7", "D-4", "F-1", "unclassified"}


def _load() -> dict:
    with open(_LEXICON, encoding="utf-8") as f:
        return json.load(f)


class EnLexiconTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(os.path.isfile(_LEXICON), f"없다: {_LEXICON}")
        self.data = _load()

    def test_has_provenance(self) -> None:
        """출처와 근거 등급이 파일 안에 있어야 한다 — 나중에 누가 등급을 물어본다."""
        self.assertIn("source", self.data)
        self.assertIn("Kobak", self.data["source"])
        self.assertRegex(self.data["evidence"], r"^E[1-4]\b")
        self.assertIn("caveat", self.data)

    def test_entries_are_wellformed(self) -> None:
        entries = self.data["entries"]
        self.assertGreaterEqual(len(entries), 300, "style words 는 400건 규모다")
        seen = set()
        for e in entries:
            self.assertEqual(e["word"], e["word"].lower(), "표제어는 소문자")
            self.assertNotIn(e["word"], seen, f"중복 표제어: {e['word']}")
            seen.add(e["word"])
            self.assertIn(e["family"], _ALLOWED_FAMILIES, f"미정의 family: {e}")

    def test_style_words_only(self) -> None:
        """content word 는 주제 부산물이라 제외한다 — 문체 티가 아니다."""
        self.assertTrue(all(e.get("type") == "style" for e in self.data["entries"]))

    def test_known_markers_present(self) -> None:
        words = {e["word"] for e in self.data["entries"]}
        for w in ("delves", "underscores", "showcasing", "intricate", "pivotal"):
            self.assertIn(w, words, f"대표 초과어 누락: {w}")

    def test_inflections_kept_verbatim(self) -> None:
        """원자료가 형태별로 담고 있으므로 그대로 보존한다."""
        words = {e["word"] for e in self.data["entries"]}
        for w in ("delve", "delves", "delving"):
            self.assertIn(w, words, f"굴절형 {w} 가 유실됐다 — 원형화하지 말 것")

    def test_verb_majority_matches_paper(self) -> None:
        """논문의 핵심 발견 — 2024 초과 어휘의 66%가 동사. 원자료로 검증됨(65.8%)."""
        fams = [e["family"] for e in self.data["entries"]]
        verbs = sum(1 for f in fams if f == "F-7")
        ratio = verbs / len(fams)
        self.assertGreater(ratio, 0.60, f"동사(F-7) 비율 {ratio:.1%}")
        self.assertLess(ratio, 0.72, f"동사(F-7) 비율 {ratio:.1%}")


if __name__ == "__main__":
    unittest.main()
