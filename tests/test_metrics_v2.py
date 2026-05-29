"""Tests for humanize-ko v2.0 metrics module.

Runs under pytest OR `python -m unittest`. Imports both the v1.6 metrics
(for regression checks) and the v2.0 metrics_v2 from this workspace.

Spec:
- Existing 13 v1.6 cases: re-run verbatim. Regression budget = 0.
- New v2.0 cases: each new metric has >= 2 cases (positive + negative).
  Total new tests >= 20.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, ".."))

# v1.6 module location
V1_DIR = os.path.join(
    PROJECT_ROOT, ".claude", "skills", "humanize-korean", "references"
)
sys.path.insert(0, V1_DIR)
sys.path.insert(0, HERE)

import metrics  # noqa: E402  (v1.6)
import metrics_v2  # noqa: E402  (v2.0 superset)

BASELINE_PATH = os.path.join(
    V1_DIR, "baseline.json"
)
BASELINE_V2_PATH = os.path.join(V1_DIR, "baseline_v2.json")


# ===========================================================================
# REGRESSION — v1.6 13 cases re-asserted on metrics_v2 re-exports
# ===========================================================================


class V16RegressionTests(unittest.TestCase):
    """v1.6 13 pytest cases — must all pass against metrics_v2 re-exports."""

    def test_empty_string_is_safe(self) -> None:
        self.assertEqual(metrics_v2.comma_inclusion_rate(""), 0.0)
        self.assertEqual(metrics_v2.comma_usage_rate(""), 0.0)
        self.assertEqual(metrics_v2.ending_comma_rate(""), 0.0)
        self.assertEqual(metrics_v2.comma_segment_length(""), 0.0)
        self.assertEqual(metrics_v2.conclusion_pivot_count(""), 0)
        self.assertEqual(metrics_v2.safe_balance_count(""), 0)
        self.assertEqual(metrics_v2.hanja_nominalizer_density(""), 0.0)
        self.assertEqual(metrics_v2.lexical_diversity(""), 0.0)

    def test_single_sentence(self) -> None:
        text = "오늘은 비가 온다."
        self.assertEqual(metrics_v2.comma_inclusion_rate(text), 0.0)
        self.assertEqual(metrics_v2.comma_usage_rate(text), 0.0)
        self.assertGreater(metrics_v2.lexical_diversity(text), 0.0)

    def test_ending_comma_pattern_detection(self) -> None:
        text = (
            "그는 일어나고, 세수했고, 옷을 입었으며, "
            "밥을 먹지만, 곧 잠들었다."
        )
        self.assertGreater(metrics_v2.ending_comma_rate(text), 0.5)

    def test_ending_no_comma(self) -> None:
        text = "그는 일어나고 세수했고 옷을 입었다."
        self.assertEqual(metrics_v2.ending_comma_rate(text), 0.0)

    def test_conclusion_pivot_lexicon(self) -> None:
        text = (
            "결론적으로 우리는 이겼다. 따라서 다음에도 이긴다. "
            "이를 통해 자신감을 얻었다."
        )
        self.assertEqual(metrics_v2.conclusion_pivot_count(text), 3)

    def test_safe_balance_lexicon(self) -> None:
        text = "양쪽 모두 일리가 있다. 장점도 있지만 단점도 있다. 신중하게 결정해야 한다."
        self.assertEqual(metrics_v2.safe_balance_count(text), 3)

    def test_hanja_suffix_counted(self) -> None:
        text = "기술적 측면에서 안정성과 효율성, 그리고 자동화는 중요하다."
        self.assertGreater(metrics_v2.hanja_nominalizer_density(text), 0.0)

    def test_hanja_zero_density(self) -> None:
        text = "오늘 비가 온다 우산이 필요하다 빨리 가자"
        self.assertEqual(metrics_v2.hanja_nominalizer_density(text), 0.0)

    def test_baseline_null_genre_falls_back(self) -> None:
        text = "오늘은 좋은 날이다."
        result = metrics.compute_all(text, genre="news", baseline_path=BASELINE_PATH)
        self.assertIn("warning", result)
        self.assertIn("news", result["warning"])

    def test_baseline_essay_no_warning(self) -> None:
        text = "오늘은 좋은 날이다."
        result = metrics.compute_all(text, genre="essay", baseline_path=BASELINE_PATH)
        self.assertNotIn("warning", result)

    def test_ai_style_text_is_high_risk(self) -> None:
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
        text = (
            "오늘 비가 왔다. 우산을 폈다. 길이 미끄럽다. "
            "버스에 탔다. 사람들이 많다. 빨리 가고 싶다."
        )
        result = metrics.compute_all(text, genre="essay", baseline_path=BASELINE_PATH)
        self.assertEqual(result["risk_band"], "low")

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


# ===========================================================================
# v2.0 NEW METRIC TESTS (>= 20)
# ===========================================================================


class V20SimplificationTests(unittest.TestCase):
    """Group A: simplification axis."""

    def test_lexical_diversity_ttr_diverse(self) -> None:
        text = "산은 푸르다. 바다는 깊다. 하늘은 맑다. 별은 빛난다."
        self.assertGreater(metrics_v2.lexical_diversity_ttr(text), 0.7)

    def test_lexical_diversity_ttr_repetitive(self) -> None:
        text = "이것은 책이다. 이것은 책이다. 이것은 책이다. 이것은 책이다."
        self.assertLess(metrics_v2.lexical_diversity_ttr(text), 0.5)

    def test_lexical_density_high_with_content(self) -> None:
        text = "혁신성과 효율성, 안정성이 중요하다. 자동화는 필요하다."
        # tokens include 혁신성과 효율성 안정성이 중요하다 자동화는 필요하다 — many content
        self.assertGreater(metrics_v2.lexical_density(text), 0.3)

    def test_lexical_density_low_function_heavy(self) -> None:
        text = "그리고 그러나 또는 즉 예를 그러므로 따라서"
        self.assertLess(metrics_v2.lexical_density(text), 0.1)

    def test_ending_diversity_high(self) -> None:
        text = "비가 온다. 옷이 젖었어. 우산을 펼까? 빨리 가자!"
        self.assertGreaterEqual(metrics_v2.ending_diversity(text), 0.5)

    def test_ending_diversity_low(self) -> None:
        text = "결정한다. 분석한다. 평가한다. 검토한다. 판단한다."
        # all "한다" → ending key = '한다' for all → diversity = 1/5
        self.assertLess(metrics_v2.ending_diversity(text), 0.5)


class V20NormalisationTests(unittest.TestCase):
    """Group B: normalisation axis."""

    def test_normalisation_score_high(self) -> None:
        text = (
            "이것은 사실이다. 결과가 도출된다. 분석을 시행한다. "
            "성능이 향상된다. 효과가 기대된다."
        )
        # all sentences end with -이다 / -된다 / -한다
        self.assertGreaterEqual(metrics_v2.normalisation_score(text), 0.8)

    def test_normalisation_score_low(self) -> None:
        text = (
            "비가 와요. 우산 챙겼어? 길이 미끄러워요. 조심하세요. 늦지 마!"
        )
        # informal endings — none of -한다/-된다/-이다
        self.assertEqual(metrics_v2.normalisation_score(text), 0.0)

    def test_da_streak_rate_long_run(self) -> None:
        text = (
            "혁신은 중요하다. 변화는 빠르다. 시장은 성장한다. 기업은 적응한다. "
            "사회는 발전한다. 미래는 밝다."
        )
        # 6 consecutive '-다' sentences = 1 streak run
        self.assertGreaterEqual(metrics_v2.da_streak_rate(text), 1)

    def test_da_streak_rate_no_streak(self) -> None:
        text = "비가 와. 우산 챙겼어? 늦었네."
        self.assertEqual(metrics_v2.da_streak_rate(text), 0)


class V20InterferenceTests(unittest.TestCase):
    """Group C: T1~T8 detection signals."""

    # T1
    def test_inanimate_subject_rate_high(self) -> None:
        text = (
            "연구는 중요한 사실을 보여준다. "
            "데이터는 새로운 추세를 시사한다. "
            "분석은 흥미로운 결과를 드러낸다."
        )
        self.assertGreater(metrics_v2.inanimate_subject_rate(text), 0.5)

    def test_inanimate_subject_rate_low(self) -> None:
        text = "철수가 학교에 갔다. 영희가 책을 읽었다. 우리가 함께 놀았다."
        self.assertEqual(metrics_v2.inanimate_subject_rate(text), 0.0)

    # T2a
    def test_by_passive_high(self) -> None:
        text = (
            "이 문제는 위원회에 의해 처리되었다. "
            "결정은 정부에 의해 내려진다. "
            "보고서는 연구진에 의해 작성되었다."
        )
        self.assertGreaterEqual(metrics_v2.by_passive_count(text), 2)

    def test_by_passive_zero(self) -> None:
        text = "위원회가 이 문제를 처리했다. 정부가 결정을 내렸다."
        self.assertEqual(metrics_v2.by_passive_count(text), 0)

    # T2b
    def test_double_passive_detected(self) -> None:
        text = "이 문제는 분석되어진다. 그 사실은 잊혀진 지 오래다."
        self.assertGreaterEqual(metrics_v2.double_passive_count(text), 2)

    def test_double_passive_zero(self) -> None:
        text = "이 문제는 분석된다. 그 사실은 잊혀지지 않았다고 보지만, 잊혔다."
        # we deliberately avoid double-passive surface forms
        text = "이 문제는 분석된다. 그 사실은 잊혔다."
        self.assertEqual(metrics_v2.double_passive_count(text), 0)

    # T3
    def test_pronoun_density_high(self) -> None:
        text = "메리는 그녀가 그녀를 그리워해서 그녀의 어머니에게 전화했다."
        self.assertGreater(metrics_v2.pronoun_density(text), 0.10)

    def test_pronoun_density_low(self) -> None:
        text = "메리는 어머니가 그리워서 전화를 걸었다."
        self.assertLess(metrics_v2.pronoun_density(text), 0.05)

    # T4
    def test_deul_overuse_abstract(self) -> None:
        text = "데이터들과 정보들과 결과들이 아이디어들을 보여준다."
        # 4 hits over a small token total — should clear 0.3
        self.assertGreater(metrics_v2.deul_overuse_rate(text), 0.3)

    def test_deul_overuse_zero(self) -> None:
        text = "데이터와 정보, 그리고 여러 결과가 새로운 생각을 보여준다."
        self.assertEqual(metrics_v2.deul_overuse_rate(text), 0.0)

    # T5
    def test_relative_clause_nesting_deep(self) -> None:
        text = (
            "그는 사고를 일으킨 화학물질을 생산한 회사에서 한때 일했던 한 남자를 만났다."
        )
        # adnominal endings: 일으킨 / 생산한 / 일했던 / 한 → >= 3
        self.assertGreaterEqual(metrics_v2.relative_clause_nesting(text), 1)

    def test_relative_clause_nesting_shallow(self) -> None:
        text = "그는 한 남자를 만났다. 그 남자는 회사원이었다."
        self.assertEqual(metrics_v2.relative_clause_nesting(text), 0)

    # T6
    def test_have_make_literal_high(self) -> None:
        text = (
            "그녀는 좋은 목소리를 가지고 있다. "
            "우리는 어제 회의를 가졌다. "
            "위원회는 결정을 내렸다."
        )
        self.assertGreaterEqual(metrics_v2.have_make_literal_count(text), 2)

    def test_have_make_literal_zero(self) -> None:
        text = "그녀는 목소리가 곱다. 우리는 어제 모였다."
        self.assertEqual(metrics_v2.have_make_literal_count(text), 0)

    # T7
    def test_double_particle_count_three(self) -> None:
        text = (
            "주점의 2층에서의 모임이 있었다. "
            "긴장으로부터의 해방이 필요하다. "
            "설문지에의 응답률이 낮았다."
        )
        self.assertGreaterEqual(metrics_v2.double_particle_count(text), 3)

    def test_double_particle_count_excludes_simple_eui(self) -> None:
        # Only bare ~의 — must be ZERO under caveat #5.
        text = "한국의 미래는 밝다. 우리의 시간은 짧다. 그의 의견은 다르다."
        self.assertEqual(metrics_v2.double_particle_count(text), 0)

    # T8b
    def test_progressive_aspect_high(self) -> None:
        text = (
            "나는 책을 읽고 있다. 그는 일을 하고 있다. 우리는 놀고 있었다."
        )
        self.assertGreater(metrics_v2.progressive_aspect_rate(text), 0.5)

    def test_progressive_aspect_zero(self) -> None:
        text = "나는 책을 읽는다. 그는 일을 한다. 우리는 놀았다."
        self.assertEqual(metrics_v2.progressive_aspect_rate(text), 0.0)

    # interference index composite
    def test_interference_index_components(self) -> None:
        text = "데이터들이 결과들을 보여준다. 그녀는 그녀의 책을 가지고 있다."
        idx = metrics_v2.interference_index(text)
        self.assertIn("components", idx)
        self.assertIn("weighted_total", idx)
        self.assertGreaterEqual(idx["weighted_total"], 0.0)


class V20IntegrationTests(unittest.TestCase):
    """compute_all_v2 end-to-end + baseline placeholder behavior."""

    def test_compute_all_v2_returns_v2_keys(self) -> None:
        text = "오늘은 비가 온다. 길이 미끄럽다."
        result = metrics_v2.compute_all_v2(
            text, genre="essay",
            baseline_path=BASELINE_PATH,
            baseline_v2_path=BASELINE_V2_PATH,
        )
        self.assertEqual(result["version"], "v2.0")
        self.assertIn("v2_metrics", result)
        self.assertIn("v2_interference_index", result)
        self.assertIn("v2_z_scores", result)
        # v1.6 keys preserved
        self.assertIn("metrics", result)
        self.assertIn("risk_band", result)

    def test_compute_all_v2_baseline_placeholder_warning(self) -> None:
        text = "오늘은 비가 온다. 길이 미끄럽다."
        result = metrics_v2.compute_all_v2(
            text, genre="essay",
            baseline_path=BASELINE_PATH,
            baseline_v2_path=BASELINE_V2_PATH,
        )
        # All v2 baseline cells are placeholders by design.
        self.assertGreater(len(result["v2_baseline_warnings"]), 0)


if __name__ == "__main__":
    unittest.main()
