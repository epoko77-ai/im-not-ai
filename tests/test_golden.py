"""Golden-fixture regression tests for humanize-korean.

Runs under pytest OR `python -m unittest` (same convention as
test_metrics_v2.py). No LLM calls: CI cannot run the pipeline, so this
suite validates the deterministic scorer itself, both directions:

  - identity:   run_checks(input, input) is always empty (no false positives)
  - good side:  a legitimate rewrite (good_output.txt) passes
  - bad side:   a known-bad rewrite (bad_output.txt) triggers at least the
                failure codes declared in expected_failures.json

To gate a real pipeline run, feed the actual rewrite of input.txt through
tests/golden/checks.py (see tests/golden/README.md).
"""

from __future__ import annotations

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GOLDEN_DIR = os.path.join(HERE, "golden")
FIXTURES_DIR = os.path.join(GOLDEN_DIR, "fixtures")
sys.path.insert(0, GOLDEN_DIR)

import checks  # noqa: E402


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _fixtures() -> list[str]:
    return sorted(
        d for d in os.listdir(FIXTURES_DIR)
        if os.path.isfile(os.path.join(FIXTURES_DIR, d, "input.txt"))
    )


# ===========================================================================
# Fixture round-trips
# ===========================================================================


class GoldenFixtureTests(unittest.TestCase):
    def test_fixtures_exist_and_are_complete(self) -> None:
        names = _fixtures()
        self.assertGreaterEqual(len(names), 2)
        for name in names:
            d = os.path.join(FIXTURES_DIR, name)
            for fn in ("input.txt", "bad_output.txt", "good_output.txt",
                       "expected_failures.json"):
                self.assertTrue(
                    os.path.isfile(os.path.join(d, fn)),
                    f"{name}/{fn} 누락",
                )

    def test_identity_never_fails(self) -> None:
        """무변경 출력은 어떤 픽스처에서도 FAIL이 없어야 한다 (오탐 가드)."""
        for name in _fixtures():
            with self.subTest(fixture=name):
                text = _read(os.path.join(FIXTURES_DIR, name, "input.txt"))
                self.assertEqual(checks.run_checks(text, text), [])

    def test_good_output_passes(self) -> None:
        for name in _fixtures():
            with self.subTest(fixture=name):
                d = os.path.join(FIXTURES_DIR, name)
                failures = checks.run_checks(
                    _read(os.path.join(d, "input.txt")),
                    _read(os.path.join(d, "good_output.txt")),
                )
                self.assertEqual(
                    failures, [],
                    "정상 윤문이 FAIL: " + "; ".join(map(str, failures)),
                )

    def test_bad_output_fails_with_expected_codes(self) -> None:
        for name in _fixtures():
            with self.subTest(fixture=name):
                d = os.path.join(FIXTURES_DIR, name)
                expected = set(json.loads(
                    _read(os.path.join(d, "expected_failures.json"))
                )["bad_must_fail"])
                failures = checks.run_checks(
                    _read(os.path.join(d, "input.txt")),
                    _read(os.path.join(d, "bad_output.txt")),
                )
                got = {x.code for x in failures}
                self.assertTrue(
                    expected <= got,
                    f"기대 실패 코드 미검출: {sorted(expected - got)} "
                    f"(검출된 코드: {sorted(got)})",
                )


# ===========================================================================
# Scorer unit tests — each gate, positive and negative
# ===========================================================================


class RegisterCheckTests(unittest.TestCase):
    def test_hayeot_injection_detected(self) -> None:
        fails = checks.run_checks("팀이 계획을 발표했다.", "팀이 계획을 발표하였다.")
        self.assertIn("hayeot_injection", {x.code for x in fails})

    def test_hayeot_preexisting_is_not_injection(self) -> None:
        """학술 원문의 기존 '하였'은 유지·감소 모두 허용 (증가만 FAIL)."""
        orig = "위원회는 안건을 의결하였다. 결과는 공개하였다."
        kept = "위원회는 안건을 의결하였다. 결과도 공개하였다."
        reduced = "위원회는 안건을 의결했다. 결과도 공개했다."
        self.assertEqual(checks.check_register(orig, kept), [])
        self.assertEqual(checks.check_register(orig, reduced), [])

    def test_cliche_injection_detected(self) -> None:
        fails = checks.run_checks(
            "매출이 크게 늘었다.", "매출이 늘어 기록적인 성과를 거두었다."
        )
        self.assertIn("cliche_injection", {x.code for x in fails})

    def test_cliche_preexisting_is_not_injection(self) -> None:
        orig = "이 제품은 주목받았다."
        out = "이 제품은 주목받았다. 판매도 늘었다."
        self.assertEqual(
            [x for x in checks.check_register(orig, out)
             if x.code == "cliche_injection"],
            [],
        )

    def test_colloquial_erased_detected(self) -> None:
        orig = "좋았는데요. 싸거든요. 편해요. 추천해요."
        out = "좋았다. 저렴하다. 편리하다. 추천할 만하다."
        fails = checks.check_register(orig, out)
        self.assertIn("colloquial_erased", {x.code for x in fails})

    def test_colloquial_gate_skipped_for_formal_original(self) -> None:
        """원문에 구어 종결이 적으면(< 3회) 게이트 자체를 건너뛴다."""
        orig = "보고서를 제출했다. 결과는 다음과 같아요."
        out = "보고서를 제출했다. 결과는 다음과 같다."
        self.assertEqual(checks.check_register(orig, out), [])

    def test_partial_retention_passes(self) -> None:
        """문장 병합 등으로 일부 줄어도 절반 이상 남으면 통과."""
        orig = "좋아요. 싸요. 편해요. 빨라요."
        out = "좋아요. 싸고 편해요. 빨라요."
        self.assertEqual(checks.check_register(orig, out), [])


class StructureCheckTests(unittest.TestCase):
    def test_heading_lost_vs_absorbed(self) -> None:
        orig = "Ⅱ. 연구 방법\n\n설문을 실시했다.\n\n(1) 표본 설계\n\n표본은 500명이다."
        out_absorbed = "연구 방법으로 설문을 실시했다. 표본 설계에서 표본은 500명이다."
        codes = {x.code for x in checks.check_headings(orig, out_absorbed)}
        self.assertIn("heading_absorbed", codes)
        out_lost = "설문을 실시했다. 표본은 500명이다."
        codes = {x.code for x in checks.check_headings(orig, out_lost)}
        self.assertIn("heading_lost", codes)

    def test_heading_kept_passes(self) -> None:
        orig = "## 배경\n\n본문이다."
        out = "## 배경\n\n본문을 다듬었다."
        self.assertEqual(checks.check_headings(orig, out), [])

    def test_numbered_prose_sentence_is_not_a_heading(self) -> None:
        orig = "1. 표본은 전국에서 모집했다.\n2. 응답률은 62%였다."
        self.assertEqual(checks.extract_headings(orig), [])

    def test_paren_heading_not_counted_as_footnote_marker(self) -> None:
        self.assertEqual(checks.extract_inline_markers("(3) 결과 분석"), [])

    def test_year_paren_not_counted_as_footnote_marker(self) -> None:
        self.assertEqual(checks.extract_inline_markers("보고서(2024)에 따르면"), [])

    def test_footnote_count_decrease_detected(self) -> None:
        orig = "성장률은 3.1%였다.1) 물가는 2.4% 올랐다.2)"
        out = "성장률은 3.1%였다.1) 물가는 2.4% 올랐다."
        codes = {x.code for x in checks.check_footnotes(orig, out)}
        self.assertIn("footnote_count", codes)
        self.assertIn("footnote_numbers", codes)

    def test_footnote_moved_to_other_sentence_detected(self) -> None:
        orig = "성장률은 3.1%였다.1) 물가는 2.4% 올랐다."
        out = "성장률은 3.1%였다. 물가는 2.4% 올랐다.1)"
        codes = {x.code for x in checks.check_footnotes(orig, out)}
        self.assertIn("footnote_anchor", codes)

    def test_footnote_definition_alteration_detected(self) -> None:
        orig = "본문이다.1)\n1) 김철수, 「연구」, 2024, 10쪽."
        out = "본문이다.1)\n1) 김철수, 「연구」, 2023, 10쪽."
        codes = {x.code for x in checks.check_footnotes(orig, out)}
        self.assertIn("footnote_def", codes)

    def test_footnotes_kept_passes(self) -> None:
        orig = "성장률은 3.1%였다.1)\n1) 한국은행, 2024."
        out = "성장률은 3.1%를 기록했다.1)\n1) 한국은행, 2024."
        self.assertEqual(checks.check_footnotes(orig, out), [])

    def test_quote_altered_detected(self) -> None:
        orig = '그는 "결과를 신중히 해석해야 한다"고 말했다.'
        out = '그는 "결과를 조심스럽게 해석해야 한다"고 말했다.'
        codes = {x.code for x in checks.check_quotes(orig, out)}
        self.assertIn("quote_altered", codes)

    def test_quote_kept_passes(self) -> None:
        orig = '그는 "결과를 신중히 해석해야 한다"고 말했다.'
        out = '"결과를 신중히 해석해야 한다"는 것이 그의 말이다.'
        self.assertEqual(checks.check_quotes(orig, out), [])


class NumberCheckTests(unittest.TestCase):
    """수치 주입/삭제 방향성 게이트 — check_numbers."""

    def test_number_injected_detected(self) -> None:
        orig = "매출이 크게 늘었다."
        out = "매출이 14개월 만에 75배 늘었다."
        codes = {x.code for x in checks.check_numbers(orig, out)}
        self.assertIn("number_injected", codes)

    def test_numbers_preserved_passes(self) -> None:
        orig = "성장률은 3.1%였다. 비용은 0.00001달러다. 14개월 걸렸다."
        out = "성장률은 3.1%를 기록했다. 14개월이 걸렸고 비용은 0.00001달러다."
        self.assertEqual(checks.check_numbers(orig, out), [])

    def test_number_dropped_is_not_a_gate(self) -> None:
        """수치 소실은 문장 병합의 정상 부산물일 수 있다 — run_checks에는
        안 나오고 dropped_numbers(advisory)로만 잡힌다."""
        orig = "성장률은 3.1%였다. 물가는 2.4% 올랐다."
        out = "성장률은 3.1%였다."
        self.assertEqual(checks.check_numbers(orig, out), [])
        self.assertEqual(checks.run_checks(orig, out), [])
        self.assertEqual(checks.dropped_numbers(orig, out), ["2.4"])

    def test_dropped_numbers_empty_when_preserved(self) -> None:
        orig = "성장률은 3.1%였다."
        out = "성장률은 3.1%를 기록했다."
        self.assertEqual(checks.dropped_numbers(orig, out), [])

    def test_korean_unit_man_equivalence(self) -> None:
        """"1만" == "10,000" — 수사 단위 표기 변경은 주입/소실이 아니다."""
        orig = "이용자는 1만 명이다."
        out = "이용자는 10,000 명이다."
        self.assertEqual(checks.check_numbers(orig, out), [])
        self.assertEqual(checks.dropped_numbers(orig, out), [])
        # 반대 방향도 대칭
        self.assertEqual(checks.check_numbers(out, orig), [])
        self.assertEqual(checks.dropped_numbers(out, orig), [])

    def test_korean_unit_eok_equivalence(self) -> None:
        """"1억" == "100,000,000" 동등."""
        orig = "예산은 1억 원이다."
        out = "예산은 100,000,000 원이다."
        self.assertEqual(checks.check_numbers(orig, out), [])
        self.assertEqual(checks.dropped_numbers(orig, out), [])

    def test_korean_unit_only_when_attached(self) -> None:
        """단위는 숫자 직후에 바로 붙은 경우만 환산 — "5 만"은 환산 안 함."""
        vals = checks._number_values("5 만 명")
        self.assertIn("5", vals)
        self.assertNotIn("50000", vals)

    def test_comma_thousands_normalized(self) -> None:
        """"10,000" ↔ "10000" 표기 변경은 수치 변조가 아니다."""
        orig = "예산은 10,000억 원이다."
        out = "예산은 10000억 원이다."
        self.assertEqual(checks.check_numbers(orig, out), [])

    def test_repetition_change_not_flagged(self) -> None:
        """값 set 비교 — 같은 값의 등장 횟수 변화(헤딩 재번호 등)는 무시."""
        orig = "1. 서론\n1) 각주가 아니라 목록.\n결과는 1건이다."
        out = "결과는 1건이다."
        codes = {x.code for x in checks.check_numbers(orig, out)}
        self.assertNotIn("number_injected", codes)
        self.assertNotIn("number_dropped", codes)

    def test_run_checks_includes_numbers(self) -> None:
        fails = checks.run_checks("보고서다.", "보고서는 2024년에 나왔다.")
        self.assertIn("number_injected", {x.code for x in fails})


class EdgeCaseTests(unittest.TestCase):
    def test_plain_text_no_failures(self) -> None:
        orig = "오늘은 날씨가 맑다. 산책을 다녀왔다."
        out = "오늘 날씨가 맑아 산책을 다녀왔다."
        self.assertEqual(checks.run_checks(orig, out), [])

    def test_empty_output_fails(self) -> None:
        fails = checks.run_checks("본문이다.", "   ")
        self.assertEqual([x.code for x in fails], ["empty_output"])

    def test_empty_original_is_safe(self) -> None:
        self.assertEqual(checks.run_checks("", "출력."), [])


if __name__ == "__main__":
    unittest.main()
