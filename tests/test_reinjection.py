"""core/reinjection.py — G3 역주입 게이트.

근거: 스파이크 윤문에서 목표 지표는 전부 0 으로 내려갔는데 em dash 가
2→5(9.33/1k)로 늘었다. 발표된 Claude Opus 4.6 = 9.09/1k 와 거의 일치 —
윤문 콜이 자기 모델의 개인어를 심은 것이다. 한국어에서도 D-9 가 '결국' 을
역주입해 2→4 로 늘었던 같은 실패 모드다.

밀도가 아니라 **원시 건수**로 판정한다 — 스파이크에서 I-4 3.42→3.73 의
상승은 역주입이 아니라 본문이 짧아진 artifact 였다(건수 2→2 불변).
"""
from __future__ import annotations

import importlib.util
import os
import re
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_MOD = os.path.join(_ROOT, "core", "reinjection.py")

COUNTERS = {
    "em_dash": lambda t: len(re.findall(r"—", t)),
    "deontic": lambda t: len(re.findall(r"\b(?:must|should|need to)\b", t, re.I)),
}


def _load():
    spec = importlib.util.spec_from_file_location("_reinjection", _MOD)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class ReinjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(os.path.isfile(_MOD), f"없다: {_MOD}")
        self.m = _load()

    def _check(self, before, after):
        return self.m.check_reinjection(
            before, after, COUNTERS, unit="tokens", long_threshold=35
        )

    def test_spike_case_is_caught(self) -> None:
        """실제 스파이크 사례 — em dash 2 → 5."""
        before = "One thing. Two thing—here. Three—here."
        after = "One thing—joined. Two—here. Three—here. Four—more. Five—last."
        out = self._check(before, after)
        self.assertTrue(out["failed"])
        self.assertIn("em_dash", out["risen"])
        self.assertEqual(out["risen"]["em_dash"], (2, 5))
        self.assertIn("em_dash 2→5", out["note"])

    def test_removal_only_passes(self) -> None:
        before = "It must be done—now. We should go—soon."
        after = "Do it now. Go soon."
        out = self._check(before, after)
        self.assertFalse(out["failed"], out)

    def test_unchanged_counts_pass(self) -> None:
        out = self._check("A—b. Must go.", "A—b. Must go.")
        self.assertFalse(out["failed"])

    def test_shorter_text_with_same_raw_count_passes(self) -> None:
        """분모 축소로 밀도만 오르는 경우는 역주입이 아니다."""
        before = "Must go. " + "Filler sentence here. " * 20
        after = "Must go. Filler sentence here."
        out = self._check(before, after)
        self.assertFalse(out["failed"], out)

    def test_dispersion_is_reported_not_failed(self) -> None:
        """분산 변화는 실패 판정이 아니라 보고 항목이다."""
        out = self._check("A b. C d. E f.", "A b. C d e f g h i j k l m n o p.")
        self.assertIn("dispersion", out)
        self.assertEqual(len(out["dispersion"]), 2)
        self.assertFalse(out["failed"])

    def test_korean_works_too(self) -> None:
        """언어 무관 — ko D-9 의 '결국' 역주입도 같은 함수로 잡힌다."""
        counters = {"결국": lambda t: t.count("결국")}
        out = self.m.check_reinjection(
            "성장은 둔화됐다. 투자도 줄었다.",
            "결국 성장은 둔화됐다. 결국 투자도 줄었다.",
            counters,
            unit="chars",
            long_threshold=100,
        )
        self.assertTrue(out["failed"])
        self.assertEqual(out["risen"]["결국"], (0, 2))

    def test_empty_counters_never_fails(self) -> None:
        out = self.m.check_reinjection("a", "b", {})
        self.assertFalse(out["failed"])


if __name__ == "__main__":
    unittest.main()


class ReinjectionCliTests(unittest.TestCase):
    """CLI — 스킬이 Bash 로 부를 수 있어야 게이트가 실제로 돈다.

    metrics_universal 이 R1 에서 '테스트만 부르는 라이브러리'였던 것과 같은
    함정을 피한다. 게이트는 호출되지 않으면 없는 것과 같다.
    """

    import subprocess as _sp
    import sys as _sys

    def _run(self, before: str, after: str, lang: str = "en"):
        import subprocess
        import sys
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            b = os.path.join(td, "b.txt")
            a = os.path.join(td, "a.txt")
            with open(b, "w", encoding="utf-8") as f:
                f.write(before)
            with open(a, "w", encoding="utf-8") as f:
                f.write(after)
            return subprocess.run(
                [sys.executable, _MOD, "--before", b, "--after", a, "--lang", lang],
                capture_output=True,
                text=True,
                timeout=60,
            )

    def test_clean_rewrite_exits_zero(self) -> None:
        r = self._run(
            "It must be done—now. We should go—soon.", "Do it now. Go soon."
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("역주입 없음", r.stdout)

    def test_reinjection_exits_one(self) -> None:
        r = self._run(
            "One thing. Two thing—here.",
            "One thing—joined. Two—here. Three—more.",
        )
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("em_dash", r.stdout)

    def test_korean_lang_uses_korean_counters(self) -> None:
        r = self._run(
            "성장은 둔화됐다. 투자도 줄었다.",
            "결국 성장은 둔화됐다. 결국 투자도 줄었다.",
            lang="ko",
        )
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("결국", r.stdout)

    def test_missing_file_exits_three(self) -> None:
        import subprocess
        import sys

        r = subprocess.run(
            [sys.executable, _MOD, "--before", "/nope/a", "--after", "/nope/b"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
