"""scripts/eval_compare.py 회귀 테스트.

verdict()/compare_metric()는 docs/watermark-baseline-runbook.md 계측 파이프라인의
판정 규칙(모듈 docstring 참조)을 코드화한 순수 함수라 fixture 없이 단위 테스트가
가능한데, 이 스크립트에는 아직 전용 테스트가 없었다. n=1 룰렛 방지 로직이라
회귀가 조용히 들어가면 계측 결과 자체가 잘못된 결론(가짜 유의/가짜 잡음)으로
이어진다.

실행: python3 -m pytest tests/test_eval_compare.py -q
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

import eval_compare as ec  # noqa: E402


class VerdictTests(unittest.TestCase):
    # ── pooled == 0 (K=1이었거나 두 스냅샷 모두 완전히 결정적) ──────────
    def test_pooled_zero_delta_zero_is_identical(self):
        self.assertEqual(ec.verdict(delta=0.0, pooled=0.0, threshold=2.0), "동일")

    def test_pooled_zero_delta_nonzero_is_undecidable(self):
        self.assertEqual(ec.verdict(delta=0.5, pooled=0.0, threshold=2.0), "판정불가")

    # ── delta가 잡음 바닥(threshold * pooled) 이내면 잡음 ───────────────
    def test_delta_within_noise_floor_is_noise(self):
        # pooled=1.0, threshold=2.0 → 바닥 2.0, delta=2.0은 경계값(<=)이라 잡음
        self.assertEqual(ec.verdict(delta=2.0, pooled=1.0, threshold=2.0), "잡음")
        self.assertEqual(ec.verdict(delta=-1.5, pooled=1.0, threshold=2.0), "잡음")

    def test_delta_beyond_noise_floor_is_significant(self):
        self.assertEqual(ec.verdict(delta=2.1, pooled=1.0, threshold=2.0), "유의")
        self.assertEqual(ec.verdict(delta=-3.0, pooled=1.0, threshold=2.0), "유의")

    def test_threshold_is_configurable(self):
        # 같은 delta·pooled라도 threshold를 낮추면 유의로 뒤집힐 수 있다
        self.assertEqual(ec.verdict(delta=2.5, pooled=1.0, threshold=2.0), "유의")
        self.assertEqual(ec.verdict(delta=2.5, pooled=1.0, threshold=3.0), "잡음")


class CompareMetricTests(unittest.TestCase):
    def _snapshot(self, mean: float, stdev: float, n: int = 5) -> dict:
        return {"mean": mean, "stdev": stdev, "n": n}

    def test_returns_none_when_metric_missing_or_not_dict(self):
        a = {"change_rate": self._snapshot(0.1, 0.01)}
        b = {"change_rate": self._snapshot(0.2, 0.01)}
        self.assertIsNone(ec.compare_metric(a, b, "not_present", 2.0))
        self.assertIsNone(ec.compare_metric({"x": 1}, {"x": 1}, "x", 2.0))

    def test_lower_is_better_metric_flags_direction(self):
        # sig_double_passive_count_out은 BETTER 테이블에서 "lower"
        key = "sig_double_passive_count_out"
        a = {key: self._snapshot(5.0, 0.1)}
        b_improved = {key: self._snapshot(1.0, 0.1)}
        b_worsened = {key: self._snapshot(9.0, 0.1)}

        r_improved = ec.compare_metric(a, b_improved, key, threshold=2.0)
        self.assertEqual(r_improved["verdict"], "유의")
        self.assertEqual(r_improved["direction"], "개선")

        r_worsened = ec.compare_metric(a, b_worsened, key, threshold=2.0)
        self.assertEqual(r_worsened["verdict"], "유의")
        self.assertEqual(r_worsened["direction"], "악화")

    def test_direction_agnostic_metric_never_labels_direction(self):
        # change_rate는 BETTER 테이블에서 방향 None — 유의해도 개선/악화 표시 없음
        key = "change_rate"
        a = {key: self._snapshot(0.10, 0.01)}
        b = {key: self._snapshot(0.40, 0.01)}
        r = ec.compare_metric(a, b, key, threshold=2.0)
        self.assertEqual(r["verdict"], "유의")
        self.assertEqual(r["direction"], "")

    def test_noise_range_change_has_no_direction_even_for_directional_metric(self):
        key = "sig_double_passive_count_out"
        a = {key: self._snapshot(5.0, 2.0)}
        b = {key: self._snapshot(5.5, 2.0)}
        r = ec.compare_metric(a, b, key, threshold=2.0)
        self.assertEqual(r["verdict"], "잡음")
        self.assertEqual(r["direction"], "")

    def test_delta_and_noise_floor_rounding(self):
        key = "change_rate"
        a = {key: self._snapshot(0.1234567, 0.0)}
        b = {key: self._snapshot(0.2345678, 0.0)}
        r = ec.compare_metric(a, b, key, threshold=2.0)
        self.assertEqual(r["delta"], round(0.2345678 - 0.1234567, 4))
        self.assertEqual(r["noise_floor"], 0.0)
        self.assertEqual(r["n_before"], 5)
        self.assertEqual(r["n_after"], 5)


if __name__ == "__main__":
    unittest.main()
