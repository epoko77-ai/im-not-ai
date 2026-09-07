"""core/change_rate.py — 언어 무관 변경률. 한국어 스킬 디렉터리 없이 동작해야 한다.

배경: verify_change_rate.py 가 skills/humanize-korean/references 를 sys.path 에
넣어 metrics_v2 를 import 했다. 정작 쓰는 change_rate() 는 문자 diff 라
언어와 무관하다(영어 스파이크에서 무수정 동작 확인). 영어팩이 한국어 디렉터리에
의존하지 않도록 커널로 분리한다.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_CORE = os.path.join(_ROOT, "core", "change_rate.py")


def _load():
    spec = importlib.util.spec_from_file_location("_core_change_rate", _CORE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CoreChangeRateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(os.path.isfile(_CORE), f"core/change_rate.py 가 없다: {_CORE}")
        self.m = _load()

    def test_identical_text_is_zero(self) -> None:
        self.assertEqual(self.m.change_rate("같은 글이다.", "같은 글이다."), 0.0)

    def test_english_input_works(self) -> None:
        """영어에서도 동작한다 — 스파이크가 실증한 언어 무관성."""
        before = "The office was the organizing principle of urban life."
        after = "The office organized urban life."
        rate = self.m.change_rate(before, after)
        self.assertGreater(rate, 0.0)
        self.assertLess(rate, 1.0)

    def test_korean_input_works(self) -> None:
        rate = self.m.change_rate(
            "이 문제에 있어서 중요한 것은 속도이다.", "이 문제에서 중요한 건 속도다."
        )
        self.assertGreater(rate, 0.0)
        self.assertLess(rate, 1.0)

    def test_thresholds_exported(self) -> None:
        self.assertEqual(self.m.CHANGE_RATE_WARN, 0.30)
        self.assertEqual(self.m.CHANGE_RATE_ABORT, 0.50)

    def test_ignore_markup_strips_structure(self) -> None:
        """마크업만 다른 두 글의 변경률은 무시 모드에서 0 이다."""
        before = "# 제목\n\n본문 한 줄."
        after = "## 제목\n\n본문 한 줄."
        self.assertEqual(self.m.change_rate(before, after, ignore_markup=True), 0.0)

    def test_no_korean_skill_dependency(self) -> None:
        """한국어 스킬 디렉터리가 sys.path 에 없어도 import 된다."""
        code = (
            "import importlib.util, sys;"
            f"spec = importlib.util.spec_from_file_location('m', {_CORE!r});"
            "m = importlib.util.module_from_spec(spec);"
            "spec.loader.exec_module(m);"
            "print(m.change_rate('a b c', 'a b d'))"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class MetricsV2BackCompatTests(unittest.TestCase):
    """기존 import 경로가 그대로 살아 있어야 한다."""

    def test_metrics_v2_still_exports(self) -> None:
        refs = os.path.join(_ROOT, "skills", "humanize-korean", "references")
        if refs not in sys.path:
            sys.path.insert(0, refs)
        import metrics_v2  # noqa: PLC0415

        self.assertEqual(metrics_v2.CHANGE_RATE_WARN, 0.30)
        self.assertEqual(metrics_v2.CHANGE_RATE_ABORT, 0.50)
        self.assertEqual(metrics_v2.change_rate("가나다", "가나다"), 0.0)


if __name__ == "__main__":
    unittest.main()
