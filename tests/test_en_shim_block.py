"""shim 결합 파일의 언어 분기 — 영어 런에 한국어 규칙을 주지 않는지.

실사고(2026-09-05, 첫 end-to-end 런): 영어 결합 파일에 한국어 `[v1.6 지표]` 8개가
전부 n/a 로 실리고, 근거 가이드가 **영어 룰북에 없는 규칙 ID**(C-11·D-1·H-1)를
적용하라고 지시했다. 윤문 콜이 룰북과 모순되는 지시를 받는 상태였다.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_SHIM = os.path.join(_ROOT, "scripts", "prepare_monolith_input.py")

_EN_TEXT = (
    "The old argument for public libraries was about scarcity, and it no longer holds. "
    "Books cost money, shelves cost space, and a town could only afford so many. "
    "That constraint shaped everything about how the institution justified itself. "
    "Digital distribution removed the constraint, so the justification has to change too. "
    "What a library offers now is curation, quiet, and a place that asks nothing of you. "
) * 3
_KO_TEXT = (
    "공공도서관의 오래된 논거는 희소성에 관한 것이었다. 책은 돈이 들고 서가는 자리를 "
    "차지했다. 그 제약이 이 기관이 스스로를 정당화하는 방식을 결정했다. "
) * 3


def _run(text: str, lang: str) -> str:
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "01_input.txt"), "w", encoding="utf-8") as f:
            f.write(text)
        proc = subprocess.run(
            [sys.executable, _SHIM, "--run-dir", td, "--lang", lang],
            capture_output=True, text=True, timeout=120,
        )
        assert proc.returncode == 0, proc.stderr
        with open(os.path.join(td, "01_input_with_metrics.txt"), encoding="utf-8") as f:
            return f.read()


class EnglishBlockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.combined = _run(_EN_TEXT, "en")

    def test_no_korean_metric_block(self) -> None:
        self.assertNotIn("[v1.6 지표]", self.combined)
        self.assertNotIn("hanja_nominalizer_density", self.combined)

    def test_no_korean_rule_prescriptions(self) -> None:
        """C-11·D-1·H-1 은 영어 룰북에 없는 ID다. 지시로 등장하면 안 된다."""
        for marker in ("C-11(", "D-1·H-1 처방", "ending_comma_rate가"):
            self.assertNotIn(marker, self.combined, marker)

    def test_carries_english_signals_and_ids(self) -> None:
        self.assertIn("영어 계측형", self.combined)
        self.assertIn("EN-1 participial", self.combined)
        self.assertIn("quick-rules.md", self.combined)
        self.assertIn("threshold_set:", self.combined)

    def test_deficit_signals_are_protected(self) -> None:
        """hedge·수동태·contraction 은 건드리지 말라는 지시가 붙어야 한다."""
        self.assertIn("hedge", self.combined)


class KoreanBlockRegressionTests(unittest.TestCase):
    def test_korean_run_keeps_korean_block(self) -> None:
        combined = _run(_KO_TEXT, "ko")
        self.assertIn("[v1.6 지표]", combined)
        self.assertNotIn("영어 계측형", combined)


if __name__ == "__main__":
    unittest.main()
