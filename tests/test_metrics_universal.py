"""core/metrics_universal.py — 언어 무관 계측 지표.

근거: 영어 스파이크(2026-09-02)에서 계측형 지표만이 깨끗하게 분리했다
(AI 에세이 문장길이 stdev 6.7~6.8 vs 대조 16.3~18.8). 산술이라 언어를 안 탄다.
한국어는 unit='chars'(100자 임계), 영어는 unit='tokens'(35어 임계)로 같은 축을 잰다.
"""
from __future__ import annotations

import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_MOD = os.path.join(_ROOT, "core", "metrics_universal.py")

EN_UNIFORM = (
    "The office was the principle. "
    "The streets were laid out. "
    "The systems grew around it. "
    "That arrangement is now gone."
)
EN_BURSTY = (
    "It ended. "
    "For more than a century the office building was the organizing principle of "
    "urban life, and streets were laid out to carry workers toward it in the "
    "morning and away from it at night, while restaurants and transit systems and "
    "entire neighborhoods grew around the rhythm of that daily commute. "
    "Nobody planned it."
)


def _load():
    spec = importlib.util.spec_from_file_location("_metrics_universal", _MOD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DispersionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            os.path.isfile(_MOD), f"core/metrics_universal.py 가 없다: {_MOD}"
        )
        self.m = _load()

    def test_uniform_text_has_low_dispersion(self) -> None:
        self.assertLess(self.m.sentence_length_dispersion(EN_UNIFORM), 3.0)

    def test_bursty_text_has_higher_dispersion(self) -> None:
        """스파이크가 실측한 방향 — 사람 글이 AI 글보다 분산이 크다."""
        self.assertGreater(
            self.m.sentence_length_dispersion(EN_BURSTY),
            self.m.sentence_length_dispersion(EN_UNIFORM),
        )

    def test_korean_chars_unit(self) -> None:
        """한국어는 문자 단위로 잰다 — 어절 수가 아니라 100자 임계가 SSOT다."""
        text = "짧다. " + "가" * 120 + ". 또 짧다."
        self.assertGreater(
            self.m.long_sentence_rate(text, threshold=100, unit="chars"), 0.0
        )

    def test_long_sentence_rate_zero_when_all_short(self) -> None:
        self.assertEqual(
            self.m.long_sentence_rate(EN_UNIFORM, threshold=35, unit="tokens"), 0.0
        )

    def test_comma_inclusion_rate(self) -> None:
        text = "One, two. Three. Four, five."
        self.assertAlmostEqual(self.m.comma_inclusion_rate(text), 200 / 3, places=1)

    def test_comma_segment_length(self) -> None:
        text = "a b c, d e f."
        self.assertAlmostEqual(self.m.comma_segment_length(text), 3.0, places=1)

    def test_comma_usage_rate_matches_korean_definition(self) -> None:
        """한국어 metrics.py 와 같은 정의 — 문장당 평균 쉼표 수."""
        self.assertAlmostEqual(self.m.comma_usage_rate("a, b, c. d e."), 1.0, places=2)
        self.assertEqual(self.m.comma_usage_rate("no commas here."), 0.0)
        self.assertEqual(self.m.comma_usage_rate(""), 0.0)

    def test_comma_usage_rate_counts_fullwidth(self) -> None:
        self.assertAlmostEqual(self.m.comma_usage_rate("가， 나. 다."), 0.5, places=2)

    def test_compute_universal_returns_all_keys(self) -> None:
        out = self.m.compute_universal(EN_BURSTY, long_threshold=35, unit="tokens")
        for key in (
            "sentence_length_dispersion",
            "long_sentence_rate",
            "comma_inclusion_rate",
            "comma_usage_rate",
            "comma_segment_length",
            "sentences",
            "tokens",
        ):
            self.assertIn(key, out)

    def test_empty_text_does_not_crash(self) -> None:
        out = self.m.compute_universal("", long_threshold=35, unit="tokens")
        self.assertEqual(out["sentences"], 0)
        self.assertEqual(out["sentence_length_dispersion"], 0.0)

    def test_bad_unit_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.m.sentence_length_dispersion(EN_UNIFORM, unit="eojeol")


if __name__ == "__main__":
    unittest.main()
