"""core/modality_loss.py — 서법 소실 게이트.

한국어 P5 의 영어판. 총수가 아니라 **문장쌍**으로 본다.
실측 보정 근거는 `lang/en/scholarship.md` 「서법 게이트 검증」.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_MOD = os.path.join(_ROOT, "core", "modality_loss.py")


def _load():
    spec = importlib.util.spec_from_file_location("_ml", _MOD)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class LossTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(os.path.isfile(_MOD), f"없다: {_MOD}")
        self.m = _load()

    def test_hedge_loss_fails(self) -> None:
        out = self.m.check_modality_loss("The data may be noisy.", "The data is noisy.")
        self.assertTrue(out["failed"])
        self.assertEqual(out["lost"][0]["kind"], "hedge")

    def test_partial_loss_within_kind_fails(self) -> None:
        """존재 여부가 아니라 건수 — 표지가 하나 남아도 소실은 소실이다."""
        out = self.m.check_modality_loss(
            "Results may indicate a shift.", "Results indicate a shift."
        )
        self.assertTrue(out["failed"], out)

    def test_deontic_loss_fails(self) -> None:
        out = self.m.check_modality_loss(
            "Any trend must be corroborated.", "Any trend is corroborated."
        )
        self.assertTrue(out["failed"])
        self.assertEqual(out["lost"][0]["kind"], "deontic")

    def test_equivalent_substitution_passes(self) -> None:
        """may → might 은 서법 보존. 건수 기준이라 통과해야 한다."""
        out = self.m.check_modality_loss(
            "The data may be noisy.", "The data might be noisy."
        )
        self.assertFalse(out["failed"], out)

    def test_split_sentence_absorption_passes(self) -> None:
        """실측 false FAIL 회귀 — 분할된 조각이 표지를 가져간 경우."""
        before = ("Results indicate that translations cluster by translator, "
                  "though certain features remain recoverable.")
        after = ("Results indicate that translations cluster by translator. "
                 "Certain features remain recoverable.")
        self.assertFalse(self.m.check_modality_loss(before, after)["failed"])

    def test_added_modality_is_not_a_failure(self) -> None:
        out = self.m.check_modality_loss("The data is noisy.", "The data may be noisy.")
        self.assertFalse(out["failed"], out)

    def test_deleted_sentence_is_not_modality(self) -> None:
        """문장 통째 삭제는 내용 소실 — content_preservation 소관이다."""
        out = self.m.check_modality_loss(
            "We ran a test. The data may be noisy.", "We ran a test."
        )
        self.assertFalse(out["failed"], out)


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
        r = self._run("The data may be noisy.", "The data may well be noisy.")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_loss_exits_one(self) -> None:
        r = self._run("The data may be noisy.", "The data is noisy.")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("hedge", r.stdout)

    def test_missing_file_exits_three(self) -> None:
        r = subprocess.run([sys.executable, _MOD, "--before", "/nope", "--after", "/nope2"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 3)


if __name__ == "__main__":
    unittest.main()
