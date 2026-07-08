"""판정 헬퍼 자체의 단위 테스트 — 결정적, 에이전트 불필요, 항상 실행 가능.

계층1(deterministic): 판정 로직이 올바른지 golden 쌍으로 검증한다.
`python3 -m unittest` 또는 pytest 양쪽에서 동작.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import humanize_asserts as ha  # noqa: E402


class ChangeRateTests(unittest.TestCase):
    def test_identical_is_zero(self) -> None:
        self.assertEqual(ha.change_rate("가나다라", "가나다라"), 0.0)

    def test_edits_raise_rate(self) -> None:
        self.assertGreater(ha.change_rate("가나다라마바", "가XY다마바"), 0.15)

    def test_full_rewrite_is_high(self) -> None:
        self.assertGreater(ha.change_rate("완전히 다른 원문", "전혀 겹치지 않는 결과물"), 0.5)


class ProtectedTokenTests(unittest.TestCase):
    def test_all_present(self) -> None:
        self.assertEqual(
            ha.missing_protected_tokens("영희님과 세 시간 회의했다", ["영희님", "세 시간"]), []
        )

    def test_detects_missing(self) -> None:
        self.assertEqual(
            ha.missing_protected_tokens("이름이 바뀐 문장", ["영희님", "42"]), ["영희님", "42"]
        )


class RegisterTests(unittest.TestCase):
    def test_hamnida(self) -> None:
        self.assertEqual(ha.register_of("성능을 높였습니다. 안정성을 다집니다."), "합니다")

    def test_haeyo(self) -> None:
        self.assertEqual(ha.register_of("정말 공감해요. 그렇게 해봐요."), "해요")

    def test_banmal(self) -> None:
        self.assertEqual(ha.register_of("회의 길었다. 답답하더라고. 물어봐야겠다."), "반말")


class SignalTests(unittest.TestCase):
    def test_conclusion_pivot_count(self) -> None:
        text = "결론적으로 이겼다. 따라서 또 이긴다. 이를 통해 자신감을 얻었다."
        self.assertEqual(ha.signal(text, "conclusion_pivot_count"), 3.0)

    def test_ending_comma_drop_is_measurable(self) -> None:
        heavy = "그는 일어나고, 세수했고, 옷을 입었으며, 밥을 먹지만, 잠들었다."
        clean = "그는 일어나 세수하고 옷을 입었다. 밥을 먹고 잠들었다."
        drop = ha.signal(heavy, "ending_comma_rate") - ha.signal(clean, "ending_comma_rate")
        self.assertGreater(drop, 0.3)


if __name__ == "__main__":
    unittest.main()
