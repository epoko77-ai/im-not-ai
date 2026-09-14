# -*- coding: utf-8 -*-
"""strip_injected_commas — C-11 역주입 결정적 후처리 단위 테스트."""
from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "scripts"))
from strip_injected_commas import strip_injected  # noqa: E402


class StripInjectedCommasTests(unittest.TestCase):
    def test_new_sentence_comma_stripped(self) -> None:
        before = "기술이 빠르게 바뀐다. 기업은 느리다."
        after = "기술이 빠르게 변화하고, 기업의 대응은 더디다."
        out, rep = strip_injected(before, after)
        self.assertEqual(out, "기술이 빠르게 변화하고 기업의 대응은 더디다.")
        self.assertEqual(rep["commas_removed"], 1)

    def test_original_sentence_untouched(self) -> None:
        # 원문에 그대로 있던 문장 — 필자의 연결어미 쉼표는 불가침.
        keep = "그는 서울에 살지만, 마음은 늘 고향에 있었다."
        before = keep + " 다른 문장이다."
        after = keep + " 다른 문장이다."
        out, rep = strip_injected(before, after)
        self.assertEqual(out, after)
        self.assertEqual(rep["commas_removed"], 0)

    def test_quoted_span_untouched(self) -> None:
        before = "원문이다."
        after = "그는 “밥을 먹고, 갔다”고 말하면서, 웃었다."
        out, rep = strip_injected(before, after)
        # 따옴표 안 "먹고," 보존 · 밖 "말하면서," 제거
        self.assertIn("먹고,", out)
        self.assertNotIn("말하면서,", out)
        self.assertEqual(rep["commas_removed"], 1)

    def test_multiple_endings(self) -> None:
        before = "짧은 원문."
        after = "비용이 낮아지며, 장벽이 사라지는데, 속도는 빨라져서, 모두 놀랐다."
        out, rep = strip_injected(before, after)
        self.assertEqual(rep["commas_removed"], 3)
        self.assertNotIn("며,", out)
        self.assertNotIn("는데,", out)
        self.assertNotIn("져서,", out)

    def test_ja_exclamation_not_stripped(self) -> None:
        # '자,'는 감탄사와 충돌 — 패턴에서 제외돼야 한다.
        before = "원문."
        after = "자, 이제 시작하자."
        out, rep = strip_injected(before, after)
        self.assertEqual(out, after)
        self.assertEqual(rep["commas_removed"], 0)

    def test_all_mode_strips_kept_sentences(self) -> None:
        # --all: 진단이 C-11을 지목한 경로 전용 — 원문 그대로인 문장도 제거.
        keep = "데이터를 정제하고, 모델을 학습시킨다."
        out, rep = strip_injected(keep, keep, all_sentences=True)
        self.assertEqual(out, "데이터를 정제하고 모델을 학습시킨다.")
        self.assertEqual(rep["commas_removed"], 1)

    def test_all_mode_quote_still_protected(self) -> None:
        t = "그는 “먹고, 갔다”고 말하면서, 웃었다."
        out, rep = strip_injected(t, t, all_sentences=True)
        self.assertIn("먹고,", out)
        self.assertNotIn("말하면서,", out)

    def test_noop_identity(self) -> None:
        before = "그대로다. 바뀐 게 없다."
        out, rep = strip_injected(before, before)
        self.assertEqual(out, before)
        self.assertEqual(rep["commas_removed"], 0)


if __name__ == "__main__":
    unittest.main()
