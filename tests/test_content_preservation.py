"""core/content_preservation.py — 내용 보존 게이트 (영어).

한국어 `scripts/checks.py` 의 대응물. 영어 게이트 3종은 전부 문체 축이었고
내용을 지키는 게 하나도 없었다 — 수치·인용·인용문헌이 무방비였다.

한국어의 설계 결정 둘을 그대로 가져온다.
 1. **수치는 주입만 FAIL, 소실은 관측만.** 문장 병합·표기 통합에서도 수치가
    사라지므로 게이트하면 양치기 소년이 된다(checks.py dropped_numbers 주석).
 2. **직접 인용은 불변** — 소실도 FAIL. 철칙 #1.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_MOD = os.path.join(_ROOT, "core", "content_preservation.py")


def _load():
    spec = importlib.util.spec_from_file_location("_cp", _MOD)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class NumberTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(os.path.isfile(_MOD), f"없다: {_MOD}")
        self.m = _load()

    def test_injection_fails(self) -> None:
        out = self.m.check(("Costs rose last year."), "Costs rose 40% last year.")
        self.assertTrue(out["failed"])
        self.assertIn("number_injected", [f["kind"] for f in out["failures"]])

    def test_deletion_is_advisory_not_failure(self) -> None:
        """소실은 경고만 — 문장 병합에서도 수치가 사라진다."""
        out = self.m.check("Costs rose 40% in 2019.", "Costs rose in 2019.")
        self.assertFalse(out["failed"], out)
        self.assertIn("40", out["advisory"]["dropped_numbers"])

    def test_comma_and_percent_format_is_not_injection(self) -> None:
        """10,000 → 10000, 40% → 40 percent 는 표기 변경이지 변조가 아니다."""
        out = self.m.check("We saw 10,000 users and 40% growth.",
                           "We saw 10000 users and 40 percent growth.")
        self.assertFalse(out["failed"], out)

    def test_scale_words_normalized(self) -> None:
        out = self.m.check("It cost 2 million dollars.", "It cost 2,000,000 dollars.")
        self.assertFalse(out["failed"], out)


class QuoteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.m = _load()

    def test_dropped_quote_fails(self) -> None:
        before = 'The report said, "the system failed under load" last spring.'
        out = self.m.check(before, "The report described a failure last spring.")
        self.assertTrue(out["failed"])
        self.assertIn("quote_dropped", [f["kind"] for f in out["failures"]])

    def test_preserved_quote_passes(self) -> None:
        before = 'He said, "the system failed under load" yesterday.'
        after = 'He said "the system failed under load" the day before.'
        self.assertFalse(self.m.check(before, after)["failed"])

    def test_short_quote_ignored(self) -> None:
        """짧은 따옴표는 강조 용법이라 인용으로 보지 않는다."""
        self.assertFalse(self.m.check('A so-called "fix" arrived.', "A fix arrived.")["failed"])


class CitationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.m = _load()

    def test_dropped_bracket_citation_fails(self) -> None:
        out = self.m.check("Prior work [12] showed this.", "Prior work showed this.")
        self.assertTrue(out["failed"])
        self.assertIn("citation_dropped", [f["kind"] for f in out["failures"]])

    def test_dropped_author_year_fails(self) -> None:
        out = self.m.check("As shown (Smith, 2020), it holds.", "As shown, it holds.")
        self.assertTrue(out["failed"])

    def test_preserved_citation_passes(self) -> None:
        self.assertFalse(self.m.check("See [3] and (Lee et al., 2019).",
                                      "See [3]; also (Lee et al., 2019).")["failed"])


class CliTests(unittest.TestCase):
    def _run(self, before, after):
        with tempfile.TemporaryDirectory() as td:
            b, a = os.path.join(td, "b.txt"), os.path.join(td, "a.txt")
            for p, t in ((b, before), (a, after)):
                with open(p, "w", encoding="utf-8") as f:
                    f.write(t)
            return subprocess.run([sys.executable, _MOD, "--before", b, "--after", a],
                                  capture_output=True, text=True, timeout=60)

    def test_clean_exits_zero(self) -> None:
        r = self._run("Costs rose 40% in 2019.", "Costs went up 40% in 2019.")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_violation_exits_one(self) -> None:
        r = self._run("Prior work [12] showed this.", "Prior work showed this.")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("citation_dropped", r.stdout)

    def test_missing_file_exits_three(self) -> None:
        r = subprocess.run([sys.executable, _MOD, "--before", "/nope", "--after", "/nope2"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 3)


class HeadingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.m = _load()

    def test_lost_heading_fails(self) -> None:
        out = self.m.check("## Method\n\nWe ran a test.", "We ran a test.")
        self.assertIn("heading_lost", [f["kind"] for f in out["failures"]])

    def test_absorbed_heading_fails(self) -> None:
        out = self.m.check("## Method\n\nWe ran a test.", "Method: we ran a test.")
        self.assertIn("heading_absorbed", [f["kind"] for f in out["failures"]])

    def test_kept_heading_passes(self) -> None:
        out = self.m.check("## Method\n\nWe ran a test.", "## Method\n\nWe tested it.")
        self.assertFalse(out["failed"], out)


if __name__ == "__main__":
    unittest.main()
