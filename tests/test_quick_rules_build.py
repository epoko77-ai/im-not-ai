"""quick-rules.md 가 taxonomy(SSOT)에서 재생성 가능하고 최신인지 검증한다.

fast 룰북을 손으로 동기화하다 ID 드리프트가 생긴 사고(D-3·G-1/G-2·J-3)의
재발 방지. CI에서 --check 가 실패하면 누군가 quick-rules.md 를 손으로 고쳤거나
taxonomy 를 고치고 재생성을 안 한 것이다.

pytest / unittest 양쪽에서 실행된다.
"""

from __future__ import annotations

import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "scripts")


def _load_builder():
    path = os.path.join(SCRIPTS, "build_quick_rules.py")
    spec = importlib.util.spec_from_file_location("build_quick_rules", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


class QuickRulesBuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = _load_builder()

    def test_every_pattern_has_quick_meta(self) -> None:
        """모든 패턴에 _quick 메타가 있어야 빌드가 성립한다(누락 = 실패)."""
        with open(self.builder._TAXONOMY, encoding="utf-8") as f:
            patterns = self.builder.parse_taxonomy(f.read())
        missing = [p["id"] for p in patterns if p["quick"] is None]
        self.assertEqual(missing, [], f"quick 메타 누락: {missing}")

    def test_quick_rules_is_up_to_date(self) -> None:
        """quick-rules.md 가 SSOT 재생성 결과와 일치해야 한다."""
        rendered, _ = self.builder.build()
        with open(self.builder._OUT, encoding="utf-8") as f:
            existing = f.read()
        self.assertEqual(
            existing.rstrip(),
            rendered.rstrip(),
            "quick-rules.md 가 taxonomy와 어긋난다. "
            "`python3 scripts/build_quick_rules.py` 로 재생성하라.",
        )

    def test_generated_ids_are_subset_of_taxonomy(self) -> None:
        """생성물의 모든 ID가 taxonomy에 실재해야 한다(1:1 매칭)."""
        with open(self.builder._TAXONOMY, encoding="utf-8") as f:
            patterns = self.builder.parse_taxonomy(f.read())
        taxo_ids = {p["id"] for p in patterns}
        quick_ids = {p["id"] for p in patterns if p["quick"] is True}
        self.assertTrue(quick_ids)
        self.assertTrue(quick_ids <= taxo_ids)


if __name__ == "__main__":
    unittest.main()
