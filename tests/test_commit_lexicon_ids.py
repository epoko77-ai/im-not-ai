"""commit-lexicon.md의 taxonomy ID 인용이 SSOT·헤더-본문 양쪽과 정합하는지 검증한다.

commit-lexicon.md는 ai-tell-taxonomy.md에서 손으로 파생시킨 소형 참조표다
(quick-rules.md처럼 자동 생성되지 않는다). 코드 리뷰에서 실제로 헤더 선언
(A-7·A-8·A-9·F-4)과 5절 표 본문(A-12 추가 인용)이 어긋난 채로 통과할 뻔한
사고가 있었다 — build_quick_rules.py/test_quick_rules_build.py가 quick-rules.md
에서 막으려던 것과 같은 종류의 ID 드리프트. 재발 방지 게이트.

pytest / unittest 양쪽에서 실행된다.
"""

from __future__ import annotations

import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "scripts")


def _load_checker():
    path = os.path.join(SCRIPTS, "check_commit_lexicon_ids.py")
    spec = importlib.util.spec_from_file_location("check_commit_lexicon_ids", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


class CommitLexiconIdDriftTests(unittest.TestCase):
    def setUp(self) -> None:
        self.checker = _load_checker()

    def test_no_drift_in_committed_lexicon(self) -> None:
        """실제 commit-lexicon.md가 지금 어긋나 있으면 안 된다."""
        errors = self.checker.validate()
        self.assertEqual(errors, [], "; ".join(errors))

    def test_all_lexicon_ids_exist_in_taxonomy(self) -> None:
        with open(self.checker._TAXONOMY, encoding="utf-8") as f:
            taxonomy_ids = self.checker.parse_taxonomy_ids(f.read())
        with open(self.checker._LEXICON, encoding="utf-8") as f:
            header_ids, body_ids = self.checker.parse_lexicon_ids(f.read())
        self.assertTrue(header_ids)
        self.assertTrue(body_ids)
        self.assertTrue((header_ids | body_ids) <= taxonomy_ids)

    def test_header_and_body_ids_match_exactly(self) -> None:
        with open(self.checker._LEXICON, encoding="utf-8") as f:
            header_ids, body_ids = self.checker.parse_lexicon_ids(f.read())
        self.assertEqual(header_ids, body_ids)

    def test_detects_body_id_missing_from_header(self) -> None:
        """헤더에 없는 ID를 본문이 인용하면 잡아야 한다 (실제 있었던 드리프트 재현)."""
        text = (
            "> 이 표는 taxonomy의 A-7·F-4를 SSOT로 삼는다.\n\n"
            "## 5. 예시\n\n"
            "| a | b | 근거 |\n|---|---|---|\n"
            "| x | y | A-12 자동화된 피동 |\n"
        )
        header_ids, body_ids = self.checker.parse_lexicon_ids(text)
        self.assertEqual(header_ids, {"A-7", "F-4"})
        self.assertEqual(body_ids, {"A-12"})
        self.assertTrue(body_ids - header_ids)

    def test_detects_unknown_id_not_in_taxonomy(self) -> None:
        taxonomy_ids = {"A-7", "A-8", "A-9", "A-12", "F-4"}
        header_ids = {"A-7", "Z-99"}
        self.assertTrue((header_ids - taxonomy_ids))


if __name__ == "__main__":
    unittest.main()
