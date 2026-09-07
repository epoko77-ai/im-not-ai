"""core/detect_language.py — 유니코드 스크립트 비율 기반 언어 감지.

형태소 분석도 통계 모델도 쓰지 않는다. 한글 음절 블록과 라틴 문자의 비율만
보면 ko/en 은 갈린다. 셋째 언어가 필요해지면 그때 확장한다.
"""
from __future__ import annotations

import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_MOD = os.path.join(_ROOT, "core", "detect_language.py")


def _load():
    spec = importlib.util.spec_from_file_location("_detect_language", _MOD)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class DetectLanguageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(os.path.isfile(_MOD), f"없다: {_MOD}")
        self.d = _load().detect_language

    def test_korean(self) -> None:
        self.assertEqual(self.d("이 문제에서 중요한 건 속도다."), "ko")

    def test_english(self) -> None:
        self.assertEqual(self.d("The office organized urban life."), "en")

    def test_korean_with_english_terms_is_korean(self) -> None:
        """전문용어 병기가 많아도 한국어다 — B-1 이 잡는 그 문체."""
        text = (
            "소버린 AI(Sovereign AI)는 데이터 주권(data sovereignty)과 "
            "컴퓨팅 인프라(computing infrastructure)를 함께 요구한다."
        )
        self.assertEqual(self.d(text), "ko")

    def test_english_with_quoted_korean_is_english(self) -> None:
        text = (
            "The Korean term is 번역투, and it describes syntax carried over "
            "from another language into Korean prose by a literal translation."
        )
        self.assertEqual(self.d(text), "en")

    def test_empty_is_unknown(self) -> None:
        self.assertEqual(self.d(""), "unknown")

    def test_digits_and_punctuation_only_is_unknown(self) -> None:
        self.assertEqual(self.d("1234 5678 ... ---"), "unknown")

    def test_real_repo_samples(self) -> None:
        """실물로 확인 — 이 저장소의 한국어·영어 문서."""
        cases = [("CLAUDE.md", "ko"), ("README.en.md", "en")]
        for path, expected in cases:
            full = os.path.join(_ROOT, path)
            with open(full, encoding="utf-8") as f:
                self.assertEqual(self.d(f.read()), expected, path)


if __name__ == "__main__":
    unittest.main()
