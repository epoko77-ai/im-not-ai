"""core/underedit.py — 과소윤문 게이트.

실측 근거(2026-09-02, n=4): 스킬 윤문 4회 중 1회가 변경률 0.4% 로 사실상
아무것도 하지 않았다 — 분산 7.04 → 7.00, 장문율 0.00% 그대로. 라우터가
standard(고칠 게 있다)로 판정했는데 티가 남았고, 게이트는 exit 0 을 냈다.

**기존 게이트는 한쪽만 본다.** 변경률(철칙 #4)과 역주입(철칙 #6)은 둘 다
'너무 많이 했다'를 잡는다. '너무 적게 했다'는 아무도 안 봤다.

같은 실측의 성공 회차는 분산 8.59·9.22·10.44 (+22%~+48%) 였다. 실패 회차는
-0.6%. 임계 +5% 는 그 사이를 가른다 — n=4 의 잠정값이므로 근거 등급 E3.
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
_MOD = os.path.join(_ROOT, "core", "underedit.py")

# 실측 회차를 재현하는 합성 텍스트.
UNIFORM = " ".join(f"Sentence number {i} sits here plainly." for i in range(1, 13))
# 같은 내용을 짧은 문장 + 긴 문장으로 재배치 (분산 상승)
VARIED = (
    "It sits. "
    + " ".join(f"Sentence number {i} sits here plainly." for i in range(1, 9))
    + " And then a much longer sentence arrives, one that keeps going past the "
    "point where the reader expects it to stop, gathering clauses as it goes."
)


def _load():
    spec = importlib.util.spec_from_file_location("_underedit", _MOD)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class UnderEditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(os.path.isfile(_MOD), f"없다: {_MOD}")
        self.m = _load()

    def _check(self, before, after, hint="standard"):
        return self.m.check_underedit(
            before, after, route_hint=hint, unit="tokens", long_threshold=35
        )

    def test_no_change_at_all_fails(self) -> None:
        out = self._check(UNIFORM, UNIFORM)
        self.assertTrue(out["failed"], out)
        self.assertEqual(out["improved"], {})

    def test_real_improvement_passes(self) -> None:
        out = self._check(UNIFORM, VARIED)
        self.assertFalse(out["failed"], out)
        self.assertIn("dispersion", out["improved"])

    def test_light_route_is_skipped(self) -> None:
        """light 는 '고칠 게 없다'는 판정이므로 과소윤문을 묻지 않는다."""
        out = self._check(UNIFORM, UNIFORM, hint="light")
        self.assertFalse(out["failed"])
        self.assertTrue(out["skipped"])

    def test_heavy_route_is_checked(self) -> None:
        out = self._check(UNIFORM, UNIFORM, hint="heavy")
        self.assertTrue(out["failed"])
        self.assertFalse(out["skipped"])

    def test_tiny_dispersion_move_is_not_enough(self) -> None:
        """7.04 → 7.00 같은 잡음은 개선이 아니다 (실측 실패 회차)."""
        before = UNIFORM
        after = UNIFORM.replace("plainly.", "plainly here.", 1)
        out = self._check(before, after)
        self.assertTrue(out["failed"], out)

    def test_reports_all_signals(self) -> None:
        out = self._check(UNIFORM, VARIED)
        for k in ("dispersion", "long_sentence_rate", "comma_inclusion_rate"):
            self.assertIn(k, out["signals"])
            self.assertEqual(len(out["signals"][k]), 2)


class UnderEditCliTests(unittest.TestCase):
    def _run(self, before, after, hint="standard", lang="en"):
        with tempfile.TemporaryDirectory() as td:
            b, a = os.path.join(td, "b.txt"), os.path.join(td, "a.txt")
            for p, t in ((b, before), (a, after)):
                with open(p, "w", encoding="utf-8") as f:
                    f.write(t)
            return subprocess.run(
                [sys.executable, _MOD, "--before", b, "--after", a,
                 "--lang", lang, "--route-hint", hint],
                capture_output=True, text=True, timeout=60,
            )

    def test_underedit_exits_one(self) -> None:
        r = self._run(UNIFORM, UNIFORM)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("과소윤문", r.stdout)

    def test_improvement_exits_zero(self) -> None:
        r = self._run(UNIFORM, VARIED)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_light_exits_zero(self) -> None:
        r = self._run(UNIFORM, UNIFORM, hint="light")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_missing_file_exits_three(self) -> None:
        r = subprocess.run(
            [sys.executable, _MOD, "--before", "/nope/a", "--after", "/nope/b",
             "--route-hint", "standard"],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(r.returncode, 3)


class ValidatedSignalTests(unittest.TestCase):
    """장르에서 검증된 신호로 판정한다.

    실측 2026-09-05: 이 게이트가 변경률 0.5% 짜리 영어 윤문을 통과시켰다 —
    렉시콘 단어 하나가 빠진 것을 개선으로 쳤고, 정작 그 장르에서 판별력이
    확인된 신호(tricolon·쉼표 절)는 보지 않았다.
    """

    def setUp(self) -> None:
        self.m = _load()

    def test_blog_genre_carries_validated_signals(self) -> None:
        got = self.m._en_validated("blog")
        self.assertIn("tricolon(EN-3)", got)
        self.assertIn("comma_segment_length", got)

    def test_abstract_genre_has_none(self) -> None:
        self.assertIsNone(self.m._en_validated("abstract"))

    def test_tricolon_drop_counts_as_improvement(self) -> None:
        before = "We shipped fast, learned, and adjusted. It worked."
        after = "We shipped fast and learned. It worked."
        out = self.m.check_underedit(
            before, after, route_hint="standard", unit="tokens",
            validated=self.m._en_validated("blog"),
        )
        self.assertIn("tricolon(EN-3)", out["improved"])
        self.assertFalse(out["failed"])

    def test_noise_level_move_is_not_improvement(self) -> None:
        """연속 지표의 미동(+0.11 급)은 개선이 아니다 — 실측에서 통과를 만들었다."""
        fn, want, min_delta = self.m._en_validated("blog")["comma_segment_length"]
        self.assertEqual(want, "up")
        self.assertGreaterEqual(min_delta, 0.3)


if __name__ == "__main__":
    unittest.main()
