"""humanize_runner 센티넬 파싱 — LLM 없이 도는 단위 테스트."""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import humanize_runner as hr  # noqa: E402


class SentinelTests(unittest.TestCase):
    def _parse(self, out: str) -> str | None:
        m = hr._SENTINEL.search(out)
        return m.group(1).strip() if m else None

    def test_exact_sentinel(self):
        self.assertEqual(self._parse("설명\n<<<H>>>\n본문이다.\n<<</H>>>\n끝"), "본문이다.")

    def test_short_closing_sentinel_seen_in_live_runs(self):
        # 실측: 모델이 닫는 표지를 `<</H>>>`로 썼다 — 본문은 멀쩡하다
        self.assertEqual(self._parse("<<<H>>>\n아 오늘 회의 길었다.\n<</H>>>\n"), "아 오늘 회의 길었다.")
        self.assertEqual(self._parse("<<<H>>>본문<<</H>>"), "본문")

    def test_no_stray_bracket_in_body(self):
        self.assertEqual(self._parse("<<<H>>>본문<<</H>>>"), "본문")

    def test_missing_closing_sentinel_still_fails(self):
        self.assertIsNone(self._parse("<<<H>>>\n본문만 있고 닫는 표지가 없다."))
        self.assertIsNone(self._parse("본문만 있다."))


class GatedRunTests(unittest.TestCase):
    """Phase 2.5 강제 중단 분기 흉내 — LLM 대신 가짜 호출로 분기만 검증한다."""

    def setUp(self):
        self._orig = hr.run_humanize
        self.calls = []

    def tearDown(self):
        hr.run_humanize = self._orig

    def _fake(self, outputs):
        def fake(text, *, strict=False, timeout=300, model=None, rollback=False):
            self.calls.append(rollback)
            return outputs[len(self.calls) - 1]
        hr.run_humanize = fake

    def test_no_rollback_under_abort_threshold(self):
        src = "첫째 문장은 그대로 둔다. 둘째 문장도 거의 그대로다."
        self._fake(["첫째 문장은 그대로 둔다. 둘째 문장도 거의 같다."])
        out, rolled = hr.run_humanize_gated(src)
        self.assertFalse(rolled)
        self.assertEqual(self.calls, [False])

    def test_rollback_once_when_over_abort_threshold(self):
        src = "첫째 문장은 그대로 둔다. 둘째 문장도 거의 그대로다."
        self._fake(["완전히 다른 글이 나왔고 원문과 닮은 데가 하나도 없다.", "첫째 문장은 그대로 둔다. 둘째 문장도 거의 같다."])
        out, rolled = hr.run_humanize_gated(src)
        self.assertTrue(rolled)
        self.assertEqual(self.calls, [False, True])  # 두 번째 호출만 롤백 지시
        self.assertTrue(out.startswith("첫째 문장은"))

    def test_rollback_prompt_carries_no_fixture_answers(self):
        p = hr._prompt("본문", strict=False, rollback=True)
        self.assertIn("50%", p)  # 스킬 전역 상수(철칙 #4)만 — 픽스처별 상한·보호 토큰은 없다
        self.assertNotIn("protected", p)


if __name__ == "__main__":
    unittest.main()
