"""Tests for humanize-ko v1.6 metrics module.

Runs under either pytest or unittest. Imports the metrics module from its
location under skills/humanize-korean/references/.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, ".."))
METRICS_DIR = os.path.join(
    PROJECT_ROOT, "skills", "humanize-korean", "references"
)
sys.path.insert(0, METRICS_DIR)

import metrics  # noqa: E402  (sys.path mutation is intentional)

# Bundled baseline shipped next to metrics.py — works on a fresh clone
# (_workspace/ is gitignored, so never depend on it in tests).
BASELINE_PATH = os.path.join(METRICS_DIR, "baseline.json")


class MetricsTests(unittest.TestCase):
    # ------------------------------------------------------------------
    # Bundled baseline wiring (fresh-clone regression guard)
    # ------------------------------------------------------------------

    def test_default_baseline_path_exists(self) -> None:
        path = metrics._default_baseline_path()
        self.assertTrue(os.path.exists(path), f"bundled baseline missing: {path}")
        self.assertEqual(os.path.abspath(path), os.path.abspath(BASELINE_PATH))

    def test_compute_all_works_without_explicit_baseline(self) -> None:
        result = metrics.compute_all("오늘은 좋은 날이다.", genre="essay")
        self.assertIn(result["risk_band"], ("low", "medium", "high"))

    # ------------------------------------------------------------------
    # Robustness
    # ------------------------------------------------------------------

    def test_empty_string_is_safe(self) -> None:
        self.assertEqual(metrics.comma_inclusion_rate(""), 0.0)
        self.assertEqual(metrics.comma_usage_rate(""), 0.0)
        self.assertEqual(metrics.ending_comma_rate(""), 0.0)
        self.assertEqual(metrics.comma_segment_length(""), 0.0)
        self.assertEqual(metrics.conclusion_pivot_count(""), 0)
        self.assertEqual(metrics.safe_balance_count(""), 0)
        self.assertEqual(metrics.hanja_nominalizer_density(""), 0.0)
        self.assertEqual(metrics.lexical_diversity(""), 0.0)

    def test_single_sentence(self) -> None:
        text = "오늘은 비가 온다."
        self.assertEqual(metrics.comma_inclusion_rate(text), 0.0)
        self.assertEqual(metrics.comma_usage_rate(text), 0.0)
        self.assertGreater(metrics.lexical_diversity(text), 0.0)

    # ------------------------------------------------------------------
    # Connective ending + comma
    # ------------------------------------------------------------------

    def test_ending_comma_pattern_detection(self) -> None:
        # 5 connective endings, all followed by ", " => rate = 1.0
        text = (
            "그는 일어나고, 세수했고, 옷을 입었으며, "
            "밥을 먹지만, 곧 잠들었다."
        )
        rate = metrics.ending_comma_rate(text)
        self.assertGreater(rate, 0.5)

    def test_ending_no_comma(self) -> None:
        text = "그는 일어나고 세수했고 옷을 입었다."
        rate = metrics.ending_comma_rate(text)
        self.assertEqual(rate, 0.0)

    # ------------------------------------------------------------------
    # Lexicon counts
    # ------------------------------------------------------------------

    def test_conclusion_pivot_lexicon(self) -> None:
        text = "결론적으로 우리는 이겼다. 따라서 다음에도 이긴다. 이를 통해 자신감을 얻었다."
        self.assertEqual(metrics.conclusion_pivot_count(text), 3)

    def test_safe_balance_lexicon(self) -> None:
        text = "양쪽 모두 일리가 있다. 장점도 있지만 단점도 있다. 신중하게 결정해야 한다."
        self.assertEqual(metrics.safe_balance_count(text), 3)

    # ------------------------------------------------------------------
    # Hanja suffix density
    # ------------------------------------------------------------------

    def test_hanja_suffix_counted(self) -> None:
        text = "기술적 측면에서 안정성과 효율성, 그리고 자동화는 중요하다."
        density = metrics.hanja_nominalizer_density(text)
        # Tokens (after punct strip): 기술적 측면에서 안정성과 효율성 그리고 자동화는 중요하다
        # Hits: 기술적(적), 안정성과(과 -> not suffix; ends with 과 not target)
        # Actually 안정성과 ends with 과, so NOT counted. Let's just assert >0.
        self.assertGreater(density, 0.0)

    def test_hanja_zero_density(self) -> None:
        text = "오늘 비가 온다 우산이 필요하다 빨리 가자"
        density = metrics.hanja_nominalizer_density(text)
        self.assertEqual(density, 0.0)

    # ------------------------------------------------------------------
    # Baseline fallback
    # ------------------------------------------------------------------

    def test_baseline_null_genre_falls_back(self) -> None:
        text = "오늘은 좋은 날이다."
        result = metrics.compute_all(text, genre="news", baseline_path=BASELINE_PATH)
        # news is null in baseline => fallback warning expected.
        self.assertIn("warning", result)
        self.assertIn("news", result["warning"])

    def test_baseline_essay_no_warning(self) -> None:
        text = "오늘은 좋은 날이다."
        result = metrics.compute_all(text, genre="essay", baseline_path=BASELINE_PATH)
        self.assertNotIn("warning", result)

    # ------------------------------------------------------------------
    # End-to-end risk band
    # ------------------------------------------------------------------

    def test_ai_style_text_is_high_risk(self) -> None:
        # Heavy comma usage + ending-comma + conclusion pivots + safe balance
        # + hanja suffixes.
        text = (
            "현대 사회에서 기술적 혁신은 중요하다. "
            "AI는 빠르게 발전하고, 산업은 변화하며, 사람들은 적응해야 한다. "
            "결론적으로, 우리는 양쪽 모두를 고려해야 한다. "
            "따라서, 자동화와 안정성, 효율성, 그리고 지속가능성을 신중하게 검토해야 한다. "
            "이를 통해 사회적 균형과 기술적 진보를 함께 달성할 수 있다. "
            "그러므로 두 가지 모두 신중하게 다루어야 한다."
        )
        result = metrics.compute_all(text, genre="essay", baseline_path=BASELINE_PATH)
        self.assertEqual(result["risk_band"], "high")
        self.assertGreaterEqual(result["metrics"]["conclusion_pivot_count"], 2)
        self.assertGreaterEqual(result["metrics"]["safe_balance_count"], 2)

    def test_human_style_text_is_low_risk(self) -> None:
        # Short sentences. No commas. No conclusion pivots. No safe balance.
        # No hanja suffix nominalizers.
        text = (
            "오늘 비가 왔다. 우산을 폈다. 길이 미끄럽다. "
            "버스에 탔다. 사람들이 많다. 빨리 가고 싶다."
        )
        result = metrics.compute_all(text, genre="essay", baseline_path=BASELINE_PATH)
        self.assertEqual(result["risk_band"], "low")

    def test_comma_family_alone_cannot_reach_high(self) -> None:
        # Pebblous 티어다운(2026-08) 반례 — 2020년(pre-ChatGPT) 사람 에세이가
        # 필자의 쉼표 습관(C-11 계열 z=+10)만으로 6/6 high 판정을 받았다.
        # 쉼표 계열은 3점 상한이라 단독으로는 low 를 넘을 수 없어야 한다.
        z = {
            "comma_inclusion_rate": 10.0,
            "ending_comma_rate": 10.0,
            "comma_segment_length": 10.0,
            "lexical_diversity": 0.0,
            "hanja_nominalizer_density": 0.0,
        }
        band, score = metrics._classify_risk(z, {})
        self.assertLessEqual(score, 3)
        self.assertEqual(band, "low")

    def test_high_requires_two_independent_families(self) -> None:
        # high 는 독립 계열 2개 이상 동시 발화 시에만 — 쉼표 상한 3점에
        # 수사·어휘 계열이 더해져야 6점에 닿는다.
        z = {
            "comma_inclusion_rate": 10.0,
            "ending_comma_rate": 10.0,
            "comma_segment_length": 10.0,
            "lexical_diversity": 0.0,
            "hanja_nominalizer_density": 2.0,
        }
        hits = {"conclusion_pivot_count": 3, "safe_balance_count": 2}
        band, score = metrics._classify_risk(z, hits)
        self.assertEqual(band, "high")
        self.assertEqual(score, 6)

    def test_column_and_report_genre_cells_exist(self) -> None:
        # SKILL.md 장르 키(column/report)가 baseline 셀 없이 essay로 폴백되던
        # 구멍(2026-08-29 FPR 실측에서 확인) — 실측 셀 추가 후 폴백 경고가 없어야 한다.
        text = "그는 학교에 가고, 밥을 먹었다. 결과를 검토했다."
        for genre in ("column", "report"):
            with self.subTest(genre=genre):
                result = metrics.compute_all(text, genre=genre, baseline_path=BASELINE_PATH)
                self.assertNotIn("warning", result, f"{genre} 셀이 essay로 폴백됨")

    def test_inverted_comma_metrics_disabled_per_genre(self) -> None:
        # 실측에서 human이 essay-AI 극을 초과(역전)한 지표는 해당 장르에서
        # 판별 불가 — z가 None이어야 한다.
        text = "그는 학교에 가고, 밥을 먹고, 잠을 잤다. 보고서를 썼다."
        col = metrics.compute_all(text, genre="column", baseline_path=BASELINE_PATH)
        self.assertIsNone(col["z_scores"]["ending_comma_rate"])
        rep = metrics.compute_all(text, genre="report", baseline_path=BASELINE_PATH)
        self.assertIsNone(rep["z_scores"]["ending_comma_rate"])
        self.assertIsNone(rep["z_scores"]["comma_segment_length"])
        # comma_inclusion_rate: 극간 거리 5.4 < 인간 내 분산 18.3 — 판별 불가 비활성
        self.assertIsNone(rep["z_scores"]["comma_inclusion_rate"])

    # ------------------------------------------------------------------
    # CLI smoke
    # ------------------------------------------------------------------

    def test_cli_writes_json_and_prints_band(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            in_path = os.path.join(td, "input.txt")
            out_path = os.path.join(td, "out.json")
            with open(in_path, "w", encoding="utf-8") as f:
                f.write("오늘 비가 왔다. 우산을 폈다.")
            rc = metrics._main(
                [
                    "--input", in_path,
                    "--genre", "essay",
                    "--output", out_path,
                    "--baseline", BASELINE_PATH,
                ]
            )
            self.assertEqual(rc, 0)
            with open(out_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["version"], "v1.6")
            self.assertIn(data["risk_band"], ("low", "medium", "high"))


if __name__ == "__main__":
    unittest.main()
