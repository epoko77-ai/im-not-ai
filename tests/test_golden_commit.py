"""Golden-fixture regression tests for commit-ko.

Runs under pytest OR `python -m unittest`, mirroring tests/test_golden.py
for humanize-korean. No LLM calls: this suite validates the deterministic
scorer itself, both directions:

  - identity:   run_checks(input, input) is always empty (no false positives)
  - good side:  a legitimate rewrite (good_output.txt) passes
  - bad side:   a known-bad rewrite (bad_output.txt) triggers at least the
                failure codes declared in expected_failures.json

To gate a real skill run, feed the actual rewrite of input.txt through
tests/golden_commit/checks.py (see tests/golden_commit/README.md).
"""

from __future__ import annotations

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GOLDEN_DIR = os.path.join(HERE, "golden_commit")
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


class PrefixCheckTests(unittest.TestCase):
    def test_type_case_change_detected(self) -> None:
        fails = checks.check_prefix("fix(auth): 버그 수정함", "Fix(auth): 버그 수정")
        self.assertIn("prefix_altered", {x.code for x in fails})

    def test_scope_dropped_detected(self) -> None:
        fails = checks.check_prefix("fix(auth): 버그 수정함", "fix: 버그 수정")
        self.assertIn("prefix_altered", {x.code for x in fails})

    def test_prefix_kept_passes(self) -> None:
        fails = checks.check_prefix("fix(auth)!: 버그 수정함", "fix(auth)!: 버그를 수정")
        self.assertEqual(fails, [])

    def test_non_conventional_commit_is_not_gated(self) -> None:
        """Conventional Commits 형식이 아니면 접두사 체크 자체를 건너뛴다."""
        fails = checks.check_prefix("로그인 버그 수정함", "로그인 버그 수정")
        self.assertEqual(fails, [])


class TrailerCheckTests(unittest.TestCase):
    def test_trailer_lost_detected(self) -> None:
        orig = "fix: 버그 수정\n\nCo-authored-by: Jane <jane@example.com>"
        out = "fix: 버그 수정"
        codes = {x.code for x in checks.check_trailers(orig, out)}
        self.assertIn("trailer_lost", codes)

    def test_trailer_value_altered_detected(self) -> None:
        orig = "fix: 버그 수정\n\nCloses #482"
        out = "fix: 버그 수정\n\nCloses #480"
        codes = {x.code for x in checks.check_trailers(orig, out)}
        self.assertIn("trailer_altered", codes)

    def test_trailer_kept_passes(self) -> None:
        orig = "fix: 버그 수정\n\nCloses #482\nCo-authored-by: Jane <jane@example.com>"
        out = "fix: 버그를 수정\n\nCloses #482\nCo-authored-by: Jane <jane@example.com>"
        self.assertEqual(checks.check_trailers(orig, out), [])


class CodeSpanCheckTests(unittest.TestCase):
    def test_code_span_lost_detected(self) -> None:
        orig = "fix: `enqueue()` 순서 버그 수정함"
        out = "fix: enqueue 순서 버그 수정"
        codes = {x.code for x in checks.check_code_spans(orig, out)}
        self.assertIn("code_span_altered", codes)

    def test_code_span_kept_passes(self) -> None:
        orig = "fix: `enqueue()` 순서 버그 수정함"
        out = "fix: `enqueue()` 순서 버그 수정"
        self.assertEqual(checks.check_code_spans(orig, out), [])


class RegisterAndBureaucraticTests(unittest.TestCase):
    def test_hayeot_injection_detected(self) -> None:
        fails = checks.check_register("docs: 오탈자 수정함", "docs: 오탈자를 수정하였습니다")
        self.assertIn("hayeot_injection", {x.code for x in fails})

    def test_hayeot_preexisting_is_not_injection(self) -> None:
        orig = "docs: 안내문을 수정하였음"
        out = "docs: 안내문 수정"
        self.assertEqual(checks.check_register(orig, out), [])

    def test_bureaucratic_injection_detected(self) -> None:
        fails = checks.check_bureaucratic("docs: 오탈자 수정함", "docs: 오탈자 수정 작업을 진행하였습니다")
        self.assertIn("bureaucratic_injection", {x.code for x in fails})

    def test_bureaucratic_removed_passes(self) -> None:
        orig = "fix: 재시도 로직을 수행함"
        out = "fix: 재시도 로직 추가"
        self.assertEqual(checks.check_bureaucratic(orig, out), [])


class NumberCheckTests(unittest.TestCase):
    def test_number_injected_detected(self) -> None:
        fails = checks.check_numbers("fix: 버그 수정함", "fix: 버그 수정 (이슈 #482)")
        self.assertIn("number_injected", {x.code for x in fails})

    def test_issue_ref_preserved_passes(self) -> None:
        orig = "fix: 버그 수정함\n\nCloses #482"
        out = "fix: 버그 수정\n\nCloses #482"
        self.assertEqual(checks.check_numbers(orig, out), [])


class EdgeCaseTests(unittest.TestCase):
    def test_plain_message_no_failures(self) -> None:
        orig = "fix(auth): 로그인 실패 시 재시도 로직을 수행함"
        out = "fix(auth): 로그인 실패 시 재시도 로직 추가"
        self.assertEqual(checks.run_checks(orig, out), [])

    def test_empty_output_fails(self) -> None:
        fails = checks.run_checks("fix: 버그 수정함", "   ")
        self.assertEqual([x.code for x in fails], ["empty_output"])

    def test_empty_original_is_safe(self) -> None:
        self.assertEqual(checks.run_checks("", "fix: 버그 수정"), [])


if __name__ == "__main__":
    unittest.main()
