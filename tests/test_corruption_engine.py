"""오염 엔진 단위 테스트 — 주입의 결정성·의미 중립·자가 검증을 고정한다."""
from __future__ import annotations

import os
import random
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "scripts"))
import corruption_engine as ce  # noqa: E402


CLEAN = (
    "정부는 지원 대상을 늘려야 한다. 부담이 커진다. 시장 점유율을 뺏는 경쟁이 이어진다. "
    "제도가 중요한 역할을 맡는다. 개혁이 필요하다.\n\n"
    "전문가들은 다른 진단을 내놓는다. 예산이 부족하고 인력이 모자라기 때문이다. "
    "그래서 채용 방식이 달라져야 한다.\n\n"
    "성장률은 3.1%였다. \"속단하기에는 이르다\"는 평가가 나온다. 판단은 유보한다."
)


class CorruptionEngineTests(unittest.TestCase):
    def test_corrupt_produces_detectable_tells(self) -> None:
        """주입된 오염본은 해당 탐지 정규식에 실제로 걸려야 한다(자가 검증 1)."""
        rng = random.Random(3)
        got = ce.corrupt(CLEAN, rng, n_tags=3)
        self.assertIsNotNone(got)
        corrupted, tags = got
        self.assertTrue(tags)
        self.assertNotEqual(corrupted, CLEAN)
        for tag, detect, _ in ce.INJECTORS:
            if tag in tags:
                self.assertTrue(detect.search(corrupted), f"{tag} 주입 후 미탐지")

    def test_numbers_and_quotes_survive(self) -> None:
        """오염은 수치·인용을 절대 건드리지 않는다(자가 검증 2 — checks.py)."""
        rng = random.Random(5)
        for _ in range(6):
            got = ce.corrupt(CLEAN, rng, n_tags=3)
            if got is None:
                continue
            corrupted, _ = got
            self.assertIn("3.1%", corrupted)
            self.assertIn("속단하기에는 이르다", corrupted)

    def test_no_comma_before_auxiliary(self) -> None:
        """C-11 주입이 보조용언('고 있다')에 쉼표를 찍으면 비문이다 — 금지 고정."""
        t = "이 책은 방향을 제시하고 있다. 논의를 이어가고 있다. 그는 걷고 뛰었다. 밥을 먹고 잤다."
        rng = random.Random(1)
        for _ in range(8):
            out = ce._inj_comma_after_connective(t, rng)
            if out:
                self.assertNotIn("고, 있", out)

    def test_sentence_split_not_on_boda(self) -> None:
        """문장 분리가 '총량보다 '의 '다'에서 끊기면 접속사가 문장 중간에 박힌다."""
        ss = ce._sents("총량보다 첫 칸이 문제다. 다음 문장이다.")
        self.assertEqual(len(ss), 2)

    def test_modality_injectors_absent(self) -> None:
        """서법 계열(완곡 주입) 주입기는 존재해선 안 된다 — 철칙 #10과 충돌.

        완곡을 주입한 오염본은 모델에게 '유보 제거'를 가르친다.
        """
        tags = {t for t, _, _ in ce.INJECTORS}
        for banned in ("A-10", "G-1", "G-2"):
            self.assertNotIn(banned, tags)


if __name__ == "__main__":
    unittest.main()
